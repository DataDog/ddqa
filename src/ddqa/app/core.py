# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import asyncio
import os
from functools import cached_property
from typing import TYPE_CHECKING

from textual.app import App

from ddqa.app.style import CSS
from ddqa.config.core import Config
from ddqa.config.file import ConfigFile
from ddqa.utils.fs import Path

if TYPE_CHECKING:
    from textual.screen import Screen

    from ddqa.models.config.repo import RepoConfig
    from ddqa.utils.git import GitRepository
    from ddqa.utils.github import GitHubRepository
    from ddqa.utils.jira import JiraClient


class Application(App):
    TITLE = 'Datadog QA'
    CSS = CSS

    def __init__(self, config_file: ConfigFile, cache_dir: str = '', *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.config_file = config_file
        self.__cache_dir = cache_dir
        self.__queued_screens: list[tuple[str, Screen]] = []

        # Hold references to long-running background tasks
        self.__background_tasks: list[asyncio.Task] = []

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
    def jira(self) -> JiraClient:
        from ddqa.models.jira import JiraConfig
        from ddqa.utils.jira import JiraClient

        jira_config = JiraConfig(**self.github.load_global_config(self.repo.global_config_source))
        return JiraClient(jira_config, self.config.auth.jira, self.repo, self.cache_dir)

    @cached_property
    def cache_dir(self) -> Path:
        if self.__cache_dir:
            return Path(self.__cache_dir)
        elif self.config.app.cache_dir:
            return Path(self.config.app.cache_dir).expand()
        else:
            from platformdirs import user_cache_dir

            return Path(user_cache_dir('ddqa', appauthor=False))

    def action_exit(self) -> None:
        self.exit()

    async def on_mount(self) -> None:
        for name, screen in self.__queued_screens:
            self.install_screen(screen, name)

        if self.config_errors():
            from ddqa.screens.configure import ConfigureScreen

            await self.push_screen(ConfigureScreen())
        elif not self.is_screen_installed('sync') and self.needs_syncing():
            from ddqa.screens.sync import SyncScreen

            await self.push_screen(SyncScreen())
        else:
            for name, _ in self.__queued_screens:
                await self.push_screen(name)

    def select_screen(self, name: str, screen: Screen) -> None:
        self.__queued_screens.append((name, screen))

    def run_in_background(self, coroutine) -> None:
        self.__background_tasks.append(asyncio.create_task(coroutine))

    def needs_syncing(self) -> bool:
        return not self.github.load_global_config(self.repo.global_config_source) or not any(
            self.github.cache_dir_team_members.iterdir()
        )

    def config_errors(self) -> list[str]:
        from pydantic import ValidationError

        errors = []

        try:
            repo_name = self.config.app.repo
        except ValidationError as e:
            for error in e.errors():
                errors.append(f'{" -> ".join(map(str, error["loc"]))}\n  {error["msg"]}')
        else:
            if not repo_name:
                errors.append('repo\n  field required')
            else:
                try:
                    repos = self.config.repos
                except ValidationError as e:
                    for error in e.errors():
                        errors.append(f'{" -> ".join(map(str, error["loc"]))}\n  {error["msg"]}')
                else:
                    if repo_name not in repos:
                        errors.append(f'repo\n  unknown repository: {repo_name}')
                    else:
                        repo_path = repos[repo_name].path
                        if not repo_path:
                            errors.append(f'repos -> {repo_name} -> path\n  field required')
                        elif not os.path.isdir(repo_path):
                            errors.append(f'repos -> {repo_name} -> path\n  directory does not exist: {repo_path}')

        try:
            _ = self.config.auth
        except ValidationError as e:
            for error in e.errors():
                errors.append(f'{" -> ".join(map(str, error["loc"]))}\n  {error["msg"]}')

        return errors
