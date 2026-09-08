# Installation

-----

!!! warning "Important"
    In addition to installing the tool itself, you will also need to use a modern terminal emulator such as:

    - [Windows Terminal](https://github.com/microsoft/terminal)
    - [iTerm2](https://gitlab.com/gnachman/iterm2)
    - [WezTerm](https://github.com/wez/wezterm)
    - [Alacritty](https://github.com/alacritty/alacritty)

## GitHub releases

Each [release](https://github.com/DataDog/ddqa/releases) provides the following:

- Standalone binaries for Linux, Windows, and macOS
- Windows AMD64 (64-bit) MSI installer
- Windows x86 (32-bit) MSI installer
- Windows universal (AMD64+x86) EXE installer
- macOS DMG installer

## pipx

[pipx](https://github.com/pypa/pipx) allows for the global installation of Python applications in isolated environments.

```
pipx install ddqa
```

## pip

DDQA is available on PyPI and can be installed with [pip](https://pip.pypa.io).

```
pip install ddqa
```

!!! warning
    This method modifies the Python environment in which you choose to install. Consider instead using [pipx](#pipx) to avoid dependency conflicts.

## Testing a pull request

To try out changes from an open pull request before it's merged and released, install directly from the branch with pip or pipx, referencing the contributor's fork/branch name (shown at the top of the PR):

```
pipx install "git+https://github.com/DataDog/ddqa.git@<branch-name>"
```

or, to upgrade an existing pipx install:

```
pipx install --force "git+https://github.com/DataDog/ddqa.git@<branch-name>"
```

Once installed, `ddqa` behaves like any other install — see [Configuration](config/user.md) to set up credentials, and [Repository configuration](config/repo.md) for repo-level settings. To go back to the released version afterwards, reinstall from PyPI:

```
pipx install --force ddqa
```
