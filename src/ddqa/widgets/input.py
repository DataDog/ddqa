# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from rich.style import Style
from textual import events
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
        self.label = Label(label)
        self.label.styles.text_style = Style(underline=True)

        super().__init__(self.switch, self.label, *args, **kwargs)

    def _on_click(self, _event: events.Click) -> None:
        self.switch.toggle()
