# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import click


@click.command(short_help='Restore the config file to default settings')
@click.pass_obj
def restore(app):
    """Restore the config file to default settings."""
    app.config_file.restore()
    click.echo('Settings were successfully restored.')
