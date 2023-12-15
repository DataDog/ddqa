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
    '-pl',
    '--pr-labels',
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
    pr_labels: list[str] | None = None,
):
    """Create QA items."""
    from ddqa.screens.create import CreateScreen

    if not pr_labels:
        pr_labels = app.config.app.pr_labels

    app.select_screen('create', CreateScreen(previous_ref, current_ref, labels, pr_labels, auto_mode=app.auto_mode))
    app.run()
