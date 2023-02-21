# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddqa.app.core import Application


@click.command(short_help='Edit the config file with your default editor')
@click.pass_obj
def edit(app: Application):
    """Edit the config file with your default editor."""
    click.edit(filename=str(app.config_file.path))
