# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from unittest import mock
from unittest.mock import MagicMock

import pytest
from httpx import Request, Response
from textual.widgets import Button, Label, RichLog

from ddqa.screens.sync import InteractiveSidebar, SyncScreen


@pytest.fixture(scope='module', autouse=True)
def mock_remote_url():
    with mock.patch('ddqa.utils.git.GitRepository.get_remote_url', return_value='https://github.com/org/repo.git'):
        yield


@pytest.fixture
def app(app):
    app.select_screen('sync', SyncScreen(manual_execution=True))
    return app


async def test_response_error(app, git_repository, helpers, mocker):
    app.configure(
        git_repository,
        caching=True,
        data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
    )
    mocker.patch('httpx.AsyncClient.get', return_value=Response(500, request=Request('GET', '')))

    async with app.run_test():
        sidebar = app.query_one(InteractiveSidebar)

        status = sidebar.query_one(Label)
        assert '500' in str(status.render())

        text_log = sidebar.query_one(RichLog)
        assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
            f"""
            Fetching global config from: {app.repo.global_config_source}
            """
        )

        button = sidebar.query_one(Button)
        assert button.disabled


async def test_parsing_error(app, git_repository, helpers, mocker):
    app.configure(
        git_repository,
        caching=True,
        data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
    )
    mocker.patch('httpx.AsyncClient.get', return_value=Response(200, request=Request('GET', ''), content='!'))

    async with app.run_test():
        sidebar = app.query_one(InteractiveSidebar)

        status = sidebar.query_one(Label)
        assert str(status.render()) == 'Unable to parse TOML source'

        text_log = sidebar.query_one(RichLog)
        assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
            f"""
            Fetching global config from: {app.repo.global_config_source}
            """
        )

        button = sidebar.query_one(Button)
        assert button.disabled


async def test_no_members(app, git_repository, helpers, mocker):
    app.configure(
        git_repository,
        caching=True,
        data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
    )
    mocker.patch('httpx.AsyncClient.get', return_value=Response(200, request=Request('GET', ''), content=''))

    async with app.run_test():
        sidebar = app.query_one(InteractiveSidebar)

        status = sidebar.query_one(Label)
        assert str(status.render()) == 'No members found in TOML source'

        text_log = sidebar.query_one(RichLog)
        assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
            f"""
            Fetching global config from: {app.repo.global_config_source}
            """
        )

        button = sidebar.query_one(Button)
        assert button.disabled


async def test_save_members(app, git_repository, helpers, mocker):
    app.configure(
        git_repository,
        caching=True,
        data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
    )
    mocker.patch(
        'httpx.AsyncClient.get',
        side_effect=[
            Response(
                200,
                request=Request('GET', ''),
                content=helpers.dedent(
                    """
                    jira_server = "https://foo.atlassian.net"

                    [members]
                    g = "j"
                    """
                ),
            ),
            Response(500, request=Request('GET', '')),
        ],
    )
    repo_config = app.repo.model_dump()
    repo_config['teams'] = {
        'foo': {
            'jira_project': 'FOO',
            'jira_issue_type': 'Foo-Task',
            'jira_statuses': {'TODO': 'Backlog', 'IN PROGRESS': 'Sprint', 'DONE': 'Done'},
            'github_team': 'foo-team',
        },
        'bar': {
            'jira_project': 'BAR',
            'jira_issue_type': 'Bar-Task',
            'jira_statuses': {'TODO': 'Backlog', 'IN PROGRESS': 'Sprint', 'DONE': 'Done'},
            'github_team': 'bar-team',
        },
    }
    app.save_repo_config(repo_config)

    async with app.run_test():
        sidebar = app.query_one(InteractiveSidebar)

        status = sidebar.query_one(Label)
        assert '500' in str(status.render())

        text_log = sidebar.query_one(RichLog)
        assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
            f"""
            Fetching global config from: {app.repo.global_config_source}
            Refreshing members for team: bar-team
            """
        )

        button = sidebar.query_one(Button)
        assert button.disabled

        assert app.github.load_global_config(app.repo.global_config_source) == {
            'jira_server': 'https://foo.atlassian.net',
            'members': {'g': 'j'},
        }


async def test_save_teams(app, git_repository, helpers, mocker):
    app.configure(
        git_repository,
        caching=True,
        data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
    )
    mocker.patch(
        'httpx.AsyncClient.get',
        side_effect=[
            Response(
                200,
                request=Request('GET', ''),
                content=helpers.dedent(
                    """
                    jira_server = "https://foo.atlassian.net"

                    [members]
                    g = "j"
                    foo1 = "jira-foo1"
                    bar1 = "jira-bar1"
                    """
                ),
            ),
        ],
    )
    mocker.patch('ddqa.utils.github.GitHubRepository.get_team_members', side_effect=(['foo1'], ['bar1']))
    mocker.patch('ddqa.utils.jira.JiraClient.get_deactivated_users', return_value=MagicMock(return_value=[]))

    repo_config = dict(app.repo.model_dump())
    repo_config['teams'] = {
        'foo': {
            'jira_project': 'FOO',
            'jira_issue_type': 'Foo-Task',
            'jira_statuses': {'TODO': 'Backlog', 'IN PROGRESS': 'Sprint', 'DONE': 'Done'},
            'github_team': 'foo-team',
        },
        'bar': {
            'jira_project': 'BAR',
            'jira_issue_type': 'Bar-Task',
            'jira_statuses': {'TODO': 'Backlog', 'IN PROGRESS': 'Sprint', 'DONE': 'Done'},
            'github_team': 'bar-team',
        },
    }
    app.save_repo_config(repo_config)

    async with app.run_test():
        sidebar = app.query_one(InteractiveSidebar)

        status = sidebar.query_one(Label)
        assert not str(status.render())

        text_log = sidebar.query_one(RichLog)
        assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
            f"""
            Fetching global config from: {app.repo.global_config_source}
            Refreshing members for team: bar-team
            Refreshing members for team: foo-team
            Validating 3 Jira users...
            """
        )

        button = sidebar.query_one(Button)
        assert not button.disabled

        assert app.github.load_global_config(app.repo.global_config_source) == {
            'jira_server': 'https://foo.atlassian.net',
            'members': {'g': 'j', 'bar1': 'jira-bar1', 'foo1': 'jira-foo1'},
        }


async def test_deactivated_jira_user(app, git_repository, helpers, mocker):
    app.configure(
        git_repository,
        caching=True,
        data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
    )
    mocker.patch(
        'httpx.AsyncClient.get',
        side_effect=[
            Response(
                200,
                request=Request('GET', ''),
                content=helpers.dedent(
                    """
                    jira_server = "https://foo.atlassian.net"

                    [members]
                    g = "j"
                    foo1 = "jira-foo1"
                    bar1 = "jira-bar1"
                    """
                ),
            ),
        ],
    )

    mocker.patch('ddqa.utils.github.GitHubRepository.get_team_members', side_effect=(['foo1'], ['bar1']))
    mock = MagicMock()
    mock.__aiter__.return_value = [{'accountId': 'j'}]
    mocker.patch('ddqa.utils.jira.JiraClient.get_deactivated_users', return_value=mock)
    repo_config = dict(app.repo.model_dump())
    repo_config['teams'] = {
        'foo': {
            'jira_project': 'FOO',
            'jira_issue_type': 'Foo-Task',
            'jira_statuses': {'TODO': 'Backlog', 'IN PROGRESS': 'Sprint', 'DONE': 'Done'},
            'github_team': 'foo-team',
        },
        'bar': {
            'jira_project': 'BAR',
            'jira_issue_type': 'Bar-Task',
            'jira_statuses': {'TODO': 'Backlog', 'IN PROGRESS': 'Sprint', 'DONE': 'Done'},
            'github_team': 'bar-team',
        },
    }
    app.save_repo_config(repo_config)

    async with app.run_test():
        sidebar = app.query_one(InteractiveSidebar)
        text_log = sidebar.query_one(RichLog)

        assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
            f"""
            Fetching global config from: {app.repo.global_config_source}
            Refreshing members for team: bar-team
            Refreshing members for team: foo-team
            Validating 3 Jira users...
            User g is deactivated on Jira
            """
        )

        button = sidebar.query_one(Button)
        assert not button.disabled

        assert app.github.load_global_config(app.repo.global_config_source) == {
            'jira_server': 'https://foo.atlassian.net',
            'members': {'bar1': 'jira-bar1', 'foo1': 'jira-foo1'},
        }


async def test_github_user_not_in_jira(app, git_repository, helpers, mocker):
    app.configure(
        git_repository,
        caching=True,
        data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
    )

    mocker.patch(
        'httpx.AsyncClient.get',
        side_effect=[
            Response(
                200,
                request=Request('GET', ''),
                content=helpers.dedent(
                    """
                    jira_server = "https://foo.atlassian.net"

                    [members]
                    g = "j"
                    foo1 = "jira-foo1"
                    """
                ),
            ),
        ],
    )

    mocker.patch('ddqa.utils.github.GitHubRepository.get_team_members', side_effect=(['foo1'], ['bar1']))
    mocker.patch('ddqa.utils.jira.JiraClient.get_deactivated_users')

    repo_config = dict(app.repo.model_dump())
    repo_config['teams'] = {
        'foo': {
            'jira_project': 'FOO',
            'jira_issue_type': 'Foo-Task',
            'jira_statuses': {'TODO': 'Backlog', 'IN PROGRESS': 'Sprint', 'DONE': 'Done'},
            'github_team': 'foo-team',
        },
        'bar': {
            'jira_project': 'BAR',
            'jira_issue_type': 'Bar-Task',
            'jira_statuses': {'TODO': 'Backlog', 'IN PROGRESS': 'Sprint', 'DONE': 'Done'},
            'github_team': 'bar-team',
        },
    }
    app.save_repo_config(repo_config)

    async with app.run_test():
        sidebar = app.query_one(InteractiveSidebar)
        text_log = sidebar.query_one(RichLog)
        assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(
            f"""
            Fetching global config from: {app.repo.global_config_source}
            Refreshing members for team: bar-team
            Refreshing members for team: foo-team
            GitHub user bar1 is not declared in the Jira config
            Validating 2 Jira users...
            """
        )

        button = sidebar.query_one(Button)
        assert not button.disabled

        assert app.github.load_global_config(app.repo.global_config_source) == {
            'jira_server': 'https://foo.atlassian.net',
            'members': {'foo1': 'jira-foo1', 'g': 'j'},
        }
