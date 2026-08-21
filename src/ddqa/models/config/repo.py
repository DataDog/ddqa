# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field, HttpUrl, field_serializer, field_validator, model_validator

from ddqa.models.config.team import TeamConfig


class RepoConfig(BaseModel):
    # Exactly one of these two sources of the GitHub-to-Jira member mapping must be configured.
    datastore_id: str = ''
    global_config_source: HttpUrl | None = None
    qa_statuses: Annotated[list[str], Field(min_length=2)]
    teams: dict[str, TeamConfig]
    ignored_labels: list[str] = []

    # This comes from user configuration
    path: str = ''

    @field_serializer('global_config_source')
    def serialize_global_config_source(self, v: HttpUrl | None) -> str | None:
        return str(v) if v is not None else None

    @field_validator('teams')
    @classmethod
    def check_teams(cls, v):
        if not v:
            message = 'must have at least one team'
            raise ValueError(message)

        return v

    @model_validator(mode='after')
    def check_member_source(self):
        if bool(self.datastore_id) == bool(self.global_config_source):
            message = 'exactly one of `datastore_id` or `global_config_source` must be set'
            raise ValueError(message)

        return self


class ReposConfig(BaseModel):
    repos: dict[str, RepoConfig] = {}
