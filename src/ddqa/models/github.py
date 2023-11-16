# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from pydantic import BaseModel


class PullRequestLabel(BaseModel):
    name: str
    color: str


class PullRequestReviewer(BaseModel):
    name: str
    association: str


class TestCandidate(BaseModel):
    id: str  # noqa: A003
    title: str
    url: str
    user: str = ''
    body: str = ''
    labels: list[PullRequestLabel] = []
    reviewers: list[PullRequestReviewer] = []
    assigned_teams: set[str] = set()

    def short_display(self) -> str:
        return f'#{self.id}' if self.id.isdigit() else self.id[:7]

    def long_display(self) -> str:
        return f'pull request #{self.id}' if self.id.isdigit() else f'commit {self.id[:7]}'
