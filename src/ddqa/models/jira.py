# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, field_validator


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
    assignee: Assignee | None = None
    description: str
    labels: list[str]
    summary: str
    updated: datetime
    components: list[str]

    @field_validator('description', mode='before')
    @classmethod
    def coerce_description(cls, v):
        return v or ''


class JiraConfig(BaseModel, extra='allow'):
    jira_server: HttpUrl
    members: dict[str, str]
    __reversed_members: dict[str, str] | None = None

    @field_validator('members')
    @classmethod
    def check_members(cls, v):
        if not v:
            message = 'must have at least one member'
            raise ValueError(message)

        return v

    def get_jira_user_id_from_github_user_id(self, github_user_id: str) -> str | None:
        return self.members.get(github_user_id)

    def get_jira_user_ids_from_github_user_ids(self, github_user_ids: Iterable[str]) -> set[str]:
        res = set()

        for gh_id in github_user_ids:
            if jira_id := self.get_jira_user_id_from_github_user_id(gh_id):
                res.add(jira_id)

        return res

    def get_github_user_id_from_jira_user_id(self, jira_user_id: str) -> str | None:
        # This only works because the self.members dict is loaded once and for all at startup
        if not self.__reversed_members:
            self.__reversed_members = {jira_id: gh_id for gh_id, jira_id in self.members.items()}

        return self.__reversed_members.get(jira_user_id)
