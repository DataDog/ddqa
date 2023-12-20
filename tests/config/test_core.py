# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import pytest

from ddqa.config.core import Config


@pytest.fixture
def config():
    return Config({'foo': 'bar', 'baz': {'key': 'value'}})


@pytest.mark.parametrize(
    'key, value, expected_dict',
    [
        pytest.param(
            'new_key',
            'new_value',
            {'foo': 'bar', 'new_key': 'new_value', 'baz': {'key': 'value'}},
            id='new key',
        ),
        pytest.param(
            'foo',
            'new_value',
            {'foo': 'new_value', 'baz': {'key': 'value'}},
            id='existing key',
        ),
        pytest.param(
            'new.key',
            'new_value',
            {'foo': 'bar', 'baz': {'key': 'value'}, 'new': {'key': 'new_value'}},
            id='new composed key',
        ),
        pytest.param(
            'baz.key',
            'new_value',
            {
                'foo': 'bar',
                'baz': {'key': 'new_value'},
            },
            id='existing composed key',
        ),
    ],
)
def test_set_field(config, key, value, expected_dict):
    config.set_field(key, value)
    assert config.data == expected_dict
