"""The `imports` group: CSV imports."""

from __future__ import annotations

from collections.abc import Mapping

from .._generated.responses import ImportPreview, ImportResult
from .._multipart import ImportUpload
from .._options import CallOptions
from .._transport import AsyncTransport, SyncTransport


class ImportsResource:
    """The `imports` operations of `Allisall`."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def preview(
        self,
        upload: ImportUpload,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ImportPreview:
        """Preview a CSV import: parse, map and validate a file exactly as `commit` would, and
        write nothing.

        The file is sent as a form of two parts, the mapping and then the file; see
        `ImportUpload`. Never retried.

        Needs the `ingest` scope. Operation `previewImport`.
        """
        return self._transport.call(
            "previewImport",
            ImportPreview,
            body=upload,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def commit(
        self,
        upload: ImportUpload,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> ImportResult:
        """Import a CSV file: store its valid rows and record an import batch.

        A problem with one row rejects that row only. The result lists the problems of the
        rejected rows, one `errors` entry per problem, up to the first 1,000; `errors_truncated`
        says when more were omitted, and the counts always cover the whole file. Events
        deduplicate as they do on ingest. The file is sent as a form of two parts, the mapping
        and then the file; see `ImportUpload`.

        Every attempt of the call sends one `Idempotency-Key`, so a retry cannot record a
        second import batch. Pass `idempotency_key` to choose the key, such as one kept
        across a restart; otherwise the SDK generates one for the call.

        Needs the `ingest` scope. Operation `commitImport`.
        """
        return self._transport.call(
            "commitImport",
            ImportResult,
            body=upload,
            options=CallOptions(
                timeout=timeout,
                max_retries=max_retries,
                headers=headers,
                idempotency_key=idempotency_key,
            ),
        )


class AsyncImportsResource:
    """The `imports` operations of `AsyncAllisall`."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def preview(
        self,
        upload: ImportUpload,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ImportPreview:
        """Preview a CSV import; see `Allisall.imports.preview`. A path is read with ordinary
        file I/O, chunk by chunk.

        Needs the `ingest` scope. Operation `previewImport`.
        """
        return await self._transport.call(
            "previewImport",
            ImportPreview,
            body=upload,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def commit(
        self,
        upload: ImportUpload,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> ImportResult:
        """Import a CSV file; see `Allisall.imports.commit`. A path is read with ordinary file
        I/O, chunk by chunk.

        Needs the `ingest` scope. Operation `commitImport`.
        """
        return await self._transport.call(
            "commitImport",
            ImportResult,
            body=upload,
            options=CallOptions(
                timeout=timeout,
                max_retries=max_retries,
                headers=headers,
                idempotency_key=idempotency_key,
            ),
        )
