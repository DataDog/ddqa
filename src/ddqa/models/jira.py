# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, validator


class Assignee(BaseModel):
    id: str = Field(alias='accountId')  # noqa: A003
    name: str = Field(alias='displayName')
    time_zone: str = Field(alias='timeZone')
    avatar_urls: dict[str, HttpUrl] = Field(alias='avatarUrls')


class JiraIssue(BaseModel):
    key: str
    project: str
    assignee: Assignee
    description: str
    labels: list[str]
    summary: str
    updated: datetime


class JiraConfig(BaseModel):
    jira_server: HttpUrl
    members: dict[str, str]

    @validator('members')
    def check_members(cls, v):  # noqa: N805
        if not v:
            message = 'must have at least one member'
            raise ValueError(message)

        return v
