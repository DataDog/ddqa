# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class GitHubAuth(BaseSettings):
    user: str
    token: str
    model_config = SettingsConfigDict(env_prefix='DDQA_GITHUB_')


class JiraAuth(BaseSettings):
    email: str
    token: str
    model_config = SettingsConfigDict(env_prefix='DDQA_JIRA_')


class DatadogAuth(BaseSettings):
    api_key: str
    app_key: str
    model_config = SettingsConfigDict(env_prefix='DDQA_DATADOG_')


class AuthConfig(BaseModel):
    github: GitHubAuth
    jira: JiraAuth
    # No `[datadog]` config table is required: credentials are commonly supplied as
    # ephemeral env vars (e.g. via `dd-auth`) rather than stored persistently. Only
    # constructed lazily since it's only needed by repos configured with `datastore_id`.
    datadog_data: dict = Field(default_factory=dict, alias='datadog')

    @property
    def datadog(self) -> DatadogAuth:
        return DatadogAuth(**self.datadog_data)
