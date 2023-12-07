# History

-----

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

***Fixed:***

- Fix GitHub API search query
- Alphabetically sort the teams and members in the status screen
- Consider unknown Jira statuses as Done and add an extra column in the Done box to specify the current status of this card
- Only retrieve merged PRs when fetching them from GitHub
- Do not show PRs that have a ignored label in the create screen
- Strip the PR title in the `create` screen
- Stop assigning cards to users that are not declared in the Jira config

***Added:***

- Disable the radio button in the status screen if the user is not assigned to the card
- Add a set of commands to interact with the cache
- Show the author of a PR on the create screen
- Make the team labels clickable in the create screen
- Save and restore the assigned teams to PRs in the create screen
- Allow users to configure their GitHub and Jira credentials with environment variables
- Add a refresh button to the status screen
- Add tooltips and a scroll bar in the create screen on the PR title and labels
- Check the status of the users in Jira in the sync command
- Add direct links to GitHub and Jira in the sync screen
- Check GitHub users are declared in the Jira config file in the sync screen
- Add a `pr_labels` option to only show PRs which have on of these labels in the create screen

## 0.4.0 - 2023-06-21

***Added:***

- Upgrade PyApp to 0.9.0
- Build for PowerPC

## 0.3.1 - 2023-06-02

***Fixed:***

- Fix race condition when prematurely creating issues

## 0.3.0 - 2023-05-24

***Added:***

- Upgrade Textual to 0.20.1
- Upgrade PyApp to 0.7.0

## 0.2.0 - 2023-05-17

***Changed:***

- Remove vendored `pyperclip` dependency and the `--copy` flag of the `config find` command

***Fixed:***

- Changed the priority of member assignment to be based on the number of currently assigned issues followed by whether or not the member was a reviewer
- Properly handle Git SSH remote URLs

## 0.1.0 - 2023-04-15

This is the initial public release.
