"""The `outcome_types` group."""

from __future__ import annotations

from collections.abc import Mapping

from .._generated.responses import OutcomeTypeList, OutcomeTypeUsage
from .._options import CallOptions
from .._pagination import AsyncPaginator, Page
from .._transport import AsyncTransport, SyncTransport
from .._types import InstantInput


class OutcomeTypesResource:
    """The `outcome_types` operations of `Allisall`."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def list(
        self,
        *,
        from_: InstantInput | None = None,
        to: InstantInput | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Page[OutcomeTypeUsage, OutcomeTypeList]:
        """List the workspace's outcome types, over the range `from_` to `to`; an absent bound
        is unbounded. `from_` is sent as the query parameter `from`.

        Returns the first page; iterating it yields every outcome type of every page from
        there.

        Needs the `read` scope. Operation `listOutcomeTypes`.
        """
        return self._transport.call_page(
            "listOutcomeTypes",
            OutcomeTypeList,
            OutcomeTypeUsage,
            query={"from_": from_, "to": to, "limit": limit, "cursor": cursor},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def list_for_client(
        self,
        client_id: str,
        /,
        *,
        from_: InstantInput | None = None,
        to: InstantInput | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Page[OutcomeTypeUsage, OutcomeTypeList]:
        """List a client's outcome types, over the range `from_` to `to`; an absent bound is
        unbounded. `from_` is sent as the query parameter `from`.

        Returns the first page; iterating it yields every outcome type of every page from
        there.

        Needs the `read` scope. Operation `listClientOutcomeTypes`.
        """
        return self._transport.call_page(
            "listClientOutcomeTypes",
            OutcomeTypeList,
            OutcomeTypeUsage,
            path=[("client_id", client_id)],
            query={"from_": from_, "to": to, "limit": limit, "cursor": cursor},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )


class AsyncOutcomeTypesResource:
    """The `outcome_types` operations of `AsyncAllisall`."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    def list(
        self,
        *,
        from_: InstantInput | None = None,
        to: InstantInput | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> AsyncPaginator[OutcomeTypeUsage, OutcomeTypeList]:
        """List the workspace's outcome types; see `Allisall.outcome_types.list`.

        Await the result for the first page, or iterate it with `async for` for every
        outcome type of every page. Nothing is sent until it is awaited or iterated.

        Needs the `read` scope. Operation `listOutcomeTypes`.
        """
        return self._transport.call_page(
            "listOutcomeTypes",
            OutcomeTypeList,
            OutcomeTypeUsage,
            query={"from_": from_, "to": to, "limit": limit, "cursor": cursor},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def list_for_client(
        self,
        client_id: str,
        /,
        *,
        from_: InstantInput | None = None,
        to: InstantInput | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> AsyncPaginator[OutcomeTypeUsage, OutcomeTypeList]:
        """List a client's outcome types; see `Allisall.outcome_types.list_for_client`.

        Await the result for the first page, or iterate it with `async for` for every
        outcome type of every page. Nothing is sent until it is awaited or iterated.

        Needs the `read` scope. Operation `listClientOutcomeTypes`.
        """
        return self._transport.call_page(
            "listClientOutcomeTypes",
            OutcomeTypeList,
            OutcomeTypeUsage,
            path=[("client_id", client_id)],
            query={"from_": from_, "to": to, "limit": limit, "cursor": cursor},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )
