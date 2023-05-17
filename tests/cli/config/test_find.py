# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
def test(ddqa, config_file, helpers):
    result = ddqa('config', 'find')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        f"""
        {config_file.path}
        """,
        terminal=True,
    )
