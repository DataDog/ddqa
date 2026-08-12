# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from collections import Counter

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Button, Header, Label, RichLog
from textual.worker import Worker, WorkerState

from ddqa.utils.network import ResponsiveNetworkClient
from ddqa.widgets.static import Placeholder


class InteractiveSidebar(Widget):
    DEFAULT_CSS = """
    InteractiveSidebar > Label {
        width: 100%;
        height: 1fr;
    }

    InteractiveSidebar > RichLog {
        height: 8fr;
    }

    InteractiveSidebar > Button {
        border: none;
        width: 100%;
        height: auto;
    }
    """

    def __init__(self, *args, manual_execution: bool = False, auto_mode: bool = False, **kwargs):
        super().__init__(*args, **kwargs)

        self.__manual_execution = manual_execution
        self.__auto_mode = auto_mode

    def compose(self) -> ComposeResult:
        yield Label()
        yield RichLog(markup=True)
        yield Button('Exit' if self.__manual_execution else 'Continue', variant='primary', disabled=True)

    def on_mount(self) -> None:
        self.run_worker(self.__on_mount())

    async def __on_mount(self) -> None:
        status = self.query_one(Label)
        text_log = self.query_one(RichLog)
        button = self.query_one(Button)

        datastore_id = self.app.repo.datastore_id

        async with ResponsiveNetworkClient(status) as client:
            text_log.write(f'Fetching members from Datadog datastore: {datastore_id}', shrink=False)
            try:
                members = await self.app.datadog.get_members(client, datastore_id, refresh=True)
            except Exception as e:
                status.update(str(e))
                return

            if not members:
                status.update('No members found in datastore')
                return

            teams = sorted(team.github_team for team in self.app.repo.teams.values())
            for team in teams:
                text_log.write(
                    f'Refreshing members for team: [link=https://github.com/orgs/{self.app.github.org}/teams/{team}]{team}[/link]',
                    shrink=False,
                )
                try:
                    github_members = await self.app.github.get_team_members(client, team, refresh=True)
                    for member in github_members:
                        if member not in members:
                            text_log.write(
                                f'GitHub user [link=https://github.com/{member}]{member}[/link] is not '
                                'declared in the Jira members datastore',
                                shrink=False,
                            )
                except Exception as e:
                    status.update(str(e))
                    return

            text_log.write('Validating the Jira members datastore...', shrink=False)

            members_values_counter = Counter(members.values())

            if duplicate_users := [key for key, value in members.items() if members_values_counter[value] > 1]:
                for duplicate_user in duplicate_users:
                    text_log.write(
                        f'Jira user `{members[duplicate_user]}` is declared multiple times in the '
                        f'Jira members datastore with GitHub user `{duplicate_user}`',
                        shrink=False,
                    )
                return

            text_log.write(f'Validating {len(members)} Jira users...', shrink=False)
            try:
                members_rev = {v: k for k, v in members.items()}

                async for jira_user in self.app.jira.get_deactivated_users(client, members.values()):
                    account_id = jira_user.get('accountId')
                    if not account_id or not (github_user_id := members_rev.get(account_id)):
                        continue

                    text_log.write(
                        f'User [link=https://github.com/{github_user_id}]{github_user_id}[/link] is deactivated on '
                        f'[link={self.app.jira.config.jira_server}/jira/people/{account_id}]Jira[/link]',
                        shrink=False,
                    )
                    del members[github_user_id]

                modified_at = self.app.datadog.cache.get_datastore_modified_at(datastore_id)
                self.app.datadog.cache.save_datastore(datastore_id, modified_at, members)
            except Exception as e:
                status.update(str(e))
                return

            text_log.write('Sync finished correctly', shrink=False)
            button.disabled = False

    async def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.state not in (WorkerState.PENDING, WorkerState.RUNNING) and self.__auto_mode:
            await self.exit_screen()

    async def on_button_pressed(self, _event: Button.Pressed) -> None:
        await self.exit_screen()

    async def exit_screen(self) -> None:
        if self.__manual_execution:
            self.app.exit()
        else:
            await self.app.switch_screen(list(self.app._installed_screens)[0])


class SyncScreen(Screen):
    BINDINGS = [
        Binding('ctrl+c', 'quit', 'Quit', show=False, priority=True),
        Binding('tab', 'focus_next', 'Focus Next', show=False),
        Binding('shift+tab', 'focus_previous', 'Focus Previous', show=False),
    ]
    DEFAULT_CSS = """
    #screen-sync {
        layout: grid;
        grid-size: 2;
        grid-columns: 1fr;
        grid-rows: 1fr;
    }

    #screen-sync-sidebar {
        height: 100%;
    }

    #screen-sync-placeholder {
        height: 100%;
    }
    """

    def __init__(self, *args, manual_execution=False, auto_mode: bool = False, **kwargs):
        super().__init__(*args, **kwargs)

        self.__manual_execution = manual_execution
        self.__auto_mode = auto_mode

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Container(
                InteractiveSidebar(manual_execution=self.__manual_execution, auto_mode=self.__auto_mode),
                id='screen-sync-sidebar',
            ),
            Container(Placeholder(width_factor=2), id='screen-sync-placeholder'),
            id='screen-sync',
        )
