"""Retries: which outcomes are retried, how long the SDK waits, and what each attempt sends."""

from __future__ import annotations

import asyncio
import math
from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from email.utils import format_datetime

import httpx
import pytest

from allisall import APIError, IngestError
from allisall._retry import backoff, parse_retry_after

from support import NOW, Harness, accept_all, assert_uuid4, event, problem, sent_events

# Statuses with no problem document, as a proxy might send them, are retried the same way.
RETRIED = [408, 429, 500, 502, 503, 504]
NOT_RETRIED = [400, 401, 403, 413, 415, 501]


def then_succeed(
    failures: Iterator[Callable[[httpx.Request], httpx.Response]],
) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        failure = next(failures, None)
        return failure(request) if failure is not None else accept_all(request)

    return handler


def status(code: int, headers: dict[str, str] | None = None) -> Callable[..., httpx.Response]:
    return lambda request: httpx.Response(code, text="error", headers=headers or {})


@pytest.mark.parametrize("code", RETRIED)
def test_retried_statuses(make: Callable[..., Harness], code: int) -> None:
    harness = make(then_succeed(iter([status(code)])))
    summary = harness.ingest([event(0)])
    assert len(harness.requests) == 2
    assert summary.accepted == 1


@pytest.mark.parametrize(
    "error",
    [httpx.ConnectError, httpx.ReadError, httpx.RemoteProtocolError, httpx.ReadTimeout],
)
def test_no_response_is_retried(make: Callable[..., Harness], error: type[Exception]) -> None:
    def reset(request: httpx.Request) -> httpx.Response:
        raise error("connection reset by peer", request=request)

    harness = make(then_succeed(iter([reset])))
    summary = harness.ingest([event(0)])
    assert len(harness.requests) == 2
    assert summary.accepted == 1


@pytest.mark.parametrize("code", NOT_RETRIED)
def test_statuses_not_retried(make: Callable[..., Harness], code: int) -> None:
    harness = make(then_succeed(iter([status(code)])))
    with pytest.raises(IngestError) as caught:
        harness.ingest([event(0)])
    assert len(harness.requests) == 1
    assert harness.sleeps == []
    assert isinstance(caught.value.__cause__, APIError)
    assert caught.value.__cause__.status == code


def test_retry_after_seconds_is_waited(make: Callable[..., Harness]) -> None:
    harness = make(then_succeed(iter([status(429, {"Retry-After": "2"})])))
    harness.ingest([event(0)])
    assert harness.sleeps == [2.0]


def test_retry_after_date_waits_until_it(make: Callable[..., Harness]) -> None:
    when = format_datetime(NOW + timedelta(seconds=7), usegmt=True)
    harness = make(then_succeed(iter([status(503, {"Retry-After": when})])))
    harness.ingest([event(0)])
    assert harness.sleeps == [7.0]


def test_retry_after_of_60_is_waited(make: Callable[..., Harness]) -> None:
    harness = make(then_succeed(iter([status(429, {"Retry-After": "60"})])))
    harness.ingest([event(0)])
    assert harness.sleeps == [60.0]


def test_retry_after_over_60_is_not_retried(make: Callable[..., Harness]) -> None:
    harness = make(
        then_succeed(iter([lambda r: problem(429, "rate_limited", headers={"Retry-After": "61"})]))
    )
    with pytest.raises(IngestError) as caught:
        harness.ingest([event(0)])
    assert len(harness.requests) == 1
    assert harness.sleeps == []
    cause = caught.value.__cause__
    assert isinstance(cause, APIError)
    assert cause.retry_after == 61.0


@pytest.mark.parametrize(
    "value", ["soon", "-5", format_datetime(NOW - timedelta(seconds=30), usegmt=True)]
)
def test_unusable_retry_after_falls_back_on_backoff(
    make: Callable[..., Harness], value: str
) -> None:
    harness = make(then_succeed(iter([status(503, {"Retry-After": value})])))
    harness.ingest([event(0)])
    assert harness.sleeps == [0.5]


def test_backoff_bounds_with_extreme_random_values(mode: str) -> None:
    for random_value, expected in [(0.0, [0.5, 1.0]), (0.999999, [0.375, 0.75])]:
        harness = Harness(
            mode,
            then_succeed(iter([status(503), status(503)])),
            random_value=random_value,
        )
        harness.ingest([event(0)])
        assert harness.sleeps == pytest.approx(expected, abs=1e-5)


def test_backoff_with_the_real_random_source(mode: str) -> None:
    for _ in range(50):
        harness = Harness(mode, then_succeed(iter([status(503), status(503)])), random_value=None)
        harness.ingest([event(0)])
        first, second = harness.sleeps
        assert 0.375 <= first <= 0.5
        assert 0.75 <= second <= 1.0


def test_backoff_formula() -> None:
    assert backoff(1, 0.0) == 0.5
    assert backoff(2, 0.0) == 1.0
    assert backoff(5, 0.0) == 8.0
    assert backoff(6, 0.0) == 8.0
    assert backoff(1, 1.0) == 0.375


def test_retries_exhausted_after_two(make: Callable[..., Harness]) -> None:
    harness = make(status(503))
    with pytest.raises(IngestError):
        harness.ingest([event(0)])
    assert len(harness.requests) == 3
    assert len(harness.sleeps) == 2


def test_max_retries_zero_sends_one_attempt(make: Callable[..., Harness]) -> None:
    harness = make(status(503), max_retries=0)
    with pytest.raises(IngestError):
        harness.ingest([event(0)])
    assert len(harness.requests) == 1
    assert harness.sleeps == []


def test_max_retries_zero_does_not_retry_a_connection_failure(make: Callable[..., Harness]) -> None:
    def reset(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadError("reset", request=request)

    harness = make(reset, max_retries=0)
    with pytest.raises(IngestError):
        harness.ingest([event(0)])
    assert len(harness.requests) == 1


def test_provider_called_per_attempt_and_request_ids_differ(make: Callable[..., Harness]) -> None:
    tokens = iter(["aia_first", "aia_second", "aia_third"])
    calls: list[str] = []

    def provider() -> str:
        token = next(tokens)
        calls.append(token)
        return token

    harness = make(then_succeed(iter([status(503), status(503)])), token_provider=provider)
    harness.ingest([event(0)])
    assert calls == ["aia_first", "aia_second", "aia_third"]
    assert [r.headers["authorization"] for r in harness.requests] == [
        "Bearer aia_first",
        "Bearer aia_second",
        "Bearer aia_third",
    ]
    ids = [r.headers["x-request-id"] for r in harness.requests]
    assert len(set(ids)) == 3
    for request_id in ids:
        assert_uuid4(request_id)


def test_async_provider_may_return_an_awaitable() -> None:
    async def provider() -> str:
        return "aia_from_coroutine"

    harness = Harness("async", token_provider=provider)
    harness.ingest([event(0)])
    assert harness.requests[0].headers["authorization"] == "Bearer aia_from_coroutine"


class SecretStoreDownError(Exception):
    pass


def test_a_provider_error_fails_the_batch(make: Callable[..., Harness]) -> None:
    # The provider serves the first batch's one attempt, then fails before the second batch,
    # after the first is stored: the IngestError must keep that batch's summary and the ids.
    calls = 0
    failure = SecretStoreDownError("secret store unreachable")

    def provider() -> str:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise failure
        return "aia_from_provider"

    harness = make(token_provider=provider)
    with pytest.raises(IngestError) as caught:
        harness.ingest([event(n) for n in range(501)])
    error = caught.value

    assert calls == 2
    assert len(harness.requests) == 1
    assert error.__cause__ is failure
    assert error.summary.accepted == 500
    assert error.summary.batches == 1
    assert error.remaining_from == 500
    assert len(error.remaining) == 1
    (rest,) = error.remaining
    assert rest["event_type"] == "step_500"
    assert_uuid4(rest["event_id"])

    # Resending remaining sends the id the failed call generated.
    retry = Harness(harness.mode)
    retry.ingest(error.remaining)
    assert sent_events(retry.requests[0])[0]["event_id"] == rest["event_id"]


def test_a_cancelled_async_provider_is_not_wrapped() -> None:
    async def provider() -> str:
        raise asyncio.CancelledError

    harness = Harness("async", token_provider=provider)
    with pytest.raises(asyncio.CancelledError):
        harness.ingest([event(0)])
    assert harness.requests == []


def test_a_success_body_of_the_wrong_shape_is_not_retried(make: Callable[..., Harness]) -> None:
    harness = make(lambda request: httpx.Response(200, json={"accepted": "many"}))
    with pytest.raises(IngestError) as caught:
        harness.ingest([event(0)])
    assert len(harness.requests) == 1
    cause = caught.value.__cause__
    assert isinstance(cause, APIError)
    assert cause.status == 200
    assert cause.problem is None


def test_parse_retry_after() -> None:
    assert parse_retry_after(None, NOW) is None
    assert parse_retry_after("0", NOW) == 0.0
    assert parse_retry_after(" 3 ", NOW) == 3.0
    assert parse_retry_after("1.5", NOW) is None
    assert parse_retry_after(format_datetime(NOW + timedelta(seconds=90), usegmt=True), NOW) == 90
    assert parse_retry_after("060", NOW) == 60.0
    assert parse_retry_after("0000000000061", NOW) == 61.0
    assert parse_retry_after("100", NOW) == math.inf
    assert parse_retry_after("Sun Nov  6 08:49:37 1994", NOW) is None


@pytest.mark.parametrize("digits", [400, 5000])
def test_a_huge_retry_after_ends_the_call_with_the_api_error(
    make: Callable[..., Harness], digits: int
) -> None:
    value = "9" * digits
    harness = make(lambda r: problem(429, "rate_limited", headers={"Retry-After": value}))
    with pytest.raises(IngestError) as caught:
        harness.ingest([event(0)])
    assert len(harness.requests) == 1
    assert harness.sleeps == []
    cause = caught.value.__cause__
    assert isinstance(cause, APIError)
    assert cause.status == 429
    assert cause.code == "rate_limited"
    assert cause.problem is not None
    assert cause.headers["retry-after"] == value
    assert cause.retry_after == math.inf


def test_parse_two_digit_years() -> None:
    # NOW is 2026-10-28 12:00:00 UTC. RFC 9110: a two-digit year more than 50 years ahead is
    # the most recent past year with those digits, so 76 is 2076 and 77 is 1977.
    in_2076 = parse_retry_after("Wednesday, 28-Oct-76 12:00:05 GMT", NOW)
    expected = (datetime(2076, 10, 28, 12, 0, 5, tzinfo=UTC) - NOW).total_seconds()
    assert in_2076 == expected
    assert parse_retry_after("Thursday, 28-Oct-77 12:00:05 GMT", NOW) is None
    assert parse_retry_after("Wednesday, 28-Oct-26 12:00:07 GMT", NOW) == 7.0
    assert parse_retry_after("Wednesday, 28-Foo-26 12:00:07 GMT", NOW) is None
    assert parse_retry_after("Wednesday, 31-Feb-26 12:00:07 GMT", NOW) is None


def test_a_two_digit_year_far_ahead_ends_the_call(make: Callable[..., Harness]) -> None:
    value = "Wednesday, 28-Oct-76 12:00:05 GMT"
    harness = make(then_succeed(iter([status(503, {"Retry-After": value})])))
    with pytest.raises(IngestError) as caught:
        harness.ingest([event(0)])
    assert len(harness.requests) == 1
    assert harness.sleeps == []
    cause = caught.value.__cause__
    assert isinstance(cause, APIError)
    assert cause.status == 503
    assert cause.retry_after is not None
    assert cause.retry_after > 49 * 365 * 24 * 3600


def test_a_two_digit_year_in_reach_is_waited(make: Callable[..., Harness]) -> None:
    harness = make(
        then_succeed(iter([status(503, {"Retry-After": "Wednesday, 28-Oct-26 12:00:07 GMT"})]))
    )
    harness.ingest([event(0)])
    assert harness.sleeps == [7.0]
