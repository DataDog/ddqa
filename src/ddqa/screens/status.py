# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import datetime, timedelta
from decimal import Decimal
from functools import cache, cached_property
from typing import TYPE_CHECKING

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, HorizontalScroll, VerticalScroll
from textual.coordinate import Coordinate
from textual.screen import Screen
from textual.widgets import Button, DataTable, Header, Label, RadioButton, RadioSet, Select

from ddqa.utils.network import ResponsiveNetworkClient
from ddqa.utils.time import format_elapsed_time
from ddqa.widgets.layout import LabeledBox

if TYPE_CHECKING:
    from ddqa.models.jira import JiraIssue

COMPLETION_PRECISION = Decimal('0.00')


class IssueFilter(ABC):
    def __init__(self) -> None:
        self.__issues: dict[str, dict[str, JiraIssue]] = {}

    @property
    def issues(self) -> dict[str, dict[str, JiraIssue]]:
        return self.__issues

    def add(self, filter_key: str, issue: JiraIssue):
        self.issues.setdefault(filter_key, {})[issue.key] = issue

    @abstractmethod
    def update(self, old_issue: JiraIssue, new_issue: JiraIssue):
        pass


class TeamIssueFilter(IssueFilter):
    def update(self, old_issue: JiraIssue, new_issue: JiraIssue):
        for issues in self.issues.values():
            if old_issue.key in issues:
                issues[old_issue.key] = new_issue


class MemberIssueFilter(IssueFilter):
    def update(self, old_issue: JiraIssue, new_issue: JiraIssue):
        for issues in self.issues.values():
            if old_issue.key in issues:
                issues[old_issue.key] = new_issue


class FilterSelect(Select):
    def __init__(self, issue_filter: IssueFilter, css_id: str | None = None):
        self.__issue_filter = issue_filter

        super().__init__(((issue, issue) for issue in sorted(self.__issue_filter.issues)), id=css_id)

    @property
    def issue_filter(self) -> IssueFilter:
        return self.__issue_filter


class FormattedTimeDelta:
    def __init__(self, td: timedelta):
        self.__td = td

    @property
    def td(self) -> timedelta:
        return self.__td

    @cached_property
    def elapsed_time(self) -> str:
        return format_elapsed_time(self.td.total_seconds())

    def __str__(self) -> str:
        return self.elapsed_time

    def __eq__(self, other) -> bool:
        return self.td.__eq__(other.td)

    def __le__(self, other) -> bool:
        return self.td.__le__(other.td)

    def __lt__(self, other) -> bool:
        return self.td.__lt__(other.td)

    def __ge__(self, other) -> bool:
        return self.td.__ge__(other.td)

    def __gt__(self, other) -> bool:
        return self.td.__gt__(other.td)

    def __hash__(self) -> int:
        return self.td.__hash__()

    def __bool__(self) -> bool:
        return self.td.__bool__()


@cache
def get_timedelta(dt: datetime):
    return FormattedTimeDelta(dt - datetime.now(tz=dt.tzinfo))


class StatusChanger(LabeledBox):
    DEFAULT_CSS = """
    #status-choices {
        border: none;
        width: 100%;
        height: 1fr;
        margin-top: 1;
    }

    #status-submission {
        border: none;
        width: 100%;
    }
    """

    def __init__(self, statuses: list[str]) -> None:
        self.__radio_buttons = {status: RadioButton(label=status) for status in statuses}
        self.__radio_set = RadioSet(*self.__radio_buttons.values(), id='status-choices')
        self.__button = Button('Move', variant='primary', id='status-submission')

        super().__init__(' Status ', self.__radio_set, self.__button)

    @property
    def radio_set(self) -> RadioSet:
        return self.__radio_set

    @property
    def radio_buttons(self) -> dict[str, RadioButton]:
        return self.__radio_buttons

    @property
    def button(self) -> Button:
        return self.__button


class StatusTable(DataTable):
    def __init__(self, qa_statuses: list[str]):
        super().__init__()

        self._qa_statuses = qa_statuses
        self.cursor_type = 'row'
        self.show_cursor = False
        self.add_column('Issue')
        self.add_column('Assignee')
        self.add_column('Last update', key='update-time')

    def on_click(self, _event: events.Click) -> None:
        # This makes it so that only a single table looks active at a time, giving it a "focus" effect
        for data_table in self.app.query(StatusTable).results():
            data_table.show_cursor = data_table is self

    def add_issue(self, issue: JiraIssue):
        super().add_row(
            issue.key,
            issue.assignee.name if issue.assignee is not None else '',
            get_timedelta(issue.updated),
            key=issue.key,
        )

    def sort_issues(self):
        super().sort('update-time', reverse=True)


class DoneStatusTable(StatusTable):
    def __init__(self, qa_statuses: list[str]):
        super().__init__(qa_statuses)
        self.add_column('Info')

    def add_issue(self, issue: JiraIssue):
        super().add_row(
            issue.key,
            issue.assignee.name if issue.assignee is not None else '',
            get_timedelta(issue.updated),
            issue.status.name if issue.status.name not in self._qa_statuses else '',
            key=issue.key,
        )


class Status(LabeledBox):
    DEFAULT_CSS = """
    Status {
        width: auto;
    }

    Status Container {
        width: auto;
    }

    Status StatusTable {
        width: auto;
        margin-top: 1;
        scrollbar-gutter: stable;
        max-height: 1fr;
    }
    """

    @staticmethod
    def get_statuses_from_qa_statuses(qa_statuses: list[str]) -> dict[str, Status]:
        statuses = {status: Status(status, qa_statuses) for status in qa_statuses[:-1]}
        statuses[qa_statuses[-1]] = Status(qa_statuses[-1], qa_statuses, DoneStatusTable)
        return statuses

    def __init__(self, name: str, qa_statuses: list[str], status_table_class: type[StatusTable] = StatusTable):
        self.__name = name
        self.__table = status_table_class(qa_statuses)

        super().__init__(f' {self.__name} ', self.__table)

    @property
    def name(self) -> str:
        return self.__name

    @property
    def table(self) -> StatusTable:
        return self.__table

    def add_issue(self, issue: JiraIssue) -> None:
        self.table.add_issue(issue)

    def sort_issues(self) -> None:
        self.table.sort_issues()

    def clear_issues(self) -> None:
        self.table.clear()


class Issues(LabeledBox):
    DEFAULT_CSS = """
    #issues-box {
        layout: grid;
        grid-size: 1 2;
        grid-rows: 1fr 9fr;
    }

    #issue-info {
        height: 100%;
        border-bottom: dashed #632CA6;
    }

    #statuses-box {
        height: 100%;
        width: 100%;
        overflow-x: auto;
    }
    """

    def __init__(self, statuses: Iterable[Status]):
        self.__info = Label()

        super().__init__(
            '',
            Container(
                HorizontalScroll(self.__info, id='issue-info'),
                HorizontalScroll(*statuses, id='statuses-box'),
                id='issues-box',
            ),
        )

    @property
    def info(self) -> Label:
        return self.__info


class OptionsSidebar(LabeledBox):
    DEFAULT_CSS = """
    #sidebar-status {
        height: auto;
        border-bottom: dashed #632CA6;
        overflow: auto;
    }

    #sidebar-options {
        height: 1fr;
    }

    #status-changer {
        height: 1fr;
    }

    .issue-filter {
        height: 5;
    }

    #refresh-button-box {
        height: 5;
    }

    #refresh-submission {
        width: 100%;
    }
    """

    def __init__(self):
        self.__status = Label()
        self.__options = VerticalScroll()

        super().__init__(
            '',
            Container(self.__status, id='sidebar-status'),
            Container(self.__options, id='sidebar-options'),
        )

    @property
    def status(self) -> Label:
        return self.__status

    @property
    def options(self) -> VerticalScroll:
        return self.__options


class StatusScreen(Screen):
    BINDINGS = [
        Binding('ctrl+c', 'quit', 'Quit', show=False, priority=True),
        Binding('tab', 'focus_next', 'Focus Next', show=False),
        Binding('shift+tab', 'focus_previous', 'Focus Previous', show=False),
    ]
    DEFAULT_CSS = """
    #screen-status {
        layout: grid;
        grid-size: 2;
        grid-columns: 1fr 5fr;
        grid-rows: 1fr;
    }

    #screen-status-sidebar {
        height: 100%;
    }

    #screen-status-rendering {
        height: 100%;
    }
    """

    def __init__(self, labels: tuple[str, ...]) -> None:
        super().__init__()

        self.__labels = labels
        self.__current_user_id = ''
        self.__team_filter = TeamIssueFilter()
        self.__member_filter = MemberIssueFilter()
        self.__refresh_button = Button('Refresh', variant='primary', id='refresh-submission')

    @property
    def labels(self) -> tuple[str, ...]:
        return self.__labels

    @property
    def current_user_id(self) -> str:
        return self.__current_user_id

    @property
    def team_filter(self) -> TeamIssueFilter:
        return self.__team_filter

    @property
    def member_filter(self) -> MemberIssueFilter:
        return self.__member_filter

    @property
    def refresh_button(self) -> Button:
        return self.__refresh_button

    @property
    def initial_status(self) -> str:
        return self.app.repo.qa_statuses[0]

    @property
    def final_status(self) -> str:
        return self.app.repo.qa_statuses[-1]

    @cached_property
    def cached_issues(self) -> dict[str, JiraIssue]:
        return {}

    @cached_property
    def statuses(self) -> dict[str, Status]:
        return Status.get_statuses_from_qa_statuses(self.app.repo.qa_statuses)

    @cached_property
    def sidebar(self) -> OptionsSidebar:
        return self.query_one(OptionsSidebar)

    @cached_property
    def issues(self) -> Issues:
        return self.query_one(Issues)

    @cached_property
    def status_changer(self) -> StatusChanger:
        return StatusChanger(self.app.repo.qa_statuses)

    @cached_property
    def team_statuses(self) -> dict[str, dict[str, str]]:
        team_statuses: dict[str, dict[str, str]] = {}

        for team, status_map in self.app.qa_statuses.items():
            team_statuses[team] = {team_status: qa_status for qa_status, team_status in status_map.items()}

        return team_statuses

    @cached_property
    def teams(self) -> dict[tuple[str, str], str]:
        return {(config.jira_project, config.jira_component): team for team, config in self.app.repo.teams.items()}

    def get_team(self, issue: JiraIssue) -> str:
        if not issue.components:
            return self.teams.get((issue.project, ''), '')

        for component in issue.components:
            if (team := self.teams.get((issue.project, component))) is not None:
                return team

        return ''

    def get_qa_status(self, issue: JiraIssue) -> str:
        return self.team_statuses[self.get_team(issue)].get(issue.status.name, self.final_status)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Container(OptionsSidebar(), id='screen-status-sidebar'),
            Container(Issues(self.statuses.values()), id='screen-status-rendering'),
            id='screen-status',
        )

    def on_mount(self) -> None:
        self.run_worker(self.__on_mount())

    async def __on_mount(self) -> None:
        issues_found = False

        self.sidebar.status.update('Loading...')
        async with ResponsiveNetworkClient(self.sidebar.status) as client:
            async for issue in self.app.jira.search_issues(client, self.labels):
                team = self.get_team(issue)
                if not team:
                    continue

                issues_found = True

                self.cached_issues[issue.key] = issue
                self.member_filter.add(':unassigned' if issue.assignee is None else issue.assignee.name, issue)
                self.team_filter.add(team, issue)

                self.statuses[self.get_qa_status(issue)].add_issue(issue)

            self.__current_user_id = await self.app.jira.get_current_user_id(client)

        if not issues_found:
            self.sidebar.status.update('No issues found')
            return

        for status in self.statuses.values():
            status.sort_issues()

        await self.sidebar.options.mount(
            HorizontalScroll(LabeledBox(' Refresh screen ', self.refresh_button), id='refresh-button-box')
        )
        await self.sidebar.options.mount(
            HorizontalScroll(
                LabeledBox(' Team ', FilterSelect(self.team_filter, 'team_select')), classes='issue-filter'
            )
        )
        await self.sidebar.options.mount(
            HorizontalScroll(
                LabeledBox(' Member ', FilterSelect(self.member_filter, 'member_select')), classes='issue-filter'
            )
        )
        await self.sidebar.options.mount(HorizontalScroll(self.status_changer, id='status-changer'))

        self.__update_completion_status()
        self.__refocus()

    async def on_select_changed(self, event: Select.Changed) -> None:
        choice = event.value
        # This clears widgets other than the one that has changed, given that filters can't be combined
        for widget in self.query(Select).results():
            if widget is not event.select:
                widget.clear()

        for status in self.statuses.values():
            status.clear_issues()

        if choice == Select.BLANK:
            # Display all issues when no filter is selected
            for keyed_issues in self.team_filter.issues.values():
                for issue in keyed_issues.values():
                    self.statuses[self.get_qa_status(issue)].add_issue(issue)

        else:
            for issue in event.select.issue_filter.issues[choice].values():
                self.statuses[self.get_qa_status(issue)].add_issue(issue)

        for status in self.statuses.values():
            status.sort_issues()

        self.__update_completion_status()
        self.__refocus()

    async def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if not event.data_table.show_cursor:
            return

        issue_key = event.data_table.get_cell_at(Coordinate(event.cursor_row, 0))
        issue = self.cached_issues[issue_key]
        self.issues.label.update(f' [link={self.app.jira.construct_issue_url(issue.key)}]{issue.key}[/link] ')
        self.issues.info.update(issue.summary)

        current_status = self.get_qa_status(issue)
        self.status_changer.radio_buttons[current_status].value = True

        disabled_radio_button = issue.assignee is None or issue.assignee.id != self.current_user_id

        for radio_button in self.status_changer.radio_buttons.values():
            radio_button.disabled = disabled_radio_button

    async def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        current_issue = self.cached_issues[str(self.issues.label.render()).strip()]
        current_status = self.get_qa_status(current_issue)
        self.status_changer.button.disabled = (
            current_issue.assignee is None
            or current_issue.assignee.id != self.current_user_id
            or str(event.pressed.label) == current_status
        )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button == self.refresh_button:
            self.__reload_screen()
            return

        old_issue = self.cached_issues[str(self.issues.label.render()).strip()]
        selected_status = str(self.status_changer.radio_set.pressed_button.label)

        async with ResponsiveNetworkClient(self.sidebar.status) as client:
            new_issue = await self.app.jira.update_issue_status(
                client, old_issue, self.app.qa_statuses[self.get_team(old_issue)][selected_status]
            )

        self.cached_issues[new_issue.key] = new_issue
        for issue_filter in (self.team_filter, self.member_filter):
            issue_filter.update(old_issue, new_issue)

        old_status = self.statuses[self.get_qa_status(old_issue)]
        preserved_issue_keys = []
        for row_key in old_status.table.rows:
            issue_key = str(row_key.value)
            if issue_key != old_issue.key:
                preserved_issue_keys.append(issue_key)

        old_status.clear_issues()
        for issue_key in preserved_issue_keys:
            old_status.add_issue(self.cached_issues[issue_key])
        old_status.sort_issues()

        new_status = self.statuses[self.get_qa_status(new_issue)]
        new_status.add_issue(new_issue)
        new_status.sort_issues()

        new_status.table.cursor_coordinate = Coordinate(0, 0)
        new_status.table.post_message(
            events.Click(
                x=0,
                y=0,
                delta_x=0,
                delta_y=0,
                button=0,
                shift=False,
                meta=False,
                ctrl=False,
            )
        )
        self.status_changer.button.disabled = True
        self.__update_completion_status()

    def __refocus(self) -> None:
        # Focus on the first available row of the first table with entries
        focused = False
        for status in self.statuses.values():
            if focused:
                status.table.show_cursor = False
            elif status.table.is_valid_row_index(0):
                status.table.cursor_coordinate = Coordinate(0, 0)
                status.table.show_cursor = True
                focused = True
            else:
                status.table.show_cursor = False

    def __update_completion_status(self) -> None:
        counts = [len(status.table.rows) for status in self.statuses.values()]
        total = sum(counts)
        done = counts[-1]

        percent = (Decimal(done) / total) * 100
        if 0 < percent < 100:  # noqa: PLR2004
            percent = percent.quantize(COMPLETION_PRECISION)

        self.sidebar.status.update(f'{done} / {total} ({percent}%)')

    def __reload_screen(self):
        self.app.pop_screen()
        self.app.uninstall_screen('status')
        self.app.install_screen(StatusScreen(self.labels), 'status')
        self.app.push_screen('status')
