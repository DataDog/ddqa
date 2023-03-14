# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterable
from functools import cached_property
from typing import TYPE_CHECKING, Any

from ddqa.utils.fs import Path

if TYPE_CHECKING:
    from ddqa.models.config.auth import JiraAuth
    from ddqa.models.config.repo import RepoConfig
    from ddqa.models.github import TestCandidate
    from ddqa.models.jira import JiraConfig, JiraIssue
    from ddqa.utils.network import ResponsiveNetworkClient


class JiraClient:
    PAGINATION_RESULT_SIZE = 100

    # https://developer.atlassian.com/cloud/jira/platform/rest/v2/api-group-myself/#api-rest-api-2-myself-get
    SELF_INSPECTION_API = '/rest/api/2/myself'

    # https://developer.atlassian.com/cloud/jira/platform/rest/v2/api-group-issues/#api-rest-api-2-issue-post
    ISSUE_API = '/rest/api/2/issue'

    # https://developer.atlassian.com/cloud/jira/platform/rest/v2/api-group-issues/#api-rest-api-2-issue-issueidorkey-transitions-get
    TRANSITIONS_API = '/rest/api/2/issue/{issue_key}/transitions'

    # https://developer.atlassian.com/cloud/jira/platform/rest/v2/api-group-issue-search/#api-rest-api-2-search-post
    SEARCH_API = '/rest/api/2/search'

    def __init__(self, config: JiraConfig, auth: JiraAuth, repo_config: RepoConfig, cache_dir: Path):
        self.__config = config
        self.__auth = auth
        self.__repo_config = repo_config
        self.__cache_dir = cache_dir
        self.__cached_current_user_id = ''

        # project key -> issue type -> status name -> transition ID
        self.__transitions: dict[str, dict[str, dict[str, str]]] = {}

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

    @cached_property
    def cache_dir_projects(self) -> Path:
        path = self.cache_dir / 'projects'
        path.ensure_dir_exists()
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
        current_user_id = response.json()['accountId']
        user_ids[key] = current_user_id
        self.cached_user_id_file.write_atomic(json.dumps(user_ids), 'w', encoding='utf-8')

        self.__cached_current_user_id = current_user_id
        return self.__cached_current_user_id

    async def create_issues(
        self,
        client: ResponsiveNetworkClient,
        candidate: TestCandidate,
        labels: tuple[str, ...],
        assignments: dict[str, str],
    ) -> dict[str, str]:
        created_issues: dict[str, str] = {}
        common_fields: dict[str, Any] = {
            'description': self.__construct_body(candidate),
            'labels': list(labels),
            'summary': candidate.title,
        }

        for team, member in assignments.items():
            team_config = self.repo_config.teams[team]
            fields: dict[str, Any] = {
                'issuetype': {'name': team_config.jira_issue_type},
                'project': {'key': team_config.jira_project},
                **common_fields,
            }
            if member in self.config.members:
                fields['assignee'] = {'id': self.config.members[member]}
            if team_config.jira_component:
                fields['components'] = [{'name': team_config.jira_component}]

            response = await self.__api_post(
                client, f'{self.config.jira_server}{self.ISSUE_API}', json={'fields': fields}
            )
            created_issues[team] = f'{self.construct_issue_url(response.json()["key"])}'

        return created_issues

    async def search_issues(self, client: ResponsiveNetworkClient, labels: tuple[str, ...]) -> AsyncIterator[JiraIssue]:
        from ddqa.models.jira import JiraIssue

        offset = 0
        query = (
            f'project in {self.__format_jql_list(team.jira_project for team in self.repo_config.teams.values())}'
            f' and '
            f'labels in {self.__format_jql_list(labels)}'
        )

        while True:
            response = await self.__api_post(
                client,
                f'{self.config.jira_server}{self.SEARCH_API}',
                json={
                    'jql': query,
                    'fields': [
                        'assignee',
                        'components',
                        'description',
                        'issuetype',
                        'labels',
                        'project',
                        'status',
                        'summary',
                        'updated',
                    ],
                    'maxResults': self.PAGINATION_RESULT_SIZE,
                    'startAt': offset,
                },
            )

            data = response.json()
            for issue in data['issues']:
                offset += 1

                jira_issue = JiraIssue(
                    key=issue['key'],
                    project=issue['fields'].pop('project')['key'],
                    type=issue['fields'].pop('issuetype')['name'],
                    components=[component['name'] for component in issue['fields'].pop('components')],
                    **issue['fields'],
                )
                await self.__get_transitions(client, jira_issue)

                yield jira_issue

            if offset >= data['total']:
                break

    async def update_issue_status(self, client: ResponsiveNetworkClient, issue: JiraIssue, status: str) -> JiraIssue:
        from datetime import datetime

        await self.__api_post(
            client,
            f'{self.config.jira_server}{self.TRANSITIONS_API.format(issue_key=issue.key)}',
            json={'transition': {'id': self.__transitions[issue.project][issue.type][status]}},
        )

        new_issue = issue.copy(deep=True)
        new_issue.status.name = status
        new_issue.updated = datetime.now(tz=issue.updated.tzinfo)

        return new_issue

    async def __get_transitions(self, client: ResponsiveNetworkClient, issue: JiraIssue) -> None:
        issue_types = self.__transitions.setdefault(issue.project, {})
        if issue.type in issue_types:
            return

        transitions_file = self.cache_dir_projects / issue.project / 'transitions.json'
        if transitions_file.is_file():
            issue_types.update(json.loads(transitions_file.read_text()))
            if issue.type in issue_types:
                return

        response = await self.__api_get(
            client, f'{self.config.jira_server}{self.TRANSITIONS_API.format(issue_key=issue.key)}'
        )

        transitions = issue_types.setdefault(issue.type, {})
        for data in response.json()['transitions']:
            transitions[data['to']['name']] = data['id']

        transitions_file.parent.ensure_dir_exists()
        transitions_file.write_atomic(json.dumps(issue_types), 'w', encoding='utf-8')

    async def __api_get(self, client: ResponsiveNetworkClient, *args, **kwargs):
        return await self.__api_request('GET', client, *args, **kwargs)

    async def __api_post(self, client: ResponsiveNetworkClient, *args, **kwargs):
        return await self.__api_request('POST', client, *args, **kwargs)

    async def __api_request(self, method: str, client: ResponsiveNetworkClient, *args, **kwargs):
        retry_wait = 2
        while True:
            try:
                response = await client.request(method, *args, auth=(self.auth.email, self.auth.token), **kwargs)

                # https://developer.atlassian.com/cloud/jira/platform/rate-limiting/#rate-limit-responses
                if 'Retry-After' in response.headers and (
                    response.status_code == 429 or 500 <= response.status_code < 600  # noqa: PLR2004
                ):
                    await client.wait(float(response.headers['Retry-After']) + 1)
                    continue

                client.check_status(response, **kwargs)
            except Exception as e:
                await client.wait(retry_wait, context=str(e))
                retry_wait *= 2
                continue

            return response

    def construct_issue_url(self, issue_key: str) -> str:
        return f'{self.config.jira_server}/browse/{issue_key}'

    @staticmethod
    def format_label(status: str) -> str:
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

    @staticmethod
    def __format_jql_list(items: Iterable[str]) -> str:
        normalized_items = [f'"{item}"' for item in items]
        return f'({", ".join(normalized_items)})'
