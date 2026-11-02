"""The `clients` group."""

from __future__ import annotations

from collections.abc import Mapping

from .._generated.requests import ClientAgentsSet, ClientCreate, ClientPatch
from .._generated.responses import Client, ClientAgents, ClientDetail, ClientList
from .._options import CallOptions
from .._pagination import AsyncPaginator, Page
from .._transport import AsyncTransport, SyncTransport


class ClientsResource:
    """The `clients` operations of `Allisall`."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def list(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Page[Client, ClientList]:
        """List clients.

        Returns the first page; iterating it yields every client of every page from there.

        Needs the `read` scope. Operation `listClients`.
        """
        return self._transport.call_page(
            "listClients",
            ClientList,
            Client,
            query={"limit": limit, "cursor": cursor},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def create(
        self,
        body: ClientCreate,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> Client:
        """Create a client.

        Every attempt of the call sends one `Idempotency-Key`, so a retry cannot create a
        second client. Pass `idempotency_key` to choose the key, such as one kept across a
        restart; otherwise the SDK generates one for the call.

        Needs the `write` scope. Operation `createClient`.
        """
        return self._transport.call(
            "createClient",
            Client,
            body=body,
            options=CallOptions(
                timeout=timeout,
                max_retries=max_retries,
                headers=headers,
                idempotency_key=idempotency_key,
            ),
        )

    def get(
        self,
        client_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ClientDetail:
        """Read a client.

        Needs the `read` scope. Operation `getClient`.
        """
        return self._transport.call(
            "getClient",
            ClientDetail,
            path=[("client_id", client_id)],
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def update(
        self,
        client_id: str,
        patch: ClientPatch,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Client:
        """Update a client with a merge patch: a key left out keeps its value, a key set to
        `None` clears the member, and any other value sets it.

        Never retried.

        Needs the `write` scope. Operation `updateClient`.
        """
        return self._transport.call(
            "updateClient",
            Client,
            path=[("client_id", client_id)],
            body=patch,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def delete(
        self,
        client_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        """Delete a client.

        Refused while events carry the client's key, or while the client has a validated or
        published calculation; set its status to `churned` instead. A retry after a lost
        response can answer `404` for a delete that succeeded.

        Needs the `write` scope. Operation `deleteClient`.
        """
        self._transport.call_empty(
            "deleteClient",
            path=[("client_id", client_id)],
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def set_agents(
        self,
        client_id: str,
        body: ClientAgentsSet,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ClientAgents:
        """Replace a client's assigned agents.

        Assignment decides how later events are attributed. An event without `client_key`
        from an agent assigned to exactly one client is attributed to that client. A `model`
        or `outcome` event from an agent assigned to two or more clients must carry
        `client_key`, or it is refused with `client_key_required`.

        Retried as `max_retries` allows, because sending the same set again leaves the same
        assignment.

        Needs the `write` scope. Operation `setClientAgents`.
        """
        return self._transport.call(
            "setClientAgents",
            ClientAgents,
            path=[("client_id", client_id)],
            body=body,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )


class AsyncClientsResource:
    """The `clients` operations of `AsyncAllisall`."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    def list(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> AsyncPaginator[Client, ClientList]:
        """List clients.

        Await the result for the first page, or iterate it with `async for` for every client
        of every page. Nothing is sent until it is awaited or iterated.

        Needs the `read` scope. Operation `listClients`.
        """
        return self._transport.call_page(
            "listClients",
            ClientList,
            Client,
            query={"limit": limit, "cursor": cursor},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def create(
        self,
        body: ClientCreate,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> Client:
        """Create a client; see `Allisall.clients.create`.

        Needs the `write` scope. Operation `createClient`.
        """
        return await self._transport.call(
            "createClient",
            Client,
            body=body,
            options=CallOptions(
                timeout=timeout,
                max_retries=max_retries,
                headers=headers,
                idempotency_key=idempotency_key,
            ),
        )

    async def get(
        self,
        client_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ClientDetail:
        """Read a client.

        Needs the `read` scope. Operation `getClient`.
        """
        return await self._transport.call(
            "getClient",
            ClientDetail,
            path=[("client_id", client_id)],
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def update(
        self,
        client_id: str,
        patch: ClientPatch,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Client:
        """Update a client with a merge patch; see `Allisall.clients.update`. A key set to
        `None` clears the member.

        Needs the `write` scope. Operation `updateClient`.
        """
        return await self._transport.call(
            "updateClient",
            Client,
            path=[("client_id", client_id)],
            body=patch,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def delete(
        self,
        client_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        """Delete a client; see `Allisall.clients.delete`.

        Needs the `write` scope. Operation `deleteClient`.
        """
        await self._transport.call_empty(
            "deleteClient",
            path=[("client_id", client_id)],
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def set_agents(
        self,
        client_id: str,
        body: ClientAgentsSet,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ClientAgents:
        """Replace a client's assigned agents; see `Allisall.clients.set_agents`.

        Retried as `max_retries` allows, because sending the same set again leaves the same
        assignment.

        Needs the `write` scope. Operation `setClientAgents`.
        """
        return await self._transport.call(
            "setClientAgents",
            ClientAgents,
            path=[("client_id", client_id)],
            body=body,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )
