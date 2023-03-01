# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from pydantic import BaseModel


class TeamConfig(BaseModel):
    jira_project: str
    jira_issue_type: str
    jira_component: str = ''
    github_team: str
    github_labels: list[str] = []
