# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from ddqa.models.jira import JiraIssue
from ddqa.screens.status import IssueFilter


class DummyIssueFilter(IssueFilter):
    def update(self, old_issue: JiraIssue, new_issue: JiraIssue):
        pass


class TestIssueFilter:
    def test_sorted_by_filter_key(self):
        dummy_filter = DummyIssueFilter()
        for issue_id in ('c', 'b', 'z', 'a'):
            issue = JiraIssue.construct(key=f'key-{issue_id}')
            dummy_filter.add(issue_id, issue)

        assert list(dummy_filter.issues.keys()) == sorted(dummy_filter.issues.keys())
