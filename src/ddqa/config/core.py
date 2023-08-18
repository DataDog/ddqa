# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import tomllib
from functools import cached_property
from typing import TYPE_CHECKING, Any

from ddqa.utils.fs import Path

if TYPE_CHECKING:
    from ddqa.models.config.app import AppConfig
    from ddqa.models.config.auth import AuthConfig
    from ddqa.models.config.repo import RepoConfig


class Config:
    def __init__(self, data: dict[str, Any]):
        self.__data = TypeResilientDict(data)

    @property
    def data(self) -> dict[str, Any]:
        return self.__data

    @cached_property
    def app(self) -> AppConfig:
        from ddqa.models.config.app import AppConfig

        return AppConfig(**self.data)

    @cached_property
    def auth(self) -> AuthConfig:
        from ddqa.models.config.auth import AuthConfig

        return AuthConfig(**self.data)

    @cached_property
    def repos(self) -> dict[str, RepoConfig]:
        from base64 import b64decode

        from ddqa.models.config.repo import ReposConfig

        if 'DDQA_REPO_CONFIG' in os.environ:
            default_repo_config_file = Path(os.environ['DDQA_REPO_CONFIG'])
        else:
            default_repo_config_file = Path.cwd() / '.ddqa' / 'config.toml'

        data = dict(self.data)
        repos = dict(data.get('repos', {}))
        for repo_name, original_repo_data in repos.items():
            repo_data = dict(original_repo_data)
            repo_config_file = (
                Path(repo_data['path']) / '.ddqa' / 'config.toml'
                if 'path' in repo_data and isinstance(repo_data['path'], str) and Path(repo_data['path']).is_dir()
                else default_repo_config_file
            )
            if repo_config_file.is_file():
                for key, value in tomllib.loads(repo_config_file.read_text()).items():
                    repo_data.setdefault(key, value)

            if (
                'global_config_source' in repo_data
                and isinstance(repo_data['global_config_source'], str)
                and not repo_data['global_config_source'].startswith('http')
            ):
                repo_data['global_config_source'] = b64decode(repo_data['global_config_source']).decode()

            repos[repo_name] = repo_data

        selected_repo = data.get('repo', '')
        if selected_repo and selected_repo in repos:
            repos = {selected_repo: repos[selected_repo]}

        data['repos'] = repos
        return ReposConfig(**data).repos


class TypeResilientDict(dict):
    """A `dict` whose `get` method also returns the default value when the key is not
    hashable, intended to make it configs with invalid types easier to navigate.
    """

    def get(self, key: Any, default: Any = None) -> Any:
        try:
            value = super().get(key, default)
            if isinstance(value, dict):
                return TypeResilientDict(value)
            return value
        except TypeError:
            return default
