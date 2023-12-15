# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT


def assert_return_code(app, auto_mode):
    if auto_mode:
        assert app.return_code == 0
    else:
        assert app.return_code is None
