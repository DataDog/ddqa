# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import typing
from collections import defaultdict

from rich.markdown import Markdown as RichMarkdown
from rich.markup import escape
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, HorizontalScroll, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, DataTable, Header, Label, Markdown, Switch
from textual.worker import Worker, WorkerState

from ddqa.cache.github import GitHubCache
from ddqa.models.jira import JiraConfig
from ddqa.utils.network import ResponsiveNetworkClient
from ddqa.utils.widgets import switch_to_widget
from ddqa.widgets.input import LabeledSwitch
from ddqa.widgets.layout import LabeledBox
from ddqa.widgets.static import Placeholder

if typing.TYPE_CHECKING:
    from ddqa.models.config.repo import RepoConfig
    from ddqa.models.config.team import TeamConfig
    from ddqa.models.github import TestCandidate


class Candidate:
    def __init__(self, candidate: TestCandidate, repo_config: RepoConfig, github_cache: GitHubCache | None = None):
        self.data = candidate
        self.__cache = github_cache

        labels = {label.name for label in candidate.labels}
        ignored = labels.intersection(repo_config.ignored_labels)
        self.assignments: dict[str, bool] = {}

        for team_name, team_data in repo_config.teams.items():
            if candidate.assigned_teams and team_name in candidate.assigned_teams:
                assigned = True
            elif ignored:
                assigned = False
            else:
                assigned = len(labels.intersection(team_data.github_labels)) > 0

            self.assign_team(team_name, assigned=assigned)

    @property
    def assigned(self) -> bool:
        return any(self.assignments.values())

    @property
    def status_indicator(self) -> str:
        return '✓' if self.assigned else ''

    def assign_team(self, team_name: str, *, assigned: bool):
        self.assignments[team_name] = assigned

        if self.__cache:
            if assigned:
                self.data.assigned_teams.add(team_name)
            else:
                self.data.assigned_teams.discard(team_name)

            self.__cache.cache_candidate_data(self.data.id, self.data.model_dump())


class CandidateListing(DataTable):
    DEFAULT_CSS = """
    CandidateListing {
        height: 1fr;
        max-height: 1fr;
    }
    """

    def __init__(
        self,
        sidebar: CandidateSidebar,
        previous_ref: str,
        current_ref: str,
        labels: tuple[str, ...],
        pr_labels: list[str] | None = None,
        auto_mode: bool = False,  # noqa
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.sidebar = sidebar
        self.previous_ref = previous_ref
        self.current_ref = current_ref
        self.labels = labels
        self.pr_labels = pr_labels
        self.auto_mode = auto_mode

        self.candidates: dict[int, Candidate] = {}

    @property
    def assigned(self) -> bool:
        return any(candidate.assigned for candidate in self.candidates.values())

    def on_mount(self) -> None:
        super().on_mount()

        self.add_column('_', key='status')
        self.add_column('_', key='title')
        self.show_header = False
        self.cursor_type = 'row'
        self.focus()

        self.run_worker(self.__on_mount())

    async def __on_mount(self) -> None:
        try:
            commits = self.app.git.get_mutually_exclusive_commits(self.previous_ref, self.current_ref)
        except Exception as e:
            self.app.print(f'Failed to get commits for {self.previous_ref}..{self.current_ref}: {e}')
            self.sidebar.label.update(' error ')
            self.sidebar.status.update(escape(str(e)))
            return

        total = len(commits)
        num_candidates = 0

        self.app.print(f'Beginning to load candidates for commits for {self.previous_ref}..{self.current_ref}')
        self.sidebar.status.loading()

        async with ResponsiveNetworkClient(self.sidebar.status) as client:
            async for model, index, ignored in self.app.github.get_candidates(
                client,
                commits,
                self.app.repo.ignored_labels,
                self.pr_labels,
            ):
                shown_index = str(index + 1)
                self.sidebar.label.update(f' {shown_index} / {total} ({ignored} ignored)')

                if model is not None:
                    self.app.print(f'Processing {model.long_display()}')

                    candidate = Candidate(model, self.app.repo, self.app.github.cache)
                    self.candidates[num_candidates] = candidate
                    self.add_row(candidate.status_indicator, escape(model.title.strip()), key=str(num_candidates))
                    num_candidates += 1

        if not num_candidates:
            self.app.print('No candidates found')
            self.sidebar.label.update(' No candidates ')
            self.sidebar.status.update(f'{self.previous_ref} -> {self.current_ref}')
            return

        self.app.print('Finished processing candidates')
        self.sidebar.update_assignment_status()

    async def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state not in (WorkerState.PENDING, WorkerState.RUNNING) and self.auto_mode:
            await self.sidebar.create_cards_or_exit()

    async def create(self) -> None:
        candidates: dict[int, Candidate] = {}
        for candidate in self.candidates.values():
            if candidate.assigned:
                candidates[len(candidates)] = candidate

        self.candidates.clear()
        self.candidates.update(candidates)
        total = len(self.candidates)

        self.clear()

        # Reset rows
        for index, candidate in self.candidates.items():
            self.add_row('', escape(candidate.data.title), key=str(index))

        self.focus()
        display_updated = False

        assignment_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

        self.app.print(f'Candidates ready for creation: {total}')
        self.sidebar.status.update('Creating...')
        async with ResponsiveNetworkClient(self.sidebar.status) as client:
            for index, candidate in list(self.candidates.items()):
                self.app.print(f'Creating issue for {candidate.data.long_display()}')

                assignments: dict[str, str | None] = {}
                for team, assigned in candidate.assignments.items():
                    if not assigned:
                        continue

                    team_members = await self.app.github.get_team_members(client, self.app.repo.teams[team].github_team)

                    assignee = get_assignee(
                        team_members,
                        self.app.jira.config,
                        candidate.data,
                        self.app.repo.teams[team],
                        assignment_counts,
                    )

                    if assignee:
                        assignment_counts[self.app.repo.teams[team].github_team][assignee] += 1

                    assignments[team] = assignee
                try:
                    created_issues = await self.app.jira.create_issues(client, candidate.data, self.labels, assignments)
                except Exception as e:
                    self.sidebar.status.update(escape(str(e)))
                    return

                self.sidebar.label.update(f' {index + 1} / {total} ')

                result = DataTable(classes='assignment-result')
                result.add_columns('Team', 'Assignee', 'Issue')
                for assignee, (team, issue_url) in zip(assignments.values(), created_issues.items(), strict=True):
                    github_user = (
                        self.app.jira.config.get_github_user_id_from_jira_user_id(assignee) if assignee else None
                    )
                    result.add_row(
                        team,
                        f'[link=https://github.com/{github_user}]{github_user}[/link]' if github_user else '',
                        f'[link={issue_url}]{issue_url.rpartition("/")[2]}[/link]',
                    )

                await self.app.query_one(CandidateRendering).add_assignment_result(
                    candidate.data.id,
                    HorizontalScroll(result, classes='assignment-result-box'),
                    update=not display_updated,
                )
                self.update_cell(str(index), 'status', len(created_issues), update_width=True)

                if not display_updated:
                    display_updated = True

        self.app.print('Finished creating issues')
        self.sidebar.status.update('Finished')
        self.sidebar.button.disabled = False

        if self.sidebar.auto_mode:
            self.app.exit()


class StatusLabel(Label):
    def loading(self) -> None:
        self.update('Loading...')

    def is_loading(self) -> bool:
        text = str(self.render())
        return text == 'Loading...' or text.startswith('Retrying in')


class CandidateSidebar(LabeledBox):
    DEFAULT_CSS = """
    #sidebar-status {
        height: auto;
        border-bottom: dashed #632CA6;
        overflow: auto;
    }

    #sidebar-listing {
        height: 1fr;
    }

    #sidebar-button {
        border: none;
        width: 100%;
    }

    #sidebar-button-container {
        height: auto;
    }
    """

    def __init__(
        self,
        previous_ref: str,
        current_ref: str,
        labels: tuple[str, ...],
        pr_labels: list[str] | None = None,
        *,
        auto_mode: bool = False,
    ):
        self.__status = StatusLabel()
        self.__listing = CandidateListing(self, previous_ref, current_ref, labels, pr_labels, auto_mode=auto_mode)
        self.__button = Button('Create', variant='primary', disabled=True, id='sidebar-button')
        self.__auto_mode = auto_mode

        super().__init__(
            '',
            Container(self.__status, id='sidebar-status'),
            Container(self.__listing, id='sidebar-listing'),
            Container(self.__button, id='sidebar-button-container'),
        )

    @property
    def status(self) -> StatusLabel:
        return self.__status

    @property
    def listing(self) -> CandidateListing:
        return self.__listing

    @property
    def button(self) -> Button:
        return self.__button

    @property
    def auto_mode(self) -> bool:
        return self.__auto_mode

    def update_assignment_status(self, *, override_is_loading_flag: bool = True) -> None:
        assigned = 0

        for candidate in self.listing.candidates.values():
            if candidate.assigned:
                assigned += 1

        self.button.disabled = not assigned

        if not override_is_loading_flag and self.status.is_loading():
            return

        self.label.update(f' {assigned} / {len(self.listing.candidates)} ')
        self.status.update('Ready for creation' if assigned else 'No candidates assigned')

    async def on_button_pressed(self, _event: Button.Pressed) -> None:
        await self.create_cards_or_exit()

    async def create_cards_or_exit(self) -> None:
        if str(self.button.label) == 'Create':
            self.button.disabled = True
            self.button.label = 'Exit'

            for widget in self.app.query_one('#candidate-assignments').children:
                await widget.remove()

            self.run_worker(self.listing.create())
        else:
            self.app.exit()

    async def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state not in (WorkerState.PENDING, WorkerState.RUNNING) and self.auto_mode:
            self.app.exit()


class CandidateRendering(LabeledBox):
    DEFAULT_CSS = """
    #candidate-info {
        layout: grid;
        grid-size: 2 1;
        height: 1fr;
        border-bottom: dashed #632CA6;
    }

    #candidate-body {
        height: 9fr;
        overflow-y: auto;
    }

    #candidate-assignments {
        height: 2fr;
        border-top: dashed #632CA6;
    }

    .assignment-row {
        width: 100%;
        height: auto;
    }

    .assignment-box {
        width: 1fr;
    }

    .assignment-result-box {
        align: center middle;
    }

    .assignment-result {
        width: auto;
        max-height: 1fr;
    }
    """

    def __init__(self) -> None:
        self.__title = Label()
        self.__labels = Label()
        self.__body = Container(Placeholder(width_factor=2.5), id='candidate-body')
        self.__body_renderings: dict[str, Markdown] = {}
        self.__candidate_assignments = VerticalScroll(id='candidate-assignments')
        self.__assignment_results: dict[str, HorizontalScroll] = {}

        super().__init__(
            '',
            Container(self.__title, HorizontalScroll(self.__labels), id='candidate-info'),
            self.__body,
            self.__candidate_assignments,
        )

    @property
    def title(self) -> Label:
        return self.__title

    @property
    def body(self) -> Container:
        return self.__body

    @property
    def labels(self) -> Label:
        return self.__labels

    @property
    def candidate_assignments(self) -> VerticalScroll:
        return self.__candidate_assignments

    async def on_mount(self) -> None:
        teams = list(self.app.repo.teams)
        width = 3
        for i in range(0, len(teams), width):
            await self.candidate_assignments.mount(
                HorizontalScroll(
                    *[LabeledSwitch(label=team, classes='assignment-box') for team in teams[i : i + width]],
                    classes='assignment-row',
                )
            )

    async def render_candidate(self, candidate: Candidate):
        data = candidate.data
        label = f' [link={data.url}]{data.short_display()}[/link] '

        if data.user:
            label += f'by [link={data.user_url}]{escape(data.user)}[/link] '

        self.label.update(label)
        self.title.update(RichMarkdown(data.title))
        self.title.tooltip = data.title

        labels = ' '.join(f'[black on #{label.color}]{label.name}[/]' for label in data.labels)
        self.labels.update(labels)
        self.labels.tooltip = labels or None

        if data.id in self.__body_renderings:
            body_rendering = self.__body_renderings[data.id]
        else:
            body_rendering = Markdown(data.body)
            self.__body_renderings[data.id] = body_rendering

        await switch_to_widget(body_rendering, self.body)

        if data.id in self.__assignment_results:
            await switch_to_widget(self.__assignment_results[data.id], self.candidate_assignments)
        else:
            self.candidate_assignments.scroll_home(animate=False)
            for widget in self.query(LabeledSwitch).results():
                widget.switch.value = candidate.assignments[str(widget.label.render())]

    async def add_assignment_result(
        self, candidate_id: str, table_box: HorizontalScroll, *, update: bool = False
    ) -> None:
        self.__assignment_results[candidate_id] = table_box
        if update:
            await switch_to_widget(table_box, self.candidate_assignments)


class CreateScreen(Screen):
    BINDINGS = [
        Binding('ctrl+c', 'quit', 'Quit', show=False, priority=True),
        Binding('tab', 'focus_next', 'Focus Next', show=False),
        Binding('shift+tab', 'focus_previous', 'Focus Previous', show=False),
    ]
    DEFAULT_CSS = """
    #screen-create {
        layout: grid;
        grid-size: 2;
        grid-columns: 1fr 5fr;
        grid-rows: 1fr;
    }

    #screen-create-sidebar {
        height: 100%;
    }

    #screen-create-rendering {
        height: 100%;
    }
    """

    def __init__(
        self,
        previous_ref: str,
        current_ref: str,
        labels: tuple[str, ...],
        pr_labels: list[str] | None = None,
        *args,
        auto_mode: bool = False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.__previous_ref = previous_ref
        self.__current_ref = current_ref
        self.__labels = labels
        self.__include__labels = pr_labels
        self.__auto_mode = auto_mode

    @property
    def previous_ref(self) -> str:
        return self.__previous_ref

    @property
    def current_ref(self) -> str:
        return self.__current_ref

    @property
    def labels(self) -> tuple[str, ...]:
        return self.__labels

    @property
    def pr_labels(self) -> list[str] | None:
        return self.__include__labels

    @property
    def auto_mode(self) -> bool:
        return self.__auto_mode

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Container(
                CandidateSidebar(
                    self.previous_ref, self.current_ref, self.labels, self.pr_labels, auto_mode=self.__auto_mode
                ),
                id='screen-create-sidebar',
            ),
            Container(CandidateRendering(), id='screen-create-rendering'),
            id='screen-create',
        )

    async def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        listing = self.query_one(CandidateListing)
        content = self.query_one(CandidateRendering)
        await content.render_candidate(listing.candidates[event.cursor_row])

    async def on_switch_changed(self, event: Switch.Changed) -> None:
        listing = self.query_one(CandidateListing)
        sidebar = self.query_one(CandidateSidebar)

        candidate = listing.candidates[listing.cursor_row]
        candidate.assign_team(str(event.switch.parent.label.render()), assigned=event.value)

        sidebar.update_assignment_status(override_is_loading_flag=False)
        listing.update_cell(str(listing.cursor_row), 'status', candidate.status_indicator)


def get_assignee(
    team_members: set[str],
    jira_config: JiraConfig,
    candidate: TestCandidate,
    team: TeamConfig,
    assignment_counts: dict[str, dict[str, int]],
) -> str | None:
    if not team_members:
        return None

    team_members.discard(candidate.user)
    team_members.difference_update(team.exclude_members)
    jira_team_members = jira_config.get_jira_user_ids_from_github_user_ids(team_members)

    counts = assignment_counts[team.github_team]
    if not jira_team_members:
        return jira_config.get_jira_user_id_from_github_user_id(candidate.user)

    reviewers = jira_config.get_jira_user_ids_from_github_user_ids({reviewer.name for reviewer in candidate.reviewers})
    member_keys = {member: (counts[member], member in reviewers) for member in jira_team_members}

    priorities: dict[tuple[int, bool], list[str]] = defaultdict(list)
    for member, key in member_keys.items():
        priorities[key].append(member)

    potential_assignees = priorities[sorted(priorities)[0]]

    import secrets

    return secrets.choice(sorted(potential_assignees))
