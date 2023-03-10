# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, validator


class Status(BaseModel):
    id: str  # noqa: A003
    name: str


class Assignee(BaseModel):
    id: str = Field(alias='accountId')  # noqa: A003
    name: str = Field(alias='displayName')
    time_zone: str = Field(alias='timeZone')
    avatar_urls: dict[str, HttpUrl] = Field(alias='avatarUrls')


class JiraIssue(BaseModel):
    key: str
    project: str
    type: str  # noqa: A003
    status: Status
    assignee: Assignee | None
    description: str
    labels: list[str]
    summary: str
    updated: datetime
    components: list[str]

    @validator('description', pre=True)
    def coerce_description(cls, v):  # noqa: N805
        return v or ''


class JiraConfig(BaseModel):
    jira_server: HttpUrl
    members: dict[str, str]

    @validator('members')
    def check_members(cls, v):  # noqa: N805
        if not v:
            message = 'must have at least one member'
            raise ValueError(message)

        return v
