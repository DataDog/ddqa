# Datadog QA

| | |
| --- | --- |
| CI/CD | [![CI - Test](https://github.com/DataDog/ddqa/actions/workflows/test.yml/badge.svg)](https://github.com/DataDog/ddqa/actions/workflows/test.yml) [![CD - Build](https://github.com/DataDog/ddqa/actions/workflows/build.yml/badge.svg)](https://github.com/DataDog/ddqa/actions/workflows/build.yml) |
| Docs | [![Docs - Build](https://github.com/DataDog/ddqa/actions/workflows/docs.yml/badge.svg)](https://github.com/DataDog/ddqa/actions/workflows/docs.yml) [![Docs - Publish](https://github.com/DataDog/ddqa/actions/workflows/publish-docs.yml/badge.svg)](https://github.com/DataDog/ddqa/actions/workflows/publish-docs.yml) |
| Package | [![PyPI - Version](https://img.shields.io/pypi/v/ddqa.svg?logo=pypi&label=PyPI&logoColor=gold)](https://pypi.org/project/ddqa/) [![PyPI - Downloads](https://img.shields.io/pypi/dm/ddqa.svg?color=blue&label=Downloads&logo=pypi&logoColor=gold)](https://pypi.org/project/ddqa/) [![PyPI - Python Version](https://img.shields.io/pypi/pyversions/ddqa.svg?logo=python&label=Python&logoColor=gold)](https://pypi.org/project/ddqa/) |
| Meta | [![Hatch project](https://img.shields.io/badge/%F0%9F%A5%9A-Hatch-4051b5.svg)](https://github.com/pypa/hatch) [![linting - Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/charliermarsh/ruff/main/assets/badge/v0.json)](https://github.com/charliermarsh/ruff) [![code style - Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black) [![types - Mypy](https://img.shields.io/badge/types-Mypy-blue.svg)](https://github.com/python/mypy) [![License - MIT](https://img.shields.io/badge/license-MIT-9400d3.svg)](https://spdx.org/licenses/) |

-----

DDQA is a tool for users of [Jira](https://www.atlassian.com/software/jira) to perform QA of anticipated releases of code on GitHub.

It works by finding test candidates between two Git references and translates each pull request or direct commit into a Jira issue per designated GitHub team, assigned to a semi-randomly chosen member of that team.

## Features

- Issue creation is completely configurable by each team, with overrides available at runtime
- Robust status tracking with optional filters
- Providing a [TUI](https://en.wikipedia.org/wiki/Text-based_user_interface) allows for running via SSH on other machines, which is useful when there is restricted access to Git repositories

## Documentation

The [documentation](https://datadoghq.dev/ddqa/) is made with [Material for MkDocs](https://github.com/squidfunk/mkdocs-material) and is hosted by [GitHub Pages](https://docs.github.com/en/pages).

## License

DDQA is distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.
