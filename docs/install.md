# Installation

-----

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
