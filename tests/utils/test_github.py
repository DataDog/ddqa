# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import json
import time
from unittest import mock

import pytest
from httpx import Request, Response
from textual.widgets import Static

from ddqa.models.github import TestCandidate as Candidate
from ddqa.utils.git import GitCommit
from ddqa.utils.network import ResponsiveNetworkClient


@pytest.fixture(scope='module', autouse=True)
def mock_remote_url():
    with mock.patch('ddqa.utils.git.GitRepository.get_remote_url', return_value='https://github.com/org/repo.git'):
        yield


@pytest.mark.parametrize(
    'url, repo_id', [('https://github.com/foo/bar.git', 'foo/bar'), ('username@github.com:foo/bar.git', 'foo/bar')]
)
def test_repo_id(app, git_repository, url, repo_id):
    app.configure(
        git_repository,
        caching=True,
        data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
    )

    with mock.patch('ddqa.utils.git.GitRepository.get_remote_url', return_value=url):
        assert app.github.repo_id == repo_id


class TestCandidates:
    async def test_pr(self, app, git_repository, mocker):
        app.configure(
            git_repository,
            caching=True,
            data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
        )

        response_mock = mocker.patch(
            'httpx.AsyncClient.get',
            side_effect=[
                Response(
                    200,
                    request=Request('GET', ''),
                    content=json.dumps(
                        {
                            'items': [
                                {
                                    'number': '123',
                                    'title': 'title123',
                                    'user': {'login': 'username123'},
                                    'labels': [
                                        {'name': 'label1', 'color': '632ca6'},
                                        {'name': 'label2', 'color': '632ca6'},
                                    ],
                                    'body': 'foo\r\nbar',
                                },
                            ],
                        },
                    ),
                ),
                Response(
                    200,
                    request=Request('GET', ''),
                    content=json.dumps(
                        [
                            {
                                'user': {'login': 'username1'},
                                'author_association': 'MEMBER',
                            },
                            {
                                'user': {'login': 'username2'},
                                'author_association': 'COLLABORATOR',
                            },
                            {
                                'user': {'login': 'username1'},
                                'author_association': 'MEMBER',
                            },
                        ],
                    ),
                ),
            ],
        )

        candidate = await app.github.get_candidate(
            ResponsiveNetworkClient(Static()), GitCommit(hash='hash9000', subject='subject9000')
        )
        assert response_mock.call_args_list == [
            mocker.call(
                'https://api.github.com/search/issues',
                params={'q': 'sha:hash9000 repo:org/repo is:merged'},
                auth=('foo', 'bar'),
            ),
            mocker.call('https://api.github.com/repos/org/repo/pulls/123/reviews', auth=('foo', 'bar')),
        ]

        assert candidate.dict() == {
            'id': '123',
            'title': 'title123',
            'url': 'https://github.com/org/repo/pull/123',
            'user': 'username123',
            'labels': [{'name': 'label1', 'color': '632ca6'}, {'name': 'label2', 'color': '632ca6'}],
            'body': 'foo\nbar',
            'reviewers': [
                {'name': 'username1', 'association': 'member'},
                {'name': 'username2', 'association': 'collaborator'},
            ],
            'assigned_teams': set(),
        }

    async def test_get_candidates(self, app, git_repository, mocker):
        app.configure(
            git_repository,
            caching=True,
            data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
        )

        response_mock = mocker.patch(
            'httpx.AsyncClient.get',
            side_effect=[
                Response(
                    200,
                    request=Request('GET', ''),
                    content=json.dumps(
                        {
                            'items': [
                                {
                                    'number': '123',
                                    'title': 'title123',
                                    'user': {'login': 'username123'},
                                    'labels': [
                                        {'name': 'label1', 'color': '632ca6'},
                                        {'name': 'label2', 'color': '632ca6'},
                                    ],
                                    'body': 'foo\r\nbar',
                                },
                            ],
                        },
                    ),
                ),
                Response(
                    200,
                    request=Request('GET', ''),
                    content=json.dumps(
                        [
                            {
                                'user': {'login': 'username1'},
                                'author_association': 'MEMBER',
                            },
                            {
                                'user': {'login': 'username2'},
                                'author_association': 'COLLABORATOR',
                            },
                            {
                                'user': {'login': 'username1'},
                                'author_association': 'MEMBER',
                            },
                        ],
                    ),
                ),
            ],
        )

        candidates = []

        async for model, index, ignore in app.github.get_candidates(
            ResponsiveNetworkClient(Static()), [GitCommit(hash='hash9000', subject='subject9000')]
        ):
            candidates.append((model, index, ignore))

        assert response_mock.call_args_list == [
            mocker.call(
                'https://api.github.com/search/issues',
                params={'q': 'sha:hash9000 repo:org/repo is:merged'},
                auth=('foo', 'bar'),
            ),
            mocker.call('https://api.github.com/repos/org/repo/pulls/123/reviews', auth=('foo', 'bar')),
        ]

        assert len(candidates) == 1
        assert candidates == [
            (
                Candidate(
                    **{
                        'id': '123',
                        'title': 'title123',
                        'url': 'https://github.com/org/repo/pull/123',
                        'user': 'username123',
                        'labels': [{'name': 'label1', 'color': '632ca6'}, {'name': 'label2', 'color': '632ca6'}],
                        'body': 'foo\nbar',
                        'reviewers': [
                            {'name': 'username1', 'association': 'member'},
                            {'name': 'username2', 'association': 'collaborator'},
                        ],
                    }
                ),
                0,
                0,
            )
        ]

    async def test_get_candidates_pr_ignored(self, app, git_repository, mocker):
        app.configure(
            git_repository,
            caching=True,
            data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
        )

        response_mock = mocker.patch(
            'httpx.AsyncClient.get',
            side_effect=[
                Response(
                    200,
                    request=Request('GET', ''),
                    content=json.dumps(
                        {
                            'items': [
                                {
                                    'number': '123',
                                    'title': 'title123',
                                    'user': {'login': 'username123'},
                                    'labels': [
                                        {'name': 'label1', 'color': '632ca6'},
                                        {'name': 'label2', 'color': '632ca6'},
                                    ],
                                    'body': 'foo\r\nbar',
                                },
                            ],
                        },
                    ),
                ),
                Response(
                    200,
                    request=Request('GET', ''),
                    content=json.dumps(
                        [
                            {
                                'user': {'login': 'username1'},
                                'author_association': 'MEMBER',
                            },
                            {
                                'user': {'login': 'username2'},
                                'author_association': 'COLLABORATOR',
                            },
                            {
                                'user': {'login': 'username1'},
                                'author_association': 'MEMBER',
                            },
                        ],
                    ),
                ),
            ],
        )

        candidates = []

        async for model, index, ignore in app.github.get_candidates(
            ResponsiveNetworkClient(Static()),
            [GitCommit(hash='hash9000', subject='subject9000')],
            ['label1'],
        ):
            candidates.append((model, index, ignore))

        assert response_mock.call_args_list == [
            mocker.call(
                'https://api.github.com/search/issues',
                params={'q': 'sha:hash9000 repo:org/repo is:merged'},
                auth=('foo', 'bar'),
            ),
            mocker.call('https://api.github.com/repos/org/repo/pulls/123/reviews', auth=('foo', 'bar')),
        ]

        assert candidates == [(None, 0, 1)]

    async def test_no_pr(self, app, git_repository, mocker):
        app.configure(
            git_repository,
            caching=True,
            data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
        )

        response_mock = mocker.patch(
            'httpx.AsyncClient.get',
            return_value=Response(
                200,
                request=Request('GET', ''),
                content=json.dumps({'items': []}),
            ),
        )

        candidate = await app.github.get_candidate(
            ResponsiveNetworkClient(Static()), GitCommit(hash='hash9000', subject='subject9000')
        )
        assert response_mock.call_args_list == [
            mocker.call(
                'https://api.github.com/search/issues',
                params={'q': 'sha:hash9000 repo:org/repo is:merged'},
                auth=('foo', 'bar'),
            ),
        ]

        assert candidate.dict() == {
            'id': 'hash9000',
            'title': 'subject9000',
            'url': 'https://github.com/org/repo/commit/hash9000',
            'user': '',
            'labels': [],
            'body': '',
            'reviewers': [],
            'assigned_teams': set(),
        }

    async def test_get_candidates_no_pr(self, app, git_repository, mocker):
        app.configure(
            git_repository,
            caching=True,
            data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
        )

        response_mock = mocker.patch(
            'httpx.AsyncClient.get',
            return_value=Response(
                200,
                request=Request('GET', ''),
                content=json.dumps({'items': []}),
            ),
        )

        candidates = []

        async for model, index, ignore in app.github.get_candidates(
            ResponsiveNetworkClient(Static()), [GitCommit(hash='hash9000', subject='subject9000')]
        ):
            candidates.append((model, index, ignore))

        assert response_mock.call_args_list == [
            mocker.call(
                'https://api.github.com/search/issues',
                params={'q': 'sha:hash9000 repo:org/repo is:merged'},
                auth=('foo', 'bar'),
            ),
        ]

        assert len(candidates) == 1
        assert candidates == [
            (
                {
                    'id': 'hash9000',
                    'title': 'subject9000',
                    'url': 'https://github.com/org/repo/commit/hash9000',
                    'user': '',
                    'labels': [],
                    'body': '',
                    'reviewers': [],
                    'assigned_teams': set(),
                },
                0,
                0,
            )
        ]

    async def test_caching(self, app, git_repository, mocker):
        app.configure(
            git_repository,
            caching=True,
            data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
        )
        repo_cache_dir = app.cache_dir / 'github' / 'org' / 'repo'
        assert not repo_cache_dir.is_dir()

        # Candidate with no PR
        response_mock = mocker.patch(
            'httpx.AsyncClient.get',
            return_value=Response(
                200,
                request=Request('GET', ''),
                content=json.dumps({'items': []}),
            ),
        )
        candidate = await app.github.get_candidate(
            ResponsiveNetworkClient(Static()), GitCommit(hash='hash1', subject='subject1')
        )
        assert response_mock.call_args_list == [
            mocker.call(
                'https://api.github.com/search/issues',
                params={'q': 'sha:hash1 repo:org/repo is:merged'},
                auth=('foo', 'bar'),
            ),
        ]
        assert candidate.dict() == {
            'id': 'hash1',
            'title': 'subject1',
            'url': 'https://github.com/org/repo/commit/hash1',
            'user': '',
            'labels': [],
            'body': '',
            'reviewers': [],
            'assigned_teams': set(),
        }

        # First encounter of a candidate with a PR
        response_mock = mocker.patch(
            'httpx.AsyncClient.get',
            side_effect=[
                Response(
                    200,
                    request=Request('GET', ''),
                    content=json.dumps(
                        {
                            'items': [
                                {
                                    'number': '123',
                                    'title': 'title123',
                                    'user': {'login': 'username123'},
                                    'labels': [
                                        {'name': 'label1', 'color': '632ca6'},
                                        {'name': 'label2', 'color': '632ca6'},
                                    ],
                                    'body': 'foo\r\nbar',
                                },
                            ],
                        },
                    ),
                ),
                Response(
                    200,
                    request=Request('GET', ''),
                    content=json.dumps(
                        [
                            {
                                'user': {'login': 'username1'},
                                'author_association': 'MEMBER',
                            },
                            {
                                'user': {'login': 'username2'},
                                'author_association': 'COLLABORATOR',
                            },
                            {
                                'user': {'login': 'username1'},
                                'author_association': 'MEMBER',
                            },
                        ],
                    ),
                ),
            ],
        )
        candidate = await app.github.get_candidate(
            ResponsiveNetworkClient(Static()), GitCommit(hash='hash2', subject='subject2')
        )
        assert response_mock.call_args_list == [
            mocker.call(
                'https://api.github.com/search/issues',
                params={'q': 'sha:hash2 repo:org/repo is:merged'},
                auth=('foo', 'bar'),
            ),
            mocker.call('https://api.github.com/repos/org/repo/pulls/123/reviews', auth=('foo', 'bar')),
        ]
        assert candidate.dict() == {
            'id': '123',
            'title': 'title123',
            'url': 'https://github.com/org/repo/pull/123',
            'user': 'username123',
            'labels': [{'name': 'label1', 'color': '632ca6'}, {'name': 'label2', 'color': '632ca6'}],
            'body': 'foo\nbar',
            'reviewers': [
                {'name': 'username1', 'association': 'member'},
                {'name': 'username2', 'association': 'collaborator'},
            ],
            'assigned_teams': set(),
        }

        # First encounter of a candidate with a PR that has already been seen
        response_mock = mocker.patch(
            'httpx.AsyncClient.get',
            return_value=Response(
                200,
                request=Request('GET', ''),
                # Only define the number to emphasize that that is all the info necessary to discern a duplicate
                content=json.dumps({'items': [{'number': '123'}]}),
            ),
        )
        candidate = await app.github.get_candidate(
            ResponsiveNetworkClient(Static()), GitCommit(hash='hash3', subject='subject3')
        )
        assert response_mock.call_args_list == [
            mocker.call(
                'https://api.github.com/search/issues',
                params={'q': 'sha:hash3 repo:org/repo is:merged'},
                auth=('foo', 'bar'),
            ),
        ]
        assert candidate.dict() == {
            'id': '123',
            'title': 'title123',
            'url': 'https://github.com/org/repo/pull/123',
            'user': 'username123',
            'labels': [{'name': 'label1', 'color': '632ca6'}, {'name': 'label2', 'color': '632ca6'}],
            'body': 'foo\nbar',
            'reviewers': [
                {'name': 'username1', 'association': 'member'},
                {'name': 'username2', 'association': 'collaborator'},
            ],
            'assigned_teams': set(),
        }

        assert repo_cache_dir.is_dir()
        assert sorted(entry.name for entry in repo_cache_dir.iterdir()) == ['commits', 'pull_requests']

        commits_dir = repo_cache_dir / 'commits'
        assert commits_dir.is_dir()
        assert sorted(entry.name for entry in commits_dir.iterdir()) == ['hash1', 'hash2', 'hash3']

        commit1_dir = commits_dir / 'hash1'
        assert [entry.name for entry in commit1_dir.iterdir()] == ['no_pr.json']
        assert json.loads((commit1_dir / 'no_pr.json').read_text()) == {
            'id': 'hash1',
            'title': 'subject1',
            'url': 'https://github.com/org/repo/commit/hash1',
        }

        commit2_dir = commits_dir / 'hash2'
        assert [entry.name for entry in commit2_dir.iterdir()] == ['123']
        assert not (commit2_dir / '123').read_text()

        commit3_dir = commits_dir / 'hash3'
        assert [entry.name for entry in commit3_dir.iterdir()] == ['123']
        assert not (commit3_dir / '123').read_text()

        pull_requests_dir = repo_cache_dir / 'pull_requests'
        assert pull_requests_dir.is_dir()
        assert sorted(entry.name for entry in pull_requests_dir.iterdir()) == ['123.json']

        assert json.loads((pull_requests_dir / '123.json').read_text()) == {
            'id': '123',
            'title': 'title123',
            'url': 'https://github.com/org/repo/pull/123',
            'user': 'username123',
            'labels': [{'name': 'label1', 'color': '632ca6'}, {'name': 'label2', 'color': '632ca6'}],
            'body': 'foo\nbar',
            'reviewers': [
                {'name': 'username1', 'association': 'member'},
                {'name': 'username2', 'association': 'collaborator'},
            ],
        }

        # Now start responding with bad status codes to ensure that caching is working
        response_mock = mocker.patch('httpx.AsyncClient.get', return_value=Response(500, request=Request('GET', '')))
        candidate = await app.github.get_candidate(
            ResponsiveNetworkClient(Static()), GitCommit(hash='hash1', subject='subject1')
        )
        assert not response_mock.call_args_list
        assert candidate.dict() == {
            'id': 'hash1',
            'title': 'subject1',
            'url': 'https://github.com/org/repo/commit/hash1',
            'user': '',
            'labels': [],
            'body': '',
            'reviewers': [],
            'assigned_teams': set(),
        }
        candidate = await app.github.get_candidate(
            ResponsiveNetworkClient(Static()), GitCommit(hash='hash2', subject='subject2')
        )
        assert not response_mock.call_args_list
        assert candidate.dict() == {
            'id': '123',
            'title': 'title123',
            'url': 'https://github.com/org/repo/pull/123',
            'user': 'username123',
            'labels': [{'name': 'label1', 'color': '632ca6'}, {'name': 'label2', 'color': '632ca6'}],
            'body': 'foo\nbar',
            'reviewers': [
                {'name': 'username1', 'association': 'member'},
                {'name': 'username2', 'association': 'collaborator'},
            ],
            'assigned_teams': set(),
        }
        candidate = await app.github.get_candidate(
            ResponsiveNetworkClient(Static()), GitCommit(hash='hash3', subject='subject3')
        )
        assert not response_mock.call_args_list
        assert candidate.dict() == {
            'id': '123',
            'title': 'title123',
            'url': 'https://github.com/org/repo/pull/123',
            'user': 'username123',
            'labels': [{'name': 'label1', 'color': '632ca6'}, {'name': 'label2', 'color': '632ca6'}],
            'body': 'foo\nbar',
            'reviewers': [
                {'name': 'username1', 'association': 'member'},
                {'name': 'username2', 'association': 'collaborator'},
            ],
            'assigned_teams': set(),
        }


class TestTeamMembers:
    async def test_first_run(self, app, git_repository, mocker):
        app.configure(
            git_repository,
            caching=True,
            data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
        )

        response_mock = mocker.patch(
            'httpx.AsyncClient.get',
            return_value=Response(
                200,
                request=Request('GET', ''),
                content=json.dumps(
                    [
                        {'login': 'foo', 'type': 'User'},
                        {'login': 'bar', 'type': 'User'},
                        {'login': 'baz', 'type': 'User'},
                        {'login': 'bot', 'type': 'other'},
                    ],
                ),
            ),
        )

        team_members = await app.github.get_team_members(ResponsiveNetworkClient(Static()), 'a-team')
        assert response_mock.call_args_list == [
            mocker.call('https://api.github.com/orgs/org/teams/a-team/members', auth=('foo', 'bar')),
        ]

        assert team_members == {'foo', 'bar', 'baz'}

    async def test_caching(self, app, git_repository, mocker):
        app.configure(
            git_repository,
            caching=True,
            data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
        )
        team_members_cache_dir = app.cache_dir / 'github' / 'org' / 'repo' / 'team_members'
        assert not team_members_cache_dir.is_dir()

        response_mock = mocker.patch(
            'httpx.AsyncClient.get',
            return_value=Response(
                200,
                request=Request('GET', ''),
                content=json.dumps(
                    [
                        {'login': 'foo', 'type': 'User'},
                        {'login': 'bar', 'type': 'User'},
                        {'login': 'baz', 'type': 'User'},
                        {'login': 'bot', 'type': 'other'},
                    ],
                ),
            ),
        )

        team_members = await app.github.get_team_members(ResponsiveNetworkClient(Static()), 'a-team')
        assert response_mock.call_args_list == [
            mocker.call('https://api.github.com/orgs/org/teams/a-team/members', auth=('foo', 'bar')),
        ]

        assert team_members == {'foo', 'bar', 'baz'}

        assert team_members_cache_dir.is_dir()
        entries = list(team_members_cache_dir.iterdir())
        assert len(entries) == 1

        members_file = entries[0]
        assert members_file.name == 'a-team.txt'
        assert set(members_file.read_text().splitlines()) == team_members

        response_mock = mocker.patch('httpx.AsyncClient.get', return_value=Response(500, request=Request('GET', '')))

        team_members = await app.github.get_team_members(ResponsiveNetworkClient(Static()), 'a-team')
        assert not response_mock.call_args_list

        assert team_members == {'foo', 'bar', 'baz'}

    async def test_refresh_invalidates_cache(self, app, git_repository, mocker):
        app.configure(
            git_repository,
            caching=True,
            data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
        )
        team_members_cache_dir = app.cache_dir / 'github' / 'org' / 'repo' / 'team_members'
        assert not team_members_cache_dir.is_dir()

        response_mock = mocker.patch(
            'httpx.AsyncClient.get',
            return_value=Response(
                200,
                request=Request('GET', ''),
                content=json.dumps(
                    [
                        {'login': 'foo', 'type': 'User'},
                        {'login': 'bar', 'type': 'User'},
                        {'login': 'baz', 'type': 'User'},
                        {'login': 'bot', 'type': 'other'},
                    ],
                ),
            ),
        )

        team_members = await app.github.get_team_members(ResponsiveNetworkClient(Static()), 'a-team')
        assert response_mock.call_args_list == [
            mocker.call('https://api.github.com/orgs/org/teams/a-team/members', auth=('foo', 'bar')),
        ]

        assert team_members == {'foo', 'bar', 'baz'}

        assert team_members_cache_dir.is_dir()
        entries = list(team_members_cache_dir.iterdir())
        assert len(entries) == 1

        members_file = entries[0]
        assert members_file.name == 'a-team.txt'
        assert set(members_file.read_text().splitlines()) == team_members

        response_mock = mocker.patch(
            'httpx.AsyncClient.get',
            return_value=Response(
                200,
                request=Request('GET', ''),
                content=json.dumps(
                    [
                        {'login': 'foobarbaz', 'type': 'User'},
                    ],
                ),
            ),
        )

        team_members = await app.github.get_team_members(ResponsiveNetworkClient(Static()), 'a-team', refresh=True)
        assert response_mock.call_args_list == [
            mocker.call('https://api.github.com/orgs/org/teams/a-team/members', auth=('foo', 'bar')),
        ]

        assert team_members == {'foobarbaz'}


async def test_rate_limit_handling(app, git_repository, mocker):
    app.configure(
        git_repository,
        caching=True,
        data={'github': {'user': 'foo', 'token': 'bar'}, 'jira': {'email': 'foo@bar.baz', 'token': 'bar'}},
    )

    start = time.time()
    response_mock = mocker.patch(
        'httpx.AsyncClient.get',
        side_effect=[
            Response(
                200,
                request=Request('GET', ''),
                content=json.dumps(
                    {
                        'items': [
                            {
                                'number': '123',
                                'title': 'title123',
                                'user': {'login': 'username123'},
                                'labels': [
                                    {'name': 'label1', 'color': '632ca6'},
                                    {'name': 'label2', 'color': '632ca6'},
                                ],
                                'body': 'foo\r\nbar',
                            },
                        ],
                    },
                ),
            ),
            Response(
                403,
                headers={'X-RateLimit-Remaining': '0', 'X-RateLimit-Reset': f'{start + 1}'},
            ),
            Response(
                200,
                request=Request('GET', ''),
                content=json.dumps(
                    [
                        {
                            'user': {'login': 'username1'},
                            'author_association': 'MEMBER',
                        },
                        {
                            'user': {'login': 'username2'},
                            'author_association': 'COLLABORATOR',
                        },
                        {
                            'user': {'login': 'username1'},
                            'author_association': 'MEMBER',
                        },
                    ],
                ),
            ),
        ],
    )
    candidate = await app.github.get_candidate(
        ResponsiveNetworkClient(Static()), GitCommit(hash='hash9000', subject='subject9000')
    )
    assert time.time() - start >= 1

    assert response_mock.call_args_list == [
        mocker.call(
            'https://api.github.com/search/issues',
            params={'q': 'sha:hash9000 repo:org/repo is:merged'},
            auth=('foo', 'bar'),
        ),
        mocker.call('https://api.github.com/repos/org/repo/pulls/123/reviews', auth=('foo', 'bar')),
        mocker.call('https://api.github.com/repos/org/repo/pulls/123/reviews', auth=('foo', 'bar')),
    ]
    assert candidate.dict() == {
        'id': '123',
        'title': 'title123',
        'url': 'https://github.com/org/repo/pull/123',
        'user': 'username123',
        'labels': [{'name': 'label1', 'color': '632ca6'}, {'name': 'label2', 'color': '632ca6'}],
        'body': 'foo\nbar',
        'reviewers': [
            {'name': 'username1', 'association': 'member'},
            {'name': 'username2', 'association': 'collaborator'},
        ],
        'assigned_teams': set(),
    }
