# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

import click

if TYPE_CHECKING:
    from ddqa.app.core import Application


@click.command(short_help='Create QA items')
@click.argument('previous_ref')
@click.argument('current_ref')
@click.option(
    '-l',
    '--label',
    'labels',
    required=True,
    multiple=True,
    help='Labels that will be attached to created issues',
)
@click.option(
    '-i',
    '--include-labels',
    'include_labels',
    required=False,
    multiple=True,
    help='Labels that should be present in the PRs',
)
@click.pass_obj
def create(
    app: Application,
    previous_ref: str,
    current_ref: str,
    labels: tuple[str, ...],
    include_labels: list[str] | None = None,
):
    """Create QA items."""
    from ddqa.screens.create import CreateScreen

    if not include_labels:
        include_labels = app.config.app.include_labels

    app.select_screen('create', CreateScreen(previous_ref, current_ref, labels, include_labels))
    app.run()
