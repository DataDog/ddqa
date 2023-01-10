# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
def test_call(ddqa, config_file, mocker):
    mock = mocker.patch('click.launch')
    result = ddqa('config', 'explore')

    assert result.exit_code == 0, result.output
    mock.assert_called_once_with(str(config_file.path), locate=True)
