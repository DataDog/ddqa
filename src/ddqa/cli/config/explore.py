# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddqa.app.core import Application


@click.command(short_help='Open the config location in your file manager')
@click.pass_obj
def explore(app: Application):
    """Open the config location in your file manager."""
    click.launch(str(app.config_file.path), locate=True)
