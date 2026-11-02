"""The `analytics` group: a client's value, cost, ROI and anomalies over a period."""

from __future__ import annotations

from collections.abc import Mapping

from .._generated.responses import Anomalies, ClientCost, ClientValue, RoiResult
from .._options import CallOptions
from .._transport import AsyncTransport, SyncTransport
from .._types import InstantInput


class AnalyticsResource:
    """The `analytics` operations of `Allisall`.

    `from_` is sent as the query parameter `from`. A period runs from `from_`, inclusive, to
    `to`, exclusive.
    """

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def get_value_for_client(
        self,
        client_id: str,
        /,
        *,
        from_: InstantInput | None = None,
        to: InstantInput | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ClientValue:
        """Compute a client's value over the range `from_` to `to`; an absent bound is
        unbounded.

        Needs the `read` scope. Operation `getClientValue`.
        """
        return self._transport.call(
            "getClientValue",
            ClientValue,
            path=[("client_id", client_id)],
            query={"from_": from_, "to": to},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def get_cost_for_client(
        self,
        client_id: str,
        /,
        *,
        from_: InstantInput,
        to: InstantInput,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ClientCost:
        """Compute a client's cost over the period `from_` to `to`.

        Both bounds are required: standing charges are prorated day by day, so an open
        `from_` would prorate each charge from its own start date, however long ago.

        Needs the `read` scope. Operation `getClientCost`.
        """
        return self._transport.call(
            "getClientCost",
            ClientCost,
            path=[("client_id", client_id)],
            query={"from_": from_, "to": to},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def get_roi_for_client(
        self,
        client_id: str,
        /,
        *,
        from_: InstantInput,
        to: InstantInput,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> RoiResult:
        """Compute a client's ROI over the period `from_` to `to`.

        Needs the `read` scope. Operation `getClientRoi`.
        """
        return self._transport.call(
            "getClientRoi",
            RoiResult,
            path=[("client_id", client_id)],
            query={"from_": from_, "to": to},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def get_anomalies_for_client(
        self,
        client_id: str,
        /,
        *,
        from_: InstantInput,
        to: InstantInput,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Anomalies:
        """Flag anomalies in a client's period, `from_` to `to`.

        Needs the `read` scope. Operation `getClientAnomalies`.
        """
        return self._transport.call(
            "getClientAnomalies",
            Anomalies,
            path=[("client_id", client_id)],
            query={"from_": from_, "to": to},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )


class AsyncAnalyticsResource:
    """The `analytics` operations of `AsyncAllisall`.

    `from_` is sent as the query parameter `from`. A period runs from `from_`, inclusive, to
    `to`, exclusive.
    """

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def get_value_for_client(
        self,
        client_id: str,
        /,
        *,
        from_: InstantInput | None = None,
        to: InstantInput | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ClientValue:
        """Compute a client's value; see `Allisall.analytics.get_value_for_client`.

        Needs the `read` scope. Operation `getClientValue`.
        """
        return await self._transport.call(
            "getClientValue",
            ClientValue,
            path=[("client_id", client_id)],
            query={"from_": from_, "to": to},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def get_cost_for_client(
        self,
        client_id: str,
        /,
        *,
        from_: InstantInput,
        to: InstantInput,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ClientCost:
        """Compute a client's cost; see `Allisall.analytics.get_cost_for_client`.

        Needs the `read` scope. Operation `getClientCost`.
        """
        return await self._transport.call(
            "getClientCost",
            ClientCost,
            path=[("client_id", client_id)],
            query={"from_": from_, "to": to},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def get_roi_for_client(
        self,
        client_id: str,
        /,
        *,
        from_: InstantInput,
        to: InstantInput,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> RoiResult:
        """Compute a client's ROI; see `Allisall.analytics.get_roi_for_client`.

        Needs the `read` scope. Operation `getClientRoi`.
        """
        return await self._transport.call(
            "getClientRoi",
            RoiResult,
            path=[("client_id", client_id)],
            query={"from_": from_, "to": to},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def get_anomalies_for_client(
        self,
        client_id: str,
        /,
        *,
        from_: InstantInput,
        to: InstantInput,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Anomalies:
        """Flag anomalies in a client's period; see
        `Allisall.analytics.get_anomalies_for_client`.

        Needs the `read` scope. Operation `getClientAnomalies`.
        """
        return await self._transport.call(
            "getClientAnomalies",
            Anomalies,
            path=[("client_id", client_id)],
            query={"from_": from_, "to": to},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )
