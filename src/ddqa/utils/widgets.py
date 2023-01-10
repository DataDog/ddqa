# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from textual.widget import Widget


async def switch_to_widget(widget: Widget, parent: Widget) -> None:
    # Hide all children first
    for child in parent.children:
        if child is not widget:
            child.display = False

    if widget.parent is None:
        await parent.mount(widget)
    else:
        widget.display = True
