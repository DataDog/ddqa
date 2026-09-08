# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT


class TestTeamMembers:
    def test_get_no_cache(self, github_cache):
        assert github_cache.get_team_members('random') is None

    def test_read(self, github_cache):
        assert github_cache.get_team_members('random') is None
        github_cache.get_team_members_file('random').write_text('m1\nm2')
        assert {'m1', 'm2'} == github_cache.get_team_members('random')

    def test_write(self, github_cache):
        assert github_cache.get_team_members('random') is None
        github_cache.save_team_members('random', {'m1', 'm2'})
        assert github_cache.get_team_members_file('random').read_text() in ('m1\nm2', 'm2\nm1')

    def test_write_read(self, github_cache):
        github_cache.save_team_members('random', {'m1', 'm2'})
        assert {'m1', 'm2'} == github_cache.get_team_members('random')


class TestGlobalConfig:
    def test_get_no_cache(self, github_cache):
        assert github_cache.load_global_config('https://example.com/config.toml') == {}

    def test_write_read(self, github_cache):
        source = 'https://example.com/config.toml'
        global_config = {'members': {'g1': 'j1'}}

        github_cache.save_global_config(source, global_config)

        assert github_cache.load_global_config(source) == global_config

    def test_write_read_different_sources(self, github_cache):
        source1 = 'https://example.com/config1.toml'
        source2 = 'https://example.com/config2.toml'

        github_cache.save_global_config(source1, {'members': {'g1': 'j1'}})
        github_cache.save_global_config(source2, {'members': {'g2': 'j2'}})

        assert github_cache.load_global_config(source1) == {'members': {'g1': 'j1'}}
        assert github_cache.load_global_config(source2) == {'members': {'g2': 'j2'}}

    def test_overwrite(self, github_cache):
        source = 'https://example.com/config.toml'

        github_cache.save_global_config(source, {'members': {'g1': 'j1'}})
        github_cache.save_global_config(source, {'members': {'g1': 'j1-new'}})

        assert github_cache.load_global_config(source) == {'members': {'g1': 'j1-new'}}
