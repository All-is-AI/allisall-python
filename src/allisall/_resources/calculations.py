"""The `calculations` group."""

from __future__ import annotations

from collections.abc import Mapping

from .._generated.requests import CalculationCreate
from .._generated.responses import Calculation, CalculationList, CalculationSummary
from .._options import CallOptions
from .._pagination import AsyncPaginator, Page
from .._transport import AsyncTransport, SyncTransport


class CalculationsResource:
    """The `calculations` operations of `Allisall`.

    Validating, publishing and reopening a calculation need a person signed in to the
    dashboard, so this client offers none of them.
    """

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def create_for_client(
        self,
        client_id: str,
        body: CalculationCreate,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> Calculation:
        """Freeze a client's ROI for a period.

        Computes the client's ROI for an ended period and freezes it as a draft calculation.
        Every attempt of the call sends one `Idempotency-Key`, so a retry cannot create a
        second calculation. Pass `idempotency_key` to choose the key, such as one kept across
        a restart; otherwise the SDK generates one for the call.

        Needs the `write` scope. Operation `createCalculation`.
        """
        return self._transport.call(
            "createCalculation",
            Calculation,
            path=[("client_id", client_id)],
            body=body,
            options=CallOptions(
                timeout=timeout,
                max_retries=max_retries,
                headers=headers,
                idempotency_key=idempotency_key,
            ),
        )

    def list_for_client(
        self,
        client_id: str,
        /,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Page[CalculationSummary, CalculationList]:
        """List a client's calculations.

        Returns the first page; iterating it yields every calculation of every page from
        there.

        Needs the `read` scope. Operation `listClientCalculations`.
        """
        return self._transport.call_page(
            "listClientCalculations",
            CalculationList,
            CalculationSummary,
            path=[("client_id", client_id)],
            query={"limit": limit, "cursor": cursor},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def get(
        self,
        calculation_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Calculation:
        """Read a calculation.

        Needs the `read` scope. Operation `getCalculation`.
        """
        return self._transport.call(
            "getCalculation",
            Calculation,
            path=[("calculation_id", calculation_id)],
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def delete(
        self,
        calculation_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        """Delete a draft calculation.

        A retry after a lost response can answer `404` for a delete that succeeded.

        Needs the `write` scope. Operation `deleteCalculation`.
        """
        self._transport.call_empty(
            "deleteCalculation",
            path=[("calculation_id", calculation_id)],
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )


class AsyncCalculationsResource:
    """The `calculations` operations of `AsyncAllisall`.

    Validating, publishing and reopening a calculation need a person signed in to the
    dashboard, so this client offers none of them.
    """

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def create_for_client(
        self,
        client_id: str,
        body: CalculationCreate,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> Calculation:
        """Freeze a client's ROI for a period; see `Allisall.calculations.create_for_client`.

        Needs the `write` scope. Operation `createCalculation`.
        """
        return await self._transport.call(
            "createCalculation",
            Calculation,
            path=[("client_id", client_id)],
            body=body,
            options=CallOptions(
                timeout=timeout,
                max_retries=max_retries,
                headers=headers,
                idempotency_key=idempotency_key,
            ),
        )

    def list_for_client(
        self,
        client_id: str,
        /,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> AsyncPaginator[CalculationSummary, CalculationList]:
        """List a client's calculations.

        Await the result for the first page, or iterate it with `async for` for every
        calculation of every page. Nothing is sent until it is awaited or iterated.

        Needs the `read` scope. Operation `listClientCalculations`.
        """
        return self._transport.call_page(
            "listClientCalculations",
            CalculationList,
            CalculationSummary,
            path=[("client_id", client_id)],
            query={"limit": limit, "cursor": cursor},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def get(
        self,
        calculation_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Calculation:
        """Read a calculation.

        Needs the `read` scope. Operation `getCalculation`.
        """
        return await self._transport.call(
            "getCalculation",
            Calculation,
            path=[("calculation_id", calculation_id)],
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def delete(
        self,
        calculation_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        """Delete a draft calculation; see `Allisall.calculations.delete`.

        Needs the `write` scope. Operation `deleteCalculation`.
        """
        await self._transport.call_empty(
            "deleteCalculation",
            path=[("calculation_id", calculation_id)],
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )
