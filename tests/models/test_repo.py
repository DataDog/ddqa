# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import pytest
from pydantic import ValidationError

from ddqa.models.config.repo import RepoConfig

TEAMS = {
    'foo': {
        'jira_project': 'FOO',
        'jira_issue_type': 'Foo-Task',
        'jira_statuses': {'TODO': 'Backlog', 'DONE': 'Done'},
        'github_team': 'foo-team',
    },
}


class TestRepoConfig:
    def test_datastore_id_only(self):
        config = RepoConfig(datastore_id='ds-id', qa_statuses=['TODO', 'DONE'], teams=TEAMS)

        assert config.datastore_id == 'ds-id'
        assert config.global_config_source is None

    def test_global_config_source_only(self):
        config = RepoConfig(
            global_config_source='https://example.com/config.toml',
            qa_statuses=['TODO', 'DONE'],
            teams=TEAMS,
        )

        assert config.datastore_id == ''
        assert str(config.global_config_source) == 'https://example.com/config.toml'

    def test_neither_source_configured(self):
        with pytest.raises(ValidationError, match='exactly one of `datastore_id` or `global_config_source`'):
            RepoConfig(qa_statuses=['TODO', 'DONE'], teams=TEAMS)

    def test_both_sources_configured(self):
        with pytest.raises(ValidationError, match='exactly one of `datastore_id` or `global_config_source`'):
            RepoConfig(
                datastore_id='ds-id',
                global_config_source='https://example.com/config.toml',
                qa_statuses=['TODO', 'DONE'],
                teams=TEAMS,
            )

    def test_global_config_source_serializes_to_string(self):
        config = RepoConfig(
            global_config_source='https://example.com/config.toml',
            qa_statuses=['TODO', 'DONE'],
            teams=TEAMS,
        )

        assert config.model_dump()['global_config_source'] == 'https://example.com/config.toml'
