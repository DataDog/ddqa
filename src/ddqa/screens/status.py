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

from textual import events
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.coordinate import Coordinate
from textual.screen import Screen
from textual.widgets import Button, DataTable, Header, Input, Label, Switch
from textual_autocomplete import AutoComplete, Dropdown, DropdownItem

from ddqa.utils.network import ResponsiveNetworkClient
from ddqa.utils.time import format_elapsed_time
from ddqa.widgets.input import LabeledSwitch
from ddqa.widgets.layout import LabeledBox

if TYPE_CHECKING:
    from ddqa.models.jira import JiraIssue

COMPLETION_PRECISION = Decimal('0.00')


class IssueFilter:
    def __init__(self, final_label: str):
        self.__final_label = final_label
        self.__issues: dict[str, dict[str, list[JiraIssue]]] = defaultdict(lambda: defaultdict(list))

    @property
    def issues(self) -> dict[str, dict[str, list[JiraIssue]]]:
        return self.__issues

    def add(self, key: str, label: str, issue: JiraIssue):
        self.issues[key][label].append(issue)

    def update(self, issue: JiraIssue, old_label: str, new_label: str):
        for key, labeled_issues in self.issues.items():
            issues = labeled_issues[old_label]
            for i, possible_issue in enumerate(issues):
                if possible_issue.key == issue.key:
                    issues.pop(i)
                    self.issues[key][new_label].append(issue)
                    return

    def dropdown_items(self) -> list[DropdownItem]:
        items: list[DropdownItem] = []
        for key in self.issues:
            done = 0
            total = 0
            for label, issues in self.issues[key].items():
                total += len(issues)
                if label == self.__final_label:
                    done += len(issues)

            percent = (Decimal(done) / total) * 100
            if 0 < percent < 100:  # noqa: PLR2004
                percent = percent.quantize(COMPLETION_PRECISION)

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


class StatusChanger(LabeledBox):
    DEFAULT_CSS = """
    #status-choices {
        height: 1fr;
    }

    #status-submission {
        border: none;
        width: 100%;
    }
    """

    def __init__(self, statuses: list[str]) -> None:
        self.__switches = {status: LabeledSwitch(label=status) for status in statuses}
        self.__button = Button('Move', variant='primary', id='status-submission')

        super().__init__(' Status ', Vertical(*self.__switches.values(), id='status-choices'), self.__button)

    @property
    def switches(self) -> dict[str, LabeledSwitch]:
        return self.__switches

    @property
    def button(self) -> Button:
        return self.__button


class StatusTable(DataTable):
    def __init__(self):
        super().__init__()

        self.cursor_type = 'row'
        self.show_cursor = False
        self.add_column('Issue')
        self.add_column('Assignee')
        self.add_column('Last update', key='update-time')

    def on_click(self, event: events.Click) -> None:
        super().on_click(event)

        for data_table in self.app.query(StatusTable).results():
            data_table.show_cursor = data_table is self


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
    }
    """

    def __init__(self, name: str):
        self.__name = name
        self.__table = StatusTable()

        super().__init__(f' {self.__name} ', self.__table)

    @property
    def name(self) -> str:
        return self.__name

    @property
    def table(self) -> StatusTable:
        return self.__table

    def add_issue(self, issue: JiraIssue) -> None:
        self.table.add_row(
            issue.key,
            issue.assignee.name if issue.assignee is not None else '',
            get_timedelta(issue.updated),
            key=issue.key,
        )

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


class OptionsSidebar(LabeledBox):
    DEFAULT_CSS = """
    #sidebar-status {
        height: auto;
        border-bottom: dashed #632CA6;
    }

    #sidebar-options {
        height: 1fr;
    }

    .issue-filter {
        height: 5;
    }
    """

    def __init__(self):
        self.__status = Label()
        self.__options = Vertical()

        super().__init__(
            '',
            Container(self.__status, id='sidebar-status'),
            Container(self.__options, id='sidebar-options'),
        )

    @property
    def status(self) -> Label:
        return self.__status

    @property
    def options(self) -> Vertical:
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

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.__current_user_id = ''

    @property
    def current_user_id(self) -> str:
        return self.__current_user_id

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
    def sidebar(self) -> OptionsSidebar:
        return self.query_one(OptionsSidebar)

    @cached_property
    def issues(self) -> Issues:
        return self.query_one(Issues)

    @cached_property
    def status_changer(self) -> StatusChanger:
        return StatusChanger(self.app.repo.jira_statuses)

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Container(OptionsSidebar(), id='screen-status-sidebar'),
            Container(Issues(self.statuses.values()), id='screen-status-rendering'),
            id='screen-status',
        )

    def on_mount(self) -> None:
        self.call_after_refresh(lambda: self.app.run_in_background(self.__on_mount()))

    async def __on_mount(self) -> None:
        project_to_team = {config.jira_project: team for team, config in self.app.repo.teams.items()}
        issues_found = False

        self.sidebar.status.update('Loading...')
        async with ResponsiveNetworkClient(self.sidebar.status) as client:
            async for issue in self.app.jira.search_issues(client):
                issues_found = True

                label = self.__get_status_label(issue.labels)
                self.cached_issues[issue.key] = issue
                self.team_filter.add(project_to_team[issue.project], label, issue)
                self.member_filter.add(':unassigned' if issue.assignee is None else issue.assignee.name, label, issue)

                self.statuses[label].add_issue(issue)

            self.__current_user_id = await self.app.jira.get_current_user_id(client)

        for status in self.statuses.values():
            status.sort_issues()

        if not issues_found:
            self.sidebar.status.update('No issues found')
            return

        await self.sidebar.options.mount(
            Horizontal(LabeledBox(' Team ', FilterAutoComplete(self.team_filter)), classes='issue-filter')
        )
        await self.sidebar.options.mount(
            Horizontal(LabeledBox(' Member ', FilterAutoComplete(self.member_filter)), classes='issue-filter')
        )
        await self.sidebar.options.mount(Horizontal(self.status_changer))

        self.__update_completion_status()
        self.__refocus()

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

        self.__update_completion_status()
        self.__refocus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.value:
            return

        for status in self.statuses.values():
            status.clear_issues()

        for labeled_issues in self.team_filter.issues.values():
            for label, issues in labeled_issues.items():
                status = self.statuses[label]

                for issue in issues:
                    status.add_issue(issue)

        for status in self.statuses.values():
            status.sort_issues()

        self.__update_completion_status()
        self.__refocus()

    async def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        if not event.sender.show_cursor:
            return

        issue_key = event.sender.get_cell_at(Coordinate(event.cursor_row, 0))
        issue = self.cached_issues[issue_key]
        self.issues.label.update(f' [link={self.app.jira.construct_issue_url(issue.key)}]{issue.key}[/link] ')
        self.issues.info.update(issue.summary)

        current_status = str(self.statuses[self.__get_status_label(issue.labels)].name)
        self.status_changer.switches[current_status].switch.value = True

    async def on_switch_changed(self, event: Switch.Changed) -> None:
        if not event.value:
            if not any(labeled_switch.switch.value for labeled_switch in self.status_changer.switches.values()):
                self.status_changer.button.disabled = True

            return

        for labeled_switch in self.status_changer.switches.values():
            if labeled_switch.switch is not event.sender:
                labeled_switch.switch.value = False

        current_issue = self.cached_issues[str(self.issues.label.render()).strip()]
        if current_issue.assignee is not None:
            self.status_changer.button.disabled = current_issue.assignee.id != self.current_user_id

    async def on_button_pressed(self, _event: Button.Pressed) -> None:
        current_issue = self.cached_issues[str(self.issues.label.render()).strip()]
        for labeled_switch in self.status_changer.switches.values():
            if labeled_switch.switch.value:
                current_status = str(labeled_switch.label.render())
                break
        else:  # no cov
            message = 'No status selected'
            raise ValueError(message)

        old_label = self.__get_status_label(current_issue.labels)
        async with ResponsiveNetworkClient(self.sidebar.status) as client:
            await self.app.jira.update_issue_status(client, current_issue, current_status)

        new_label = self.__get_status_label(current_issue.labels)
        for issue_filter in [self.team_filter, self.member_filter]:
            issue_filter.update(current_issue, old_label, new_label)

        old_status = self.statuses[old_label]
        preserved_issue_keys = []
        for row_key in old_status.table.rows:
            issue_key = str(row_key.value)
            if issue_key != current_issue.key:
                preserved_issue_keys.append(issue_key)

        old_status.clear_issues()
        for issue_key in preserved_issue_keys:
            old_status.add_issue(self.cached_issues[issue_key])
        old_status.sort_issues()

        new_status = self.statuses[new_label]
        new_status.add_issue(current_issue)
        new_status.sort_issues()

        new_status.table.cursor_coordinate = Coordinate(0, 0)
        await new_status.table.post_message(
            events.Click(
                sender=self.app,
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
        self.status_changer.switches[str(new_status.name)].switch.value = True
        self.__update_completion_status()

    def __get_status_label(self, labels: list[str]) -> str:
        for label in labels:
            if label in self.statuses:
                return label

        message = f'Unknown status: {labels}'
        raise ValueError(message)

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
        counts = []
        for status in self.statuses.values():
            counts.append(len(status.table.rows))

        total = sum(counts)
        done = counts[-1]

        percent = (Decimal(done) / total) * 100
        if 0 < percent < 100:  # noqa: PLR2004
            percent = percent.quantize(COMPLETION_PRECISION)

        self.sidebar.status.update(f'{done} / {total} ({percent}%)')
