# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import os
import pathlib
import sys
from collections.abc import Generator
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from ddqa.utils.structures import EnvVars

if TYPE_CHECKING:
    from _typeshed import FileDescriptorLike

# There is special recognition in Mypy for `sys.platform`, not `os.name`
# https://github.com/python/cpython/blob/09d7319bfe0006d9aa3fc14833b69c24ccafdca6/Lib/pathlib.py#L957
if sys.platform == 'win32':
    _PathBase = pathlib.WindowsPath
else:
    _PathBase = pathlib.PosixPath

disk_sync = os.fsync
# https://mjtsai.com/blog/2022/02/17/apple-ssd-benchmarks-and-f_fullsync/
# https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/fsync.2.html
if sys.platform == 'darwin':
    import fcntl

    if hasattr(fcntl, 'F_FULLFSYNC'):

        def disk_sync(fd: FileDescriptorLike) -> None:
            fcntl.fcntl(fd, fcntl.F_FULLFSYNC)


class Path(_PathBase):
    def ensure_dir_exists(self) -> None:
        self.mkdir(parents=True, exist_ok=True)

    def read_text(self, encoding: str | None = None, errors: str | None = None) -> str:
        if encoding is None:
            encoding = 'utf-8'

        return super().read_text(encoding=encoding, errors=errors)

    def expand(self) -> Path:
        return Path(os.path.expanduser(os.path.expandvars(self)))

    def resolve(self, strict: bool = False) -> Path:  # noqa: ARG002, FBT001, FBT002
        # https://bugs.python.org/issue38671
        return Path(os.path.realpath(self))

    def remove(self) -> None:
        if self.is_file():
            os.remove(self)
        elif self.is_dir():
            import shutil

            shutil.rmtree(self, ignore_errors=False)

    def write_atomic(self, data: str | bytes, *args: Any, **kwargs: Any) -> None:
        from tempfile import mkstemp

        fd, path = mkstemp(dir=self.parent)
        with os.fdopen(fd, *args, **kwargs) as f:
            f.write(data)
            f.flush()
            disk_sync(fd)

        os.replace(path, self)

    @contextmanager
    def as_cwd(self, *args: Any, **kwargs: Any) -> Generator[Path, None, None]:
        origin = os.getcwd()
        os.chdir(self)

        try:
            if args or kwargs:
                with EnvVars(*args, **kwargs):
                    yield self
            else:
                yield self
        finally:
            os.chdir(origin)
