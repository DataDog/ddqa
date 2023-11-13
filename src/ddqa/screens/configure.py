# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from contextlib import suppress

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Button, Header, Input, Label, RichLog

from ddqa.utils.errors import error_tree
from ddqa.widgets.input import LabeledInput
from ddqa.widgets.static import Placeholder


class DefaultValue:
    def __init__(self, value: object):
        self.inner = value if isinstance(value, str) else ''


class ValidatedInput(Input):
    def validate_value(self, value: object):
        if isinstance(value, DefaultValue):
            return value.inner

        self.validate_user_input(value)
        return value

    def validate_user_input(self, value: object):
        pass


class RepoNameInput(ValidatedInput):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__added = ''

    def on_mount(self) -> None:
        self.value = DefaultValue(self.app.config.data.get('repo', ''))

    def validate_user_input(self, value: object):
        with suppress(AttributeError):
            del self.app.config.app

        previous_repo = self.app.config.data.get('repo', '')
        self.app.config.data['repo'] = value

        repos = self.app.config.data.setdefault('repos', {})
        new_repo = value not in repos

        if previous_repo in repos:
            config = repos.setdefault(value, {})
            config['path'] = repos.get(previous_repo, {}).get('path', '')

            if previous_repo == self.__added:
                del repos[previous_repo]

        if new_repo:
            self.__added = value

            with suppress(AttributeError):
                del self.app.config.repos

        return value


class RepoPathInput(ValidatedInput):
    def on_mount(self) -> None:
        self.value = DefaultValue(
            self.app.config.data.get('repos', {}).get(self.app.config.data.get('repo', ''), {}).get('path', '')
        )

    def validate_user_input(self, value: object):
        with suppress(AttributeError):
            del self.app.config.repos

        repo = self.app.config.data.get('repo', '')
        self.app.config.data.setdefault('repos', {}).setdefault(repo, {})['path'] = value


class GitHubUserInput(ValidatedInput):
    def on_mount(self) -> None:
        self.value = DefaultValue(self.app.config.data.get('github', {}).get('user', ''))

    def validate_user_input(self, value: object):
        with suppress(AttributeError):
            del self.app.config.auth

        if value:
            self.app.config.data.setdefault('github', {})['user'] = value
        else:
            self.app.config.data.get('github', {}).pop('user', None)


class GitHubTokenInput(ValidatedInput):
    def __init__(self, *args, **kwargs):
        kwargs['password'] = True
        super().__init__(*args, **kwargs)

    def on_mount(self) -> None:
        self.value = DefaultValue(self.app.config.data.get('github', {}).get('token', ''))

    def validate_user_input(self, value: object):
        with suppress(AttributeError):
            del self.app.config.auth

        if value:
            self.app.config.data.setdefault('github', {})['token'] = value
        else:
            self.app.config.data.get('github', {}).pop('token', None)


class JiraEmailInput(ValidatedInput):
    def on_mount(self) -> None:
        self.value = DefaultValue(self.app.config.data.get('jira', {}).get('email', ''))

    def validate_user_input(self, value: object):
        with suppress(AttributeError):
            del self.app.config.auth

        if value:
            self.app.config.data.setdefault('jira', {})['email'] = value
        else:
            self.app.config.data.get('jira', {}).pop('email', None)


class JiraTokenInput(ValidatedInput):
    def __init__(self, *args, **kwargs):
        kwargs['password'] = True
        super().__init__(*args, **kwargs)

    def on_mount(self) -> None:
        self.value = DefaultValue(self.app.config.data.get('jira', {}).get('token', ''))

    def validate_user_input(self, value: object):
        with suppress(AttributeError):
            del self.app.config.auth

        if value:
            self.app.config.data.setdefault('jira', {})['token'] = value
        else:
            self.app.config.data.get('jira', {}).pop('token', None)


class ConfigurationInput(Widget):
    DEFAULT_CSS = """
    ConfigurationInput {
        layout: grid;
        grid-size: 1 3;
        grid-rows: 6fr 4fr 1fr;
    }

    #input-box {
        height: 100%;
        width: 100%;
        scrollbar-gutter: stable;
    }

    ConfigurationInput > Button {
        border: none;
        width: 100%;
        height: auto;
    }

    ConfigurationInput > RichLog {
        height: 100%;
        scrollbar-gutter: stable;
    }
    """

    def compose(self) -> ComposeResult:
        yield Container(
            LabeledInput(Label('Repo name:'), RepoNameInput()),
            LabeledInput(Label('Repo path:'), RepoPathInput()),
            LabeledInput(Label('GitHub user:'), GitHubUserInput()),
            LabeledInput(Label('GitHub token:'), GitHubTokenInput()),
            LabeledInput(Label('Jira email:'), JiraEmailInput()),
            LabeledInput(Label('Jira token:'), JiraTokenInput()),
            id='input-box',
        )
        yield RichLog()
        yield Button('Save', variant='primary', disabled=True)

    async def on_button_pressed(self, _event: Button.Pressed) -> None:
        self.app.config_file.save()

        with suppress(AttributeError):
            del self.app.repo
        with suppress(AttributeError):
            del self.app.repo_path
        with suppress(AttributeError):
            del self.app.git

        if self.app.needs_syncing():
            from ddqa.screens.sync import SyncScreen

            self.app.install_screen(SyncScreen(), 'sync')
            await self.app.switch_screen('sync')
        else:
            await self.app.switch_screen(list(self.app._installed_screens)[0])

    def on_mount(self) -> None:
        text_log = self.query_one(RichLog)
        if errors := self.app.config_errors():
            text_log.write(error_tree(errors), shrink=False)


class ConfigureScreen(Screen):
    BINDINGS = [
        Binding('ctrl+c', 'quit', 'Quit', show=False, priority=True),
        Binding('tab', 'focus_next', 'Focus Next', show=False),
        Binding('shift+tab', 'focus_previous', 'Focus Previous', show=False),
    ]
    DEFAULT_CSS = """
    #screen-configure {
        layout: grid;
        grid-size: 2;
        grid-columns: 1fr;
        grid-rows: 1fr;
    }

    #screen-configure-sidebar {
        height: 100%;
    }

    #screen-configure-placeholder {
        height: 100%;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Container(
            Container(ConfigurationInput(), id='screen-configure-sidebar'),
            Container(Placeholder(width_factor=2), id='screen-configure-placeholder'),
            id='screen-configure',
        )

    def on_input_changed(self, _event: Input.Changed) -> None:
        text_log = self.query_one(RichLog)
        button = self.query_one(Button)

        text_log.clear()
        errors = self.app.config_errors()
        if errors:
            text_log.write(error_tree(errors), shrink=False)
            button.disabled = True
        else:
            button.disabled = False
