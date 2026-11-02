"""The `agents` group."""

from __future__ import annotations

from collections.abc import Mapping

from .._generated.requests import AgentCreate, AgentPatch
from .._generated.responses import Agent, AgentDetail, AgentList, AgentListItem
from .._options import CallOptions
from .._pagination import AsyncPaginator, Page
from .._transport import AsyncTransport, SyncTransport
from .._types import InstantInput


class AgentsResource:
    """The `agents` operations of `Allisall`."""

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
    ) -> Page[AgentListItem, AgentList]:
        """List agents.

        Returns the first page; iterating it yields every agent of every page from there.

        Needs the `read` scope. Operation `listAgents`.
        """
        return self._transport.call_page(
            "listAgents",
            AgentList,
            AgentListItem,
            query={"limit": limit, "cursor": cursor},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def create(
        self,
        body: AgentCreate,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> Agent:
        """Create an agent.

        Every attempt of the call sends one `Idempotency-Key`, so a retry cannot create a
        second agent. Pass `idempotency_key` to choose the key, such as one kept across a
        restart; otherwise the SDK generates one for the call.

        Needs the `write` scope. Operation `createAgent`.
        """
        return self._transport.call(
            "createAgent",
            Agent,
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
        agent_id: str,
        /,
        *,
        from_: InstantInput | None = None,
        to: InstantInput | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> AgentDetail:
        """Read an agent.

        `from_` and `to` bound the statistics only; absent bounds mean all time. `from_` is
        sent as the query parameter `from`.

        Needs the `read` scope. Operation `getAgent`.
        """
        return self._transport.call(
            "getAgent",
            AgentDetail,
            path=[("agent_id", agent_id)],
            query={"from_": from_, "to": to},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def update(
        self,
        agent_id: str,
        patch: AgentPatch,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Agent:
        """Update an agent with a merge patch: a key left out keeps its value, a key set to
        `None` clears the member, and any other value sets it.

        Never retried.

        Needs the `write` scope. Operation `updateAgent`.
        """
        return self._transport.call(
            "updateAgent",
            Agent,
            path=[("agent_id", agent_id)],
            body=patch,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def delete(
        self,
        agent_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        """Delete an agent.

        Refused while events reference the agent; set its status to `retired` instead. A
        retry after a lost response can answer `404` for a delete that succeeded.

        Needs the `write` scope. Operation `deleteAgent`.
        """
        self._transport.call_empty(
            "deleteAgent",
            path=[("agent_id", agent_id)],
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )


class AsyncAgentsResource:
    """The `agents` operations of `AsyncAllisall`."""

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
    ) -> AsyncPaginator[AgentListItem, AgentList]:
        """List agents.

        Await the result for the first page, or iterate it with `async for` for every agent
        of every page. Nothing is sent until it is awaited or iterated.

        Needs the `read` scope. Operation `listAgents`.
        """
        return self._transport.call_page(
            "listAgents",
            AgentList,
            AgentListItem,
            query={"limit": limit, "cursor": cursor},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def create(
        self,
        body: AgentCreate,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> Agent:
        """Create an agent; see `Allisall.agents.create`.

        Needs the `write` scope. Operation `createAgent`.
        """
        return await self._transport.call(
            "createAgent",
            Agent,
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
        agent_id: str,
        /,
        *,
        from_: InstantInput | None = None,
        to: InstantInput | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> AgentDetail:
        """Read an agent; see `Allisall.agents.get`.

        Needs the `read` scope. Operation `getAgent`.
        """
        return await self._transport.call(
            "getAgent",
            AgentDetail,
            path=[("agent_id", agent_id)],
            query={"from_": from_, "to": to},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def update(
        self,
        agent_id: str,
        patch: AgentPatch,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Agent:
        """Update an agent with a merge patch; see `Allisall.agents.update`. A key set to
        `None` clears the member.

        Needs the `write` scope. Operation `updateAgent`.
        """
        return await self._transport.call(
            "updateAgent",
            Agent,
            path=[("agent_id", agent_id)],
            body=patch,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def delete(
        self,
        agent_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        """Delete an agent; see `Allisall.agents.delete`.

        Needs the `write` scope. Operation `deleteAgent`.
        """
        await self._transport.call_empty(
            "deleteAgent",
            path=[("agent_id", agent_id)],
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )
