"""The `imports` group: CSV imports."""

from __future__ import annotations

from collections.abc import Mapping

from .._generated.responses import Import, ImportList, ImportPreview, ImportResult, ImportSummary
from .._multipart import ImportUpload
from .._options import CallOptions
from .._pagination import AsyncPaginator, Page
from .._transport import AsyncTransport, SyncTransport


class ImportsResource:
    """The `imports` operations of `Allisall`."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def list(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        page: int | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Page[ImportSummary, ImportList]:
        """List the workspace's imports, newest first, each with its counts.

        Returns the first page; iterating it yields every import of every page from there.

        Pass `page` or `cursor`, not both. Pass `page` for a numbered page: the page's `body`
        then holds `page` and `total`. Only that first page is counted; every later page of a
        walk continues by cursor from it, and its `page` and `total` are `None`. To show another
        numbered page, call this method again with its `page` rather than `get_next_page()`. A
        `page` past the end has no items, and the walk ends there.

        Needs the `read` scope. Operation `listImports`.
        """
        return self._transport.call_page(
            "listImports",
            ImportList,
            ImportSummary,
            query={"limit": limit, "cursor": cursor, "page": page},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def get(
        self,
        import_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Import:
        """Read an import, with the mapping it ran with.

        Pass that mapping to `to_import_mapping` to send it as the next import's mapping.

        Needs the `read` scope. Operation `getImport`.
        """
        return self._transport.call(
            "getImport",
            Import,
            path=[("import_id", import_id)],
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

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

    def list(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        page: int | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> AsyncPaginator[ImportSummary, ImportList]:
        """List the workspace's imports, newest first, each with its counts.

        Await the result for the first page, or iterate it with `async for` for every import of
        every page. Nothing is sent until it is awaited or iterated.

        Pass `page` or `cursor`, not both. Pass `page` for a numbered page: the page's `body`
        then holds `page` and `total`. Only that first page is counted; every later page of a
        walk continues by cursor from it, and its `page` and `total` are `None`. To show another
        numbered page, call this method again with its `page` rather than `get_next_page()`. A
        `page` past the end has no items, and the walk ends there.

        Needs the `read` scope. Operation `listImports`.
        """
        return self._transport.call_page(
            "listImports",
            ImportList,
            ImportSummary,
            query={"limit": limit, "cursor": cursor, "page": page},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def get(
        self,
        import_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Import:
        """Read an import, with the mapping it ran with.

        Pass that mapping to `to_import_mapping` to send it as the next import's mapping.

        Needs the `read` scope. Operation `getImport`.
        """
        return await self._transport.call(
            "getImport",
            Import,
            path=[("import_id", import_id)],
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

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
