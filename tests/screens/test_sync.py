# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import json
from unittest import mock

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
    repo_config = app.repo.dict()
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
            Response(
                200,
                request=Request('GET', ''),
                content=json.dumps(
                    [
                        {'login': 'foo1', 'type': 'User'},
                        {'login': 'bot', 'type': 'other'},
                    ],
                ),
            ),
            Response(
                200,
                request=Request('GET', ''),
                content=json.dumps(
                    [
                        {'login': 'bar1', 'type': 'User'},
                        {'login': 'bot', 'type': 'other'},
                    ],
                ),
            ),
        ],
    )
    mocker.patch(
        'httpx.AsyncClient.request',
        side_effect=[
            Response(
                200,
                request=Request('GET', ''),
                content=json.dumps(
                    {
                        'maxResults': 100,
                        'startAt': 0,
                        'total': 1,
                        'values': [
                            {
                                'self': 'https://your-domain.atlassian.net/rest/api/2/user?accountId=f',
                                'accountId': 'j',
                                'accountType': 'atlassian',
                                'emailAddress': 'j@example.com',
                                'active': True,
                            },
                        ],
                    },
                ),
            ),
        ],
    )
    repo_config = dict(app.repo.dict())
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
            Response(
                200,
                request=Request('GET', ''),
                content=json.dumps(
                    [
                        {'login': 'foo1', 'type': 'User'},
                        {'login': 'bot', 'type': 'other'},
                    ],
                ),
            ),
            Response(
                200,
                request=Request('GET', ''),
                content=json.dumps(
                    [
                        {'login': 'bar1', 'type': 'User'},
                        {'login': 'bot', 'type': 'other'},
                    ],
                ),
            ),
        ],
    )
    mocker.patch(
        'httpx.AsyncClient.request',
        side_effect=[
            Response(
                200,
                request=Request('GET', ''),
                content=json.dumps(
                    {
                        'maxResults': 100,
                        'startAt': 0,
                        'total': 1,
                        'values': [
                            {
                                'self': 'https://your-domain.atlassian.net/rest/api/2/user?accountId=f',
                                'accountId': 'j',
                                'accountType': 'atlassian',
                                'emailAddress': 'j@example.com',
                                'active': False,
                            },
                        ],
                    },
                ),
            ),
        ],
    )
    repo_config = dict(app.repo.dict())
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
    mock_get = mocker.patch(
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
            Response(
                200,
                request=Request('GET', ''),
                content=json.dumps(
                    [
                        {'login': 'foo1', 'type': 'User'},
                        {'login': 'bot', 'type': 'other'},
                    ],
                ),
            ),
            Response(
                200,
                request=Request('GET', ''),
                content=json.dumps(
                    [
                        {'login': 'bar1', 'type': 'User'},
                        {'login': 'bot', 'type': 'other'},
                    ],
                ),
            ),
        ],
    )
    mock_request = mocker.patch(
        'httpx.AsyncClient.request',
        side_effect=[
            Response(
                200,
                request=Request('GET', ''),
                content=json.dumps(
                    {
                        'maxResults': 100,
                        'startAt': 0,
                        'total': 1,
                        'values': [
                            {
                                'self': 'https://your-domain.atlassian.net/rest/api/2/user?accountId=f',
                                'accountId': 'j',
                                'accountType': 'atlassian',
                                'emailAddress': 'j@example.com',
                                'active': True,
                            },
                        ],
                    },
                ),
            ),
        ],
    )
    repo_config = dict(app.repo.dict())
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
        assert mock_request.call_count == 1
        assert mock_request.call_args_list == [
            mocker.call(
                'GET',
                'https://foo.atlassian.net/rest/api/2/user/bulk',
                auth=('foo@bar.baz', 'bar'),
                params={'maxResults': 100, 'accountId': ['j', 'jira-foo1'], 'startAt': 0},
            )
        ]

        assert mock_get.call_count == 3
        assert mock_get.call_args_list == [
            mocker.call('https://www.google.com', auth=('foo', 'bar')),
            mocker.call('https://api.github.com/orgs/org/teams/bar-team/members', auth=('foo', 'bar')),
            mocker.call('https://api.github.com/orgs/org/teams/foo-team/members', auth=('foo', 'bar')),
        ]

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
