# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from unittest.mock import MagicMock

from ddqa.widgets.input import ClickableLabel, LabeledSwitch


class TestClickableSwitch:
    async def test_click(self, app):  # noqa ARG002
        mock = MagicMock()
        labeled_switch = ClickableLabel(label='label', callback=mock.callback)

        assert not mock.callback.called
        labeled_switch.on_click()
        assert mock.callback.called
        assert mock.callback.call_count == 1

        labeled_switch.on_click()
        labeled_switch.on_click()
        assert mock.callback.called
        assert mock.callback.call_count == 3


class TestLabeledSwitch:
    async def test_click(self, app):  # noqa ARG002
        labeled_switch = LabeledSwitch(label='label')

        assert not labeled_switch.switch.value
        labeled_switch.label.on_click()
        assert labeled_switch.switch.value
        labeled_switch.label.on_click()
        assert not labeled_switch.switch.value
