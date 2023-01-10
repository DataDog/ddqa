# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import json
from unittest import mock

import pytest
from httpx import Request, Response
from rich.markdown import Markdown as RichMarkdown
from textual.coordinate import Coordinate
from textual.widgets import Markdown

from ddqa.screens.create import (
    CandidateRendering,
    CandidateSidebar,
    CreateScreen,
    LabeledSwitch,
)
from ddqa.utils.git import GitCommit


@pytest.fixture(scope='module', autouse=True)
def mock_remote_url():
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


@pytest.fixture
def app(app):
    app.select_screen('create', CreateScreen('previous_ref', 'current_ref'))
    return app


@pytest.fixture
def mock_pull_requests(mocker):
    def perform_mock(*pull_requests):
        bad_responses = 0
        valid_pull_request_commits = []
        responses = []

        processed_pr_numbers = set()
        for i, pr in enumerate(pull_requests):
            response_data = pr.pop('response', {})
            bad_response = not pr and response_data
            status_code = response_data.pop('status_code', 200)
            reviewers = pr.pop(
                'reviewers',
                [
                    {'user': {'login': 'username1'}, 'author_association': 'MEMBER'},
                    {'user': {'login': 'username2'}, 'author_association': 'COLLABORATOR'},
                    {'user': {'login': 'username1'}, 'author_association': 'MEMBER'},
                ],
            )

            responses.append(
                Response(
                    status_code,
                    request=Request('GET', ''),
                    content=json.dumps({'items': [pr] if pr else []}),
                    **response_data,
                )
            )

            if bad_response:
                bad_responses += 1
                continue

            index = i - bad_responses + 1
            valid_pull_request_commits.append(GitCommit(hash=f'hash{index}', subject=f'subject{index}'))
            if 'number' not in pr or pr['number'] in processed_pr_numbers:
                continue

            processed_pr_numbers.add(pr['number'])

            responses.append(Response(200, request=Request('GET', ''), content=json.dumps(reviewers)))

        mocker.patch(
            'ddqa.utils.git.GitRepository.get_mutually_exclusive_commits', return_value=valid_pull_request_commits
        )
        mocker.patch('httpx.AsyncClient.get', side_effect=responses)

    return perform_mock


class TestDefaultState:
    async def test_error(self, app, git_repository, helpers):
        app.configure(
            git_repository,
            caching=True,
            data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
            github_teams={'foo-team': ['github-foo1']},
        )

        async with app.run_test() as pilot:
            await pilot.pause(helpers.ASYNC_WAIT)

            sidebar = app.query_one(CandidateSidebar)
            assert sidebar is not None
            assert not sidebar.listing.rows
            assert str(sidebar.label.render()) == ' error '
            assert 'unknown commit current_ref' in str(sidebar.status.render())
            assert sidebar.button.disabled

            rendering = app.query_one(CandidateRendering)
            assert rendering is not None
            assert not str(rendering.label.render())
            assert not str(rendering.title.render())
            assert not str(rendering.labels.render())

            assignments = list(rendering.candidate_assignments.query(LabeledSwitch).results())
            assert len(assignments) == 1
            assert str(assignments[0].label.render()) == 'foo'
            assert assignments[0].switch.value is False

    async def test_no_candidates(self, app, git_repository, helpers):
        app.configure(
            git_repository,
            caching=True,
            data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
            github_teams={'foo-team': ['github-foo1']},
        )
        app.git.capture('tag', 'previous_ref')
        app.git.capture('tag', 'current_ref')

        async with app.run_test() as pilot:
            await pilot.pause(helpers.ASYNC_WAIT)

            sidebar = app.query_one(CandidateSidebar)
            assert sidebar is not None
            assert not sidebar.listing.rows
            assert str(sidebar.label.render()) == ' No candidates '
            assert str(sidebar.status.render()) == 'previous_ref -> current_ref'
            assert sidebar.button.disabled

            rendering = app.query_one(CandidateRendering)
            assert rendering is not None
            assert not str(rendering.label.render())
            assert not str(rendering.title.render())
            assert not str(rendering.labels.render())

            assignments = list(rendering.candidate_assignments.query(LabeledSwitch).results())
            assert len(assignments) == 1
            assert str(assignments[0].label.render()) == 'foo'
            assert assignments[0].switch.value is False


async def test_population(app, git_repository, helpers, mock_pull_requests):
    app.configure(
        git_repository,
        caching=True,
        data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
        github_teams={'foo-team': ['github-foo1']},
    )

    mock_pull_requests(
        {
            'number': '2',
            'title': 'title2',
            'user': {'login': 'username2'},
            'labels': [{'name': 'label1', 'color': '632ca6'}, {'name': 'label2', 'color': '632ca6'}],
            'body': 'foo2\r\nbar2',
        },
        {
            'number': '2',
            'title': 'title2',
            'user': {'login': 'username2'},
            'labels': [{'name': 'label1', 'color': '632ca6'}, {'name': 'label2', 'color': '632ca6'}],
            'body': 'foo2\r\nbar2',
        },
        {},
        {
            'number': '1',
            'title': 'title1',
            'user': {'login': 'username1'},
            'labels': [{'name': 'label1', 'color': '632ca6'}, {'name': 'label2', 'color': '632ca6'}],
            'body': 'foo1\r\nbar1',
        },
    )

    async with app.run_test() as pilot:
        await pilot.pause(helpers.ASYNC_WAIT)

        sidebar = app.query_one(CandidateSidebar)
        table = sidebar.listing
        num_candidates = len(table.rows)
        assert num_candidates == 3
        assert table.get_row_at(0) == ['', 'title2']
        assert table.get_row_at(1) == ['', 'subject3']
        assert table.get_row_at(2) == ['', 'title1']

        assert table.cursor_coordinate == Coordinate(0, 0)

        assert str(sidebar.label.render()) == f' {num_candidates} / {num_candidates} '
        assert str(sidebar.status.render()) == 'No candidates assigned'
        assert sidebar.button.disabled

        rendering = app.query_one(CandidateRendering)
        assignments = list(rendering.candidate_assignments.query(LabeledSwitch).results())
        assert len(assignments) == 1
        assert str(assignments[0].label.render()) == 'foo'
        assert assignments[0].switch.value is False


async def test_rendering(app, git_repository, helpers, mock_pull_requests):
    app.configure(
        git_repository,
        caching=True,
        data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
        github_teams={'foo-team': ['github-foo1']},
    )

    mock_pull_requests(
        {
            'number': '2',
            'title': 'title2',
            'user': {'login': 'username2'},
            'labels': [{'name': 'label1', 'color': '632ca6'}, {'name': 'label2', 'color': '632ca6'}],
            'body': 'foo2\r\nbar2',
        },
        {
            'number': '2',
            'title': 'title2',
            'user': {'login': 'username2'},
            'labels': [{'name': 'label1', 'color': '632ca6'}, {'name': 'label2', 'color': '632ca6'}],
            'body': 'foo2\r\nbar2',
        },
        {},
        {
            'number': '1',
            'title': 'title1',
            'user': {'login': 'username1'},
            'labels': [{'name': 'label1', 'color': '632ca6'}, {'name': 'label2', 'color': '632ca6'}],
            'body': 'foo1\r\nbar1',
        },
    )

    async with app.run_test() as pilot:
        await pilot.pause(helpers.ASYNC_WAIT)

        sidebar = app.query_one(CandidateSidebar)
        table = sidebar.listing

        rendering = app.query_one(CandidateRendering)
        rendered_label = rendering.label.render()
        rendered_label_text = str(rendered_label)
        assert rendered_label_text == ' PR 2 '
        assert len(rendered_label.spans) == 1
        rendered_label_span = rendered_label.spans[0]
        assert rendered_label_span.start == 1
        assert rendered_label_span.end == len(rendered_label_text) - 1
        assert rendered_label_span.style == 'link https://github.com/org/repo/pull/2'

        rendered_title = rendering.title.render()
        assert isinstance(rendered_title, RichMarkdown)
        assert helpers.rich_render(rendered_title).strip() == table.get_row_at(0)[1]

        rendered_labels = rendering.labels.render()
        assert helpers.rich_render(rendered_labels).strip() == 'label1 label2'

        rendered_body1 = [w for w in rendering.body.children if isinstance(w, Markdown)][0]

        table.cursor_coordinate = Coordinate(1, 0)
        await pilot.pause(helpers.ASYNC_WAIT)

        rendered_label = rendering.label.render()
        rendered_label_text = str(rendered_label)
        assert rendered_label_text == ' Commit hash3 '
        assert len(rendered_label.spans) == 1
        rendered_label_span = rendered_label.spans[0]
        assert rendered_label_span.start == 1
        assert rendered_label_span.end == len(rendered_label_text) - 1
        assert rendered_label_span.style == 'link https://github.com/org/repo/commit/hash3'

        rendered_title = rendering.title.render()
        assert isinstance(rendered_title, RichMarkdown)
        assert helpers.rich_render(rendered_title).strip() == table.get_row_at(1)[1]

        assert any(w for w in rendering.body.children if isinstance(w, Markdown) and w is not rendered_body1)

        assignments = list(rendering.candidate_assignments.query(LabeledSwitch).results())
        assert len(assignments) == 1
        assert str(assignments[0].label.render()) == 'foo'
        assert assignments[0].switch.value is False


class TestAssignment:
    async def test_default(self, app, git_repository, helpers, mock_pull_requests):
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
                'github_team': 'foo-team',
                'github_labels': ['foo-label'],
            },
            'bar': {
                'jira_project': 'BAR',
                'jira_issue_type': 'Bar-Task',
                'github_team': 'bar-team',
                'github_labels': ['bar-label'],
            },
        }
        app.save_repo_config(repo_config)

        mock_pull_requests(
            {
                'number': '2',
                'title': 'title2',
                'user': {'login': 'username2'},
                'labels': [{'name': 'foo-label', 'color': '632ca6'}, {'name': 'baz-label', 'color': '632ca6'}],
                'body': 'foo2\r\nbar2',
            },
            {
                'number': '2',
                'title': 'title2',
                'user': {'login': 'username2'},
                'labels': [{'name': 'foo-label', 'color': '632ca6'}, {'name': 'baz-label', 'color': '632ca6'}],
                'body': 'foo2\r\nbar2',
            },
            {},
            {
                'number': '1',
                'title': 'title1',
                'user': {'login': 'username1'},
                'labels': [{'name': 'bar-label', 'color': '632ca6'}, {'name': 'baz-label', 'color': '632ca6'}],
                'body': 'foo1\r\nbar1',
            },
        )

        async with app.run_test() as pilot:
            await pilot.pause(helpers.ASYNC_WAIT)

            sidebar = app.query_one(CandidateSidebar)
            table = sidebar.listing
            num_candidates = len(table.rows)
            assert num_candidates == 3
            assert table.get_row_at(0) == ['✓', 'title2']
            assert table.get_row_at(1) == ['', 'subject3']
            assert table.get_row_at(2) == ['✓', 'title1']
            assert [c.assigned for c in table.candidates.values()] == [
                True,
                False,
                True,
            ]

            assert table.cursor_coordinate == Coordinate(0, 0)

            assert str(sidebar.label.render()) == f' {num_candidates} / {num_candidates} '
            assert str(sidebar.status.render()) == 'Ready for creation'
            assert not sidebar.button.disabled

            rendering = app.query_one(CandidateRendering)
            assignments = list(rendering.candidate_assignments.query(LabeledSwitch).results())
            assert len(assignments) == 2
            assert str(assignments[0].label.render()) == 'foo'
            assert str(assignments[1].label.render()) == 'bar'

    async def test_choice(self, app, git_repository, helpers, mock_pull_requests):
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
                'github_team': 'foo-team',
                'github_labels': ['foo-label'],
            },
            'bar': {
                'jira_project': 'BAR',
                'jira_issue_type': 'Bar-Task',
                'github_team': 'bar-team',
                'github_labels': ['bar-label'],
            },
        }
        app.save_repo_config(repo_config)

        mock_pull_requests(
            {
                'number': '2',
                'title': 'title2',
                'user': {'login': 'username2'},
                'labels': [{'name': 'foo-label', 'color': '632ca6'}, {'name': 'baz-label', 'color': '632ca6'}],
                'body': 'foo2\r\nbar2',
            },
            {
                'number': '2',
                'title': 'title2',
                'user': {'login': 'username2'},
                'labels': [{'name': 'foo-label', 'color': '632ca6'}, {'name': 'baz-label', 'color': '632ca6'}],
                'body': 'foo2\r\nbar2',
            },
            {},
            {
                'number': '1',
                'title': 'title1',
                'user': {'login': 'username1'},
                'labels': [{'name': 'bar-label', 'color': '632ca6'}, {'name': 'baz-label', 'color': '632ca6'}],
                'body': 'foo1\r\nbar1',
            },
        )

        async with app.run_test() as pilot:
            await pilot.pause(helpers.ASYNC_WAIT)

            sidebar = app.query_one(CandidateSidebar)
            table = sidebar.listing
            num_candidates = len(table.rows)
            assert num_candidates == 3
            assert table.get_row_at(0) == ['✓', 'title2']
            assert table.get_row_at(1) == ['', 'subject3']
            assert table.get_row_at(2) == ['✓', 'title1']
            assert [c.assigned for c in table.candidates.values()] == [
                True,
                False,
                True,
            ]

            assert table.cursor_coordinate == Coordinate(0, 0)

            assert str(sidebar.label.render()) == f' {num_candidates} / {num_candidates} '
            assert str(sidebar.status.render()) == 'Ready for creation'
            assert not sidebar.button.disabled

            rendering = app.query_one(CandidateRendering)
            assignments = list(rendering.candidate_assignments.query(LabeledSwitch).results())
            assert len(assignments) == 2
            assert str(assignments[0].label.render()) == 'foo'
            assert str(assignments[1].label.render()) == 'bar'

            app.set_focus(assignments[0].switch)
            await pilot.press('enter')
            assert table.get_row_at(0) == ['', 'title2']
            assert table.get_row_at(1) == ['', 'subject3']
            assert table.get_row_at(2) == ['✓', 'title1']
            assert [c.assigned for c in table.candidates.values()] == [
                False,
                False,
                True,
            ]
            assert str(sidebar.status.render()) == 'Ready for creation'
            assert not sidebar.button.disabled

            table.cursor_coordinate = Coordinate(2, 0)
            app.set_focus(assignments[1].switch)
            await pilot.press('enter')
            assert table.get_row_at(0) == ['', 'title2']
            assert table.get_row_at(1) == ['', 'subject3']
            assert table.get_row_at(2) == ['', 'title1']
            assert [c.assigned for c in table.candidates.values()] == [
                False,
                False,
                False,
            ]
            assert str(sidebar.status.render()) == 'No candidates assigned'
            assert sidebar.button.disabled

            table.cursor_coordinate = Coordinate(1, 0)
            await pilot.press('enter')
            assert table.get_row_at(0) == ['', 'title2']
            assert table.get_row_at(1) == ['✓', 'subject3']
            assert table.get_row_at(2) == ['', 'title1']
            assert [c.assigned for c in table.candidates.values()] == [
                False,
                True,
                False,
            ]
            assert str(sidebar.status.render()) == 'Ready for creation'
            assert not sidebar.button.disabled

    async def test_ignored_labels(self, app, git_repository, helpers, mock_pull_requests):
        app.configure(
            git_repository,
            caching=True,
            data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
            github_teams={'foo-team': ['github-foo1']},
        )
        repo_config = dict(app.repo.dict())
        repo_config['ignored_labels'] = ['baz-label']
        repo_config['teams'] = {
            'foo': {
                'jira_project': 'FOO',
                'jira_issue_type': 'Foo-Task',
                'github_team': 'foo-team',
                'github_labels': ['foo-label'],
            },
            'bar': {
                'jira_project': 'BAR',
                'jira_issue_type': 'Bar-Task',
                'github_team': 'bar-team',
                'github_labels': ['bar-label'],
            },
        }
        app.save_repo_config(repo_config)

        mock_pull_requests(
            {
                'number': '2',
                'title': 'title2',
                'user': {'login': 'username2'},
                'labels': [{'name': 'foo-label', 'color': '632ca6'}, {'name': 'baz-label', 'color': '632ca6'}],
                'body': 'foo2\r\nbar2',
            },
            {
                'number': '2',
                'title': 'title2',
                'user': {'login': 'username2'},
                'labels': [{'name': 'foo-label', 'color': '632ca6'}, {'name': 'baz-label', 'color': '632ca6'}],
                'body': 'foo2\r\nbar2',
            },
            {},
            {
                'number': '1',
                'title': 'title1',
                'user': {'login': 'username1'},
                'labels': [{'name': 'bar-label', 'color': '632ca6'}, {'name': 'baz-label', 'color': '632ca6'}],
                'body': 'foo1\r\nbar1',
            },
        )

        async with app.run_test() as pilot:
            await pilot.pause(helpers.ASYNC_WAIT)

            sidebar = app.query_one(CandidateSidebar)
            table = sidebar.listing
            num_candidates = len(table.rows)
            assert num_candidates == 3
            assert table.get_row_at(0) == ['', 'title2']
            assert table.get_row_at(1) == ['', 'subject3']
            assert table.get_row_at(2) == ['', 'title1']
            assert [c.assigned for c in table.candidates.values()] == [
                False,
                False,
                False,
            ]

            assert table.cursor_coordinate == Coordinate(0, 0)

            assert str(sidebar.label.render()) == f' {num_candidates} / {num_candidates} '
            assert str(sidebar.status.render()) == 'No candidates assigned'
            assert sidebar.button.disabled

            rendering = app.query_one(CandidateRendering)
            assignments = list(rendering.candidate_assignments.query(LabeledSwitch).results())
            assert len(assignments) == 2
            assert str(assignments[0].label.render()) == 'foo'
            assert assignments[0].switch.value is False
            assert str(assignments[1].label.render()) == 'bar'
            assert assignments[1].switch.value is False


class TestCreation:
    async def test_assignment(self, app, git_repository, helpers, mocker, mock_pull_requests):
        app.configure(
            git_repository,
            caching=True,
            data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
            github_teams={
                'foo-team': ['github-foo1', 'github-foo2', 'github-foo3', 'github-foo4', 'github-foo5', 'github-foo6'],
                'bar-team': ['github-bar1', 'github-bar2', 'github-bar3', 'github-bar4', 'github-bar5', 'github-bar6'],
            },
        )
        repo_config = dict(app.repo.dict())
        repo_config['ignored_labels'] = ['baz-label']
        repo_config['teams'] = {
            'Foo Baz': {
                'jira_project': 'FOO',
                'jira_issue_type': 'Foo-Task',
                'github_team': 'foo-team',
                'github_labels': ['foo-label'],
            },
            'Bar Baz': {
                'jira_project': 'BAR',
                'jira_issue_type': 'Bar-Task',
                'github_team': 'bar-team',
                'github_labels': ['bar-label'],
            },
        }
        app.save_repo_config(repo_config)

        mock_pull_requests(
            {
                'number': '2',
                'title': 'title2',
                'user': {'login': 'github-foo1'},
                'labels': [{'name': 'foo-label', 'color': '632ca6'}],
                'body': 'foo2\r\nbar2',
                'reviewers': [
                    {'user': {'login': 'github-foo2'}, 'author_association': 'MEMBER'},
                    {'user': {'login': 'github-foo3'}, 'author_association': 'MEMBER'},
                    {'user': {'login': 'github-foo4'}, 'author_association': 'MEMBER'},
                    {'user': {'login': 'github-foo5'}, 'author_association': 'MEMBER'},
                ],
            },
            {
                'number': '2',
                'title': 'title2',
                'user': {'login': 'github-foo1'},
                'labels': [{'name': 'foo-label', 'color': '632ca6'}],
                'body': 'foo2\r\nbar2',
                'reviewers': [
                    {'user': {'login': 'github-foo2'}, 'author_association': 'MEMBER'},
                    {'user': {'login': 'github-foo3'}, 'author_association': 'MEMBER'},
                    {'user': {'login': 'github-foo4'}, 'author_association': 'MEMBER'},
                    {'user': {'login': 'github-foo5'}, 'author_association': 'MEMBER'},
                ],
            },
            {},
            {
                'number': '1',
                'title': 'title1',
                'user': {'login': 'github-bar1'},
                'labels': [{'name': 'foo-label', 'color': '632ca6'}, {'name': 'bar-label', 'color': '632ca6'}],
                'body': 'foo1\r\nbar1',
                'reviewers': [
                    {'user': {'login': 'github-foo1'}, 'author_association': 'MEMBER'},
                    {'user': {'login': 'github-foo2'}, 'author_association': 'MEMBER'},
                    {'user': {'login': 'github-foo3'}, 'author_association': 'MEMBER'},
                    {'user': {'login': 'github-foo4'}, 'author_association': 'MEMBER'},
                    {'user': {'login': 'github-foo5'}, 'author_association': 'MEMBER'},
                    {'user': {'login': 'github-bar2'}, 'author_association': 'MEMBER'},
                    {'user': {'login': 'github-bar3'}, 'author_association': 'MEMBER'},
                    {'user': {'login': 'github-bar4'}, 'author_association': 'MEMBER'},
                    {'user': {'login': 'github-bar5'}, 'author_association': 'MEMBER'},
                ],
            },
        )

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
                Response(
                    200,
                    request=Request('POST', ''),
                    content=json.dumps(
                        {
                            'key': 'FOO-2',
                        },
                    ),
                ),
                Response(
                    200,
                    request=Request('POST', ''),
                    content=json.dumps(
                        {
                            'key': 'BAR-2',
                        },
                    ),
                ),
            ],
        )

        async with app.run_test() as pilot:
            await pilot.pause(helpers.ASYNC_WAIT)

            sidebar = app.query_one(CandidateSidebar)
            table = sidebar.listing
            num_candidates = len(table.rows)
            assert num_candidates == 3
            assert table.get_row_at(0) == ['✓', 'title2']
            assert table.get_row_at(1) == ['', 'subject3']
            assert table.get_row_at(2) == ['✓', 'title1']
            assert [c.assigned for c in table.candidates.values()] == [
                True,
                False,
                True,
            ]
            assert str(sidebar.status.render()) == 'Ready for creation'
            assert not sidebar.button.disabled

            rendering = app.query_one(CandidateRendering)
            assignments = list(rendering.candidate_assignments.query(LabeledSwitch).results())
            assert len(assignments) == 2
            assert str(assignments[0].label.render()) == 'Foo Baz'
            assert str(assignments[1].label.render()) == 'Bar Baz'

            table.cursor_coordinate = Coordinate(1, 0)
            app.set_focus(assignments[1].switch)
            await pilot.press('enter')

            assert table.get_row_at(0) == ['✓', 'title2']
            assert table.get_row_at(1) == ['✓', 'subject3']
            assert table.get_row_at(2) == ['✓', 'title1']
            assert [c.assigned for c in table.candidates.values()] == [
                True,
                True,
                True,
            ]

            app.set_focus(sidebar.button)
            await pilot.press('enter')

            assert str(sidebar.status.render()) == 'Finished'
            assert str(sidebar.label.render()) == f' {num_candidates} / {num_candidates} '
            assert str(sidebar.button.label) == 'Exit'

            assert response_mock.call_args_list == [
                mocker.call('GET', 'https://foobarbaz.atlassian.net/rest/api/2/myself', auth=('foo@bar.baz', 'bar')),
                mocker.call(
                    'POST',
                    'https://foobarbaz.atlassian.net/rest/api/2/issue',
                    auth=('foo@bar.baz', 'bar'),
                    json={
                        'fields': {
                            'assignee': {'id': 'jira-foo6'},
                            'description': helpers.dedent(
                                """
                                Pull request: [#2|https://github.com/org/repo/pull/2]
                                Author: [github-foo1|https://github.com/github-foo1]
                                Labels: {{foo-label}}
        
                                foo2
                                bar2
                                """
                            ),
                            'issuetype': {'name': 'Foo-Task'},
                            'labels': ['ddqa-todo'],
                            'project': {'key': 'FOO'},
                            'reporter': {'id': 'qwerty1234567890'},
                            'summary': 'title2',
                        },
                    },
                ),
                mocker.call(
                    'POST',
                    'https://foobarbaz.atlassian.net/rest/api/2/issue',
                    auth=('foo@bar.baz', 'bar'),
                    json={
                        'fields': {
                            'assignee': {'id': mocker.ANY},
                            'description': helpers.dedent(
                                """
                                Commit: [hash3|https://github.com/org/repo/commit/hash3]


                                """
                            ),
                            'issuetype': {'name': 'Bar-Task'},
                            'labels': ['ddqa-todo'],
                            'project': {'key': 'BAR'},
                            'reporter': {'id': 'qwerty1234567890'},
                            'summary': 'subject3',
                        },
                    },
                ),
                mocker.call(
                    'POST',
                    'https://foobarbaz.atlassian.net/rest/api/2/issue',
                    auth=('foo@bar.baz', 'bar'),
                    json={
                        'fields': {
                            'assignee': {'id': 'jira-foo6'},
                            'description': helpers.dedent(
                                """
                                Pull request: [#1|https://github.com/org/repo/pull/1]
                                Author: [github-bar1|https://github.com/github-bar1]
                                Labels: {{foo-label}}, {{bar-label}}
        
                                foo1
                                bar1
                                """
                            ),
                            'issuetype': {'name': 'Foo-Task'},
                            'labels': ['ddqa-todo'],
                            'project': {'key': 'FOO'},
                            'reporter': {'id': 'qwerty1234567890'},
                            'summary': 'title1',
                        },
                    },
                ),
                mocker.call(
                    'POST',
                    'https://foobarbaz.atlassian.net/rest/api/2/issue',
                    auth=('foo@bar.baz', 'bar'),
                    json={
                        'fields': {
                            'assignee': {'id': 'jira-bar6'},
                            'description': helpers.dedent(
                                """
                                Pull request: [#1|https://github.com/org/repo/pull/1]
                                Author: [github-bar1|https://github.com/github-bar1]
                                Labels: {{foo-label}}, {{bar-label}}
        
                                foo1
                                bar1
                                """
                            ),
                            'issuetype': {'name': 'Bar-Task'},
                            'labels': ['ddqa-todo'],
                            'project': {'key': 'BAR'},
                            'reporter': {'id': 'qwerty1234567890'},
                            'summary': 'title1',
                        },
                    },
                ),
            ]
