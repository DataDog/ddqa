# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, HttpUrl, field_serializer, field_validator

from ddqa.models.config.team import TeamConfig


class RepoConfig(BaseModel):
    global_config_source: HttpUrl
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

    @field_serializer('global_config_source')
    def serialize_global_config_source(self, global_config_source: HttpUrl, _info):
        return str(global_config_source) if global_config_source else None


class ReposConfig(BaseModel):
    repos: dict[str, RepoConfig] = {}
