# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
def test_get_remote_url(app, git_repository):
    app.configure(git_repository)

    remote_url = 'https://github.com/foo/bar.git'
    app.git.capture('remote', 'add', 'origin', remote_url)
    assert app.git.get_remote_url() == remote_url


def test_get_current_branch(app, git_repository):
    app.configure(git_repository)

    app.git.capture('checkout', '-b', 'foo')
    assert app.git.get_current_branch() == 'foo'

    app.git.capture('checkout', '-b', 'bar')
    assert app.git.get_current_branch() == 'bar'


def test_get_latest_commit_hash(app, git_repository):
    app.configure(git_repository)

    (app.git.path / 'test1.txt').touch()
    app.git.capture('add', '.')
    commit_subject1 = app.git.capture('commit', '-m', 'test1')
    commit_hash1 = app.git.get_latest_commit_hash()
    assert len(commit_hash1) == 40

    (app.git.path / 'test2.txt').touch()
    app.git.capture('add', '.')
    commit_subject2 = app.git.capture('commit', '-m', 'test2')
    commit_hash2 = app.git.get_latest_commit_hash()
    assert len(commit_hash2) == 40

    short_hash1 = commit_hash1[:7]
    short_hash2 = commit_hash2[:7]

    assert short_hash1 in commit_subject1
    assert short_hash1 not in commit_subject2
    assert short_hash2 in commit_subject2
    assert short_hash2 not in commit_subject1


def test_mutually_exclusive_commits(app, git_repository):
    app.configure(git_repository)
    head_ref = app.git.get_current_branch()
    upstream_ref = 'foo'
    app.git.capture('branch', upstream_ref)

    commits = []
    for i in range(3):
        filename = f'test{i}.txt'
        (app.git.path / filename).touch()
        app.git.capture('add', '.')
        app.git.capture('commit', '-m', filename)
        commits.append((app.git.get_latest_commit_hash(), filename))

    assert [(c.hash, c.subject) for c in app.git.get_mutually_exclusive_commits(upstream_ref, head_ref)] == commits

    app.git.capture('checkout', upstream_ref)
    for _ in range(2):
        app.git.capture('cherry-pick', commits.pop()[0])

    assert [(c.hash, c.subject) for c in app.git.get_mutually_exclusive_commits(upstream_ref, head_ref)] == commits

    # Just make sure the output doesn't depend on the current branch
    app.git.capture('checkout', head_ref)
    assert [(c.hash, c.subject) for c in app.git.get_mutually_exclusive_commits(upstream_ref, head_ref)] == commits
