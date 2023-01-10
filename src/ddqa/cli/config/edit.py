# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import click


@click.command(short_help='Edit the config file with your default editor')
@click.pass_obj
def edit(app):
    """Edit the config file with your default editor."""
    click.edit(filename=str(app.config_file.path))
