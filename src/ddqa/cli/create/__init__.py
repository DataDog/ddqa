# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddqa.app.core import Application


@click.command(short_help='Create QA items')
@click.argument('previous_ref')
@click.argument('current_ref')
@click.pass_obj
def create(app: Application, previous_ref: str, current_ref: str):
    """Create QA items."""
    from ddqa.screens.create import CreateScreen

    app.select_screen('create', CreateScreen(previous_ref, current_ref))
    app.run()
