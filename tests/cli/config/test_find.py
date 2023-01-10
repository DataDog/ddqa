# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import os

import pytest

from ddqa.config.constants import ConfigEnvVars


def test_copy(ddqa, config_file, mocker):
    mock = mocker.patch('pyperclip.copy')
    result = ddqa('config', 'find', '-c')

    assert result.exit_code == 0, result.output
    mock.assert_called_once_with(str(config_file.path))


def test_pipe_to_editor(ddqa, config_file, helpers):
    config_file.path = config_file.path.parent / 'a space' / 'config.toml'
    config_file.path.parent.ensure_dir_exists()
    config_file.restore()
    os.environ[ConfigEnvVars.CONFIG] = str(config_file.path)

    result = ddqa('config', 'find')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        "{config_file.path}"
        """,
        terminal=True,
    )


def test_standard(ddqa, config_file, helpers):
    config_path = str(config_file.path)
    if ' ' in config_path:  # no cov
        pytest.xfail('Path to system temporary directory contains spaces')

    result = ddqa('config', 'find')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        {config_path}
        """,
        terminal=True,
    )
