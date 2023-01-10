# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from pydantic import BaseModel


class GitHubAuth(BaseModel):
    user: str
    token: str


class JiraAuth(BaseModel):
    email: str
    token: str


class AuthConfig(BaseModel):
    github: GitHubAuth
    jira: JiraAuth
