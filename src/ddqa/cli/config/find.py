# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddqa.app.core import Application


@click.command(short_help='Show the location of the config file')
@click.option('--copy', '-c', is_flag=True, help='Copy the path to the config file to the clipboard')
@click.pass_obj
def find(app: Application, copy):
    """Show the location of the config file."""
    config_path = str(app.config_file.path)
    if copy:
        import pyperclip

        pyperclip.copy(config_path)
    elif ' ' in config_path:
        app.print(f'"{config_path}"')
    else:
        app.print(config_path)
