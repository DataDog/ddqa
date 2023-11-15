# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import click


@click.command(short_help='Show the location of the cache folder')
@click.pass_obj
def find(app):
    """Show the location of the cache folder."""
    app.print(str(app.cache_dir))
