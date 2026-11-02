"""The `value_models` group: value models and value templates."""

from __future__ import annotations

from collections.abc import Mapping

from .._generated.requests import ValueLineItemsSet, ValueModelCreate, ValueModelPatch
from .._generated.responses import (
    ValueModel,
    ValueModelList,
    ValueModelSummary,
    ValueTemplate,
    ValueTemplateList,
)
from .._options import CallOptions
from .._pagination import AsyncPaginator, Page
from .._transport import AsyncTransport, SyncTransport


class ValueModelsResource:
    """The `value_models` operations of `Allisall`.

    `get` takes a value model's id. The methods ending `_for_client` take a client's id, and
    act on that client's active value model.
    """

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
    ) -> Page[ValueModelSummary, ValueModelList]:
        """List value models.

        Returns the first page; iterating it yields every value model of every page from
        there.

        Needs the `read` scope. Operation `listValueModels`.
        """
        return self._transport.call_page(
            "listValueModels",
            ValueModelList,
            ValueModelSummary,
            query={"limit": limit, "cursor": cursor},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def get(
        self,
        value_model_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ValueModel:
        """Read a value model: any model in the workspace, archived ones included.

        Needs the `read` scope. Operation `getValueModel`.
        """
        return self._transport.call(
            "getValueModel",
            ValueModel,
            path=[("value_model_id", value_model_id)],
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def get_for_client(
        self,
        client_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ValueModel:
        """Read a client's active value model.

        Needs the `read` scope. Operation `getClientValueModel`.
        """
        return self._transport.call(
            "getClientValueModel",
            ValueModel,
            path=[("client_id", client_id)],
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def create_for_client(
        self,
        client_id: str,
        body: ValueModelCreate,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> ValueModel:
        """Create a client's value model.

        Every attempt of the call sends one `Idempotency-Key`, so a retry cannot create a
        second value model. Pass `idempotency_key` to choose the key, such as one kept across
        a restart; otherwise the SDK generates one for the call.

        Needs the `write` scope. Operation `createValueModel`.
        """
        return self._transport.call(
            "createValueModel",
            ValueModel,
            path=[("client_id", client_id)],
            body=body,
            options=CallOptions(
                timeout=timeout,
                max_retries=max_retries,
                headers=headers,
                idempotency_key=idempotency_key,
            ),
        )

    def update_for_client(
        self,
        client_id: str,
        patch: ValueModelPatch,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ValueModel:
        """Update a client's active value model with a merge patch: a key left out keeps its
        value, a key set to `None` clears the member, and any other value sets it.

        Never retried.

        Needs the `write` scope. Operation `updateValueModel`.
        """
        return self._transport.call(
            "updateValueModel",
            ValueModel,
            path=[("client_id", client_id)],
            body=patch,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def delete_for_client(
        self,
        client_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        """Delete a client's active value model.

        A retry after a lost response can answer `404` for a delete that succeeded.

        Needs the `write` scope. Operation `deleteValueModel`.
        """
        self._transport.call_empty(
            "deleteValueModel",
            path=[("client_id", client_id)],
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def set_line_items_for_client(
        self,
        client_id: str,
        body: ValueLineItemsSet,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ValueModel:
        """Replace the line items of a client's active value model.

        Replaces the whole set, guarded by `version`: a stale version is refused rather than
        overwriting a co-editor's change.

        Never retried: a retry after a lost response would be refused as stale even when the
        first attempt landed. After a connection error, read the value model again for its
        current `version` before trying again.

        Needs the `write` scope. Operation `setValueModelLineItems`.
        """
        return self._transport.call(
            "setValueModelLineItems",
            ValueModel,
            path=[("client_id", client_id)],
            body=body,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def list_templates(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Page[ValueTemplate, ValueTemplateList]:
        """List value templates.

        Returns the first page; iterating it yields every template of every page from there.

        Needs the `read` scope. Operation `listValueTemplates`.
        """
        return self._transport.call_page(
            "listValueTemplates",
            ValueTemplateList,
            ValueTemplate,
            query={"limit": limit, "cursor": cursor},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )


class AsyncValueModelsResource:
    """The `value_models` operations of `AsyncAllisall`.

    `get` takes a value model's id. The methods ending `_for_client` take a client's id, and
    act on that client's active value model.
    """

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
    ) -> AsyncPaginator[ValueModelSummary, ValueModelList]:
        """List value models.

        Await the result for the first page, or iterate it with `async for` for every value
        model of every page. Nothing is sent until it is awaited or iterated.

        Needs the `read` scope. Operation `listValueModels`.
        """
        return self._transport.call_page(
            "listValueModels",
            ValueModelList,
            ValueModelSummary,
            query={"limit": limit, "cursor": cursor},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def get(
        self,
        value_model_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ValueModel:
        """Read a value model: any model in the workspace, archived ones included.

        Needs the `read` scope. Operation `getValueModel`.
        """
        return await self._transport.call(
            "getValueModel",
            ValueModel,
            path=[("value_model_id", value_model_id)],
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def get_for_client(
        self,
        client_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ValueModel:
        """Read a client's active value model.

        Needs the `read` scope. Operation `getClientValueModel`.
        """
        return await self._transport.call(
            "getClientValueModel",
            ValueModel,
            path=[("client_id", client_id)],
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def create_for_client(
        self,
        client_id: str,
        body: ValueModelCreate,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
        idempotency_key: str | None = None,
    ) -> ValueModel:
        """Create a client's value model; see `Allisall.value_models.create_for_client`.

        Needs the `write` scope. Operation `createValueModel`.
        """
        return await self._transport.call(
            "createValueModel",
            ValueModel,
            path=[("client_id", client_id)],
            body=body,
            options=CallOptions(
                timeout=timeout,
                max_retries=max_retries,
                headers=headers,
                idempotency_key=idempotency_key,
            ),
        )

    async def update_for_client(
        self,
        client_id: str,
        patch: ValueModelPatch,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ValueModel:
        """Update a client's active value model with a merge patch; see
        `Allisall.value_models.update_for_client`. A key set to `None` clears the member.

        Needs the `write` scope. Operation `updateValueModel`.
        """
        return await self._transport.call(
            "updateValueModel",
            ValueModel,
            path=[("client_id", client_id)],
            body=patch,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def delete_for_client(
        self,
        client_id: str,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        """Delete a client's active value model; see
        `Allisall.value_models.delete_for_client`.

        Needs the `write` scope. Operation `deleteValueModel`.
        """
        await self._transport.call_empty(
            "deleteValueModel",
            path=[("client_id", client_id)],
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def set_line_items_for_client(
        self,
        client_id: str,
        body: ValueLineItemsSet,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ValueModel:
        """Replace the line items of a client's active value model; see
        `Allisall.value_models.set_line_items_for_client`.

        Never retried. After a connection error, read the value model again for its current
        `version` before trying again.

        Needs the `write` scope. Operation `setValueModelLineItems`.
        """
        return await self._transport.call(
            "setValueModelLineItems",
            ValueModel,
            path=[("client_id", client_id)],
            body=body,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def list_templates(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> AsyncPaginator[ValueTemplate, ValueTemplateList]:
        """List value templates.

        Await the result for the first page, or iterate it with `async for` for every
        template of every page. Nothing is sent until it is awaited or iterated.

        Needs the `read` scope. Operation `listValueTemplates`.
        """
        return self._transport.call_page(
            "listValueTemplates",
            ValueTemplateList,
            ValueTemplate,
            query={"limit": limit, "cursor": cursor},
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )
