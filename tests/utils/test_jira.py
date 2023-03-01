# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import json
import time
from datetime import datetime, timedelta, timezone
from unittest import mock

import pytest
from httpx import Request, Response
from textual.widgets import Static

from ddqa.models.github import TestCandidate
from ddqa.utils.network import ResponsiveNetworkClient


@pytest.fixture(scope='module', autouse=True)
def mock_calls():
    with (
        mock.patch('ddqa.utils.git.GitRepository.get_remote_url', return_value='https://github.com/org/repo.git'),
        mock.patch(
            'ddqa.utils.github.GitHubRepository.load_global_config',
            return_value={
                'jira_server': 'https://foobarbaz.atlassian.net',
                'members': {'github-foo': 'jira-foo', 'github-bar': 'jira-bar'},
            },
        ),
    ):
        yield


class TestGetCurrentUserID:
    async def test_no_cache(self, app, git_repository, mocker):
        app.configure(
            git_repository,
            caching=True,
            data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
        )
        cached_user_id_file = app.cache_dir / 'jira' / 'user_ids.json'
        assert not cached_user_id_file.is_file()

        response_mock = mocker.patch(
            'httpx.AsyncClient.request',
            return_value=Response(
                200,
                request=Request('GET', ''),
                content=json.dumps(
                    {
                        'accountId': 'qwerty1234567890',
                    },
                ),
            ),
        )

        current_user_id = await app.jira.get_current_user_id(ResponsiveNetworkClient(Static()))
        assert response_mock.call_args_list == [
            mocker.call('GET', 'https://foobarbaz.atlassian.net/rest/api/2/myself', auth=('foo@bar.baz', 'bar')),
        ]

        assert current_user_id == 'qwerty1234567890'

        assert cached_user_id_file.is_file()
        assert app.config.auth.jira.token not in cached_user_id_file.read_text()

    async def test_cache(self, app, git_repository, mocker):
        app.configure(
            git_repository,
            caching=True,
            data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
        )
        cached_user_id_file = app.cache_dir / 'jira' / 'user_ids.json'
        assert not cached_user_id_file.is_file()

        response_mock = mocker.patch(
            'httpx.AsyncClient.request',
            side_effect=[
                Response(
                    200,
                    request=Request('GET', ''),
                    content=json.dumps(
                        {
                            'accountId': 'qwerty1234567890',
                        },
                    ),
                ),
                Response(500, request=Request('GET', '')),
            ],
        )

        current_user_id = await app.jira.get_current_user_id(ResponsiveNetworkClient(Static()))
        assert response_mock.call_args_list == [
            mocker.call('GET', 'https://foobarbaz.atlassian.net/rest/api/2/myself', auth=('foo@bar.baz', 'bar')),
        ]

        assert current_user_id == 'qwerty1234567890'

        assert cached_user_id_file.is_file()
        assert app.config.auth.jira.token not in cached_user_id_file.read_text()

        current_user_id = await app.jira.get_current_user_id(ResponsiveNetworkClient(Static()))
        assert response_mock.call_args_list == [
            mocker.call('GET', 'https://foobarbaz.atlassian.net/rest/api/2/myself', auth=('foo@bar.baz', 'bar')),
        ]

        assert current_user_id == 'qwerty1234567890'


async def test_create_issues(app, git_repository, helpers, mocker):
    app.configure(
        git_repository,
        caching=True,
        data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
    )
    repo_config = dict(app.repo.dict())
    repo_config['teams'] = {
        'foo': {
            'jira_project': 'FOO',
            'jira_issue_type': 'Foo-Task',
            'jira_component': 'Foo-Component',
            'github_team': 'foo-team',
        },
        'bar': {
            'jira_project': 'BAR',
            'jira_issue_type': 'Bar-Task',
            'jira_component': 'Bar-Component',
            'github_team': 'bar-team',
        },
    }
    app.save_repo_config(repo_config)

    response_mock = mocker.patch(
        'httpx.AsyncClient.request',
        side_effect=[
            Response(
                200,
                request=Request('POST', ''),
                content=json.dumps(
                    {
                        'key': 'FOO-1',
                    },
                ),
            ),
            Response(
                200,
                request=Request('POST', ''),
                content=json.dumps(
                    {
                        'key': 'BAR-1',
                    },
                ),
            ),
        ],
    )

    created_issues = await app.jira.create_issues(
        ResponsiveNetworkClient(Static()),
        TestCandidate(
            **{
                'id': '123',
                'title': 'title123',
                'url': 'https://github.com/org/repo/pull/123',
                'user': 'user9000',
                'labels': [
                    {'name': 'label1', 'color': '632ca6'},
                    {'name': 'label2', 'color': '632ca6'},
                ],
                'body': '## test body\n\n```yaml\nfoo: bar\n```\n\n```\nbaz\n```\n\n[test link](https://example.com)',
            }
        ),
        {'foo': 'github-foo', 'bar': 'github-bar'},
    )
    assert response_mock.call_args_list == [
        mocker.call(
            'POST',
            'https://foobarbaz.atlassian.net/rest/api/2/issue',
            auth=('foo@bar.baz', 'bar'),
            json={
                'fields': {
                    'assignee': {'id': 'jira-foo'},
                    'components': [{'name': 'Foo-Component'}],
                    'description': helpers.dedent(
                        """
                        Pull request: [#123|https://github.com/org/repo/pull/123]
                        Author: [user9000|https://github.com/user9000]
                        Labels: {{label1}}, {{label2}}

                        h2. test body

                        {code:yaml}
                        foo: bar
                        {code}

                        {code:plaintext}
                        baz
                        {code}

                        [test link|https://example.com]
                        """
                    ),
                    'issuetype': {'name': 'Foo-Task'},
                    'labels': ['ddqa-todo'],
                    'project': {'key': 'FOO'},
                    'summary': 'title123',
                },
            },
        ),
        mocker.call(
            'POST',
            'https://foobarbaz.atlassian.net/rest/api/2/issue',
            auth=('foo@bar.baz', 'bar'),
            json={
                'fields': {
                    'assignee': {'id': 'jira-bar'},
                    'components': [{'name': 'Bar-Component'}],
                    'description': helpers.dedent(
                        """
                        Pull request: [#123|https://github.com/org/repo/pull/123]
                        Author: [user9000|https://github.com/user9000]
                        Labels: {{label1}}, {{label2}}

                        h2. test body

                        {code:yaml}
                        foo: bar
                        {code}

                        {code:plaintext}
                        baz
                        {code}

                        [test link|https://example.com]
                        """
                    ),
                    'issuetype': {'name': 'Bar-Task'},
                    'labels': ['ddqa-todo'],
                    'project': {'key': 'BAR'},
                    'summary': 'title123',
                },
            },
        ),
    ]

    assert created_issues == {
        'foo': 'https://foobarbaz.atlassian.net/browse/FOO-1',
        'bar': 'https://foobarbaz.atlassian.net/browse/BAR-1',
    }


async def test_search_issues(app, git_repository, mocker):
    app.configure(
        git_repository,
        caching=True,
        data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
    )
    repo_config = dict(app.repo.dict())
    repo_config['teams'] = {
        'foo': {
            'jira_project': 'FOO',
            'jira_issue_type': 'Foo-Task',
            'github_team': 'foo-team',
        },
        'bar': {
            'jira_project': 'BAR',
            'jira_issue_type': 'Bar-Task',
            'github_team': 'bar-team',
        },
    }
    app.save_repo_config(repo_config)

    response_mock = mocker.patch(
        'httpx.AsyncClient.request',
        side_effect=[
            Response(
                200,
                request=Request('POST', ''),
                content=json.dumps(
                    {
                        'issues': [
                            {
                                'fields': {
                                    'assignee': {
                                        'accountId': 'qwerty1234567890',
                                        'avatarUrls': {'16x16': 'https://secure.gravatar.com/avatar.png'},
                                        'displayName': 'U.N. Owen',
                                        'timeZone': 'America/New_York',
                                    },
                                    'description': 'Test description',
                                    'labels': ['ddqa-todo'],
                                    'project': {'key': 'FOO'},
                                    'summary': 'Test summary',
                                    'updated': '2023-02-13T12:08:50.058-0500',
                                },
                                'key': 'FOO-1',
                            },
                            {
                                'fields': {
                                    'assignee': {
                                        'accountId': 'qwerty1234567890',
                                        'avatarUrls': {'16x16': 'https://secure.gravatar.com/avatar.png'},
                                        'displayName': 'U.N. Owen',
                                        'timeZone': 'America/New_York',
                                    },
                                    'description': 'Test description',
                                    'labels': ['ddqa-todo'],
                                    'project': {'key': 'BAR'},
                                    'summary': 'Test summary',
                                    'updated': '2023-02-13T12:08:50.058-0500',
                                },
                                'key': 'BAR-1',
                            },
                        ],
                        'maxResults': 2,
                        'startAt': 0,
                        'total': 5,
                    }
                ),
            ),
            Response(
                200,
                request=Request('POST', ''),
                content=json.dumps(
                    {
                        'issues': [
                            {
                                'fields': {
                                    'assignee': {
                                        'accountId': 'qwerty1234567890',
                                        'avatarUrls': {'16x16': 'https://secure.gravatar.com/avatar.png'},
                                        'displayName': 'U.N. Owen',
                                        'timeZone': 'America/New_York',
                                    },
                                    'description': 'Test description',
                                    'labels': ['ddqa-in-progress'],
                                    'project': {'key': 'FOO'},
                                    'summary': 'Test summary',
                                    'updated': '2023-02-13T12:08:50.058-0500',
                                },
                                'key': 'FOO-2',
                            },
                            {
                                'fields': {
                                    'assignee': {
                                        'accountId': 'qwerty1234567890',
                                        'avatarUrls': {'16x16': 'https://secure.gravatar.com/avatar.png'},
                                        'displayName': 'U.N. Owen',
                                        'timeZone': 'America/New_York',
                                    },
                                    'description': 'Test description',
                                    'labels': ['ddqa-in-progress'],
                                    'project': {'key': 'BAR'},
                                    'summary': 'Test summary',
                                    'updated': '2023-02-13T12:08:50.058-0500',
                                },
                                'key': 'BAR-2',
                            },
                        ],
                        'maxResults': 2,
                        'startAt': 2,
                        'total': 5,
                    }
                ),
            ),
            Response(
                200,
                request=Request('POST', ''),
                content=json.dumps(
                    {
                        'issues': [
                            {
                                'fields': {
                                    'assignee': {
                                        'accountId': 'qwerty1234567890',
                                        'avatarUrls': {'16x16': 'https://secure.gravatar.com/avatar.png'},
                                        'displayName': 'U.N. Owen',
                                        'timeZone': 'America/New_York',
                                    },
                                    'description': 'Test description',
                                    'labels': ['ddqa-done'],
                                    'project': {'key': 'FOO'},
                                    'summary': 'Test summary',
                                    'updated': '2023-02-13T12:08:50.058-0500',
                                },
                                'key': 'FOO-3',
                            },
                        ],
                        'maxResults': 2,
                        'startAt': 4,
                        'total': 5,
                    }
                ),
            ),
        ],
    )

    assert app.jira.PAGINATION_RESULT_SIZE == 100
    app.jira.PAGINATION_RESULT_SIZE = 2

    issues = []
    async for issue in app.jira.search_issues(ResponsiveNetworkClient(Static())):
        issues.append(issue)

    assert response_mock.call_args_list == [
        mocker.call(
            'POST',
            'https://foobarbaz.atlassian.net/rest/api/2/search',
            auth=('foo@bar.baz', 'bar'),
            json={
                'jql': 'project in ("FOO", "BAR") and labels in ("ddqa-todo", "ddqa-in-progress", "ddqa-done")',
                'fields': ['assignee', 'description', 'labels', 'project', 'summary', 'updated'],
                'maxResults': 2,
                'startAt': 0,
            },
        ),
        mocker.call(
            'POST',
            'https://foobarbaz.atlassian.net/rest/api/2/search',
            auth=('foo@bar.baz', 'bar'),
            json={
                'jql': 'project in ("FOO", "BAR") and labels in ("ddqa-todo", "ddqa-in-progress", "ddqa-done")',
                'fields': ['assignee', 'description', 'labels', 'project', 'summary', 'updated'],
                'maxResults': 2,
                'startAt': 2,
            },
        ),
        mocker.call(
            'POST',
            'https://foobarbaz.atlassian.net/rest/api/2/search',
            auth=('foo@bar.baz', 'bar'),
            json={
                'jql': 'project in ("FOO", "BAR") and labels in ("ddqa-todo", "ddqa-in-progress", "ddqa-done")',
                'fields': ['assignee', 'description', 'labels', 'project', 'summary', 'updated'],
                'maxResults': 2,
                'startAt': 4,
            },
        ),
    ]

    assert len(issues) == 5
    assert issues[0].dict() == {
        'key': 'FOO-1',
        'project': 'FOO',
        'assignee': {
            'avatar_urls': {'16x16': 'https://secure.gravatar.com/avatar.png'},
            'id': 'qwerty1234567890',
            'name': 'U.N. Owen',
            'time_zone': 'America/New_York',
        },
        'description': 'Test description',
        'labels': ['ddqa-todo'],
        'summary': 'Test summary',
        'updated': datetime(2023, 2, 13, 12, 8, 50, 58000, tzinfo=timezone(timedelta(days=-1, seconds=68400))),
    }
    assert issues[1].dict() == {
        'key': 'BAR-1',
        'project': 'BAR',
        'assignee': {
            'avatar_urls': {'16x16': 'https://secure.gravatar.com/avatar.png'},
            'id': 'qwerty1234567890',
            'name': 'U.N. Owen',
            'time_zone': 'America/New_York',
        },
        'description': 'Test description',
        'labels': ['ddqa-todo'],
        'summary': 'Test summary',
        'updated': datetime(2023, 2, 13, 12, 8, 50, 58000, tzinfo=timezone(timedelta(days=-1, seconds=68400))),
    }
    assert issues[2].dict() == {
        'key': 'FOO-2',
        'project': 'FOO',
        'assignee': {
            'avatar_urls': {'16x16': 'https://secure.gravatar.com/avatar.png'},
            'id': 'qwerty1234567890',
            'name': 'U.N. Owen',
            'time_zone': 'America/New_York',
        },
        'description': 'Test description',
        'labels': ['ddqa-in-progress'],
        'summary': 'Test summary',
        'updated': datetime(2023, 2, 13, 12, 8, 50, 58000, tzinfo=timezone(timedelta(days=-1, seconds=68400))),
    }
    assert issues[3].dict() == {
        'key': 'BAR-2',
        'project': 'BAR',
        'assignee': {
            'avatar_urls': {'16x16': 'https://secure.gravatar.com/avatar.png'},
            'id': 'qwerty1234567890',
            'name': 'U.N. Owen',
            'time_zone': 'America/New_York',
        },
        'description': 'Test description',
        'labels': ['ddqa-in-progress'],
        'summary': 'Test summary',
        'updated': datetime(2023, 2, 13, 12, 8, 50, 58000, tzinfo=timezone(timedelta(days=-1, seconds=68400))),
    }
    assert issues[4].dict() == {
        'key': 'FOO-3',
        'project': 'FOO',
        'assignee': {
            'avatar_urls': {'16x16': 'https://secure.gravatar.com/avatar.png'},
            'id': 'qwerty1234567890',
            'name': 'U.N. Owen',
            'time_zone': 'America/New_York',
        },
        'description': 'Test description',
        'labels': ['ddqa-done'],
        'summary': 'Test summary',
        'updated': datetime(2023, 2, 13, 12, 8, 50, 58000, tzinfo=timezone(timedelta(days=-1, seconds=68400))),
    }


async def test_rate_limit_handling(app, git_repository, mocker):
    app.configure(
        git_repository,
        caching=True,
        data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
    )
    repo_config = dict(app.repo.dict())
    repo_config['teams'] = {
        'foo': {
            'jira_project': 'FOO',
            'jira_issue_type': 'Foo-Task',
            'github_team': 'foo-team',
        },
        'bar': {
            'jira_project': 'BAR',
            'jira_issue_type': 'Bar-Task',
            'github_team': 'bar-team',
        },
    }
    app.save_repo_config(repo_config)

    response_mock = mocker.patch(
        'httpx.AsyncClient.request',
        side_effect=[
            Response(
                500,
                request=Request('POST', ''),
                headers={'Retry-After': '1'},
                content=json.dumps(
                    {
                        'key': 'FOO-1',
                    },
                ),
            ),
            Response(
                429,
                request=Request('POST', ''),
                headers={'Retry-After': '1'},
                content=json.dumps(
                    {
                        'key': 'FOO-1',
                    },
                ),
            ),
            Response(
                200,
                request=Request('POST', ''),
                content=json.dumps(
                    {
                        'key': 'FOO-1',
                    },
                ),
            ),
            Response(
                200,
                request=Request('POST', ''),
                content=json.dumps(
                    {
                        'key': 'BAR-1',
                    },
                ),
            ),
        ],
    )

    start = time.time()
    created_issues = await app.jira.create_issues(
        ResponsiveNetworkClient(Static()),
        TestCandidate(
            **{
                'id': '123',
                'title': 'title123',
                'url': 'https://github.com/org/repo/pull/123',
                'body': 'test body',
            }
        ),
        {'foo': 'github-foo', 'bar': 'github-bar'},
    )
    assert time.time() - start >= 2

    assert response_mock.call_args_list == [
        mocker.call(
            'POST',
            'https://foobarbaz.atlassian.net/rest/api/2/issue',
            auth=('foo@bar.baz', 'bar'),
            json={
                'fields': {
                    'assignee': {'id': 'jira-foo'},
                    'description': 'Pull request: [#123|https://github.com/org/repo/pull/123]\n\ntest body',
                    'issuetype': {'name': 'Foo-Task'},
                    'labels': ['ddqa-todo'],
                    'project': {'key': 'FOO'},
                    'summary': 'title123',
                },
            },
        ),
        mocker.call(
            'POST',
            'https://foobarbaz.atlassian.net/rest/api/2/issue',
            auth=('foo@bar.baz', 'bar'),
            json={
                'fields': {
                    'assignee': {'id': 'jira-foo'},
                    'description': 'Pull request: [#123|https://github.com/org/repo/pull/123]\n\ntest body',
                    'issuetype': {'name': 'Foo-Task'},
                    'labels': ['ddqa-todo'],
                    'project': {'key': 'FOO'},
                    'summary': 'title123',
                },
            },
        ),
        mocker.call(
            'POST',
            'https://foobarbaz.atlassian.net/rest/api/2/issue',
            auth=('foo@bar.baz', 'bar'),
            json={
                'fields': {
                    'assignee': {'id': 'jira-foo'},
                    'description': 'Pull request: [#123|https://github.com/org/repo/pull/123]\n\ntest body',
                    'issuetype': {'name': 'Foo-Task'},
                    'labels': ['ddqa-todo'],
                    'project': {'key': 'FOO'},
                    'summary': 'title123',
                },
            },
        ),
        mocker.call(
            'POST',
            'https://foobarbaz.atlassian.net/rest/api/2/issue',
            auth=('foo@bar.baz', 'bar'),
            json={
                'fields': {
                    'assignee': {'id': 'jira-bar'},
                    'description': 'Pull request: [#123|https://github.com/org/repo/pull/123]\n\ntest body',
                    'issuetype': {'name': 'Bar-Task'},
                    'labels': ['ddqa-todo'],
                    'project': {'key': 'BAR'},
                    'summary': 'title123',
                },
            },
        ),
    ]

    assert created_issues == {
        'foo': 'https://foobarbaz.atlassian.net/browse/FOO-1',
        'bar': 'https://foobarbaz.atlassian.net/browse/BAR-1',
    }
