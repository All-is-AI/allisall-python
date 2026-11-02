"""The `dashboard` group: the workspace's month, and renewal readiness."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal, TypeAlias

from .._generated.responses import Dashboard, Renewal, RenewalList
from .._options import CallOptions
from .._pagination import AsyncPaginator, Page
from .._transport import AsyncTransport, SyncTransport
from ._query import SortDirection

DashboardSort: TypeAlias = Literal["name", "value_total", "cost_total", "roi", "renewal_date"]
"""The sort keys of the dashboard's clients."""


class DashboardResource:
    """The `dashboard` operations of `Allisall`."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def get(
        self,
        *,
        month: str,
        sort: DashboardSort | None = None,
        dir_: SortDirection | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Dashboard:
        """Read the workspace's month.

        `month` is a calendar month, such as `2026-08`, between `1900-01` and `9999-12`.
        `sort` orders `clients`, ascending by default; `dir_` is sent as the query parameter
        `dir`.

        Needs the `read` scope. Operation `getDashboard`.
        """
        return self._transport.call(
            "getDashboard",
            Dashboard,
            query={"month": month, "sort": sort, "dir_": dir_},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def list_renewals(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Page[Renewal, RenewalList]:
        """List renewal readiness.

        Reads each client's latest published figures, whatever month the dashboard shows.
        Returns the first page; iterating it yields every renewal of every page from there.

        Needs the `read` scope. Operation `listRenewals`.
        """
        return self._transport.call_page(
            "listRenewals",
            RenewalList,
            Renewal,
            query={"limit": limit, "cursor": cursor},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )


class AsyncDashboardResource:
    """The `dashboard` operations of `AsyncAllisall`."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def get(
        self,
        *,
        month: str,
        sort: DashboardSort | None = None,
        dir_: SortDirection | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Dashboard:
        """Read the workspace's month; see `Allisall.dashboard.get`.

        Needs the `read` scope. Operation `getDashboard`.
        """
        return await self._transport.call(
            "getDashboard",
            Dashboard,
            query={"month": month, "sort": sort, "dir_": dir_},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def list_renewals(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> AsyncPaginator[Renewal, RenewalList]:
        """List renewal readiness; see `Allisall.dashboard.list_renewals`.

        Await the result for the first page, or iterate it with `async for` for every
        renewal of every page. Nothing is sent until it is awaited or iterated.

        Needs the `read` scope. Operation `listRenewals`.
        """
        return self._transport.call_page(
            "listRenewals",
            RenewalList,
            Renewal,
            query={"limit": limit, "cursor": cursor},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )
