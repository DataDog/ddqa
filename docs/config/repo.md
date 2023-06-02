# Repository configuration

-----

A repository must be configured ([example](https://github.com/DataDog/integrations-core/blob/master/.ddqa/config.toml)) before use:

```toml
global_config_source = "..."
qa_statuses = ["..."]

[teams."..."]
github_team = "..."
jira_project = "..."
jira_issue_type = "..."
jira_statuses = ["..."]
```

The config file is located by default in your repository at `/.ddqa/config.toml` and can be overridden with the top level `--config` option.

## Core options

### Global config source (*required*) ### {: #global-config-source }

Key: `global_config_source`

This is a URL (optionally encoded in [Base64](https://en.wikipedia.org/wiki/Base64)) like `https://raw.githubusercontent.com/org/repo/master/jira.toml` that points to the raw contents of a TOML file on GitHub that contains potentially private metadata that the tool needs in order to operate. Currently, the only required information is the cloud URL and a mapping of GitHub usernames to Jira IDs:

```toml
jira_server = "https://<ORG>.atlassian.net"

[members]
github-user1 = "jira-id1"
```

### QA statuses (*required*) ### {: #qa-statuses }

Key: `qa_statuses`

The entries and order of this list correspond to the desired QA workflow, for example:

```toml
qa_statuses = [
  "TODO",
  "Testing",
  "Done",
]
```

### Ignored labels

Key: `ignored_labels`

Any pull requests labeled with any of the entries will not be assigned by default:

```toml
ignored_labels = [
  "changelog/no-changelog",
]
```

## Teams

Each team must be configured.

```toml
[teams."..."]
# Per-team options
```

The name of each team is arbitrary but should be the human readable version or a nickname. The order of teams is also arbitrary but would benefit from being ordered by teams that commit/would be assigned most frequently as manual selection would potentially require less scrolling.

### GitHub team (*required*) ### {: #github-team }

Key: `github_team`

This is the team's GitHub name, excluding the organization `<ORG>/` prefix.

### Jira project (*required*) ### {: #jira-project }

Key: `jira_project`

This is the team's Jira project in which issues will be created. If there exists an issue `FOO-123`, the project name is `FOO`.

### Jira issue type (*required*) ### {: #jira-issue-type }

Key: `jira_issue_type`

This is the type of Jira issue that will be created and will most often be `Task`. The issue type can be found as the `fields.issuetype.name` returned value in the payload from the [`/rest/api/2/issue/{issueIdOrKey}`](https://developer.atlassian.com/cloud/jira/platform/rest/v2/api-group-issues/#api-rest-api-2-issue-issueidorkey-get) endpoint.

### Jira statuses (*required*) ### {: #jira-statuses }

Key: `jira_statuses`

This is an array of Jira statuses that correspond to the order of [QA status](#qa-statuses) entries. Alternatively, this may be a mapping of [QA statuses](#qa-statuses) to Jira statuses. The available Jira statuses may be found using the [`/rest/api/2/project/{projectIdOrKey}/statuses`](https://developer.atlassian.com/cloud/jira/platform/rest/v2/api-group-projects/#api-rest-api-2-project-projectidorkey-statuses-get) endpoint.

### GitHub labels

Key: `github_labels`

This team will be assigned by default to any pull requests that are labeled with any of the entries (as long as the pull request has no labels that match any of those defined as [ignored](#ignored-labels)).

### Jira component

Key: `jira_component`

This is the name of a Jira [project component](https://support.atlassian.com/jira-software-cloud/docs/organize-work-with-components/) with which to create issues.

### Excluded members

Key: `exclude_members`

This is an array of GitHub usernames who should be excluded from QA participation.
