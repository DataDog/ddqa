# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import tomllib
from typing import cast

from ddqa.config.core import Config
from ddqa.config.utils import scrub_config
from ddqa.utils.fs import Path


class ConfigFile:
    def __init__(self, path: Path | None = None):
        self.path: Path = path or self.get_default_location()
        self.model = cast(Config, None)

    def save(self, content: str = ''):
        import tomli_w

        if not content:
            content = tomli_w.dumps(self.model.data)

        self.path.parent.ensure_dir_exists()
        self.path.write_atomic(content, 'w', encoding='utf-8')

    def load(self):
        self.model = Config(tomllib.loads(self.read()))

    def read(self) -> str:
        return self.path.read_text()

    def read_scrubbed(self) -> str:
        import tomli_w

        config = Config(tomllib.loads(self.read()))
        scrub_config(config.data)

        return tomli_w.dumps(config.data)

    def restore(self):
        import tomli_w

        config = Config({})
        default = config.app.model_dump()

        # Add these so the configuration error messages are more granular about missing keys
        default['github'] = {}
        default['jira'] = {}

        content = tomli_w.dumps(default)
        self.save(content)

        del config.app
        self.model = config

    @classmethod
    def get_default_location(cls) -> Path:
        from platformdirs import user_config_dir

        return Path(user_config_dir('ddqa', appauthor=False)) / 'config.toml'
