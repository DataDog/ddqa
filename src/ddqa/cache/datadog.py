# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import json
from functools import cached_property
from typing import Any

from ddqa.utils.fs import Path


class DatadogCache:
    def __init__(self, cache_dir: Path) -> None:
        self.__cache_dir = cache_dir

    @cached_property
    def cache_dir(self) -> Path:
        return self.__cache_dir / 'datadog'

    @cached_property
    def datastores_file(self) -> Path:
        path = self.cache_dir / 'datastores.json'
        path.parent.ensure_dir_exists()
        return path

    def __load(self) -> dict[str, Any]:
        if not self.datastores_file.is_file():
            return {}

        return json.loads(self.datastores_file.read_text())

    def get_datastore_modified_at(self, datastore_id: str) -> str | None:
        return self.__load().get(datastore_id, {}).get('modified_at')

    def get_datastore_members(self, datastore_id: str) -> dict[str, str]:
        return self.__load().get(datastore_id, {}).get('members', {})

    def save_datastore(self, datastore_id: str, modified_at: str, members: dict[str, str]) -> None:
        data = self.__load()
        data[datastore_id] = {'modified_at': modified_at, 'members': members}
        self.datastores_file.write_atomic(json.dumps(data), 'w', encoding='utf-8')
