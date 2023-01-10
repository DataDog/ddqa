# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddqa.app.core import Application


@click.command(short_help='Sync team data')
@click.pass_obj
def sync(app: Application):
    """Sync team data."""
    from ddqa.screens.sync import SyncScreen

    app.select_screen('sync', SyncScreen(manual_execution=True))
    app.run()
