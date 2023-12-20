# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class GitHubAuth(BaseSettings):
    user: str
    token: str
    model_config = SettingsConfigDict(env_prefix='DDQA_GITHUB_')


class JiraAuth(BaseSettings):
    email: str
    token: str
    model_config = SettingsConfigDict(env_prefix='DDQA_JIRA_')


class AuthConfig(BaseModel):
    github: GitHubAuth
    jira: JiraAuth
