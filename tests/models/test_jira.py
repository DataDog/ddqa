# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT

import pytest


class TestJiraConfig:
    @pytest.mark.parametrize(
        'github_user_id, expected_jira_user_id',
        [
            pytest.param('g1', 'j1', id='g1 found'),
            pytest.param('g2', 'j2', id='g2 found'),
            pytest.param('g3', None, id='g3 not found'),
            pytest.param('', None, id='empty'),
        ],
    )
    def test_get_jira_user_id_from_github_user_id(self, jira_config, github_user_id, expected_jira_user_id):
        assert expected_jira_user_id == jira_config.get_jira_user_id_from_github_user_id(github_user_id)

    @pytest.mark.parametrize(
        'github_user_ids, expected_jira_user_ids',
        [
            pytest.param({'g1'}, {'j1'}, id='g1 found'),
            pytest.param({'g2'}, {'j2'}, id='g2 found'),
            pytest.param({'g1', 'g2'}, {'j1', 'j2'}, id='all found'),
            pytest.param({}, set(), id='empty set'),
            pytest.param({'g1', 'g3'}, {'j1'}, id='g1 found and g3 not found'),
            pytest.param({'g3'}, set(), id='g3 not found'),
        ],
    )
    def test_get_jira_user_ids_from_github_user_ids(self, github_user_ids, expected_jira_user_ids, jira_config):
        assert expected_jira_user_ids == jira_config.get_jira_user_ids_from_github_user_ids(github_user_ids)

    @pytest.mark.parametrize(
        'jira_user_id, expected_github_user_id',
        [
            pytest.param('j1', 'g1', id='j1 found'),
            pytest.param('j2', 'g2', id='j2 found'),
            pytest.param('j3', None, id='j3 not found'),
            pytest.param('', None, id='empty'),
        ],
    )
    def test_get_github_user_id_from_jira_user_id(self, jira_config, jira_user_id, expected_github_user_id):
        assert expected_github_user_id == jira_config.get_github_user_id_from_jira_user_id(jira_user_id)
