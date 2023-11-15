# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
def test(ddqa, helpers, temp_dir):
    result = ddqa('--cache-dir', temp_dir, 'cache', 'find')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        {temp_dir}
        """,
        terminal=True,
    )
