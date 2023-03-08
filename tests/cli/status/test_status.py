# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import asyncio
from unittest import mock

import pytest

from ddqa.app.core import Application


@pytest.fixture(scope='module', autouse=True)
def mock_remote_url():
    with mock.patch('ddqa.utils.git.GitRepository.get_remote_url', return_value='https://github.com/org/repo.git'):
        yield


def mock_run(*args, **kwargs):
    asyncio.run(Application.on_mount(*args, **kwargs))


class AwaitableMock(mock.AsyncMock):
    def __await__(self):
        return iter([])


def test_bad_config(ddqa, mocker):
    status_screen = object()
    mocker.patch('ddqa.screens.status.StatusScreen', return_value=status_screen)

    configure_screen = object()
    mocker.patch('ddqa.screens.configure.ConfigureScreen', return_value=configure_screen)

    install_screen = mocker.patch('ddqa.app.core.Application.install_screen', return_value=AwaitableMock())
    push_screen = mocker.patch('ddqa.app.core.Application.push_screen', return_value=AwaitableMock())
    mocker.patch.object(Application, 'run', mock_run)

    result = ddqa('status', 'qa-1.2.3')

    assert result.exit_code == 0, result.output
    assert not result.output

    assert install_screen.call_args_list == [mocker.call(status_screen, 'status')]
    assert push_screen.call_args_list == [mocker.call(configure_screen)]


def test_needs_syncing(ddqa, isolation, config_file, mocker):
    config_file.model.data.update(
        {
            'repo': 'test',
            'repos': {'test': {'path': str(isolation)}},
            'github': {'user': 'foo', 'token': 'bar'},
            'jira': {'email': 'foo', 'token': 'bar'},
        }
    )
    config_file.save()

    status_screen = object()
    mocker.patch('ddqa.screens.status.StatusScreen', return_value=status_screen)

    sync_screen = object()
    mocker.patch('ddqa.screens.sync.SyncScreen', return_value=sync_screen)

    install_screen = mocker.patch('ddqa.app.core.Application.install_screen', return_value=AwaitableMock())
    push_screen = mocker.patch('ddqa.app.core.Application.push_screen', return_value=AwaitableMock())
    mocker.patch.object(Application, 'run', mock_run)

    result = ddqa('status', 'qa-1.2.3')

    assert result.exit_code == 0, result.output
    assert not result.output

    assert install_screen.call_args_list == [mocker.call(status_screen, 'status')]
    assert push_screen.call_args_list == [mocker.call(sync_screen)]


def test_valid_setup(ddqa, isolation, config_file, mocker):
    config_file.model.data.update(
        {
            'repo': 'test',
            'repos': {'test': {'path': str(isolation)}},
            'github': {'user': 'foo', 'token': 'bar'},
            'jira': {'email': 'foo', 'token': 'bar'},
        }
    )
    config_file.save()

    status_screen = object()
    mocker.patch('ddqa.screens.status.StatusScreen', return_value=status_screen)

    install_screen = mocker.patch('ddqa.app.core.Application.install_screen', return_value=AwaitableMock())
    push_screen = mocker.patch('ddqa.app.core.Application.push_screen', return_value=AwaitableMock())
    mocker.patch('ddqa.app.core.Application.needs_syncing', return_value=False)
    mocker.patch.object(Application, 'run', mock_run)

    result = ddqa('status', 'qa-1.2.3')

    assert result.exit_code == 0, result.output
    assert not result.output

    install_screen.assert_called_once_with(status_screen, 'status')
    push_screen.assert_called_once_with('status')
