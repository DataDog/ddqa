# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
def test(ddqa, temp_dir, mocker):
    mock = mocker.patch('click.launch')
    result = ddqa('--cache-dir', temp_dir, 'cache', 'explore')

    assert result.exit_code == 0, result.output
    mock.assert_called_once_with(str(temp_dir), locate=True)
