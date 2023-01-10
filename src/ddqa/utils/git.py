# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ddqa.utils.fs import Path


class GitCommit:
    def __init__(self, *, hash: str, subject: str):  # noqa: A002
        self.__hash = hash
        self.__subject = subject

    @property
    def hash(self) -> str:  # noqa: A003
        return self.__hash

    @property
    def subject(self) -> str:
        return self.__subject


class GitRepository:
    def __init__(self, path: Path):
        self.__path = path

    @property
    def path(self) -> Path:
        return self.__path

    def get_remote_url(self) -> str:
        return self.capture('config', '--get', 'remote.origin.url').strip()

    def get_current_branch(self) -> str:
        return self.capture('rev-parse', '--abbrev-ref', 'HEAD').strip()

    def get_latest_commit_hash(self) -> str:
        return self.capture('rev-parse', 'HEAD').strip()

    def get_mutually_exclusive_commits(self, upstream: str, head: str) -> list[GitCommit]:
        commits = []
        for line in self.capture('cherry', '-v', upstream, head).splitlines():
            sign, commit_hash, commit_subject = line.split(maxsplit=2)

            # Cherry-picked commit
            if sign == '-':
                continue

            commits.append(GitCommit(hash=commit_hash, subject=commit_subject))

        return commits

    def capture(self, *args) -> str:
        import subprocess

        try:
            process = subprocess.run(
                ['git', *args],
                cwd=str(self.path),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                encoding='utf-8',
                check=True,
            )
        except subprocess.CalledProcessError as e:
            message = f'{str(e)[:-1]}:\n{e.output}'
            raise OSError(message) from None

        return process.stdout
