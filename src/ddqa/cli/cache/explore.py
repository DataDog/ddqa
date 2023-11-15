# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import click


@click.command(short_help='Show the location of the cache folder')
@click.pass_obj
def explore(app):
    """Open the cache location in your file manager."""
    click.launch(str(app.cache_dir), locate=True)
