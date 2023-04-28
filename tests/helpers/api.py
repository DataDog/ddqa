# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import re
from textwrap import dedent as _dedent

import pytest
from rich.console import Console

# The default time to wait for all triggered events to complete
ASYNC_WAIT = 0.5

_initial_value = object()


class MutatingEqualityValue:
    def __init__(self, initial=_initial_value):
        self.value = initial

    def inverse(self):
        return InverseEqualityValue(self)

    def __eq__(self, other):
        original = self.value
        self.value = other
        return original is _initial_value or original == other


class InverseEqualityValue:
    def __init__(self, value: MutatingEqualityValue):
        self.value = value

    def __eq__(self, other):
        return self.value.value != other


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
