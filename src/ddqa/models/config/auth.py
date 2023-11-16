# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from pydantic import BaseModel, BaseSettings


class GitHubAuth(BaseSettings):  # type: ignore
    user: str
    token: str

    class Config:
        env_prefix = 'DDQA_GITHUB_'


class JiraAuth(BaseSettings):  # type: ignore
    email: str
    token: str

    class Config:
        env_prefix = 'DDQA_JIRA_'


class AuthConfig(BaseModel):
    github: GitHubAuth
    jira: JiraAuth
