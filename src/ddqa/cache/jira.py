# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import json
from functools import cached_property

from ddqa.models.jira import JiraIssue
from ddqa.utils.fs import Path


class JiraCache:
    def __init__(self, cache_dir: Path) -> None:
        self.__cache_dir = cache_dir

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

    def get_transitions_file(self, issue: JiraIssue) -> Path:
        path = self.cache_dir_projects / issue.project / 'transitions.json'
        path.parent.ensure_dir_exists()
        return path

    def get_user_ids(self) -> dict[str, str]:
        if self.cached_user_id_file.is_file():
            return json.loads(self.cached_user_id_file.read_text())

        return {}

    def get_user_id(self, email: str, token: str) -> str | None:
        user_ids = self.get_user_ids()
        return user_ids.get(self.__get_user_key(email, token))

    def save_user_id(self, email: str, token: str, user_id: str) -> None:
        user_ids = self.get_user_ids()
        user_ids[self.__get_user_key(email, token)] = user_id
        self.cached_user_id_file.write_atomic(json.dumps(user_ids), 'w', encoding='utf-8')

    def get_transitions(self, issue: JiraIssue) -> dict[str, dict[str, str]]:
        transitions_file = self.cache_dir_projects / issue.project / 'transitions.json'

        if transitions_file.is_file():
            return json.loads(transitions_file.read_text())

        return {}

    def save_transitions(self, issue: JiraIssue, transitions: dict[str, dict[str, str]]) -> None:
        transitions_file = self.get_transitions_file(issue)
        transitions_file.write_atomic(json.dumps(transitions), 'w', encoding='utf-8')

    @staticmethod
    def __get_user_key(email: str, token: str) -> str:
        from base64 import urlsafe_b64encode
        from hashlib import sha256

        return urlsafe_b64encode(sha256(f'{email}{token}'.encode()).digest()).decode('ascii')
