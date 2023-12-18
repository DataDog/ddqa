# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT

from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddqa.app.core import Application


@click.command('set', short_help='Assign values to config file entries')
@click.argument('key')
@click.argument('value', required=False)
@click.pass_obj
def set_value(app: Application, key: str, value: str):
    if value is None:
        from fnmatch import fnmatch

        from ddqa.config.utils import SCRUBBED_GLOBS

        scrubbing = any(fnmatch(key, glob) for glob in SCRUBBED_GLOBS)
        value = click.prompt(f'Value for `{key}`', hide_input=scrubbing)

    app.config_file.model.set_field(key, value)
    app.config_file.save()
