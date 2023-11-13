# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

import asyncio
import json
import typing
from time import monotonic

import httpx

if typing.TYPE_CHECKING:
    from textual.widgets import Static


class ResponsiveNetworkClient(httpx.AsyncClient):
    def __init__(self, status: Static, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.__status = status

    @property
    def status(self) -> Static:
        return self.__status

    async def wait(self, seconds_to_wait: int | float, *, context: str = '') -> None:
        original_status = self.status.render()
        start_time = monotonic()

        while (elapsed_seconds := monotonic() - start_time) < seconds_to_wait:
            remaining_minutes, remaining_seconds = divmod(seconds_to_wait - elapsed_seconds, 60)
            remaining_hours, remaining_minutes = divmod(remaining_minutes, 60)

            message = f'Retrying in: {remaining_hours:02,.0f}:{remaining_minutes:02.0f}:{remaining_seconds:05.2f}'
            if context:
                message = f'{message}\n\n{context}'

            self.status.update(message)
            await asyncio.sleep(0.1)

        self.status.update(original_status)

    @staticmethod
    def check_status(response: httpx.Response, **kwargs) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            kwargs.pop('auth', None)
            try:
                data = response.json()
            except json.JSONDecodeError:
                response_text = response.text
            else:
                response_text = json.dumps(data, indent=2, sort_keys=True)

            message = f"""\
{e}

Data
----
{json.dumps(kwargs, indent=2, sort_keys=True)}
Response
--------
{response_text}
""".rstrip()
            raise httpx.HTTPStatusError(message, request=response.request, response=response) from None
