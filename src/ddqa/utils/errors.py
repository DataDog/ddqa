# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from rich.tree import Tree


def error_tree(errors):
    tree = Tree('Configuration errors')
    for error in errors:
        tree.add(error)

    return tree
