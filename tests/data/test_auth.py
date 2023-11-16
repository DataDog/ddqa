# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from ddqa.models.config.auth import GitHubAuth, JiraAuth
from ddqa.utils.structures import EnvVars


class TestGitHubAuth:
    def test_load_from_env_variables(self):
        with EnvVars({'DDQA_GITHUB_USER': 'my_user', 'DDQA_GITHUB_TOKEN': 'my_token'}):
            auth = GitHubAuth()
            assert auth.user == 'my_user'
            assert auth.token == 'my_token'


class TestJiraAuth:
    def test_load_from_env_variables(self):
        with EnvVars({'DDQA_JIRA_EMAIL': 'my_email', 'DDQA_JIRA_TOKEN': 'my_token'}):
            auth = JiraAuth()
            assert auth.email == 'my_email'
            assert auth.token == 'my_token'
