# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Any

from ddqa.utils.fs import Path

if TYPE_CHECKING:
    from ddqa.models.config.auth import JiraAuth
    from ddqa.models.config.repo import RepoConfig
    from ddqa.models.github import TestCandidate
    from ddqa.models.jira import JiraConfig
    from ddqa.utils.network import ResponsiveNetworkClient


class JiraClient:
    # https://developer.atlassian.com/cloud/jira/platform/rest/v2/api-group-myself/#api-rest-api-2-myself-get
    SELF_INSPECTION_API = '/rest/api/2/myself'

    # https://developer.atlassian.com/cloud/jira/platform/rest/v2/api-group-issues/#api-rest-api-2-issue-post
    ISSUE_CREATION_API = '/rest/api/2/issue'

    def __init__(self, config: JiraConfig, auth: JiraAuth, repo_config: RepoConfig, cache_dir: Path):
        self.__config = config
        self.__auth = auth
        self.__repo_config = repo_config
        self.__cache_dir = cache_dir
        self.__cached_current_user_id = ''

    @property
    def config(self) -> JiraConfig:
        return self.__config

    @property
    def auth(self) -> JiraAuth:
        return self.__auth

    @property
    def repo_config(self) -> RepoConfig:
        return self.__repo_config

    @cached_property
    def cache_dir(self) -> Path:
        return self.__cache_dir / 'jira'

    @cached_property
    def cached_user_id_file(self) -> Path:
        path = self.cache_dir / 'user_ids.json'
        path.parent.ensure_dir_exists()
        return path

    async def get_current_user_id(self, client: ResponsiveNetworkClient) -> str:
        if self.__cached_current_user_id:
            return self.__cached_current_user_id

        import json
        from base64 import urlsafe_b64encode
        from hashlib import sha256

        user_ids = {}
        if self.cached_user_id_file.is_file():
            user_ids.update(json.loads(self.cached_user_id_file.read_text()))

        key = urlsafe_b64encode(sha256(f'{self.auth.email}{self.auth.token}'.encode()).digest()).decode('ascii')
        if key in user_ids:
            self.__cached_current_user_id = user_ids[key]
            return self.__cached_current_user_id

        response = await self.__api_get(client, f'{self.config.jira_server}{self.SELF_INSPECTION_API}')
        response.raise_for_status()

        current_user_id = response.json()['accountId']
        user_ids[key] = current_user_id
        self.cached_user_id_file.write_atomic(json.dumps(user_ids), 'w', encoding='utf-8')

        self.__cached_current_user_id = current_user_id
        return self.__cached_current_user_id

    async def create_issues(
        self, client: ResponsiveNetworkClient, candidate: TestCandidate, assignments: dict[str, str]
    ) -> dict[str, str]:
        created_issues: dict[str, str] = {}
        common_fields: dict[str, Any] = {
            'description': self.__construct_body(candidate),
            'labels': [self.__format_label(self.repo_config.jira_statuses[0])],
            'reporter': {'id': await self.get_current_user_id(client)},
            'summary': candidate.title,
        }

        for team, member in assignments.items():
            team_config = self.repo_config.teams[team]
            fields = {
                'issuetype': {'name': team_config.jira_issue_type},
                'project': {'key': team_config.jira_project},
                **common_fields,
            }
            if member in self.config.members:
                fields['assignee'] = {'id': self.config.members[member]}

            response = await self.__api_post(
                client, f'{self.config.jira_server}{self.ISSUE_CREATION_API}', json={'fields': fields}
            )
            response.raise_for_status()

            created_issues[team] = f'{self.config.jira_server}/browse/{response.json()["key"]}'

        return created_issues

    async def __api_get(self, client: ResponsiveNetworkClient, *args, **kwargs):
        return await self.__api_request('GET', client, *args, **kwargs)

    async def __api_post(self, client: ResponsiveNetworkClient, *args, **kwargs):
        return await self.__api_request('POST', client, *args, **kwargs)

    async def __api_request(self, method: str, client: ResponsiveNetworkClient, *args, **kwargs):
        while True:
            response = await client.request(method, *args, auth=(self.auth.email, self.auth.token), **kwargs)

            # https://developer.atlassian.com/cloud/jira/platform/rate-limiting/#rate-limit-responses
            if 'Retry-After' in response.headers and (
                response.status_code == 429 or 500 <= response.status_code < 600  # noqa: PLR2004
            ):
                await client.wait(float(response.headers['Retry-After']) + 1)
                continue

            return response

    @staticmethod
    def __format_label(status: str) -> str:
        return f'ddqa-{status.strip()}'.lower().replace(' ', '-')

    @staticmethod
    def __construct_body(candidate: TestCandidate) -> str:
        """
        https://jira.atlassian.com/secure/WikiRendererHelpAction.jspa?section=all
        """
        import re

        metadata_lines = []
        if candidate.id.isdigit():
            metadata_lines.append(f'Pull request: [#{candidate.id}|{candidate.url}]')
        else:
            metadata_lines.append(f'Commit: [{candidate.id[:7]}|{candidate.url}]')

        if candidate.user:
            metadata_lines.append(f'Author: [{candidate.user}|https://github.com/{candidate.user}]')
        if candidate.labels:
            metadata_lines.append(f'Labels: {", ".join(f"{{{{{label.name}}}}}" for label in candidate.labels)}')

        metadata_section = '\n'.join(metadata_lines)

        # Convert hyperlinks
        body = re.sub(r'\[(.+?)]\((.+?)\)', r'[\1|\2]', candidate.body)

        # Convert headers
        body = re.sub(r'^#+', lambda match: f'h{len(match.group(0))}.', body, flags=re.MULTILINE)

        # Convert code blocks
        body = re.sub(
            r'```(\w*)$(.+?)```',
            lambda match: f'{{code:{match.group(1) or "plaintext"}}}{match.group(2)}{{code}}',
            body,
            flags=re.MULTILINE | re.DOTALL,
        )

        return f'{metadata_section}\n\n{body}'
