# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Button, Header, Label, TextLog

from ddqa.utils.network import ResponsiveNetworkClient
from ddqa.utils.toml import load_toml_data
from ddqa.widgets.static import Placeholder


class InteractiveSidebar(Widget):
    DEFAULT_CSS = """
    InteractiveSidebar > Label {
        width: 100%;
        height: 1fr;
    }

    InteractiveSidebar > TextLog {
        height: 8fr;
    }

    InteractiveSidebar > Button {
        border: none;
        width: 100%;
        height: 1fr;
    }
    """

    def __init__(self, *args, manual_execution, **kwargs):
        super().__init__(*args, **kwargs)

        self.__manual_execution = manual_execution

    def compose(self) -> ComposeResult:
        yield Label()
        yield TextLog()
        yield Button('Exit' if self.__manual_execution else 'Continue', variant='primary', disabled=True)

    def on_mount(self) -> None:
        self.call_after_refresh(lambda: self.app.run_in_background(self.__on_mount()))

    async def __on_mount(self) -> None:
        status = self.query_one(Label)
        text_log = self.query_one(TextLog)
        button = self.query_one(Button)

        async with ResponsiveNetworkClient(status) as client:
            text_log.write(f'Fetching global config from: {self.app.repo.global_config_source}', shrink=False)
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
                global_config = load_toml_data(response.text)
            except Exception:
                status.update('Unable to parse TOML source')
                return

            if not global_config:
                status.update('No members found in TOML source')
                return

            self.app.github.save_global_config(self.app.repo.global_config_source, global_config)

            teams = sorted(team.github_team for team in self.app.repo.teams.values())
            for team in teams:
                text_log.write(f'Refreshing members for team: {team}', shrink=False)
                try:
                    await self.app.github.get_team_members(client, team, refresh=True)
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
