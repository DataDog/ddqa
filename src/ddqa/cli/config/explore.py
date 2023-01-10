# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import click


@click.command(short_help='Open the config location in your file manager')
@click.pass_obj
def explore(app):
    """Open the config location in your file manager."""
    click.launch(str(app.config_file.path), locate=True)
