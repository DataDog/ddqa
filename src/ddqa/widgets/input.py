# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from textual.containers import Horizontal
from textual.widgets import Label, Switch


class LabeledInput(Horizontal):
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


class LabeledSwitch(Horizontal):
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
        self.label = Label(label)
        self.switch = Switch()

        super().__init__(self.switch, self.label, *args, **kwargs)
