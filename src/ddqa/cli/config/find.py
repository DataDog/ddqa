# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import click


@click.command(short_help='Show the location of the config file')
@click.option('--copy', '-c', is_flag=True, help='Copy the path to the config file to the clipboard')
@click.pass_obj
def find(app, copy):
    """Show the location of the config file."""
    config_path = str(app.config_file.path)
    if copy:
        import pyperclip

        pyperclip.copy(config_path)
    elif ' ' in config_path:
        click.echo(f'"{config_path}"')
    else:
        click.echo(config_path)
