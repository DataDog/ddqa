# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddqa.app.core import Application


@click.command(short_help='Show the location of the config file')
@click.pass_obj
def find(app: Application):
    """Show the location of the config file."""
    app.print(str(app.config_file.path))
