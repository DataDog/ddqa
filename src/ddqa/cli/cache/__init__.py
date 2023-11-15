# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import click

from ddqa.cli.cache.explore import explore
from ddqa.cli.cache.find import find
from ddqa.cli.cache.purge import purge


@click.group(short_help='Manage the cache')
def cache():
    pass


cache.add_command(explore)
cache.add_command(find)
cache.add_command(purge)
