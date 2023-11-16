# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from collections.abc import Callable

from rich.style import Style
from textual.containers import HorizontalScroll
from textual.widgets import Label, Switch


class LabeledInput(HorizontalScroll):
    DEFAULT_CSS = """
    LabeledInput {
        height: 3;
    }

    LabeledInput > Label {
        margin-top: 1;
        width: 1fr;
        text-align: right;
    }

    LabeledInput > Input {
        width: 5fr;
    }
    """


class ClickableLabel(Label):
    def __init__(self, label: str, callback: Callable[[], None]) -> None:
        super().__init__(label)
        self.styles.text_style = Style(underline=True)
        self.__callback = callback

    def on_click(self):
        self.__callback()


class LabeledSwitch(HorizontalScroll):
    DEFAULT_CSS = """
    LabeledSwitch {
        height: auto;
        width: auto;
    }

    LabeledSwitch > Label {
        height: 3;
        content-align: center middle;
        width: auto;
    }

    LabeledSwitch > Switch {
        height: auto;
        width: auto;
    }
    """

    def __init__(self, *args, label: str, **kwargs):
        self.switch = Switch()
        self.label = ClickableLabel(label, self.switch.action_toggle)

        super().__init__(self.switch, self.label, *args, **kwargs)
