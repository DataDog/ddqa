# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
from functools import cached_property
from typing import TYPE_CHECKING

from rich.console import Console
from textual.app import App

from ddqa.app.style import CSS
from ddqa.config.core import Config
from ddqa.config.file import ConfigFile
from ddqa.utils.fs import Path

if TYPE_CHECKING:
    from textual.screen import Screen

    from ddqa.models.config.repo import RepoConfig
    from ddqa.utils.datadog import DatadogDatastore
    from ddqa.utils.git import GitRepository
    from ddqa.utils.github import GitHubRepository
    from ddqa.utils.jira import JiraClient


class Application(App):
    TITLE = 'Datadog QA'
    CSS = CSS

    def __init__(
        self,
        config_file: ConfigFile,
        cache_dir: str = '',
        color: bool | None = None,
        auto_mode: bool = False,  # noqa
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.__console = Console(
            force_terminal=color,
            no_color=color is False,
            markup=False,
            emoji=False,
            highlight=False,
        )
        self.auto_mode = auto_mode
        self.__config_file = config_file
        self.__cache_dir = cache_dir
        self.__queued_screens: list[tuple[str, Screen]] = []

    @property
    def config_file(self) -> ConfigFile:
        return self.__config_file

    @property
    def config(self) -> Config:
        return self.config_file.model

    @cached_property
    def repo(self) -> RepoConfig:
        return self.config.repos[self.config.app.repo]

    @cached_property
    def repo_path(self) -> Path:
        return Path(self.repo.path or os.getcwd()).expand()

    @cached_property
    def git(self) -> GitRepository:
        from ddqa.utils.git import GitRepository

        return GitRepository(self.repo_path)

    @cached_property
    def github(self) -> GitHubRepository:
        from ddqa.utils.github import GitHubRepository

        return GitHubRepository(self.git, self.config.auth.github, self.cache_dir)

    @cached_property
    def datadog(self) -> DatadogDatastore:
        from ddqa.utils.datadog import DatadogDatastore

        return DatadogDatastore(self.config.auth.datadog, self.cache_dir)

    @cached_property
    def jira(self) -> JiraClient:
        from ddqa.models.jira import JiraConfig
        from ddqa.utils.jira import JiraClient

        if self.repo.global_config_source:
            jira_config = JiraConfig(**self.github.load_global_config(self.repo.global_config_source))
        else:
            jira_config = JiraConfig(
                members=self.datadog.cache.get_datastore_members(self.repo.datastore_id),
                jira_server=self.datadog.cache.get_datastore_jira_server(self.repo.datastore_id),
            )

        return JiraClient(jira_config, self.config.auth.jira, self.repo, self.cache_dir)

    @cached_property
    def qa_statuses(self) -> dict[str, dict[str, str]]:
        qa_statuses: dict[str, dict[str, str]] = {}

        for team, config in self.repo.teams.items():
            statuses = {}
            if isinstance(config.jira_statuses, dict):
                if missing_statuses := set(self.repo.qa_statuses).difference(config.jira_statuses):
                    ordered_statuses = [status for status in self.repo.qa_statuses if status in missing_statuses]
                    message = f"repos -> {team} -> jira_statuses\n  Missing statuses: {', '.join(ordered_statuses)}"
                    raise ValueError(message)

                statuses.update(config.jira_statuses)
            else:
                if (num_statuses := len(config.jira_statuses)) != (expected_statuses := len(self.repo.qa_statuses)):
                    message = (
                        f'repos -> {team} -> jira_statuses\n'
                        f'  Expected {expected_statuses} statuses, found {num_statuses}'
                    )
                    raise ValueError(message)

                for repo_status, team_status in zip(self.repo.qa_statuses, config.jira_statuses, strict=False):
                    statuses[repo_status] = team_status

            qa_statuses[team] = statuses

        return qa_statuses

    @cached_property
    def cache_dir(self) -> Path:
        if self.__cache_dir:
            return Path(self.__cache_dir)
        elif self.config.app.cache_dir:
            return Path(self.config.app.cache_dir).expand()
        else:
            from platformdirs import user_cache_dir

            return Path(user_cache_dir('ddqa', appauthor=False))

    async def on_mount(self) -> None:
        for name, screen in self.__queued_screens:
            self.install_screen(screen, name)

        if self.config_errors():
            from ddqa.screens.configure import ConfigureScreen

            await self.push_screen(ConfigureScreen())
        elif not self.is_screen_installed('sync') and self.needs_syncing():
            from ddqa.screens.sync import SyncScreen

            await self.push_screen(SyncScreen(auto_mode=self.auto_mode))
        else:
            for name, _ in self.__queued_screens:
                await self.push_screen(name)

    def select_screen(self, name: str, screen: Screen) -> None:
        self.__queued_screens.append((name, screen))

    def print(self, *args, **kwargs) -> None:  # noqa: A003
        self.__console.print(*args, **kwargs)

    def needs_syncing(self) -> bool:
        if self.repo.global_config_source:
            has_members = bool(self.github.load_global_config(self.repo.global_config_source))
        else:
            has_members = bool(self.datadog.cache.get_datastore_members(self.repo.datastore_id))

        return not has_members or not any(self.github.cache.cache_dir_team_members.iterdir())

    def config_errors(self) -> list[str]:
        from pydantic import ValidationError

        errors = []

        try:
            repo_name = self.config.app.repo
        except ValidationError as e:
            for error in e.errors():
                errors.append(f"{' -> '.join(map(str, error['loc']))}\n  {error['msg']}")
        else:
            if not repo_name:
                errors.append('repo\n  Field required')
            else:
                try:
                    repos = self.config.repos
                except ValidationError as e:
                    for error in e.errors():
                        errors.append(f"{' -> '.join(map(str, error['loc']))}\n  {error['msg']}")
                else:
                    if repo_name not in repos:
                        errors.append(f'repo\n  unknown repository: {repo_name}')
                    else:
                        repo_path = repos[repo_name].path
                        if not repo_path:
                            errors.append(f'repos -> {repo_name} -> path\n  Field required')
                        elif not os.path.isdir(repo_path):
                            errors.append(f'repos -> {repo_name} -> path\n  Directory does not exist: {repo_path}')

                        try:
                            _ = self.qa_statuses
                        except Exception as e:
                            errors.append(str(e))

        needs_datadog_auth = True
        try:
            needs_datadog_auth = bool(self.repo.datastore_id)
        except Exception:
            pass

        from ddqa.models.config.auth import DatadogAuth, GitHubAuth, JiraAuth

        for prefix, model in (('github', GitHubAuth), ('jira', JiraAuth)):
            try:
                model(**self.config.data.get(prefix, {}))
            except ValidationError as e:
                for error in e.errors():
                    errors.append(f"{prefix} -> {' -> '.join(map(str, error['loc']))}\n  {error['msg']}")

        if needs_datadog_auth:
            try:
                DatadogAuth(**self.config.data.get('datadog', {}))
            except ValidationError as e:
                for error in e.errors():
                    errors.append(f"datadog -> {' -> '.join(map(str, error['loc']))}\n  {error['msg']}")

        return errors
