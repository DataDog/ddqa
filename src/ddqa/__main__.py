# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import sys

if __name__ == '__main__':
    from ddqa.cli import ddqa

    sys.exit(ddqa())
