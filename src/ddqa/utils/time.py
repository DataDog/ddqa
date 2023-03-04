# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from decimal import Decimal

SECOND = 1
MINUTE = SECOND * 60
HOUR = MINUTE * 60
DAY = HOUR * 24
WEEK = DAY * 7
MONTH = WEEK * 4
YEAR = MONTH * 12
TIME_UNITS: tuple[tuple[str, int], ...] = (
    ('year', YEAR),
    ('month', MONTH),
    ('week', WEEK),
    ('day', DAY),
    ('hour', HOUR),
    ('minute', MINUTE),
    ('second', SECOND),
)
ELAPSED_PRECISION = Decimal('0.00')


def format_elapsed_time(seconds: float) -> str:
    elapsed_time = Decimal(str(abs(seconds)))
    if elapsed_time < 1:
        return f'{elapsed_time.quantize(ELAPSED_PRECISION)}s'

    units: list[tuple[str, Decimal]] = []
    for unit, factor in TIME_UNITS:
        quotient, remainder = divmod(elapsed_time, factor)
        if quotient < 1:
            continue
        elif not units:
            units.append((unit, quotient))
            elapsed_time -= quotient * factor
        else:
            final = elapsed_time / factor
            if remainder:
                final = final.quantize(ELAPSED_PRECISION)

            units.append((unit, final))
            break

    return ', '.join(f'{value} {unit}{"s" if value > 1 else ""}' for unit, value in units)
