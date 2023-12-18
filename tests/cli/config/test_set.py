# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
def test(ddqa, helpers):
    result = ddqa('config', 'set', 'github.user', 'new-user')

    assert result.exit_code == 0, result.output
    assert not result.output

    result = ddqa('config', 'show')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        repo = ""
        cache_dir = ""
        pr_labels = []

        [github]
        user = "new-user"

        [jira]
        """,
        terminal=True,
    )
