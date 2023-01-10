# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import os


def running_in_ci() -> bool:
    return any(os.environ.get(env_var) in ('true', '1') for env_var in ('CI', 'GITHUB_ACTIONS'))
