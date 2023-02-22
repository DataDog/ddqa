# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddqa.app.core import Application


@click.command(short_help='Show the contents of the config file')
@click.option('--all', '-a', 'all_keys', is_flag=True, help='Do not scrub secret fields')
@click.pass_obj
def show(app: Application, all_keys):
    """Show the contents of the config file."""
    if not app.config_file.path.is_file():  # no cov
        click.echo('No config file found! Please try `ddev config restore`.')
    else:
        from rich.syntax import Syntax

        text = app.config_file.read() if all_keys else app.config_file.read_scrubbed()
        app.print(Syntax(text.rstrip(), 'toml', background_color='default'))
