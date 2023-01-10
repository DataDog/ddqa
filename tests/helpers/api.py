# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import re
from textwrap import dedent as _dedent

import pytest
from rich.console import Console

# The default time to wait after artificial key presses for all triggered events to complete
# https://github.com/Textualize/textual/issues/1606
ASYNC_WAIT = 0.2


def dedent(text, *, terminal=False):
    text = _dedent(text[1:])
    if terminal:
        return text

    return text[:-1]


def remove_trailing_spaces(text):
    return ''.join(f'{line.rstrip()}\n' for line in text.splitlines(True))


def rich_render(obj, **kwargs) -> str:
    console = Console(**kwargs)
    with console.capture() as capture:
        console.print(obj)

    return capture.get()


def error(exception_class, message='', **kwargs):
    if message:
        kwargs['match'] = f'^{re.escape(message)}$'

    return pytest.raises(exception_class, **kwargs)
