"""The `events` group: ingest, and the event drill-down."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from typing import Literal, TypeAlias

from .._errors import IngestError
from .._generated.requests import EventSource
from .._generated.responses import (
    AttributedEvent,
    ClientEventList,
    EventArrivalList,
    EventList,
    EventSummary,
)
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

    def list(
        self,
        *,
        from_: InstantInput | None = None,
        to: InstantInput | None = None,
        as_of: InstantInput | None = None,
        client_id: str | None = None,
        agent_id: str | None = None,
        category: EventCategory | None = None,
        outcome_type: str | None = None,
        source: EventSource | None = None,
        import_batch_id: str | None = None,
        sort: EventSort | None = None,
        dir_: SortDirection | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        page: int | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Page[AttributedEvent, EventList]:
        """List the workspace's events whose `timestamp` falls in the period, newest first.

        Returns the first page; iterating it yields every event of every page from there.

        `from_` is sent as `from`, and `dir_` as `dir`. `from_` and `to` are required unless
        `import_batch_id` is sent, and then are both sent or neither; the API refuses a missing
        bound with `required`.

        The list is held still under an arrival limit, `as_of`, which the first response issues.
        A walk follows `next_cursor`, which carries it, so every page of one walk reads the same
        events while new ones arrive. To show numbered pages instead, send the first response's
        `as_of` with each later `page`. Filtered by `import_batch_id`, `as_of` is issued but not
        applied, because an import's events appear together when it commits. Otherwise an event
        appears a second or two after the API stores it, and later while a long request, such as
        a large import, is still in progress, so a read straight after an ingest may not include
        it yet.

        Pass `page` or `cursor`, not both. Pass `page` for a numbered page: the page's `body`
        then holds `page`, `total` and `total_capped`. `total` counts at most 10,000 events, and
        `total_capped` is `True` when more matched; filtered by `import_batch_id`, `total` is
        exact. Only that first page is counted; every later page of a walk continues by cursor
        from it, and its `page`, `total` and `total_capped` are `None`. To show another numbered
        page, call this method again with its `page` rather than `get_next_page()`.

        A `sort` and `dir_` other than `timestamp` descending need `page`, or the API refuses
        the call with `required` on `page`. A walk from a sorted page continues by offset and
        reads every earlier row for each page, so walk in the default order.

        Needs the `read` scope. Operation `listEvents`.
        """
        return self._transport.call_page(
            "listEvents",
            EventList,
            AttributedEvent,
            query={
                "from_": from_,
                "to": to,
                "as_of": as_of,
                "client_id": client_id,
                "agent_id": agent_id,
                "category": category,
                "outcome_type": outcome_type,
                "source": source,
                "import_batch_id": import_batch_id,
                "sort": sort,
                "dir_": dir_,
                "limit": limit,
                "cursor": cursor,
                "page": page,
            },
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def get_summary(
        self,
        *,
        from_: InstantInput,
        to: InstantInput,
        as_of: InstantInput | None = None,
        client_id: str | None = None,
        agent_id: str | None = None,
        category: EventCategory | None = None,
        outcome_type: str | None = None,
        source: EventSource | None = None,
        import_batch_id: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> EventSummary:
        """Count the events `list` holds under the same period, filters and `as_of`: in all, per
        day and per category.

        `from_` is sent as `from`. A day is 24 hours counted from `from_`, so local midnight
        with its offset as `from_` gives local days. The period is required, also with
        `import_batch_id`. Without `import_batch_id`, an event is counted a second or two after
        the API stores it, and later while a long request, such as a large import, is still in
        progress, so a read straight after an ingest may not count it yet.

        Needs the `read` scope. Operation `getEventSummary`.
        """
        return self._transport.call(
            "getEventSummary",
            EventSummary,
            query={
                "from_": from_,
                "to": to,
                "as_of": as_of,
                "client_id": client_id,
                "agent_id": agent_id,
                "category": category,
                "outcome_type": outcome_type,
                "source": source,
                "import_batch_id": import_batch_id,
            },
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def list_arrivals(
        self,
        *,
        since: InstantInput | None = None,
        as_of: InstantInput | None = None,
        from_: InstantInput | None = None,
        to: InstantInput | None = None,
        client_id: str | None = None,
        agent_id: str | None = None,
        category: EventCategory | None = None,
        outcome_type: str | None = None,
        source: EventSource | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Page[AttributedEvent, EventArrivalList]:
        """List the workspace's events in the order the API stored them, newest first, below an
        arrival limit, `as_of`, which the response issues.

        Returns the first page; iterating it yields every event of every page from there.

        `from_` is sent as `from`. `from_` and `to` filter by `timestamp`, and each is optional
        on its own.

        With `since`, the list holds the events that arrived at or after it, and `body.count`
        counts them. To poll, send each response's `as_of` as the next call's `since` and walk
        the result: consecutive windows meet without a gap or an overlap. To learn only how many
        arrived, pass `limit=1` and read `body.count`. The SDK does not poll on its own. `since`
        may be at most 24 hours back; a feed further behind reloads without it. An event falls
        below `as_of` a second or two after the API stores it, and later while a long request,
        such as a large import, is still in progress. A read straight after an ingest may not
        include it yet; poll with `since` until it does.

        Needs the `read` scope. Operation `listEventArrivals`.
        """
        return self._transport.call_page(
            "listEventArrivals",
            EventArrivalList,
            AttributedEvent,
            query={
                "since": since,
                "as_of": as_of,
                "from_": from_,
                "to": to,
                "client_id": client_id,
                "agent_id": agent_id,
                "category": category,
                "outcome_type": outcome_type,
                "source": source,
                "limit": limit,
                "cursor": cursor,
            },
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

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

    def list(
        self,
        *,
        from_: InstantInput | None = None,
        to: InstantInput | None = None,
        as_of: InstantInput | None = None,
        client_id: str | None = None,
        agent_id: str | None = None,
        category: EventCategory | None = None,
        outcome_type: str | None = None,
        source: EventSource | None = None,
        import_batch_id: str | None = None,
        sort: EventSort | None = None,
        dir_: SortDirection | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        page: int | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> AsyncPaginator[AttributedEvent, EventList]:
        """List the workspace's events whose `timestamp` falls in the period, newest first.

        Await the result for the first page, or iterate it with `async for` for every event of
        every page. Nothing is sent until it is awaited or iterated.

        `from_` is sent as `from`, and `dir_` as `dir`. `from_` and `to` are required unless
        `import_batch_id` is sent, and then are both sent or neither; the API refuses a missing
        bound with `required`.

        The list is held still under an arrival limit, `as_of`, which the first response issues.
        A walk follows `next_cursor`, which carries it, so every page of one walk reads the same
        events while new ones arrive. To show numbered pages instead, send the first response's
        `as_of` with each later `page`. Filtered by `import_batch_id`, `as_of` is issued but not
        applied, because an import's events appear together when it commits. Otherwise an event
        appears a second or two after the API stores it, and later while a long request, such as
        a large import, is still in progress, so a read straight after an ingest may not include
        it yet.

        Pass `page` or `cursor`, not both. Pass `page` for a numbered page: the page's `body`
        then holds `page`, `total` and `total_capped`. `total` counts at most 10,000 events, and
        `total_capped` is `True` when more matched; filtered by `import_batch_id`, `total` is
        exact. Only that first page is counted; every later page of a walk continues by cursor
        from it, and its `page`, `total` and `total_capped` are `None`. To show another numbered
        page, call this method again with its `page` rather than `get_next_page()`.

        A `sort` and `dir_` other than `timestamp` descending need `page`, or the API refuses
        the call with `required` on `page`. A walk from a sorted page continues by offset and
        reads every earlier row for each page, so walk in the default order.

        Needs the `read` scope. Operation `listEvents`.
        """
        return self._transport.call_page(
            "listEvents",
            EventList,
            AttributedEvent,
            query={
                "from_": from_,
                "to": to,
                "as_of": as_of,
                "client_id": client_id,
                "agent_id": agent_id,
                "category": category,
                "outcome_type": outcome_type,
                "source": source,
                "import_batch_id": import_batch_id,
                "sort": sort,
                "dir_": dir_,
                "limit": limit,
                "cursor": cursor,
                "page": page,
            },
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def get_summary(
        self,
        *,
        from_: InstantInput,
        to: InstantInput,
        as_of: InstantInput | None = None,
        client_id: str | None = None,
        agent_id: str | None = None,
        category: EventCategory | None = None,
        outcome_type: str | None = None,
        source: EventSource | None = None,
        import_batch_id: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> EventSummary:
        """Count the events `list` holds under the same period, filters and `as_of`: in all, per
        day and per category.

        `from_` is sent as `from`. A day is 24 hours counted from `from_`, so local midnight
        with its offset as `from_` gives local days. The period is required, also with
        `import_batch_id`. Without `import_batch_id`, an event is counted a second or two after
        the API stores it, and later while a long request, such as a large import, is still in
        progress, so a read straight after an ingest may not count it yet.

        Needs the `read` scope. Operation `getEventSummary`.
        """
        return await self._transport.call(
            "getEventSummary",
            EventSummary,
            query={
                "from_": from_,
                "to": to,
                "as_of": as_of,
                "client_id": client_id,
                "agent_id": agent_id,
                "category": category,
                "outcome_type": outcome_type,
                "source": source,
                "import_batch_id": import_batch_id,
            },
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def list_arrivals(
        self,
        *,
        since: InstantInput | None = None,
        as_of: InstantInput | None = None,
        from_: InstantInput | None = None,
        to: InstantInput | None = None,
        client_id: str | None = None,
        agent_id: str | None = None,
        category: EventCategory | None = None,
        outcome_type: str | None = None,
        source: EventSource | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> AsyncPaginator[AttributedEvent, EventArrivalList]:
        """List the workspace's events in the order the API stored them, newest first, below an
        arrival limit, `as_of`, which the response issues.

        Await the result for the first page, or iterate it with `async for` for every event of
        every page. Nothing is sent until it is awaited or iterated.

        `from_` is sent as `from`. `from_` and `to` filter by `timestamp`, and each is optional
        on its own.

        With `since`, the list holds the events that arrived at or after it, and `body.count`
        counts them. To poll, send each response's `as_of` as the next call's `since` and walk
        the result: consecutive windows meet without a gap or an overlap. To learn only how many
        arrived, pass `limit=1` and read `body.count`. The SDK does not poll on its own. `since`
        may be at most 24 hours back; a feed further behind reloads without it. An event falls
        below `as_of` a second or two after the API stores it, and later while a long request,
        such as a large import, is still in progress. A read straight after an ingest may not
        include it yet; poll with `since` until it does.

        Needs the `read` scope. Operation `listEventArrivals`.
        """
        return self._transport.call_page(
            "listEventArrivals",
            EventArrivalList,
            AttributedEvent,
            query={
                "since": since,
                "as_of": as_of,
                "from_": from_,
                "to": to,
                "client_id": client_id,
                "agent_id": agent_id,
                "category": category,
                "outcome_type": outcome_type,
                "source": source,
                "limit": limit,
                "cursor": cursor,
            },
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

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
