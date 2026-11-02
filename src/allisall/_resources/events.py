"""The `events` group: ingest, and the event drill-down."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from typing import Literal, TypeAlias

from .._errors import IngestError
from .._generated.responses import AttributedEvent, ClientEventList
from .._ingest import Batch, BatchResult, Combiner, Plan, parse_ingest_result, prepare, remaining
from .._options import CallOptions
from .._pagination import AsyncPaginator, Page
from .._request import ingest_call, resolve_options
from .._transport import AsyncTransport, SyncTransport
from .._types import EventCategory, EventInput, IngestSummary, InstantInput
from ._query import SortDirection

EventSort: TypeAlias = Literal["timestamp", "cost", "agent_name", "attributed_by", "source"]
"""The sort keys of the event drill-down."""


def _batch_reader(batch: Batch) -> Callable[[bytes], BatchResult]:
    def read(content: bytes) -> BatchResult:
        return parse_ingest_result(json.loads(content), batch)

    return read


def _failed(plan: Plan, batch: Batch, combiner: Combiner, err: Exception) -> IngestError:
    rest, start = remaining(plan, batch)
    return IngestError(
        f"ingest stopped at the batch starting at events[{start}]: {err}",
        summary=combiner.summary(),
        remaining=rest,
        remaining_from=start,
    )


class EventsResource:
    """The `events` operations of `Allisall`."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def ingest(
        self,
        events: Sequence[EventInput],
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> IngestSummary:
        """Send any number of events, in as many batches as the API's limits require.

        Each event without an `event_id` is given a UUID version 4; the objects passed in are
        never modified. A batch holds at most 500 events and a 4,000,000-byte body. Batches are
        sent one at a time, each retried as `max_retries` allows. An event too large to send
        even alone is not sent, and is reported as a rejected row with the code `too_large`.

        `timeout`, `max_retries` and `headers` apply to every batch of this call; each left
        at `None` takes the client's. `headers` are sent over the client's
        `default_headers`, and may not name `Authorization`, `Content-Type`,
        `Idempotency-Key` or `X-Request-Id`.

        Raises `AllisallError`, before sending anything, for a `timeout` or `max_retries` the
        client would refuse. Raises `ValueError`, before sending anything, when `headers`
        cannot be sent or an event cannot be encoded, including a `cost` `Decimal` whose
        exponent's magnitude is over 400. Raises `IngestError` when a batch fails, including
        when the token provider raises for one of its attempts; the batches after it are not
        sent, and the error that failed the batch is its `__cause__`.
        """
        config = self._transport.config
        call = ingest_call(
            config,
            resolve_options(
                config, CallOptions(timeout=timeout, max_retries=max_retries, headers=headers)
            ),
        )
        plan = prepare(events)
        combiner = Combiner(plan.too_large)
        for batch in plan.batches:
            try:
                result = self._transport.send(
                    replace(call, content=batch.body), _batch_reader(batch)
                )
            except Exception as err:  # not BaseException: cancellation propagates unwrapped
                raise _failed(plan, batch, combiner, err) from err
            combiner.add(result)
        return combiner.summary()

    def list_for_client(
        self,
        client_id: str,
        /,
        *,
        from_: InstantInput,
        to: InstantInput,
        category: EventCategory | None = None,
        outcome_type: str | None = None,
        agent_id: str | None = None,
        sort: EventSort | None = None,
        dir_: SortDirection | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        page: int | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Page[AttributedEvent, ClientEventList]:
        """List the events behind a client's totals: the event drill-down, over the period
        `from_` to `to`.

        `from_` is sent as the query parameter `from`, and `dir_` as `dir`. Pass `page` or
        `cursor`, not both; neither means page 1. A `page` beyond the end returns no rows and
        the true `total`. Returns the first page, whose `body` holds `total` and `period`;
        iterating it yields every event of every page from there, continuing by cursor.

        Needs the `read` scope. Operation `listClientEvents`.
        """
        return self._transport.call_page(
            "listClientEvents",
            ClientEventList,
            AttributedEvent,
            path=[("client_id", client_id)],
            query={
                "from_": from_,
                "to": to,
                "category": category,
                "outcome_type": outcome_type,
                "agent_id": agent_id,
                "sort": sort,
                "dir_": dir_,
                "limit": limit,
                "cursor": cursor,
                "page": page,
            },
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )


class AsyncEventsResource:
    """The `events` operations of `AsyncAllisall`."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def ingest(
        self,
        events: Sequence[EventInput],
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> IngestSummary:
        """Send any number of events, in as many batches as the API's limits require.

        Behaves as `Allisall.events.ingest`. Cancelling the task cancels the call: the
        `asyncio.CancelledError` propagates unwrapped, from the transport or from the token
        provider, and the partial summary is lost.
        """
        config = self._transport.config
        call = ingest_call(
            config,
            resolve_options(
                config, CallOptions(timeout=timeout, max_retries=max_retries, headers=headers)
            ),
        )
        plan = prepare(events)
        combiner = Combiner(plan.too_large)
        for batch in plan.batches:
            try:
                result = await self._transport.send(
                    replace(call, content=batch.body), _batch_reader(batch)
                )
            except Exception as err:  # not BaseException: cancellation propagates unwrapped
                raise _failed(plan, batch, combiner, err) from err
            combiner.add(result)
        return combiner.summary()

    def list_for_client(
        self,
        client_id: str,
        /,
        *,
        from_: InstantInput,
        to: InstantInput,
        category: EventCategory | None = None,
        outcome_type: str | None = None,
        agent_id: str | None = None,
        sort: EventSort | None = None,
        dir_: SortDirection | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        page: int | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> AsyncPaginator[AttributedEvent, ClientEventList]:
        """List the events behind a client's totals; see `Allisall.events.list_for_client`.

        Await the result for the first page, or iterate it with `async for` for every event
        of every page. Nothing is sent until it is awaited or iterated.

        Needs the `read` scope. Operation `listClientEvents`.
        """
        return self._transport.call_page(
            "listClientEvents",
            ClientEventList,
            AttributedEvent,
            path=[("client_id", client_id)],
            query={
                "from_": from_,
                "to": to,
                "category": category,
                "outcome_type": outcome_type,
                "agent_id": agent_id,
                "sort": sort,
                "dir_": dir_,
                "limit": limit,
                "cursor": cursor,
                "page": page,
            },
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )
