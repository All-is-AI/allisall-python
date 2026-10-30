"""A batch that fails stops the call with `IngestError`."""

from __future__ import annotations

import asyncio
import copy
from collections.abc import Callable

import httpx
import pytest

from allisall import (
    APIConnectionError,
    APIError,
    AsyncAllisall,
    ErrorCode,
    FieldErrorCode,
    IngestError,
)

from support import Harness, accept_all, event, problem, sent_events, sized


def fail_batch(
    number: int, response: Callable[[], httpx.Response]
) -> Callable[..., httpx.Response]:
    batches = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal batches
        batches += 1
        if batches == number:
            return response()
        return accept_all(request)

    return handler


def test_the_batches_after_a_failed_one_are_not_sent(make: Callable[..., Harness]) -> None:
    events = [event(n) for n in range(1001)]
    before = copy.deepcopy(events)
    harness = make(fail_batch(2, lambda: problem(401, "unauthenticated")))
    with pytest.raises(IngestError) as caught:
        harness.ingest(events)
    error = caught.value

    assert [len(sent_events(r)) for r in harness.requests] == [500, 500]
    assert error.summary.accepted == 500
    assert error.summary.batches == 1
    assert error.remaining_from == 500
    assert len(error.remaining) == 501

    sent_ids = [e["event_id"] for e in sent_events(harness.requests[1])]
    assert [e["event_id"] for e in error.remaining[:500]] == sent_ids
    assert [e["event_type"] for e in error.remaining] == [f"step_{n}" for n in range(500, 1001)]
    assert error.remaining[500]["event_id"]

    assert isinstance(error.__cause__, APIError)
    assert error.__cause__.status == 401
    assert error.__cause__.code == ErrorCode.UNAUTHENTICATED
    assert events == before


def test_resending_remaining_resumes_with_the_same_ids(make: Callable[..., Harness]) -> None:
    harness = make(fail_batch(1, lambda: problem(400, "invalid_json")))
    with pytest.raises(IngestError) as caught:
        harness.ingest([event(n) for n in range(3)])
    first_ids = [e["event_id"] for e in sent_events(harness.requests[0])]

    retry = make()
    retry.ingest(caught.value.remaining)
    assert [e["event_id"] for e in sent_events(retry.requests[0])] == first_ids


def test_events_too_large_are_in_the_summary_never_in_remaining(
    make: Callable[..., Harness],
) -> None:
    # Positions: 0..499 batch 1, 500 too large, 501..1000 batch 2 (fails), 1001 too large.
    events = [event(n) for n in range(1002)]
    events[500] = sized(500, 4_999_988)
    events[1001] = sized(1001, 4_999_988)
    harness = make(fail_batch(2, lambda: problem(403, "insufficient_scope")))
    with pytest.raises(IngestError) as caught:
        harness.ingest(events)
    error = caught.value
    assert error.summary.rejected == 2
    assert [(e.index, e.code) for e in error.summary.errors] == [
        (500, FieldErrorCode.TOO_LARGE),
        (1001, FieldErrorCode.TOO_LARGE),
    ]
    assert error.remaining_from == 501
    assert len(error.remaining) == 500
    assert all(e.get("metadata") is None for e in error.remaining)


def test_a_connection_failure_on_the_last_attempt(make: Callable[..., Harness]) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    harness = make(handler)
    with pytest.raises(IngestError) as caught:
        harness.ingest([event(0)])
    cause = caught.value.__cause__
    assert isinstance(cause, APIConnectionError)
    assert isinstance(cause.__cause__, httpx.ConnectError)
    assert len(harness.requests) == 3
    assert cause.request_id == harness.requests[-1].headers["x-request-id"]


def test_async_cancellation_propagates_unwrapped() -> None:
    harness = Harness("async", lambda request: problem(503, "internal_error"))
    assert isinstance(harness.client, AsyncAllisall)
    client = harness.client
    waiting = asyncio.Event()

    async def wait_forever(seconds: float) -> None:
        waiting.set()
        await asyncio.Event().wait()

    client._transport.sleep = wait_forever

    async def run() -> None:
        task = asyncio.create_task(client.events.ingest([event(0)]))
        await waiting.wait()
        task.cancel()
        await task

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(run())
    assert len(harness.requests) == 1
