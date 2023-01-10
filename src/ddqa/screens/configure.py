# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from contextlib import suppress

from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import Screen
from textual.widget import Widget
from textual.widgets import Button, Footer, Header, Input, Label, TextLog

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
        super().on_mount()

        self.value = DefaultValue(self.app.config.data.get('repo', ''))

    def validate_user_input(self, value: object):
        with suppress(AttributeError):
            del self.app.config.app

        previous_repo = self.app.config.data.get('repo', '')
        self.app.config.data['repo'] = value

        repos = self.app.config.data.setdefault('repos', {})
        new_repo = value not in repos

        config = repos.setdefault(value, {})
        if previous_repo in repos:
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
        super().on_mount()

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
        super().on_mount()

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
        super().on_mount()

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
        super().on_mount()

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
        super().on_mount()

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
    ConfigurationInput > Button {
        margin: 1;
        width: 100%;
    }

    ConfigurationInput > TextLog {
        margin: 1;
        padding-bottom: 2;
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield LabeledInput(Label('Repo name:'), RepoNameInput())
        yield LabeledInput(Label('Repo path:'), RepoPathInput())
        yield LabeledInput(Label('GitHub user:'), GitHubUserInput())
        yield LabeledInput(Label('GitHub token:'), GitHubTokenInput())
        yield LabeledInput(Label('Jira email:'), JiraEmailInput())
        yield LabeledInput(Label('Jira token:'), JiraTokenInput())
        yield Button('Save', variant='primary', disabled=True)
        yield TextLog()

    async def on_button_pressed(self, _event: Button.Pressed) -> None:
        self.app.config_file.save()

        del self.app.repo
        del self.app.repo_path
        del self.app.git

        if self.app.needs_syncing():
            from ddqa.screens.sync import SyncScreen

            self.app.install_screen(SyncScreen(), 'sync')
            await self.app.switch_screen('sync')
        else:
            await self.app.switch_screen(list(self.app._installed_screens)[0])

    def on_mount(self) -> None:
        text_log = self.query_one(TextLog)
        errors = self.app.config_errors()
        if errors:
            text_log.write(error_tree(errors), shrink=False)


class ConfigureScreen(Screen):
    BINDINGS = [('escape', 'app.exit', 'Exit app')]
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
        yield Footer()

    def on_input_changed(self, _event: Input.Changed) -> None:
        text_log = self.query_one(TextLog)
        button = self.query_one(Button)

        text_log.clear()
        errors = self.app.config_errors()
        if errors:
            text_log.write(error_tree(errors), shrink=False)
            button.disabled = True
        else:
            button.disabled = False
