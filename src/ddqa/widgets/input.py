# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
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


class SwitchLabel(Label):
    def __init__(self, label: str, switch: Switch) -> None:
        super().__init__(label)
        self.styles.text_style = Style(underline=True)
        self.__switch = switch

    def on_click(self):
        self.__switch.action_toggle()


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
        self.label = SwitchLabel(label, self.switch)

        super().__init__(self.switch, self.label, *args, **kwargs)
