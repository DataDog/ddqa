# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import shutil


def test(ddqa, helpers, temp_dir):
    result = ddqa('--cache-dir', temp_dir, 'cache', 'purge')

    assert not temp_dir.exists()
    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        Removing {temp_dir}...
        """,
        terminal=True,
    )


def test_not_exist(ddqa, helpers, temp_dir):
    shutil.rmtree(str(temp_dir))
    assert not temp_dir.exists()

    result = ddqa('--cache-dir', temp_dir, 'cache', 'purge')

    assert not temp_dir.exists()
    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        Cache directory {temp_dir} does not exist.
        """,
        terminal=True,
    )
