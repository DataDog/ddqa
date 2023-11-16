# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
from functools import cached_property
from typing import TYPE_CHECKING, Any

from ddqa.utils.fs import Path

if TYPE_CHECKING:
    from ddqa.utils.github import GitHubRepository


class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        return list(obj)


class GitHubCache:
    def __init__(self, cache_dir: Path, github_repo: GitHubRepository) -> None:
        super().__init__()
        self.__cache_dir = cache_dir
        self.__github_repo = github_repo

    @cached_property
    def cache_dir(self) -> Path:
        return self.__cache_dir / 'github' / self.__github_repo.org / self.__github_repo.repo_name

    @cached_property
    def cache_dir_commits(self) -> Path:
        directory = self.cache_dir / 'commits'
        directory.ensure_dir_exists()
        return directory

    @cached_property
    def cache_dir_pull_requests(self) -> Path:
        directory = self.cache_dir / 'pull_requests'
        directory.ensure_dir_exists()
        return directory

    @cached_property
    def cache_dir_team_members(self) -> Path:
        directory = self.cache_dir / 'team_members'
        directory.ensure_dir_exists()
        return directory

    @cached_property
    def global_config_file(self) -> Path:
        path = self.cache_dir / 'config.json'
        path.parent.ensure_dir_exists()
        return path

    def save_global_config(self, source: str, global_config: dict[str, Any]) -> None:
        data = {}
        if self.global_config_file.is_file():
            data.update(json.loads(self.global_config_file.read_text()))

        data[source] = global_config
        self.global_config_file.write_atomic(json.dumps(data), 'w', encoding='utf-8')

    def get_team_members_file(self, team):
        return self.cache_dir_team_members / f'{team}.txt'

    def get_cached_candidate_data_from_commit(self, commit_hash: str):
        directory = self.cache_dir_commits / commit_hash
        if not directory.is_dir():
            return

        entries = list(directory.iterdir())
        if not entries:
            return

        data = entries[0]
        if data.stem == 'no_pr':
            return json.loads(data.read_text())
        elif (cached_candidate_data := self.cache_dir_pull_requests / f'{data.name}.json').is_file():
            return json.loads(cached_candidate_data.read_text())

    def get_cached_candidate_data_from_pr_number(self, number: str):
        if (cached_candidate_data := self.cache_dir_pull_requests / f'{number}.json').is_file():
            return json.loads(cached_candidate_data.read_text())

    def duplicate_cached_candidate_data_from_pr_number(self, commit_hash: str, number: str):
        directory = self.cache_dir_commits / commit_hash
        directory.ensure_dir_exists()
        (directory / number).touch()

    def cache_candidate_data(self, commit_hash: str, candidate_data: dict):
        directory = self.cache_dir_commits / commit_hash
        directory.ensure_dir_exists()

        if candidate_data['id'].isdigit():
            (self.cache_dir_pull_requests / f'{candidate_data["id"]}.json').write_text(
                json.dumps(candidate_data, cls=SetEncoder)
            )
            (directory / candidate_data['id']).touch()
        else:
            (directory / 'no_pr.json').write_text(json.dumps(candidate_data, cls=SetEncoder))
