# SPDX-FileCopyrightText: 2023-present Datadog, Inc. <dev@datadoghq.com>
#
# SPDX-License-Identifier: MIT
import json

from httpx import Request, Response
from textual.widgets import Static

from ddqa.models.config.auth import DatadogAuth
from ddqa.utils.datadog import DatadogDatastore
from ddqa.utils.fs import Path
from ddqa.utils.network import ResponsiveNetworkClient


def make_items_response(items):
    return Response(
        200,
        request=Request('GET', ''),
        content=json.dumps(
            {
                'data': [{'attributes': {'value': item}} for item in items],
                'meta': {'page': {'hasMore': False}},
            }
        ),
    )


class TestGetMembers:
    async def test_extracts_reserved_jira_server_key(self, tmp_path, mocker):
        datastore = DatadogDatastore(DatadogAuth(api_key='key', app_key='app'), Path(tmp_path))
        datastore_id = 'ds-1'

        mocker.patch(
            'httpx.AsyncClient.request',
            side_effect=[
                Response(
                    200,
                    request=Request('GET', ''),
                    content=json.dumps({'data': {'attributes': {'modified_at': '2024-01-01T00:00:00Z'}}}),
                ),
                make_items_response(
                    [
                        {'github_user': 'g1', 'jira_user': 'j1'},
                        {'github_user': 'ddqa__jira_server__', 'jira_user': 'https://example.atlassian.net'},
                        {'github_user': 'g2', 'jira_user': 'j2'},
                    ]
                ),
            ],
        )

        members = await datastore.get_members(ResponsiveNetworkClient(Static()), datastore_id, refresh=True)

        assert members == {'g1': 'j1', 'g2': 'j2'}
        assert datastore.cache.get_datastore_members(datastore_id) == {'g1': 'j1', 'g2': 'j2'}
        assert datastore.cache.get_datastore_jira_server(datastore_id) == 'https://example.atlassian.net'

    async def test_no_jira_server_entry(self, tmp_path, mocker):
        datastore = DatadogDatastore(DatadogAuth(api_key='key', app_key='app'), Path(tmp_path))
        datastore_id = 'ds-1'

        mocker.patch(
            'httpx.AsyncClient.request',
            side_effect=[
                Response(
                    200,
                    request=Request('GET', ''),
                    content=json.dumps({'data': {'attributes': {'modified_at': '2024-01-01T00:00:00Z'}}}),
                ),
                make_items_response([{'github_user': 'g1', 'jira_user': 'j1'}]),
            ],
        )

        members = await datastore.get_members(ResponsiveNetworkClient(Static()), datastore_id, refresh=True)

        assert members == {'g1': 'j1'}
        assert datastore.cache.get_datastore_jira_server(datastore_id) is None
