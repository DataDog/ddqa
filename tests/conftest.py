# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import errno
import os
import shutil
import stat
import subprocess
from collections.abc import Generator
from tempfile import TemporaryDirectory
from typing import Any

import pytest
import tomli_w
from click.testing import CliRunner

from ddqa.app.core import Application
from ddqa.config.constants import AppEnvVars, ConfigEnvVars
from ddqa.config.file import ConfigFile
from ddqa.utils.fs import Path


class TestApplication(Application):
    def configure(
        self,
        repo: Path,
        *,
        caching: bool = False,
        data: dict[str, Any] | None = None,
        github_teams: dict[str, list[str]] | None = None,
    ):
        self.config_file.model.data['repo'] = 'test'
        self.config_file.model.data['repos'] = {'test': {'path': str(repo)}}

        if caching:
            self.cache_dir = repo.parent / 'cache'

        if data is not None:
            self.config_file.model.data.update(data)

        self.config_file.save()

        if github_teams is not None:
            for team, members in github_teams.items():
                (self.github.cache_dir_team_members / f'{team}.txt').write_text('\n'.join(members))

    def save_repo_config(self, repo_config: dict[str, Any]) -> None:
        Path(self.repo.path, '.ddqa', 'config.toml').write_text(tomli_w.dumps(repo_config))
        self.config_file.load()
        del self.repo


class BoundCliRunner(CliRunner):
    def __init__(self, command):
        super().__init__()
        self.__command = command

    def __call__(self, *args, **kwargs):
        # Exceptions should always be handled
        kwargs.setdefault('catch_exceptions', False)

        return self.invoke(self.__command, args, **kwargs)


@pytest.fixture(scope='session')
def ddqa():
    from ddqa import cli

    return BoundCliRunner(cli.ddqa)


@pytest.fixture(autouse=True)
def config_file(tmp_path) -> ConfigFile:
    path = Path(tmp_path, 'config.toml')
    os.environ[ConfigEnvVars.CONFIG] = str(path)
    config = ConfigFile(path)
    config.restore()
    config.load()
    return config


@pytest.fixture
def app(config_file):
    return TestApplication(config_file, os.environ[ConfigEnvVars.CACHE])


@pytest.fixture
def temp_dir(tmp_path) -> Path:
    path = Path(tmp_path, 'temp')
    path.mkdir()
    return path


@pytest.fixture(scope='session', autouse=True)
def isolation() -> Generator[Path, None, None]:
    with TemporaryDirectory() as d:
        directory = Path(d).resolve()

        cache_dir = directory / 'cache'
        cache_dir.mkdir()

        repo_config_file = directory / '.ddqa' / 'config.toml'
        repo_config_file.parent.ensure_dir_exists()
        repo_config_file.write_text(
            tomli_w.dumps(
                {
                    'global_config_source': 'https://www.google.com',
                    'jira_statuses': ['TODO', 'IN PROGRESS', 'DONE'],
                    'teams': {
                        'foo': {
                            'jira_project': 'FOO',
                            'jira_issue_type': 'Foo-Task',
                            'jira_statuses': {'TODO': 'Backlog', 'IN PROGRESS': 'Sprint', 'DONE': 'Done'},
                            'github_team': 'foo-team',
                        },
                    },
                }
            )
        )

        default_env_vars = {
            AppEnvVars.NO_COLOR: '1',
            ConfigEnvVars.CACHE: str(cache_dir),
            'DDQA_REPO_CONFIG': str(repo_config_file),
            # 2.5x the default of 80x24
            'COLUMNS': '200',
            'LINES': '60',
        }
        with directory.as_cwd(default_env_vars):
            yield directory


@pytest.fixture(scope='session')
def helpers():
    # https://docs.pytest.org/en/latest/writing_plugins.html#assertion-rewriting
    pytest.register_assert_rewrite('tests.helpers.api')

    from .helpers import api

    return api


@pytest.fixture
def git_repository(isolation, temp_dir):
    path = temp_dir / 'git_repo'
    path.mkdir()

    shutil.copytree(isolation / '.ddqa', path / '.ddqa')

    options = {
        'cwd': str(path),
        'stdout': subprocess.PIPE,
        'stderr': subprocess.PIPE,
        'encoding': 'utf-8',
        'check': True,
    }

    try:
        subprocess.run(['git', 'init'], **options)
        subprocess.run(['git', 'config', '--local', 'user.name', 'foo'], **options)
        subprocess.run(['git', 'config', '--local', 'user.email', 'foo@bar.baz'], **options)
        subprocess.run(['git', 'commit', '-m', 'init', '--allow-empty'], **options)

        yield path
    finally:
        shutil.rmtree(path, ignore_errors=False, onerror=handle_remove_readonly)


def handle_remove_readonly(func, path, exc):  # no cov
    # PermissionError: [WinError 5] Access is denied: '...\\.git\\...'
    if func in (os.rmdir, os.remove, os.unlink) and exc[1].errno == errno.EACCES:
        os.chmod(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)  # noqa: S103
        func(path)
    else:
        raise
