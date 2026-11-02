"""The `reports` group."""

from __future__ import annotations

from collections.abc import Mapping

from .._generated.requests import ReportPatch
from .._generated.responses import Report, ReportList, ReportSummary, ReportWithPreview
from .._options import CallOptions
from .._pagination import AsyncPaginator, Page
from .._transport import AsyncTransport, SyncTransport


class ReportsResource:
    """The `reports` operations of `Allisall`.

    Sharing a report and revoking its link need a person signed in to the dashboard, so this
    client offers neither.
    """

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def create_for_calculation(
        self,
        calculation_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> Report:
        """Compose a report on a calculation.

        Creates a report on a published calculation, with its disclosures taken from the
        calculation's coverage. Takes no request body. Every attempt of the call sends one
        `Idempotency-Key`, so a retry cannot create a second report. Pass `idempotency_key`
        to choose the key, such as one kept across a restart; otherwise the SDK generates one
        for the call.

        Needs the `write` scope. Operation `createReport`.
        """
        return self._transport.call(
            "createReport",
            Report,
            path=[("calculation_id", calculation_id)],
            options=CallOptions(
                timeout=timeout,
                max_retries=max_retries,
                headers=headers,
                idempotency_key=idempotency_key,
            ),
        )

    def list_for_calculation(
        self,
        calculation_id: str,
        /,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Page[ReportSummary, ReportList]:
        """List a calculation's reports.

        Returns the first page; iterating it yields every report of every page from there. Each
        item is a summary without `disclosures`; `get` reads a report with them.

        Needs the `read` scope. Operation `listCalculationReports`.
        """
        return self._transport.call_page(
            "listCalculationReports",
            ReportList,
            ReportSummary,
            path=[("calculation_id", calculation_id)],
            query={"limit": limit, "cursor": cursor},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def get(
        self,
        report_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ReportWithPreview:
        """Read a report.

        Needs the `read` scope. Operation `getReport`.
        """
        return self._transport.call(
            "getReport",
            ReportWithPreview,
            path=[("report_id", report_id)],
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def update(
        self,
        report_id: str,
        patch: ReportPatch,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Report:
        """Edit a report with a merge patch: a key left out keeps its value, a key set to
        `None` clears the member, and any other value sets it.

        Never retried.

        Needs the `write` scope. Operation `updateReport`.
        """
        return self._transport.call(
            "updateReport",
            Report,
            path=[("report_id", report_id)],
            body=patch,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def delete(
        self,
        report_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        """Delete an unshared report.

        A shared report cannot be deleted; revoke its link instead. A retry after a lost
        response can answer `404` for a delete that succeeded.

        Needs the `write` scope. Operation `deleteReport`.
        """
        self._transport.call_empty(
            "deleteReport",
            path=[("report_id", report_id)],
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )


class AsyncReportsResource:
    """The `reports` operations of `AsyncAllisall`.

    Sharing a report and revoking its link need a person signed in to the dashboard, so this
    client offers neither.
    """

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def create_for_calculation(
        self,
        calculation_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> Report:
        """Compose a report on a calculation; see `Allisall.reports.create_for_calculation`.

        Needs the `write` scope. Operation `createReport`.
        """
        return await self._transport.call(
            "createReport",
            Report,
            path=[("calculation_id", calculation_id)],
            options=CallOptions(
                timeout=timeout,
                max_retries=max_retries,
                headers=headers,
                idempotency_key=idempotency_key,
            ),
        )

    def list_for_calculation(
        self,
        calculation_id: str,
        /,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> AsyncPaginator[ReportSummary, ReportList]:
        """List a calculation's reports.

        Await the result for the first page, or iterate it with `async for` for every report
        of every page. Nothing is sent until it is awaited or iterated. Each item is a summary
        without `disclosures`; `get` reads a report with them.

        Needs the `read` scope. Operation `listCalculationReports`.
        """
        return self._transport.call_page(
            "listCalculationReports",
            ReportList,
            ReportSummary,
            path=[("calculation_id", calculation_id)],
            query={"limit": limit, "cursor": cursor},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def get(
        self,
        report_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ReportWithPreview:
        """Read a report.

        Needs the `read` scope. Operation `getReport`.
        """
        return await self._transport.call(
            "getReport",
            ReportWithPreview,
            path=[("report_id", report_id)],
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def update(
        self,
        report_id: str,
        patch: ReportPatch,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Report:
        """Edit a report with a merge patch; see `Allisall.reports.update`. A key set to
        `None` clears the member.

        Needs the `write` scope. Operation `updateReport`.
        """
        return await self._transport.call(
            "updateReport",
            Report,
            path=[("report_id", report_id)],
            body=patch,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def delete(
        self,
        report_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        """Delete an unshared report; see `Allisall.reports.delete`.

        Needs the `write` scope. Operation `deleteReport`.
        """
        await self._transport.call_empty(
            "deleteReport",
            path=[("report_id", report_id)],
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )
