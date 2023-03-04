# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import pytest

from ddqa.utils import time as time_utils


@pytest.mark.parametrize(
    'seconds, formatted',
    [
        # Use expressions so the test output looks nice
        ('SECOND / 100', '0.01s'),
        ('SECOND', '1 second'),
        ('MINUTE + (SECOND * 3)', '1 minute, 3 seconds'),
        ('(MINUTE * 2) + (SECOND * 3)', '2 minutes, 3 seconds'),
        ('(HOUR * 2) + (SECOND * 3)', '2 hours, 3 seconds'),
        ('(HOUR * 2) + (MINUTE * 7) + (SECOND * 30)', '2 hours, 7.50 minutes'),
        ('(DAY * 2) + (MINUTE * 7) + (SECOND * 30)', '2 days, 7.50 minutes'),
        ('(DAY * 2) + (HOUR * 7) + (MINUTE * 30)', '2 days, 7.50 hours'),
        ('(WEEK * 2) + (MINUTE * 7) + (SECOND * 30)', '2 weeks, 7.50 minutes'),
        ('(WEEK * 2) + (DAY * 4) + (HOUR * 12)', '2 weeks, 4.50 days'),
        ('(MONTH * 2) + (MINUTE * 7) + (SECOND * 30)', '2 months, 7.50 minutes'),
        ('(MONTH * 2) + (WEEK * 2) + (DAY * 3.5)', '2 months, 2.50 weeks'),
        ('(YEAR * 2) + (MINUTE * 7) + (SECOND * 30)', '2 years, 7.50 minutes'),
        ('(YEAR * 2) + (MONTH * 8) + (WEEK * 2)', '2 years, 8.50 months'),
        ('YEAR', '1 year'),
    ],
)
def test_format_elapsed_time(seconds, formatted):
    assert time_utils.format_elapsed_time(eval(seconds, {}, vars(time_utils))) == formatted
