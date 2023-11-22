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
