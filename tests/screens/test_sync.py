# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from unittest import mock
from unittest.mock import MagicMock

import pytest
import tomli_w
from httpx import HTTPStatusError, Request, Response
from pydantic import HttpUrl
from textual.widgets import Button, Label, RichLog

from ddqa.screens.sync import InteractiveSidebar, SyncScreen
from tests.common import assert_return_code


@pytest.fixture(scope='module', autouse=True)
def mock_remote_url():
    with mock.patch('ddqa.utils.git.GitRepository.get_remote_url', return_value='https://github.com/org/repo.git'):
        yield


@pytest.fixture
def app(app):
    app.select_screen('sync', SyncScreen(manual_execution=True))
    return app


@pytest.fixture
def auto_mode_app(auto_mode_app):
    auto_mode_app.select_screen('sync', SyncScreen(manual_execution=True, auto_mode=True))
    return auto_mode_app


async def test_response_error(app, git_repository, helpers, mocker):
    app.configure(
        git_repository,
        caching=True,
        data={
            'github': {'user': 'foo', 'token': 'bar'},
            'jira': {'email': 'foo@bar.baz', 'token': 'bar'},
            'datadog': {'api_key': 'baz', 'app_key': 'baz'},
        },
    )
    error = HTTPStatusError('500 error', request=Request('GET', ''), response=Response(500, request=Request('GET', '')))
    mocker.patch('ddqa.utils.datadog.DatadogDatastore.get_members', side_effect=error)

    async with app.run_test():
        sidebar = app.query_one(InteractiveSidebar)

        status = sidebar.query_one(Label)
        assert '500' in str(status.render())

        text_log = sidebar.query_one(RichLog)
        assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(f"""
            Fetching members from Datadog datastore: {app.repo.datastore_id}
            """)

        button = sidebar.query_one(Button)
        assert button.disabled


@pytest.mark.parametrize(
    'application,auto_mode',
    [
        pytest.param('app', False, id='manual'),
        pytest.param('auto_mode_app', True, id='auto'),
    ],
)
async def test_no_members(application, auto_mode, request, git_repository, helpers, mocker):
    app = request.getfixturevalue(application)
    app.configure(
        git_repository,
        caching=True,
        data={
            'github': {'user': 'foo', 'token': 'bar'},
            'jira': {'email': 'foo@bar.baz', 'token': 'bar'},
            'datadog': {'api_key': 'baz', 'app_key': 'baz'},
        },
    )
    mocker.patch('ddqa.utils.datadog.DatadogDatastore.get_members', return_value={})

    async with app.run_test():
        sidebar = app.query_one(InteractiveSidebar)

        status = sidebar.query_one(Label)
        assert str(status.render()) == 'No members found in datastore'

        text_log = sidebar.query_one(RichLog)
        assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(f"""
            Fetching members from Datadog datastore: {app.repo.datastore_id}
            """)

        button = sidebar.query_one(Button)
        assert button.disabled

    assert_return_code(app, auto_mode)


@pytest.mark.parametrize(
    'application,auto_mode',
    [
        pytest.param('app', False, id='manual'),
        pytest.param('auto_mode_app', True, id='auto'),
    ],
)
async def test_save_members(application, auto_mode, request, git_repository, helpers, mocker):
    app = request.getfixturevalue(application)
    app.configure(
        git_repository,
        caching=True,
        data={
            'github': {'user': 'foo', 'token': 'bar'},
            'jira': {'email': 'foo@bar.baz', 'token': 'bar'},
            'datadog': {'api_key': 'baz', 'app_key': 'baz'},
        },
    )
    mocker.patch('ddqa.utils.datadog.DatadogDatastore.get_members', return_value={'g': 'j'})
    mocker.patch('ddqa.cache.datadog.DatadogCache.get_datastore_modified_at', return_value='2024-01-01T00:00:00Z')
    save_datastore = mocker.patch('ddqa.cache.datadog.DatadogCache.save_datastore')

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

    error = HTTPStatusError('500 error', request=Request('GET', ''), response=Response(500, request=Request('GET', '')))
    mocker.patch('ddqa.utils.github.GitHubRepository.get_team_members', side_effect=error)

    async with app.run_test():
        sidebar = app.query_one(InteractiveSidebar)

        text_log = sidebar.query_one(RichLog)
        assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(f"""
            Fetching members from Datadog datastore: {app.repo.datastore_id}
            Refreshing members for team: bar-team
            """)

        button = sidebar.query_one(Button)
        assert button.disabled

        save_datastore.assert_not_called()

    assert_return_code(app, auto_mode)


@pytest.mark.parametrize(
    'application,auto_mode',
    [
        pytest.param('app', False, id='manual'),
        pytest.param('auto_mode_app', True, id='auto'),
    ],
)
async def test_save_teams(application, auto_mode, git_repository, helpers, mocker, request):
    app = request.getfixturevalue(application)
    app.configure(
        git_repository,
        caching=True,
        data={
            'github': {'user': 'foo', 'token': 'bar'},
            'jira': {'email': 'foo@bar.baz', 'token': 'bar'},
            'datadog': {'api_key': 'baz', 'app_key': 'baz'},
        },
    )
    mocker.patch(
        'ddqa.utils.datadog.DatadogDatastore.get_members',
        return_value={'g': 'j', 'foo1': 'jira-foo1', 'bar1': 'jira-bar1'},
    )
    mocker.patch('ddqa.cache.datadog.DatadogCache.get_datastore_modified_at', return_value='2024-01-01T00:00:00Z')
    mocker.patch('ddqa.cache.datadog.DatadogCache.get_datastore_members', return_value={'placeholder': 'placeholder'})
    mocker.patch(
        'ddqa.cache.datadog.DatadogCache.get_datastore_jira_server', return_value='https://example.atlassian.net'
    )
    save_datastore = mocker.patch('ddqa.cache.datadog.DatadogCache.save_datastore')
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
        assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(f"""
            Fetching members from Datadog datastore: {app.repo.datastore_id}
            Refreshing members for team: bar-team
            Refreshing members for team: foo-team
            Validating the Jira members datastore...
            Validating 3 Jira users...
            Sync finished correctly
            """)

        button = sidebar.query_one(Button)
        assert not button.disabled

        save_datastore.assert_called_once_with(
            app.repo.datastore_id,
            '2024-01-01T00:00:00Z',
            {'g': 'j', 'foo1': 'jira-foo1', 'bar1': 'jira-bar1'},
            'https://example.atlassian.net',
        )

        assert_return_code(app, auto_mode)


@pytest.mark.parametrize(
    'application,auto_mode',
    [
        pytest.param('app', False, id='manual'),
        pytest.param('auto_mode_app', True, id='auto'),
    ],
)
async def test_deactivated_jira_user(application, auto_mode, git_repository, helpers, mocker, request):
    app = request.getfixturevalue(application)
    app.configure(
        git_repository,
        caching=True,
        data={
            'github': {'user': 'foo', 'token': 'bar'},
            'jira': {'email': 'foo@bar.baz', 'token': 'bar'},
            'datadog': {'api_key': 'baz', 'app_key': 'baz'},
        },
    )
    mocker.patch(
        'ddqa.utils.datadog.DatadogDatastore.get_members',
        return_value={'g': 'j', 'foo1': 'jira-foo1', 'bar1': 'jira-bar1'},
    )
    mocker.patch('ddqa.cache.datadog.DatadogCache.get_datastore_modified_at', return_value='2024-01-01T00:00:00Z')
    mocker.patch('ddqa.cache.datadog.DatadogCache.get_datastore_members', return_value={'placeholder': 'placeholder'})
    mocker.patch(
        'ddqa.cache.datadog.DatadogCache.get_datastore_jira_server', return_value='https://example.atlassian.net'
    )
    save_datastore = mocker.patch('ddqa.cache.datadog.DatadogCache.save_datastore')
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

        assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(f"""
            Fetching members from Datadog datastore: {app.repo.datastore_id}
            Refreshing members for team: bar-team
            Refreshing members for team: foo-team
            Validating the Jira members datastore...
            Validating 3 Jira users...
            User g is deactivated on Jira
            Sync finished correctly
            """)

        button = sidebar.query_one(Button)
        assert not button.disabled

        save_datastore.assert_called_once_with(
            app.repo.datastore_id,
            '2024-01-01T00:00:00Z',
            {'foo1': 'jira-foo1', 'bar1': 'jira-bar1'},
            'https://example.atlassian.net',
        )

    assert_return_code(app, auto_mode)


@pytest.mark.parametrize(
    'application,auto_mode',
    [
        pytest.param('app', False, id='manual'),
        pytest.param('auto_mode_app', True, id='auto'),
    ],
)
async def test_github_user_not_in_jira(application, auto_mode, git_repository, helpers, mocker, request):
    app = request.getfixturevalue(application)
    app.configure(
        git_repository,
        caching=True,
        data={
            'github': {'user': 'foo', 'token': 'bar'},
            'jira': {'email': 'foo@bar.baz', 'token': 'bar'},
            'datadog': {'api_key': 'baz', 'app_key': 'baz'},
        },
    )

    mocker.patch(
        'ddqa.utils.datadog.DatadogDatastore.get_members',
        return_value={'g': 'j', 'foo1': 'jira-foo1'},
    )
    mocker.patch('ddqa.cache.datadog.DatadogCache.get_datastore_modified_at', return_value='2024-01-01T00:00:00Z')
    mocker.patch('ddqa.cache.datadog.DatadogCache.get_datastore_members', return_value={'placeholder': 'placeholder'})
    mocker.patch(
        'ddqa.cache.datadog.DatadogCache.get_datastore_jira_server', return_value='https://example.atlassian.net'
    )
    save_datastore = mocker.patch('ddqa.cache.datadog.DatadogCache.save_datastore')
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
        assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(f"""
            Fetching members from Datadog datastore: {app.repo.datastore_id}
            Refreshing members for team: bar-team
            Refreshing members for team: foo-team
            GitHub user bar1 is not declared in the Jira members datastore
            Validating the Jira members datastore...
            Validating 2 Jira users...
            Sync finished correctly
            """)

        button = sidebar.query_one(Button)
        assert not button.disabled

        save_datastore.assert_called_once_with(
            app.repo.datastore_id,
            '2024-01-01T00:00:00Z',
            {'g': 'j', 'foo1': 'jira-foo1'},
            'https://example.atlassian.net',
        )

        assert_return_code(app, auto_mode)


@pytest.mark.parametrize(
    'application,auto_mode',
    [
        pytest.param('app', False, id='manual'),
        pytest.param('auto_mode_app', True, id='auto'),
    ],
)
async def test_duplicate_jira_user(application, auto_mode, git_repository, helpers, mocker, request):
    app = request.getfixturevalue(application)
    app.configure(
        git_repository,
        caching=True,
        data={
            'github': {'user': 'foo', 'token': 'bar'},
            'jira': {'email': 'foo@bar.baz', 'token': 'bar'},
            'datadog': {'api_key': 'baz', 'app_key': 'baz'},
        },
    )
    mocker.patch(
        'ddqa.utils.datadog.DatadogDatastore.get_members',
        return_value={'g': 'j', 'foo1': 'jira-foo1', 'bar1': 'jira-foo1', 'baz1': 'jira-baz1'},
    )
    mocker.patch('ddqa.cache.datadog.DatadogCache.get_datastore_modified_at', return_value='2024-01-01T00:00:00Z')
    save_datastore = mocker.patch('ddqa.cache.datadog.DatadogCache.save_datastore')

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

        assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(f"""
            Fetching members from Datadog datastore: {app.repo.datastore_id}
            Refreshing members for team: bar-team
            Refreshing members for team: foo-team
            Validating the Jira members datastore...
            Jira user `jira-foo1` is declared multiple times in the Jira members datastore with GitHub user `foo1`
            Jira user `jira-foo1` is declared multiple times in the Jira members datastore with GitHub user `bar1`
            """)

        button = sidebar.query_one(Button)
        assert button.disabled

        save_datastore.assert_not_called()

    assert_return_code(app, auto_mode)


@pytest.mark.parametrize(
    'application,auto_mode',
    [
        pytest.param('app', False, id='manual'),
        pytest.param('auto_mode_app', True, id='auto'),
    ],
)
async def test_global_config_source(application, auto_mode, git_repository, helpers, mocker, request):
    app = request.getfixturevalue(application)
    app.configure(
        git_repository,
        caching=True,
        data={
            'github': {'user': 'foo', 'token': 'bar'},
            'jira': {'email': 'foo@bar.baz', 'token': 'bar'},
        },
    )

    source = 'https://example.com/config.toml'
    global_config = {'members': {'foo1': 'jira-foo1', 'bar1': 'jira-bar1'}}
    response = Response(200, request=Request('GET', source), text=tomli_w.dumps(global_config))
    mocker.patch('ddqa.utils.network.ResponsiveNetworkClient.get', return_value=response)
    mocker.patch('ddqa.utils.github.GitHubRepository.get_team_members', side_effect=(['foo1'], ['bar1']))
    mocker.patch('ddqa.utils.jira.JiraClient.get_deactivated_users', return_value=MagicMock(return_value=[]))
    mocker.patch(
        'ddqa.cache.github.GitHubCache.load_global_config',
        return_value={'jira_server': 'https://example.atlassian.net', 'members': {'placeholder': 'placeholder'}},
    )
    save_global_config = mocker.patch('ddqa.cache.github.GitHubCache.save_global_config')

    repo_config = dict(app.repo.model_dump())
    del repo_config['datastore_id']
    repo_config['global_config_source'] = source
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
        assert '\n'.join(line.text for line in text_log.lines) == helpers.dedent(f"""
            Fetching global config from: {source}
            Refreshing members for team: bar-team
            Refreshing members for team: foo-team
            Validating the Jira config...
            Validating 2 Jira users...
            Sync finished correctly
            """)

        button = sidebar.query_one(Button)
        assert not button.disabled

        save_global_config.assert_called_with(HttpUrl(source), global_config)

        assert_return_code(app, auto_mode)
