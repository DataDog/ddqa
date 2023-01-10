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
