# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from ddqa.cache.datadog import JIRA_SERVER_KEY, DatadogCache

if TYPE_CHECKING:
    from ddqa.models.config.auth import DatadogAuth
    from ddqa.utils.fs import Path
    from ddqa.utils.network import ResponsiveNetworkClient


class DatadogDatastore:
    API_BASE = 'https://api.datadoghq.com/api/v2/actions-datastores'

    # Members are only re-fetched when the datastore's `modified_at` timestamp changes,
    # since a full page walk is otherwise wasted work on every sync.
    PAGE_SIZE = 100

    def __init__(self, auth: DatadogAuth, cache_dir: Path):
        self.__auth = auth
        self.__cache = DatadogCache(cache_dir)

    @property
    def auth(self) -> DatadogAuth:
        return self.__auth

    @property
    def cache(self) -> DatadogCache:
        return self.__cache

    @cached_property
    def __headers(self) -> dict[str, str]:
        return {'DD-API-KEY': self.auth.api_key, 'DD-APPLICATION-KEY': self.auth.app_key}

    async def get_members(
        self, client: ResponsiveNetworkClient, datastore_id: str, *, refresh: bool = False
    ) -> dict[str, str]:
        cached_modified_at = self.cache.get_datastore_modified_at(datastore_id)

        response = await self.__api_get(client, f'{self.API_BASE}/{datastore_id}')
        modified_at = response.json()['data']['attributes']['modified_at']

        if not refresh and cached_modified_at == modified_at:
            return self.cache.get_datastore_members(datastore_id)

        members, jira_server = await self.__fetch_all_members(client, datastore_id)
        self.cache.save_datastore(datastore_id, modified_at, members, jira_server)
        return members

    async def __fetch_all_members(
        self, client: ResponsiveNetworkClient, datastore_id: str
    ) -> tuple[dict[str, str], str | None]:
        members: dict[str, str] = {}
        jira_server: str | None = None
        offset = 0

        while True:
            response = await self.__api_get(
                client,
                f'{self.API_BASE}/{datastore_id}/items',
                params={'page[limit]': self.PAGE_SIZE, 'page[offset]': offset},
            )
            payload = response.json()

            for item in payload['data']:
                value = item['attributes']['value']
                github_user = str(value['github_user'])
                if github_user == JIRA_SERVER_KEY:
                    jira_server = str(value['jira_user'])
                else:
                    members[github_user] = str(value['jira_user'])

            if not payload['meta']['page']['hasMore']:
                break

            offset += self.PAGE_SIZE

        return members, jira_server

    async def __api_get(self, client: ResponsiveNetworkClient, *args, **kwargs):
        retry_wait = 2
        while True:
            try:
                response = await client.get(*args, headers=self.__headers, **kwargs)

                if response.status_code == 429:  # noqa: PLR2004
                    retry_after = float(response.headers.get('X-RateLimit-Reset', retry_wait))
                    await client.wait(retry_after, context='Rate limited by Datadog API')
                    continue

                client.check_status(response, **kwargs)
            except Exception as e:
                await client.wait(retry_wait, context=str(e))
                retry_wait *= 2
                continue

            return response
