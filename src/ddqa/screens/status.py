# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timedelta
from decimal import Decimal
from functools import cache, cached_property
from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.coordinate import Coordinate
from textual.screen import Screen
from textual.widgets import DataTable, Header, Input, Label
from textual_autocomplete import AutoComplete, Dropdown, DropdownItem

from ddqa.utils.network import ResponsiveNetworkClient
from ddqa.utils.time import format_elapsed_time
from ddqa.widgets.layout import LabeledBox

if TYPE_CHECKING:
    from ddqa.models.jira import JiraIssue

COMPLETION_PRECISION = Decimal('0.0')


class IssueFilter:
    def __init__(self, final_label: str):
        self.__final_label = final_label
        self.__issues: dict[str, dict[str, list[JiraIssue]]] = defaultdict(lambda: defaultdict(list))

    @property
    def issues(self) -> dict[str, dict[str, list[JiraIssue]]]:
        return self.__issues

    def add(self, key: str, label: str, issue: JiraIssue):
        self.issues[key][label].append(issue)

    def progress(self, key: str) -> tuple[int, int, Decimal]:
        done = 0
        total = 0
        for label, issues in self.issues[key].items():
            total += len(issues)
            if label == self.__final_label:
                done += len(issues)

        percent = Decimal(done) / total
        if not done or done == total:
            percent.quantize(COMPLETION_PRECISION)

        return done, total, percent

    def dropdown_items(self) -> list[DropdownItem]:
        items: list[DropdownItem] = []
        for key in self.issues:
            _, _, percent = self.progress(key)
            items.append(DropdownItem(key, f'{percent}%'))

        return items


class FilterAutoComplete(AutoComplete):
    def __init__(self, issue_filter: IssueFilter):
        self.__issue_filter = issue_filter

        super().__init__(Input(), Dropdown(items=self.__issue_filter.dropdown_items()))

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


class Status(LabeledBox):
    DEFAULT_CSS = """
    Status {
        width: auto;
    }

    Status Container {
        width: auto;
    }

    Status DataTable {
        width: auto;
        margin-top: 1;
    }
    """

    def __init__(self, name: str):
        self.__name = name
        self.__table = DataTable()
        self.__table.cursor_type = 'row'
        self.__table.add_column('Issue')
        self.__table.add_column('Assignee')
        self.__table.add_column('Last update', key='update-time')

        super().__init__(f' {self.__name} ', self.__table)

    @property
    def name(self) -> str:
        return self.__name

    @property
    def table(self) -> DataTable:
        return self.__table

    def add_issue(self, issue: JiraIssue) -> None:
        self.table.add_row(issue.key, issue.assignee.name, get_timedelta(issue.updated))

    def sort_issues(self) -> None:
        self.table.sort('update-time', reverse=True)

    def clear_issues(self) -> None:
        self.table.clear()


class Issues(LabeledBox):
    DEFAULT_CSS = """
    #issue-info {
        height: 1fr;
        border-bottom: dashed #632CA6;
    }

    #statuses-box {
        height: 9fr;
        align: center middle;
    }
    """

    def __init__(self, statuses: Iterable[Status]):
        self.__info = Label()

        super().__init__('', Container(self.__info, id='issue-info'), Horizontal(*statuses, id='statuses-box'))

    @property
    def info(self) -> Label:
        return self.__info


class FiltersSidebar(LabeledBox):
    DEFAULT_CSS = """
    #sidebar-status {
        height: 1fr;
        border-bottom: dashed #632CA6;
    }

    #sidebar-filters {
        height: 9fr;
    }

    .issue-filter {
        height: 5;
    }
    """

    def __init__(self):
        self.__status = Label()
        self.__filters = Vertical()

        super().__init__(
            '',
            Container(self.__status, id='sidebar-status'),
            Container(self.__filters, id='sidebar-filters'),
        )

    @property
    def status(self) -> Label:
        return self.__status

    @property
    def filters(self) -> Vertical:
        return self.__filters


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

    @cached_property
    def cached_issues(self) -> dict[str, JiraIssue]:
        return {}

    @cached_property
    def team_filter(self) -> IssueFilter:
        return IssueFilter(self.final_label)

    @cached_property
    def member_filter(self) -> IssueFilter:
        return IssueFilter(self.final_label)

    @cached_property
    def final_label(self) -> str:
        return self.app.jira.format_label(self.app.repo.jira_statuses[-1])

    @cached_property
    def statuses(self) -> dict[str, Status]:
        return {self.app.jira.format_label(status): Status(status) for status in self.app.repo.jira_statuses}

    @cached_property
    def sidebar(self) -> FiltersSidebar:
        return self.query_one(FiltersSidebar)

    @cached_property
    def issues(self) -> Issues:
        return self.query_one(Issues)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Container(FiltersSidebar(), id='screen-status-sidebar'),
            Container(Issues(self.statuses.values()), id='screen-status-rendering'),
            id='screen-status',
        )

    def on_mount(self) -> None:
        self.call_after_refresh(lambda: self.app.run_in_background(self.__on_mount()))

    async def __on_mount(self) -> None:
        project_to_team = {config.jira_project: team for team, config in self.app.repo.teams.items()}
        done = 0
        total = 0

        self.sidebar.status.update('Loading...')
        async with ResponsiveNetworkClient(self.sidebar.status) as client:
            async for issue in self.app.jira.search_issues(client):
                label = (set(issue.labels) & set(self.statuses)).pop()
                self.cached_issues[issue.key] = issue
                self.team_filter.add(project_to_team[issue.project], label, issue)
                self.member_filter.add(issue.assignee.name, label, issue)

                self.statuses[label].add_issue(issue)

                total += 1
                if label == self.final_label:
                    done += 1

        for status in self.statuses.values():
            status.sort_issues()

        if not total:
            self.sidebar.status.update('No issues found')
            return

        percent = Decimal(done) / total
        if not done or done == total:
            percent.quantize(COMPLETION_PRECISION)

        self.sidebar.status.update(f'{done} / {total} ({percent}%)')
        self.__refocus()

        await self.sidebar.filters.mount(
            Horizontal(LabeledBox(' Team ', FilterAutoComplete(self.team_filter)), classes='issue-filter')
        )
        await self.sidebar.filters.mount(
            Horizontal(LabeledBox(' Member ', FilterAutoComplete(self.member_filter)), classes='issue-filter')
        )

    async def on_auto_complete_selected(self, event: AutoComplete.Selected) -> None:
        choice = str(event.item.main)
        for widget in self.query(Input).results():
            if widget is not event.sender.input:
                widget.value = ''

        for status in self.statuses.values():
            status.clear_issues()

        for label, issues in event.sender.issue_filter.issues[choice].items():
            status = self.statuses[label]

            for issue in issues:
                status.add_issue(issue)

            status.sort_issues()

        done, total, percent = event.sender.issue_filter.progress(choice)
        self.sidebar.status.update(f'{done} / {total} ({percent}%)')
        self.__refocus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if not event.value:
            done = 0
            total = 0
            for status in self.statuses.values():
                status.clear_issues()

            for labeled_issues in self.team_filter.issues.values():
                for label, issues in labeled_issues.items():
                    status = self.statuses[label]

                    for issue in issues:
                        status.add_issue(issue)

                    total += len(issues)
                    if label == self.final_label:
                        done += len(issues)

            for status in self.statuses.values():
                status.sort_issues()

            percent = Decimal(done) / total
            if not done or done == total:
                percent.quantize(COMPLETION_PRECISION)

            self.sidebar.status.update(f'{done} / {total} ({percent}%)')
            self.__refocus()

    async def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        issue_key = event.sender.get_cell_at(Coordinate(event.cursor_row, 0))
        issue = self.cached_issues[issue_key]
        self.issues.info.update(f'[link={self.app.jira.construct_issue_url(issue.key)}]{issue.summary}[/link]')

    def __refocus(self) -> None:
        # Focus on the first available row
        for status in self.statuses.values():
            if status.table.is_valid_row_index(0):
                status.table.cursor_coordinate = Coordinate(0, 0)
                break
