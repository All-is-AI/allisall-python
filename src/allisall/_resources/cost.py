"""The `cost` group: cost line items and the price table."""

from __future__ import annotations

from collections.abc import Mapping

from .._generated.requests import CostLineItemCreate, CostLineItemPatch, PriceTableSet
from .._generated.responses import CostLineItem, CostLineItemList, PriceTable
from .._options import CallOptions
from .._pagination import AsyncPaginator, Page
from .._transport import AsyncTransport, SyncTransport


class CostResource:
    """The `cost` operations of `Allisall`."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def list_line_items(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Page[CostLineItem, CostLineItemList]:
        """List cost line items.

        Returns the first page; iterating it yields every line item of every page from
        there.

        Needs the `read` scope. Operation `listCostLineItems`.
        """
        return self._transport.call_page(
            "listCostLineItems",
            CostLineItemList,
            CostLineItem,
            query={"limit": limit, "cursor": cursor},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def create_line_item(
        self,
        body: CostLineItemCreate,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> CostLineItem:
        """Create a cost line item.

        `monthly_amount` may be a `Decimal`, an `int` or a `float`; a `Decimal` is sent with
        its exact digits. Every attempt of the call sends one `Idempotency-Key`, so a retry
        cannot create a second line item. Pass `idempotency_key` to choose the key, such as
        one kept across a restart; otherwise the SDK generates one for the call.

        Needs the `write` scope. Operation `createCostLineItem`.
        """
        return self._transport.call(
            "createCostLineItem",
            CostLineItem,
            body=body,
            options=CallOptions(
                timeout=timeout,
                max_retries=max_retries,
                headers=headers,
                idempotency_key=idempotency_key,
            ),
        )

    def get_line_item(
        self,
        line_item_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> CostLineItem:
        """Read a cost line item.

        Needs the `read` scope. Operation `getCostLineItem`.
        """
        return self._transport.call(
            "getCostLineItem",
            CostLineItem,
            path=[("line_item_id", line_item_id)],
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def update_line_item(
        self,
        line_item_id: str,
        patch: CostLineItemPatch,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> CostLineItem:
        """Update a cost line item with a merge patch: a key left out keeps its value, a key
        set to `None` clears the member, and any other value sets it.

        Never retried.

        Needs the `write` scope. Operation `updateCostLineItem`.
        """
        return self._transport.call(
            "updateCostLineItem",
            CostLineItem,
            path=[("line_item_id", line_item_id)],
            body=patch,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def delete_line_item(
        self,
        line_item_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        """Delete a cost line item.

        A retry after a lost response can answer `404` for a delete that succeeded.

        Needs the `write` scope. Operation `deleteCostLineItem`.
        """
        self._transport.call_empty(
            "deleteCostLineItem",
            path=[("line_item_id", line_item_id)],
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def get_price_table(
        self,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> PriceTable:
        """Read the price table.

        Needs the `read` scope. Operation `getPriceTable`.
        """
        return self._transport.call(
            "getPriceTable",
            PriceTable,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def set_price_table(
        self,
        body: PriceTableSet,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> PriceTable:
        """Replace the price table.

        Retried as `max_retries` allows, because sending the same table again leaves the same
        prices.

        Needs the `write` scope. Operation `setPriceTable`.
        """
        return self._transport.call(
            "setPriceTable",
            PriceTable,
            body=body,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )


class AsyncCostResource:
    """The `cost` operations of `AsyncAllisall`."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    def list_line_items(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> AsyncPaginator[CostLineItem, CostLineItemList]:
        """List cost line items.

        Await the result for the first page, or iterate it with `async for` for every line
        item of every page. Nothing is sent until it is awaited or iterated.

        Needs the `read` scope. Operation `listCostLineItems`.
        """
        return self._transport.call_page(
            "listCostLineItems",
            CostLineItemList,
            CostLineItem,
            query={"limit": limit, "cursor": cursor},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def create_line_item(
        self,
        body: CostLineItemCreate,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> CostLineItem:
        """Create a cost line item; see `Allisall.cost.create_line_item`.

        Needs the `write` scope. Operation `createCostLineItem`.
        """
        return await self._transport.call(
            "createCostLineItem",
            CostLineItem,
            body=body,
            options=CallOptions(
                timeout=timeout,
                max_retries=max_retries,
                headers=headers,
                idempotency_key=idempotency_key,
            ),
        )

    async def get_line_item(
        self,
        line_item_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> CostLineItem:
        """Read a cost line item.

        Needs the `read` scope. Operation `getCostLineItem`.
        """
        return await self._transport.call(
            "getCostLineItem",
            CostLineItem,
            path=[("line_item_id", line_item_id)],
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def update_line_item(
        self,
        line_item_id: str,
        patch: CostLineItemPatch,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> CostLineItem:
        """Update a cost line item with a merge patch; see `Allisall.cost.update_line_item`.
        A key set to `None` clears the member.

        Needs the `write` scope. Operation `updateCostLineItem`.
        """
        return await self._transport.call(
            "updateCostLineItem",
            CostLineItem,
            path=[("line_item_id", line_item_id)],
            body=patch,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def delete_line_item(
        self,
        line_item_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        """Delete a cost line item; see `Allisall.cost.delete_line_item`.

        Needs the `write` scope. Operation `deleteCostLineItem`.
        """
        await self._transport.call_empty(
            "deleteCostLineItem",
            path=[("line_item_id", line_item_id)],
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def get_price_table(
        self,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> PriceTable:
        """Read the price table.

        Needs the `read` scope. Operation `getPriceTable`.
        """
        return await self._transport.call(
            "getPriceTable",
            PriceTable,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def set_price_table(
        self,
        body: PriceTableSet,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> PriceTable:
        """Replace the price table.

        Retried as `max_retries` allows, because sending the same table again leaves the same
        prices.

        Needs the `write` scope. Operation `setPriceTable`.
        """
        return await self._transport.call(
            "setPriceTable",
            PriceTable,
            body=body,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )
