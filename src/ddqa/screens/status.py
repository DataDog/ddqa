# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Footer, Header


class StatusScreen(Screen):
    BINDINGS = [('escape', 'app.exit', 'Exit app')]
    DEFAULT_CSS = """
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
