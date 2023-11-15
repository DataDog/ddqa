# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from unittest.mock import MagicMock

from ddqa.widgets.input import LabeledSwitch


class TestLabeledSwitch:
    async def test_click(self, app):  # noqa ARG002
        labeled_switch = LabeledSwitch(label='label')

        assert not labeled_switch.switch.value
        labeled_switch._on_click(MagicMock())
        assert labeled_switch.switch.value
        labeled_switch._on_click(MagicMock())
        assert not labeled_switch.switch.value
