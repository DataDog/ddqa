# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
def test_default_scrubbed(ddqa, config_file, helpers):
    config_file.model.data.update(config_file.model.app.dict())
    config_file.model.data.update({'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo', 'token': 'bar'}})
    config_file.save()

    result = ddqa('config', 'show')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        repo = ""
        cache_dir = ""
        pr_labels = []

        [github]
        user = "foo"
        token = "*****"

        [jira]
        email = "foo"
        token = "*****"
        """,
        terminal=True,
    )


def test_reveal(ddqa, config_file, helpers):
    config_file.model.data.update(config_file.model.app.dict())
    config_file.model.data.update({'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo', 'token': 'bar'}})
    config_file.save()

    result = ddqa('config', 'show', '-a')

    assert result.exit_code == 0, result.output
    assert result.output == helpers.dedent(
        """
        repo = ""
        cache_dir = ""
        pr_labels = []

        [github]
        user = "foo"
        token = "bar"

        [jira]
        email = "foo"
        token = "bar"
        """,
        terminal=True,
    )
