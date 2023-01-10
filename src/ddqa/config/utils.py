# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
SCRUBBED_VALUE = '*****'


def scrub_config(config: dict):
    if 'token' in config.get('github', {}):
        config['github']['token'] = SCRUBBED_VALUE

    if 'token' in config.get('jira', {}):
        config['jira']['token'] = SCRUBBED_VALUE
