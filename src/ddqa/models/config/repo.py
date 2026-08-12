# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from ddqa.models.config.team import TeamConfig


class RepoConfig(BaseModel):
    datastore_id: str
    qa_statuses: Annotated[list[str], Field(min_length=2)]
    teams: dict[str, TeamConfig]
    ignored_labels: list[str] = []

    # This comes from user configuration
    path: str = ''

    @field_validator('teams')
    @classmethod
    def check_teams(cls, v):
        if not v:
            message = 'must have at least one team'
            raise ValueError(message)

        return v


class ReposConfig(BaseModel):
    repos: dict[str, RepoConfig] = {}
