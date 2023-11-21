# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import tomllib

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Button, Header, Label, RichLog

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

    def __init__(self, *args, manual_execution, **kwargs):
        super().__init__(*args, **kwargs)

        self.__manual_execution = manual_execution

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

        async with ResponsiveNetworkClient(status) as client:
            text_log.write(
                f'Fetching global config from: '
                f'[link={self.app.repo.global_config_source}]{self.app.repo.global_config_source}[/link]',
                shrink=False,
            )
            try:
                response = await client.get(
                    self.app.repo.global_config_source,
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

            self.app.github.cache.save_global_config(self.app.repo.global_config_source, global_config)

            teams = sorted(team.github_team for team in self.app.repo.teams.values())
            for team in teams:
                text_log.write(
                    f'Refreshing members for team: [link=https://github.com/orgs/{self.app.github.org}/teams/{team}]{team}[/link]',
                    shrink=False,
                )
                try:
                    await self.app.github.get_team_members(client, team, refresh=True)
                except Exception as e:
                    status.update(str(e))
                    return

            text_log.write(f'Validating {len(global_config.get("members", {}))} Jira users...', shrink=False)
            try:
                members_rev = {v: k for k, v in global_config.get('members', {}).items()}

                async for jira_user in self.app.jira.get_deactivated_users(
                    client, global_config.get('members', {}).values()
                ):
                    github_user_id = members_rev[jira_user['accountId']]
                    text_log.write(
                        f'User [link=https://github.com/{github_user_id}]{github_user_id}[/link] is deactivated on '
                        f'[link={self.app.jira.config.jira_server}/jira/people/{jira_user["accountId"]}]Jira[/link]',
                        shrink=False,
                    )
                    del global_config['members'][github_user_id]

                self.app.github.cache.save_global_config(self.app.repo.global_config_source, global_config)
            except Exception as e:
                status.update(str(e))
                return

            button.disabled = False

    async def on_button_pressed(self, _event: Button.Pressed) -> None:
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

    def __init__(self, *args, manual_execution=False, **kwargs):
        super().__init__(*args, **kwargs)

        self.__manual_execution = manual_execution

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Container(InteractiveSidebar(manual_execution=self.__manual_execution), id='screen-sync-sidebar'),
            Container(Placeholder(width_factor=2), id='screen-sync-placeholder'),
            id='screen-sync',
        )
