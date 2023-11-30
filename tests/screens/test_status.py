# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from datetime import datetime
from unittest import mock
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import pytest
from textual.widgets import Select

from ddqa.models.jira import Assignee, JiraIssue, Status
from ddqa.screens.status import FilterSelect, IssueFilter, StatusScreen


@pytest.fixture
def app(app):
    app.select_screen('sync', StatusScreen('7.50.0-qa'))
    return app


@pytest.fixture(scope='module', autouse=True)
def mock_remote_call():
    with (
        mock.patch('ddqa.utils.git.GitRepository.get_remote_url', return_value='https://github.com/org/repo.git'),
        mock.patch(
            'ddqa.utils.github.GitHubRepository.load_global_config',
            return_value={
                'jira_server': 'https://foobarbaz.atlassian.net',
                'members': {
                    'github-foo1': 'jira-foo1',
                    'github-foo2': 'jira-foo2',
                    'github-foo3': 'jira-foo3',
                    'github-foo4': 'jira-foo4',
                    'github-foo5': 'jira-foo5',
                    'github-foo6': 'jira-foo6',
                    'github-bar1': 'jira-bar1',
                    'github-bar2': 'jira-bar2',
                    'github-bar3': 'jira-bar3',
                    'github-bar4': 'jira-bar4',
                    'github-bar5': 'jira-bar5',
                    'github-bar6': 'jira-bar6',
                },
            },
        ),
    ):
        yield


class DummyIssueFilter(IssueFilter):
    def update(self, old_issue: JiraIssue, new_issue: JiraIssue):
        pass


class TestFilterSelect:
    def test_sorted_by_filter_key(self):
        dummy_filter = DummyIssueFilter()
        for issue_id in ('c', 'b', 'z', 'a'):
            issue = JiraIssue.construct(key=f'key-{issue_id}')
            dummy_filter.add(issue_id, issue)

        select = FilterSelect(dummy_filter)

        assert select._options == [('', Select.BLANK), ('a', 'a'), ('b', 'b'), ('c', 'c'), ('z', 'z')]


class TestStatus:
    async def test_default(self, app, git_repository, helpers, mocker):
        app.configure(
            git_repository,
            caching=True,
            data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
            github_teams={'foo-team': ['github-foo1']},
        )
        repo_config = dict(app.repo.dict())
        repo_config['teams'] = {
            'foo': {
                'jira_project': 'FOO',
                'jira_issue_type': 'Foo-Task',
                'jira_statuses': {'TODO': 'Backlog', 'IN PROGRESS': 'Sprint', 'DONE': 'Done'},
                'github_team': 'foo-team',
            },
        }
        app.save_repo_config(repo_config)

        issue1 = JiraIssue.construct(
            key='i1',
            project='FOO',
            components=[],
            summary='',
            updated=datetime.now(tz=ZoneInfo('UTC')),
            status=Status.construct(name='Backlog'),
            assignee=Assignee.construct(id='1', name='jira-foo1'),
        )
        issue2 = JiraIssue.construct(
            key='i2',
            project='FOO',
            components=[],
            summary='',
            updated=datetime.now(tz=ZoneInfo('UTC')),
            status=Status.construct(name='Sprint'),
            assignee=Assignee.construct(id='2', name='jira-foo2'),
        )
        issue3 = JiraIssue.construct(
            key='i3',
            project='FOO',
            components=[],
            summary='',
            updated=datetime.now(tz=ZoneInfo('UTC')),
            status=Status.construct(name='Done'),
            assignee=Assignee.construct(id='1', name='jira-foo1'),
        )

        jira_mock = MagicMock()
        jira_mock.__aiter__.return_value = [issue1, issue2, issue3]
        mocker.patch('ddqa.utils.jira.JiraClient.search_issues', return_value=jira_mock)
        mocker.patch('ddqa.utils.jira.JiraClient.get_current_user_id', return_value='current_user_id')

        async with app.run_test() as pilot:
            await pilot.pause(helpers.ASYNC_WAIT)
            screen = app.query_one(StatusScreen)

            member_filter = screen.member_filter
            assert len(member_filter.issues) == 2
            assert len(member_filter.issues['jira-foo1']) == 2
            assert len(member_filter.issues['jira-foo2']) == 1
            assert member_filter.issues['jira-foo1'] == {'i1': issue1, 'i3': issue3}
            assert member_filter.issues['jira-foo2'] == {'i2': issue2}

            team_filter = screen.team_filter
            assert len(team_filter.issues) == 1
            assert len(team_filter.issues['foo']) == 3
            assert team_filter.issues['foo'] == {'i1': issue1, 'i2': issue2, 'i3': issue3}

            assert screen.statuses['TODO'].table.row_count == 1
            row = screen.statuses['TODO'].table.get_row_at(0)
            assert row[0] == 'i1'
            assert row[1] == 'jira-foo1'
            assert screen.statuses['IN PROGRESS'].table.row_count == 1
            row = screen.statuses['IN PROGRESS'].table.get_row_at(0)
            assert row[0] == 'i2'
            assert row[1] == 'jira-foo2'
            assert screen.statuses['DONE'].table.row_count == 1
            row = screen.statuses['DONE'].table.get_row_at(0)
            assert row[0] == 'i3'
            assert row[1] == 'jira-foo1'

    async def test_filter_by_team(self, app, git_repository, helpers, mocker):
        app.configure(
            git_repository,
            caching=True,
            data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
            github_teams={'foo-team': ['github-foo1']},
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

        issue1 = JiraIssue.construct(
            key='i1',
            project='FOO',
            components=[],
            summary='',
            updated=datetime.now(tz=ZoneInfo('UTC')),
            status=Status.construct(name='Backlog'),
            assignee=Assignee.construct(id='1', name='jira-foo1'),
        )
        issue2 = JiraIssue.construct(
            key='i2',
            project='FOO',
            components=[],
            summary='',
            updated=datetime.now(tz=ZoneInfo('UTC')),
            status=Status.construct(name='Sprint'),
            assignee=Assignee.construct(id='2', name='jira-foo2'),
        )
        issue3 = JiraIssue.construct(
            key='i3',
            project='BAR',
            components=[],
            summary='',
            updated=datetime.now(tz=ZoneInfo('UTC')),
            status=Status.construct(name='Done'),
            assignee=Assignee.construct(id='1', name='jira-foo1'),
        )

        jira_mock = MagicMock()
        jira_mock.__aiter__.return_value = [issue1, issue2, issue3]
        mocker.patch('ddqa.utils.jira.JiraClient.search_issues', return_value=jira_mock)
        mocker.patch('ddqa.utils.jira.JiraClient.get_current_user_id', return_value='current_user_id')

        async with app.run_test() as pilot:
            await pilot.pause(helpers.ASYNC_WAIT)
            screen = app.query_one(StatusScreen)

            select = app.query_one('#team_select')
            select.value = 'foo'
            await screen.on_select_changed(Select.Changed(select, 'foo'))
            await pilot.pause(helpers.ASYNC_WAIT)

            assert screen.statuses['TODO'].table.row_count == 1
            row = screen.statuses['TODO'].table.get_row_at(0)
            assert row[0] == 'i1'
            assert row[1] == 'jira-foo1'
            assert screen.statuses['IN PROGRESS'].table.row_count == 1
            row = screen.statuses['IN PROGRESS'].table.get_row_at(0)
            assert row[0] == 'i2'
            assert row[1] == 'jira-foo2'
            assert screen.statuses['DONE'].table.row_count == 0

    async def test_filter_by_member(self, app, git_repository, helpers, mocker):
        app.configure(
            git_repository,
            caching=True,
            data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
            github_teams={'foo-team': ['github-foo1']},
        )
        repo_config = dict(app.repo.dict())
        repo_config['teams'] = {
            'foo': {
                'jira_project': 'FOO',
                'jira_issue_type': 'Foo-Task',
                'jira_statuses': {'TODO': 'Backlog', 'IN PROGRESS': 'Sprint', 'DONE': 'Done'},
                'github_team': 'foo-team',
            },
        }
        app.save_repo_config(repo_config)

        issue1 = JiraIssue.construct(
            key='i1',
            project='FOO',
            components=[],
            summary='',
            updated=datetime.now(tz=ZoneInfo('UTC')),
            status=Status.construct(name='Backlog'),
            assignee=Assignee.construct(id='1', name='jira-foo1'),
        )
        issue2 = JiraIssue.construct(
            key='i2',
            project='FOO',
            components=[],
            summary='',
            updated=datetime.now(tz=ZoneInfo('UTC')),
            status=Status.construct(name='Sprint'),
            assignee=Assignee.construct(id='2', name='jira-foo2'),
        )
        issue3 = JiraIssue.construct(
            key='i3',
            project='FOO',
            components=[],
            summary='',
            updated=datetime.now(tz=ZoneInfo('UTC')),
            status=Status.construct(name='Done'),
            assignee=Assignee.construct(id='1', name='jira-foo1'),
        )

        jira_mock = MagicMock()
        jira_mock.__aiter__.return_value = [issue1, issue2, issue3]
        mocker.patch('ddqa.utils.jira.JiraClient.search_issues', return_value=jira_mock)
        mocker.patch('ddqa.utils.jira.JiraClient.get_current_user_id', return_value='current_user_id')

        async with app.run_test() as pilot:
            await pilot.pause(helpers.ASYNC_WAIT)
            screen = app.query_one(StatusScreen)
            select = app.query_one('#member_select')
            select.value = 'jira-foo1'
            await screen.on_select_changed(Select.Changed(select, 'jira-foo1'))
            await pilot.pause(helpers.ASYNC_WAIT)

            assert screen.statuses['TODO'].table.row_count == 1
            row = screen.statuses['TODO'].table.get_row_at(0)
            assert row[0] == 'i1'
            assert row[1] == 'jira-foo1'
            assert screen.statuses['IN PROGRESS'].table.row_count == 0
            assert screen.statuses['DONE'].table.row_count == 1
            row = screen.statuses['DONE'].table.get_row_at(0)
            assert row[0] == 'i3'
            assert row[1] == 'jira-foo1'
