# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import tomllib
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

        global_config_source = self.app.repo.global_config_source

        async with ResponsiveNetworkClient(status) as client:
            if global_config_source:
                text_log.write(
                    f'Fetching global config from: [link={global_config_source}]{global_config_source}[/link]',
                    shrink=False,
                )
                try:
                    response = await client.get(
                        str(global_config_source),
                        auth=(self.app.config.auth.github.user, self.app.config.auth.github.token),
                    )
                    response.raise_for_status()
                except Exception as e:
                    status.update(str(e))
                    return

                try:
                    global_config = tomllib.loads(response.text)
                except Exception:
                    status.update('Unable to parse TOML source')
                    return

                if not global_config:
                    status.update('No members found in TOML source')
                    return

                self.app.github.cache.save_global_config(global_config_source, global_config)
                members = global_config.get('members', {})
            else:
                datastore_id = self.app.repo.datastore_id
                text_log.write(f'Fetching members from Datadog datastore: {datastore_id}', shrink=False)
                try:
                    members = await self.app.datadog.get_members(client, datastore_id, refresh=True)
                except Exception as e:
                    status.update(str(e))
                    return

                if not members:
                    status.update('No members found in datastore')
                    return

            source_link = (
                f'[link={global_config_source}]Jira config[/link]' if global_config_source else 'Jira members datastore'
            )

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
                                f'declared in the {source_link}',
                                shrink=False,
                            )
                except Exception as e:
                    status.update(str(e))
                    return

            text_log.write(f'Validating the {source_link}...', shrink=False)

            members_values_counter = Counter(members.values())

            if duplicate_users := [key for key, value in members.items() if members_values_counter[value] > 1]:
                for duplicate_user in duplicate_users:
                    text_log.write(
                        f'Jira user `{members[duplicate_user]}` is declared multiple times in the '
                        f'{source_link} with GitHub user `{duplicate_user}`',
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

                if global_config_source:
                    global_config['members'] = members
                    self.app.github.cache.save_global_config(global_config_source, global_config)
                else:
                    datastore_id = self.app.repo.datastore_id
                    modified_at = self.app.datadog.cache.get_datastore_modified_at(datastore_id)
                    jira_server = self.app.datadog.cache.get_datastore_jira_server(datastore_id)
                    self.app.datadog.cache.save_datastore(datastore_id, modified_at, members, jira_server)
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
