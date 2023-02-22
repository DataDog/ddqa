# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import typing

from rich.markdown import Markdown as RichMarkdown
from rich.markup import escape
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Header, Label, Markdown, Switch

from ddqa.utils.network import ResponsiveNetworkClient
from ddqa.utils.widgets import switch_to_widget
from ddqa.widgets.input import LabeledSwitch
from ddqa.widgets.layout import LabeledBox
from ddqa.widgets.static import Placeholder

if typing.TYPE_CHECKING:
    from ddqa.models.config.repo import RepoConfig
    from ddqa.models.github import TestCandidate


class Candidate:
    def __init__(self, candidate: TestCandidate, repo_config: RepoConfig):
        self.data = candidate

        labels = {label.name for label in candidate.labels}
        ignored = labels.intersection(repo_config.ignored_labels)
        self.assignments: dict[str, bool] = {
            team_name: False if ignored else len(labels.intersection(team_data.github_labels)) > 0
            for team_name, team_data in repo_config.teams.items()
        }

    @property
    def assigned(self) -> bool:
        return any(self.assignments.values())

    @property
    def status_indicator(self) -> str:
        return '✓' if self.assigned else ''


class CandidateListing(DataTable):
    def __init__(self, sidebar: CandidateSidebar, previous_ref: str, current_ref: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.sidebar = sidebar
        self.previous_ref = previous_ref
        self.current_ref = current_ref

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

        self.call_after_refresh(lambda: self.app.run_in_background(self.__on_mount()))

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
        ignored = 0
        processed_pr_numbers = set()

        self.app.print(f'Beginning to load candidates for commits for {self.previous_ref}..{self.current_ref}')
        self.sidebar.status.update('Loading...')
        async with ResponsiveNetworkClient(self.sidebar.status) as client:
            for i, commit in enumerate(commits):
                model = await self.app.github.get_candidate(client, commit)
                if model.id.isdigit():
                    if model.id in processed_pr_numbers:
                        ignored += 1
                        continue

                    processed_pr_numbers.add(model.id)
                    self.app.print(f'Processing pull request #{model.id}')
                else:
                    self.app.print(f'Processing commit {model.id[:7]}')

                index = i - ignored
                candidate = Candidate(model, self.app.repo)
                self.candidates[index] = candidate

                shown_index = str(index + 1)
                self.sidebar.label.update(f' {shown_index} / {total - ignored} ')
                self.add_row(candidate.status_indicator, escape(model.title), key=str(index))
                num_candidates += 1

        if not num_candidates:
            self.app.print('No candidates found')
            self.sidebar.label.update(' No candidates ')
            self.sidebar.status.update(f'{self.previous_ref} -> {self.current_ref}')
            return

        self.app.print('Finished processing candidates')
        self.sidebar.update_assignment_status()

    async def create(self) -> None:
        import secrets

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

        self.app.print(f'Candidates ready for creation: {total}')
        self.sidebar.status.update('Creating...')
        async with ResponsiveNetworkClient(self.sidebar.status) as client:
            for index, candidate in self.candidates.items():
                if candidate.data.id.isdigit():
                    self.app.print(f'Creating issue for pull request #{candidate.data.id}')
                else:
                    self.app.print(f'Creating issue for commit {candidate.data.id[:7]}')

                self.sidebar.label.update(f' {index + 1} / {total} ')

                assignments: dict[str, str] = {}
                for team, assigned in candidate.assignments.items():
                    if not assigned:
                        continue

                    team_members = await self.app.github.get_team_members(client, self.app.repo.teams[team].github_team)
                    team_members.discard(candidate.data.user)
                    for reviewer in candidate.data.reviewers:
                        team_members.discard(reviewer.name)

                    assignee = secrets.choice(sorted(team_members)) if team_members else ''
                    assignments[team] = assignee

                try:
                    created_issues = await self.app.jira.create_issues(client, candidate.data, assignments)
                except Exception as e:
                    self.sidebar.status.update(escape(str(e)))
                    return

                result = DataTable(classes='assignment-result')
                result.add_columns('Team', 'Assignee', 'Issue')
                for assignee, (team, issue_url) in zip(assignments.values(), created_issues.items(), strict=True):
                    result.add_row(
                        team,
                        f'[link=https://github.com/{assignee}]{assignee}[/link]' if assignee else '',
                        f'[link={issue_url}]{issue_url.rpartition("/")[2]}[/link]',
                    )

                await self.app.query_one(CandidateRendering).add_assignment_result(
                    candidate.data.id, Horizontal(result, classes='assignment-result-box'), update=not display_updated
                )
                self.update_cell(str(index), 'status', len(created_issues), update_width=True)

                if not display_updated:
                    display_updated = True

        self.app.print('Finished creating issues')
        self.sidebar.status.update('Finished')
        self.sidebar.button.disabled = False


class CandidateSidebar(LabeledBox):
    DEFAULT_CSS = """
    #sidebar-status {
        height: 1fr;
        border-bottom: dashed #632CA6;
    }

    #sidebar-listing {
        height: 9fr;
    }

    #sidebar-button {
        width: 100%;
        offset-y: 1;
    }

    #sidebar-button-container {
        height: 1fr;
    }
    """

    def __init__(self, previous_ref: str, current_ref: str):
        self.__status = Label()
        self.__listing = CandidateListing(self, previous_ref, current_ref)
        self.__button = Button('Create', variant='primary', disabled=True, id='sidebar-button')

        super().__init__(
            '',
            Container(self.__status, id='sidebar-status'),
            Container(self.__listing, id='sidebar-listing'),
            Container(self.__button, id='sidebar-button-container'),
        )

    @property
    def status(self) -> Label:
        return self.__status

    @property
    def listing(self) -> CandidateListing:
        return self.__listing

    @property
    def button(self) -> Button:
        return self.__button

    def update_assignment_status(self) -> None:
        assigned = self.listing.assigned
        self.status.update('Ready for creation' if assigned else 'No candidates assigned')
        self.button.disabled = not assigned

    async def on_button_pressed(self, _event: Button.Pressed) -> None:
        if str(self.button.label) == 'Create':
            self.button.disabled = True
            self.button.label = 'Exit'

            for widget in self.app.query_one('#candidate-assignments').children:
                await widget.remove()

            self.app.run_in_background(self.listing.create())
        else:
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
    }
    """

    def __init__(self) -> None:
        self.__title = Label()
        self.__labels = Label()
        self.__body = Container(Placeholder(width_factor=2.5), id='candidate-body')
        self.__body_renderings: dict[str, Markdown] = {}
        self.__candidate_assignments = Vertical(id='candidate-assignments')
        self.__assignment_results: dict[str, DataTable] = {}

        super().__init__(
            '',
            Container(self.__title, self.__labels, id='candidate-info'),
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
    def candidate_assignments(self) -> Vertical:
        return self.__candidate_assignments

    async def on_mount(self) -> None:
        teams = list(self.app.repo.teams)
        width = 3
        for i in range(0, len(teams), width):
            await self.candidate_assignments.mount(
                Horizontal(
                    *[LabeledSwitch(label=team, classes='assignment-box') for team in teams[i : i + width]],
                    classes='assignment-row',
                )
            )

    async def render_candidate(self, candidate: Candidate):
        data = candidate.data
        self.label.update(
            f' [link={data.url}]PR {data.id}[/link] '
            if data.id.isdigit()
            else f' [link={data.url}]Commit {data.id[:7]}[/link] '
        )
        self.title.update(RichMarkdown(data.title))
        self.labels.update(' '.join(f'[black on #{label.color}]{label.name}[/]' for label in data.labels))

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

    async def add_assignment_result(self, candidate_id: str, table: DataTable, *, update: bool = False) -> None:
        self.__assignment_results[candidate_id] = table
        if update:
            await switch_to_widget(table, self.candidate_assignments)


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

    def __init__(self, previous_ref: str, current_ref: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.previous_ref = previous_ref
        self.current_ref = current_ref

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Container(CandidateSidebar(self.previous_ref, self.current_ref), id='screen-create-sidebar'),
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
        candidate.assignments[str(event.input.parent.label.render())] = event.value

        sidebar.update_assignment_status()
        listing.update_cell(str(listing.cursor_row), 'status', candidate.status_indicator)
