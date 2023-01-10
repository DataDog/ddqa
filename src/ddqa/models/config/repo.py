# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, HttpUrl, validator

from ddqa.models.config.team import TeamConfig


class RepoConfig(BaseModel):
    global_config_source: HttpUrl
    jira_statuses: Annotated[list[str], Field(min_items=1)]
    teams: dict[str, TeamConfig]
    ignored_labels: list[str] = []

    # This comes from user configuration
    path: str = ''

    @validator('teams')
    def check_teams(cls, v):  # noqa: N805
        if not v:
            message = 'must have at least one team'
            raise ValueError(message)

        return v


class ReposConfig(BaseModel):
    repos: dict[str, RepoConfig] = {}
