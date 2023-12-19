# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import click

from ddqa.cli.config.edit import edit
from ddqa.cli.config.explore import explore
from ddqa.cli.config.find import find
from ddqa.cli.config.restore import restore
from ddqa.cli.config.set import set_value
from ddqa.cli.config.show import show


@click.group(short_help='Manage the config file')
def config():
    pass


config.add_command(edit)
config.add_command(explore)
config.add_command(find)
config.add_command(restore)
config.add_command(set_value)
config.add_command(show)
