# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from textual.widgets import Button, Input, TextLog

from ddqa.screens.configure import (
    GitHubTokenInput,
    GitHubUserInput,
    JiraEmailInput,
    JiraTokenInput,
    RepoNameInput,
    RepoPathInput,
)


async def test_default_state(app, helpers):
    async with app.run_test():
        inputs = list(app.query(Input).results())
        expected_inputs = (
            RepoNameInput,
            RepoPathInput,
            GitHubUserInput,
            GitHubTokenInput,
            JiraEmailInput,
            JiraTokenInput,
        )

        for input_instance, expected_type in zip(inputs, expected_inputs, strict=True):
            assert isinstance(input_instance, expected_type)

        save_button = app.query_one(Button)
        assert save_button.disabled is True

        text_log = app.query_one(TextLog)
        assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
            """
            Configuration errors
            ├── repo
            │     field required
            ├── github -> user
            │     field required
            ├── github -> token
            │     field required
            ├── jira -> email
            │     field required
            └── jira -> token
                  field required
            """
        )


class TestRepoNameInput:
    async def test_default_state(self, app, isolation, config_file, helpers):
        config_file.model.data.update(
            {
                'repos': {'agent': {'path': str(isolation)}},
                'github': {'user': 'foo', 'token': 'bar'},
                'jira': {'email': 'foo', 'token': 'bar'},
            }
        )
        config_file.save()

        async with app.run_test():
            input_box = app.query_one(RepoNameInput)
            save_button = app.query_one(Button)
            text_log = app.query_one(TextLog)

            assert not app.config.data['repo']
            assert not input_box.value
            assert save_button.disabled is True
            assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
                """
                Configuration errors
                └── repo
                      field required
                """
            )

    async def test_wrong_type(self, app, config_file, helpers):
        config_file.model.data.update(
            {
                'repo': ['foo'],
                'github': {'user': 'foo', 'token': 'bar'},
                'jira': {'email': 'foo', 'token': 'bar'},
            }
        )
        config_file.save()

        async with app.run_test():
            input_box = app.query_one(RepoNameInput)
            save_button = app.query_one(Button)
            text_log = app.query_one(TextLog)

            assert app.config.data['repo'] == ['foo']
            assert not input_box.value
            assert save_button.disabled is True
            assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
                """
                Configuration errors
                └── repo
                      str type expected
                """
            )

    async def test_unknown(self, app, config_file, helpers):
        config_file.model.data.update(
            {
                'repo': 'foo',
                'github': {'user': 'foo', 'token': 'bar'},
                'jira': {'email': 'foo', 'token': 'bar'},
            }
        )
        config_file.save()

        async with app.run_test():
            input_box = app.query_one(RepoNameInput)
            save_button = app.query_one(Button)
            text_log = app.query_one(TextLog)

            assert app.config.data['repo'] == 'foo'
            assert input_box.value == 'foo'
            assert save_button.disabled is True
            assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
                """
                Configuration errors
                └── repo
                      unknown repository: foo
                """
            )

    async def test_save(self, app, isolation, config_file, helpers):
        config_file.model.data.update(
            {
                'repos': {'agent': {'path': str(isolation)}},
                'github': {'user': 'foo', 'token': 'bar'},
                'jira': {'email': 'foo', 'token': 'bar'},
            }
        )
        config_file.save()

        async with app.run_test() as pilot:
            input_box = app.query_one(RepoNameInput)
            save_button = app.query_one(Button)
            text_log = app.query_one(TextLog)

            assert not app.config.data['repo']
            assert not input_box.value
            assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
                """
                Configuration errors
                └── repo
                      field required
                """
            )
            assert save_button.disabled is True

            app.set_focus(input_box)
            await pilot.press(*'agent')

            assert app.config.data['repo'] == 'agent'
            assert input_box.value == 'agent'
            assert not text_log.lines
            assert save_button.disabled is False


class TestRepoPathInput:
    async def test_missing(self, app, config_file, helpers):
        config_file.model.data.update(
            {
                'repo': 'agent',
                'repos': {'agent': {}},
                'github': {'user': 'foo', 'token': 'bar'},
                'jira': {'email': 'foo', 'token': 'bar'},
            }
        )
        config_file.save()

        async with app.run_test():
            input_box = app.query_one(RepoPathInput)
            save_button = app.query_one(Button)
            text_log = app.query_one(TextLog)

            assert app.config.data['repos'] == {'agent': {}}
            assert not input_box.value
            assert save_button.disabled is True
            assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
                """
                Configuration errors
                └── repos -> agent -> path
                      field required
                """
            )

    async def test_wrong_type(self, app, config_file, helpers):
        config_file.model.data.update(
            {
                'repo': 'agent',
                'repos': {'agent': {'path': ['foo']}},
                'github': {'user': 'foo', 'token': 'bar'},
                'jira': {'email': 'foo', 'token': 'bar'},
            }
        )
        config_file.save()

        async with app.run_test():
            input_box = app.query_one(RepoPathInput)
            save_button = app.query_one(Button)
            text_log = app.query_one(TextLog)

            assert app.config.data['repos'] == {'agent': {'path': ['foo']}}
            assert not input_box.value
            assert save_button.disabled is True
            assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
                """
                Configuration errors
                └── repos -> agent -> path
                      str type expected
                """
            )

    async def test_does_not_exist(self, app, isolation, config_file, helpers):
        path = str(isolation / 'foo')
        config_file.model.data.update(
            {
                'repo': 'agent',
                'repos': {'agent': {'path': path}},
                'github': {'user': 'foo', 'token': 'bar'},
                'jira': {'email': 'foo', 'token': 'bar'},
            }
        )
        config_file.save()

        async with app.run_test():
            input_box = app.query_one(RepoPathInput)
            save_button = app.query_one(Button)
            text_log = app.query_one(TextLog)

            assert app.config.data['repos'] == {'agent': {'path': path}}
            assert input_box.value == path
            assert save_button.disabled is True
            assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
                f"""
                Configuration errors
                └── repos -> agent -> path
                      directory does not exist: {path}
                """
            )

    async def test_save(self, app, isolation, config_file, helpers):
        path = str(isolation)
        config_file.model.data.update(
            {
                'repo': 'agent',
                'repos': {'agent': {}},
                'github': {'user': 'foo', 'token': 'bar'},
                'jira': {'email': 'foo', 'token': 'bar'},
            }
        )
        config_file.save()

        async with app.run_test() as pilot:
            input_box = app.query_one(RepoPathInput)
            save_button = app.query_one(Button)
            text_log = app.query_one(TextLog)

            assert app.config.data['repos'] == {'agent': {}}
            assert not input_box.value
            assert save_button.disabled is True
            assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
                """
                Configuration errors
                └── repos -> agent -> path
                      field required
                """
            )

            app.set_focus(input_box)
            await pilot.pause(helpers.ASYNC_WAIT)
            await pilot.press(*[p.replace('_', 'underscore') for p in path])
            assert app.config.data['repos'] == {'agent': {'path': path}}

            assert input_box.value == path
            assert save_button.disabled is False
            assert not text_log.lines


class TestGitHubUserInput:
    async def test_default_state(self, app, isolation, config_file, helpers):
        config_file.model.data.update(
            {
                'repo': 'agent',
                'repos': {'agent': {'path': str(isolation)}},
                'github': {'token': 'bar'},
                'jira': {'email': 'foo', 'token': 'bar'},
            }
        )
        config_file.save()

        async with app.run_test():
            input_box = app.query_one(GitHubUserInput)
            save_button = app.query_one(Button)
            text_log = app.query_one(TextLog)

            assert app.config.data['github'] == {'token': 'bar'}
            assert not input_box.value
            assert save_button.disabled is True
            assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
                """
                Configuration errors
                └── github -> user
                      field required
                """
            )

    async def test_wrong_type(self, app, isolation, config_file, helpers):
        config_file.model.data.update(
            {
                'repo': 'agent',
                'repos': {'agent': {'path': str(isolation)}},
                'github': {'user': ['foo'], 'token': 'bar'},
                'jira': {'email': 'foo', 'token': 'bar'},
            }
        )
        config_file.save()

        async with app.run_test():
            input_box = app.query_one(GitHubUserInput)
            save_button = app.query_one(Button)
            text_log = app.query_one(TextLog)

            assert app.config.data['github'] == {'user': ['foo'], 'token': 'bar'}
            assert not input_box.value
            assert save_button.disabled is True
            assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
                """
                Configuration errors
                └── github -> user
                      str type expected
                """
            )

    async def test_save(self, app, isolation, config_file, helpers):
        config_file.model.data.update(
            {
                'repo': 'agent',
                'repos': {'agent': {'path': str(isolation)}},
                'github': {'token': 'bar'},
                'jira': {'email': 'foo', 'token': 'bar'},
            }
        )
        config_file.save()

        async with app.run_test() as pilot:
            input_box = app.query_one(GitHubUserInput)
            save_button = app.query_one(Button)
            text_log = app.query_one(TextLog)

            assert app.config.data['github'] == {'token': 'bar'}
            assert not input_box.value
            assert save_button.disabled is True
            assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
                """
                Configuration errors
                └── github -> user
                      field required
                """
            )

            app.set_focus(input_box)
            await pilot.press(*'foo')

            assert app.config.data['github'] == {'user': 'foo', 'token': 'bar'}
            assert input_box.value == 'foo'
            assert save_button.disabled is False
            assert not text_log.lines


class TestGitHubTokenInput:
    async def test_default_state(self, app, isolation, config_file, helpers):
        config_file.model.data.update(
            {
                'repo': 'agent',
                'repos': {'agent': {'path': str(isolation)}},
                'github': {'user': 'foo'},
                'jira': {'email': 'foo', 'token': 'bar'},
            }
        )
        config_file.save()

        async with app.run_test():
            input_box = app.query_one(GitHubTokenInput)
            save_button = app.query_one(Button)
            text_log = app.query_one(TextLog)

            assert app.config.data['github'] == {'user': 'foo'}
            assert input_box.password is True
            assert not input_box.value
            assert save_button.disabled is True
            assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
                """
                Configuration errors
                └── github -> token
                      field required
                """
            )

    async def test_wrong_type(self, app, isolation, config_file, helpers):
        config_file.model.data.update(
            {
                'repo': 'agent',
                'repos': {'agent': {'path': str(isolation)}},
                'github': {'user': 'foo', 'token': ['bar']},
                'jira': {'email': 'foo', 'token': 'bar'},
            }
        )
        config_file.save()

        async with app.run_test():
            input_box = app.query_one(GitHubTokenInput)
            save_button = app.query_one(Button)
            text_log = app.query_one(TextLog)

            assert app.config.data['github'] == {'user': 'foo', 'token': ['bar']}
            assert input_box.password is True
            assert not input_box.value
            assert save_button.disabled is True
            assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
                """
                Configuration errors
                └── github -> token
                      str type expected
                """
            )

    async def test_save(self, app, isolation, config_file, helpers):
        config_file.model.data.update(
            {
                'repo': 'agent',
                'repos': {'agent': {'path': str(isolation)}},
                'github': {'user': 'foo'},
                'jira': {'email': 'foo', 'token': 'bar'},
            }
        )
        config_file.save()

        async with app.run_test() as pilot:
            input_box = app.query_one(GitHubTokenInput)
            save_button = app.query_one(Button)
            text_log = app.query_one(TextLog)

            assert app.config.data['github'] == {'user': 'foo'}
            assert input_box.password is True
            assert not input_box.value
            assert save_button.disabled is True
            assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
                """
                Configuration errors
                └── github -> token
                      field required
                """
            )

            app.set_focus(input_box)
            await pilot.press(*'bar')

            assert app.config.data['github'] == {'user': 'foo', 'token': 'bar'}
            assert input_box.password is True
            assert input_box.value == 'bar'
            assert save_button.disabled is False
            assert not text_log.lines


class TestJiraEmailInput:
    async def test_default_state(self, app, isolation, config_file, helpers):
        config_file.model.data.update(
            {
                'repo': 'agent',
                'repos': {'agent': {'path': str(isolation)}},
                'github': {'user': 'foo', 'token': 'bar'},
                'jira': {'token': 'bar'},
            }
        )
        config_file.save()

        async with app.run_test():
            input_box = app.query_one(JiraEmailInput)
            save_button = app.query_one(Button)
            text_log = app.query_one(TextLog)

            assert app.config.data['jira'] == {'token': 'bar'}
            assert not input_box.value
            assert save_button.disabled is True
            assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
                """
                Configuration errors
                └── jira -> email
                      field required
                """
            )

    async def test_wrong_type(self, app, isolation, config_file, helpers):
        config_file.model.data.update(
            {
                'repo': 'agent',
                'repos': {'agent': {'path': str(isolation)}},
                'github': {'user': 'foo', 'token': 'bar'},
                'jira': {'email': ['foo'], 'token': 'bar'},
            }
        )
        config_file.save()

        async with app.run_test():
            input_box = app.query_one(JiraEmailInput)
            save_button = app.query_one(Button)
            text_log = app.query_one(TextLog)

            assert app.config.data['jira'] == {'email': ['foo'], 'token': 'bar'}
            assert not input_box.value
            assert save_button.disabled is True
            assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
                """
                Configuration errors
                └── jira -> email
                      str type expected
                """
            )

    async def test_save(self, app, isolation, config_file, helpers):
        config_file.model.data.update(
            {
                'repo': 'agent',
                'repos': {'agent': {'path': str(isolation)}},
                'github': {'user': 'foo', 'token': 'bar'},
                'jira': {'token': 'bar'},
            }
        )
        config_file.save()

        async with app.run_test() as pilot:
            input_box = app.query_one(JiraEmailInput)
            save_button = app.query_one(Button)
            text_log = app.query_one(TextLog)

            assert app.config.data['jira'] == {'token': 'bar'}
            assert not input_box.value
            assert save_button.disabled is True
            assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
                """
                Configuration errors
                └── jira -> email
                      field required
                """
            )

            app.set_focus(input_box)
            await pilot.press(*'foo')

            assert app.config.data['jira'] == {'email': 'foo', 'token': 'bar'}
            assert input_box.value == 'foo'
            assert save_button.disabled is False
            assert not text_log.lines


class TestJiraTokenInput:
    async def test_default_state(self, app, isolation, config_file, helpers):
        config_file.model.data.update(
            {
                'repo': 'agent',
                'repos': {'agent': {'path': str(isolation)}},
                'github': {'user': 'foo', 'token': 'bar'},
                'jira': {'email': 'foo'},
            }
        )
        config_file.save()

        async with app.run_test():
            input_box = app.query_one(JiraTokenInput)
            save_button = app.query_one(Button)
            text_log = app.query_one(TextLog)

            assert app.config.data['jira'] == {'email': 'foo'}
            assert input_box.password is True
            assert not input_box.value
            assert save_button.disabled is True
            assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
                """
                Configuration errors
                └── jira -> token
                      field required
                """
            )

    async def test_wrong_type(self, app, isolation, config_file, helpers):
        config_file.model.data.update(
            {
                'repo': 'agent',
                'repos': {'agent': {'path': str(isolation)}},
                'github': {'user': 'foo', 'token': 'bar'},
                'jira': {'email': 'foo', 'token': ['bar']},
            }
        )
        config_file.save()

        async with app.run_test():
            input_box = app.query_one(JiraTokenInput)
            save_button = app.query_one(Button)
            text_log = app.query_one(TextLog)

            assert app.config.data['jira'] == {'email': 'foo', 'token': ['bar']}
            assert input_box.password is True
            assert not input_box.value
            assert save_button.disabled is True
            assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
                """
                Configuration errors
                └── jira -> token
                      str type expected
                """
            )

    async def test_save(self, app, isolation, config_file, helpers):
        config_file.model.data.update(
            {
                'repo': 'agent',
                'repos': {'agent': {'path': str(isolation)}},
                'github': {'user': 'foo', 'token': 'bar'},
                'jira': {'email': 'foo'},
            }
        )
        config_file.save()

        async with app.run_test() as pilot:
            input_box = app.query_one(JiraTokenInput)
            save_button = app.query_one(Button)
            text_log = app.query_one(TextLog)

            assert app.config.data['jira'] == {'email': 'foo'}
            assert input_box.password is True
            assert not input_box.value
            assert save_button.disabled is True
            assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
                """
                Configuration errors
                └── jira -> token
                      field required
                """
            )

            app.set_focus(input_box)
            await pilot.press(*'bar')

            assert app.config.data['jira'] == {'email': 'foo', 'token': 'bar'}
            assert input_box.password is True
            assert input_box.value == 'bar'
            assert save_button.disabled is False
            assert not text_log.lines
