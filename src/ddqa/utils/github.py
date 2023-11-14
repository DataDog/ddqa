# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator, Iterable
from functools import cached_property
from typing import TYPE_CHECKING, Any

from ddqa.cache.github import GitHubCache
from ddqa.utils.fs import Path

if TYPE_CHECKING:
    from ddqa.models.config.auth import GitHubAuth
    from ddqa.models.github import TestCandidate
    from ddqa.utils.git import GitCommit, GitRepository
    from ddqa.utils.network import ResponsiveNetworkClient


class GitHubRepository:
    # https://docs.github.com/en/rest/search?apiVersion=2022-11-28#search-issues-and-pull-requests
    ISSUE_SEARCH_API = 'https://api.github.com/search/issues'

    # https://docs.github.com/en/rest/pulls/reviews?apiVersion=2022-11-28#list-reviews-for-a-pull-request
    PR_REVIEWS_API = 'https://api.github.com/repos/{org}/{repo}/pulls/{number}/reviews'

    # https://docs.github.com/en/rest/teams/members?apiVersion=2022-11-28#list-team-members
    TEAM_MEMBERS_API = 'https://api.github.com/orgs/{org}/teams/{team}/members'

    def __init__(self, repo: GitRepository, auth: GitHubAuth, cache_dir: Path):
        self.__repo = repo
        self.__auth = auth
        self.__cache = GitHubCache(cache_dir, self)

    @property
    def repo(self) -> GitRepository:
        return self.__repo

    @property
    def auth(self) -> GitHubAuth:
        return self.__auth

    @property
    def cache(self) -> GitHubCache:
        return self.__cache

    @cached_property
    def repo_id(self) -> str:
        # https://github.com/foo/bar.git -> foo/bar
        # or username@github.com:foo/bar.git -> foo/bar
        repo = self.repo.get_remote_url().split('github.com', 1)[1]
        return repo[1:].removesuffix('.git')

    @cached_property
    def org(self) -> str:
        return self.repo_id.partition('/')[0]

    @cached_property
    def repo_name(self) -> str:
        return self.repo_id.partition('/')[2]

    def load_global_config(self, source: str) -> dict[str, Any]:
        if not self.cache.global_config_file.is_file():
            return {}

        return json.loads(self.cache.global_config_file.read_text()).get(source, {})

    async def get_team_members(self, client: ResponsiveNetworkClient, team: str, *, refresh: bool = False) -> set[str]:
        members_file = self.cache.get_team_members_file(team)
        if refresh or not members_file.is_file():
            response = await self.__api_get(client, self.TEAM_MEMBERS_API.format(org=self.org, team=team))
            members_file.write_text(
                '\n'.join(
                    user['login']
                    for user in response.json()
                    # No bots
                    if user['type'] == 'User'
                )
            )

        return set(members_file.read_text().splitlines())

    async def get_candidate(self, client: ResponsiveNetworkClient, commit: GitCommit) -> TestCandidate:
        from ddqa.models.github import TestCandidate

        if cached_candidate_data := self.cache.get_cached_candidate_data_from_commit(commit.hash):
            return TestCandidate(**cached_candidate_data)

        candidate_data: dict[str, Any] = {}
        response = await self.__api_get(
            client,
            self.ISSUE_SEARCH_API,
            # https://docs.github.com/en/search-github/searching-on-github/searching-issues-and-pull-requests
            params={'q': f'sha:{commit.hash} repo:{self.repo_id} is:merged'},
        )
        pr_data = response.json()

        if not pr_data['items']:
            candidate_data['id'] = commit.hash
            candidate_data['title'] = commit.subject
            candidate_data['url'] = f'https://github.com/{self.repo_id}/commit/{commit.hash}'

            self.cache.cache_candidate_data(commit.hash, candidate_data)
            return TestCandidate(**candidate_data)

        pr_data = pr_data['items'][0]
        candidate_data['id'] = str(pr_data['number'])

        # This would only happen on the first encounter of a duplicate per commit hash
        if cached_candidate_data := self.cache.get_cached_candidate_data_from_pr_number(candidate_data['id']):
            self.cache.duplicate_cached_candidate_data_from_pr_number(commit.hash, candidate_data['id'])
            return TestCandidate(**cached_candidate_data)

        candidate_data['title'] = pr_data['title']
        candidate_data['url'] = f'https://github.com/{self.repo_id}/pull/{pr_data["number"]}'
        candidate_data['user'] = pr_data['user']['login']
        candidate_data['labels'] = [{'name': label['name'], 'color': label['color']} for label in pr_data['labels']]

        if pr_data['body'] is not None:
            # The API returns new line endings based on the user agent,
            # so we normalize to remove carriage returns on Windows
            candidate_data['body'] = '\n'.join(pr_data['body'].splitlines())

        response = await self.__api_get(
            client, self.PR_REVIEWS_API.format(org=self.org, repo=self.repo_name, number=candidate_data['id'])
        )
        pr_review_data = response.json()

        # Deduplicate
        candidate_data['reviewers'] = [
            {'name': name, 'association': association}
            for name, association in {
                reviewer['user']['login']: reviewer['author_association'].lower() for reviewer in pr_review_data
            }.items()
        ]

        self.cache.cache_candidate_data(commit.hash, candidate_data)
        return TestCandidate(**candidate_data)

    async def get_candidates(
        self,
        client: ResponsiveNetworkClient,
        commits: Iterable[GitCommit],
        ignored_labels: Iterable[str] | None = None,
    ) -> AsyncIterator[tuple[TestCandidate | None, int, int]]:
        processed_pr_numbers = set()
        ignored = 0
        for index, commit in enumerate(commits):
            model = await self.get_candidate(client, commit)

            if model.id.isdigit():
                if model.id in processed_pr_numbers:
                    ignored += 1
                    continue

                processed_pr_numbers.add(model.id)

                labels = {label.name for label in model.labels}
                if ignored_labels and any(label in labels for label in ignored_labels):
                    ignored += 1
                    yield None, index, ignored
                    continue

            yield model, index, ignored

    async def __api_get(self, client: ResponsiveNetworkClient, *args, **kwargs):
        retry_wait = 2
        while True:
            try:
                response = await client.get(*args, auth=(self.auth.user, self.auth.token), **kwargs)

                # https://docs.github.com/en/rest/overview/resources-in-the-rest-api?apiVersion=2022-11-28#rate-limiting
                # https://docs.github.com/en/rest/guides/best-practices-for-integrators?apiVersion=2022-11-28#dealing-with-rate-limits
                if response.status_code == 403 and response.headers['X-RateLimit-Remaining'] == '0':  # noqa: PLR2004
                    await client.wait(float(response.headers['X-RateLimit-Reset']) - time.time() + 1)
                    continue

                client.check_status(response, **kwargs)
            except Exception as e:
                await client.wait(retry_wait, context=str(e))
                retry_wait *= 2
                continue

            return response
