# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from textual.containers import Container
from textual.widgets import Label


class LabeledBox(Container):
    DEFAULT_CSS = """
    LabeledBox {
        layers: base_ top_;
        width: 100%;
        height: 100%;
    }

    LabeledBox > Container {
        layer: base_;
        border: round $primary;
        width: 100%;
        height: 100%;
        layout: vertical;
    }

    LabeledBox > Label {
        layer: top_;
        offset-x: 2;
    }
    """

    def __init__(self, title, *args, **kwargs):
        self.__label = Label(title)

        super().__init__(self.__label, Container(*args, **kwargs))

    @property
    def label(self):
        return self.__label
