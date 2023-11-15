# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import click


@click.command(short_help='Purge the cache folder')
@click.pass_obj
def purge(app):
    """Remove the cache location."""
    if app.cache_dir.exists():
        app.print(f'Removing {app.cache_dir}...')
        import shutil

        shutil.rmtree(str(app.cache_dir))
    else:
        app.print(f'Cache directory {app.cache_dir} does not exist.')
