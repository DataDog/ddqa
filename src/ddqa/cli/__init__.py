# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import os
import sys

import click

from ddqa._version import __version__
from ddqa.cli.config import config
from ddqa.cli.create import create
from ddqa.cli.status import status
from ddqa.cli.sync import sync
from ddqa.config.constants import AppEnvVars, ConfigEnvVars


@click.group(context_settings={'help_option_names': ['-h', '--help']}, invoke_without_command=True)
@click.option(
    '--color/--no-color',
    default=None,
    help='Whether or not to display colored output (default is auto-detection) [env vars: `FORCE_COLOR`/`NO_COLOR`]',
)
@click.option(
    '--cache-dir',
    envvar=ConfigEnvVars.CACHE,
    help='The path to a custom directory used to cache data [env var: `DDQA_CACHE_DIR`]',
)
@click.option(
    '--config',
    'config_file_path',
    envvar=ConfigEnvVars.CONFIG,
    help='The path to a custom config file to use [env var: `DDQA_CONFIG`]',
)
@click.version_option(version=__version__, prog_name='ddqa')
@click.pass_context
def ddqa(ctx: click.Context, color, cache_dir, config_file_path):
    """
    \b
         _     _
      __| | __| | __ _  __ _
     / _` |/ _` |/ _` |/ _` |
    | (_| | (_| | (_| | (_| |
     \\__,_|\\__,_|\\__, |\\__,_|
                    |_|
    """
    from ddqa.app.core import Application
    from ddqa.config.file import ConfigFile
    from ddqa.utils.fs import Path

    if color is None:
        if os.environ.get(AppEnvVars.NO_COLOR) == '1':
            color = False
        elif os.environ.get(AppEnvVars.FORCE_COLOR) == '1':
            color = True

    if config_file_path:
        config_file = ConfigFile(Path(config_file_path).resolve())
        if not config_file.path.is_file():
            click.echo(f'The selected config file `{str(config_file.path)}` does not exist.')
            ctx.exit(1)
    else:
        config_file = ConfigFile()
        if not config_file.path.is_file():
            try:
                config_file.restore()
            except OSError:  # no cov
                click.echo(
                    f'Unable to create config file located at `{str(config_file.path)}`. Please check your permissions.'
                )
                ctx.exit(1)

    app = Application(config_file, cache_dir, color)

    if not ctx.invoked_subcommand:
        click.echo(ctx.get_help())
        return

    # Persist app for sub-commands
    ctx.obj = app

    try:
        app.config_file.load()
    except OSError as e:  # no cov
        click.echo(f'Error loading configuration: {e}')
        ctx.exit(1)


ddqa.add_command(config)
ddqa.add_command(create)
ddqa.add_command(status)
ddqa.add_command(sync)


def main():  # no cov
    try:
        return ddqa(prog_name='ddqa', windows_expand_args=False)
    except Exception:
        from rich.console import Console

        suppressed_modules = []
        if not getattr(sys, 'frozen', False):
            suppressed_modules.append(click)

        console = Console()
        console.print_exception(suppress=suppressed_modules)
        return 1
