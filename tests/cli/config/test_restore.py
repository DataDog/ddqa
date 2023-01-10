# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
def test_standard(ddqa, config_file, helpers):
    config_file.model.data.update({'repo': 'foo'})
    config_file.save()

    result = ddqa('config', 'restore')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        Settings were successfully restored.
        """,
        terminal=True,
    )

    config_file.load()
    assert config_file.model.app.repo == ''


def test_allow_invalid_config(ddqa, config_file, helpers):
    config_file.save(
        helpers.dedent(
            """
            repo = [""]
            """
        )
    )

    result = ddqa('config', 'restore')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        Settings were successfully restored.
        """,
        terminal=True,
    )
