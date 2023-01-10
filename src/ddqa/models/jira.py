# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from pydantic import BaseModel, HttpUrl, validator


class JiraConfig(BaseModel):
    jira_server: HttpUrl
    members: dict[str, str]

    @validator('members')
    def check_members(cls, v):  # noqa: N805
        if not v:
            message = 'must have at least one member'
            raise ValueError(message)

        return v
