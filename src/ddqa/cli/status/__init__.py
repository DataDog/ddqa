# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddqa.app.core import Application


@click.command(short_help='Display the QA dashboard')
@click.pass_obj
def status(app: Application):
    """Display the QA dashboard."""
    from ddqa.screens.status import StatusScreen

    app.select_screen('status', StatusScreen())
    app.run()
