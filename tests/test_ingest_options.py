"""Ingest's per-call options, the clients' `default_headers`, and the bound on a `cost`
exponent. With no option set, ingest sends what it always has."""

from __future__ import annotations

import re
import time
from collections.abc import Callable
from datetime import datetime
from decimal import Decimal
from typing import Any

import httpx
import pytest

from allisall import AllisallError, APIError, IngestError, _request

from support import TEST_KEY, Harness, accept_all, assert_uuid4, event, problem

OWNED = ["Authorization", "content-type", "IDEMPOTENCY-KEY", "X-Request-Id"]

# What ingest sent before it took options, recorded from that release for one event whose
# members the test sets: the method, the URL, the header names in order, and the body.
EXPECTED_HEADER_NAMES = [
    "Host",
    "Accept",
    "Accept-Encoding",
    "Connection",
    "Authorization",
    "Content-Type",
    "X-Request-Id",
    "User-Agent",
    "Content-Length",
]
EXPECTED_BODY = (
    b'{"events":[{"timestamp":"2026-10-28T12:00:00Z","agent_key":"support-bot",'
    b'"category":"task","event_type":"step_0","event_id":"e-1"}]}'
)


def test_ingest_with_no_option_sends_what_it_always_has(make: Callable[..., Harness]) -> None:
    harness = make()
    harness.ingest([event(0, event_id="e-1")])
    (request,) = harness.requests
    assert request.method == "POST"
    assert str(request.url) == "https://api.allisai.ai/v1/events"
    assert [name.decode() for name, _ in request.headers.raw] == EXPECTED_HEADER_NAMES
    assert request.headers["authorization"] == f"Bearer {TEST_KEY}"
    assert request.headers["content-type"] == "application/json"
    assert_uuid4(request.headers["x-request-id"])
    assert request.headers["user-agent"].startswith("allisall-python/")
    assert request.content == EXPECTED_BODY
    assert request.extensions["timeout"]["read"] == 60.0


def test_ingest_sends_the_call_s_headers_over_the_client_s(mode: str) -> None:
    harness = Harness(mode, accept_all, default_headers={"X-Team": "a", "X-Keep": "k"})
    harness.ingest([event(0)], headers={"x-team": "b"})
    harness.ingest([event(1)])
    first, second = harness.requests
    assert [v for k, v in first.headers.raw if k.lower() == b"x-team"] == [b"b"]
    assert first.headers["x-keep"] == "k"
    assert second.headers["x-team"] == "a"


def test_ingest_takes_a_call_s_max_retries_and_timeout(make: Callable[..., Harness]) -> None:
    harness = make(lambda r: httpx.Response(503))
    with pytest.raises(IngestError):
        harness.ingest([event(0)], max_retries=0, timeout=2.5)
    assert len(harness.requests) == 1
    assert harness.requests[0].extensions["timeout"]["read"] == 2.5


def test_a_call_s_options_apply_to_every_batch(make: Callable[..., Harness]) -> None:
    harness = make()
    harness.ingest([event(n) for n in range(501)], headers={"X-Job": "j"}, timeout=3.0)
    assert len(harness.requests) == 2
    assert all(r.headers["x-job"] == "j" for r in harness.requests)
    assert all(r.extensions["timeout"]["read"] == 3.0 for r in harness.requests)


@pytest.mark.parametrize("options", [{"timeout": 0}, {"max_retries": -1}])
def test_a_limit_the_client_would_refuse_is_refused_before_sending(
    make: Callable[..., Harness], options: dict[str, float]
) -> None:
    harness = make()
    with pytest.raises(AllisallError) as caught:
        harness.ingest([event(0)], **options)
    assert not isinstance(caught.value, IngestError)
    assert harness.requests == []


@pytest.mark.parametrize("name", OWNED)
def test_ingest_s_headers_may_not_set_a_header_the_sdk_owns(
    make: Callable[..., Harness], name: str
) -> None:
    harness = make()
    with pytest.raises(ValueError, match="the SDK sets it"):
        harness.ingest([event(0)], headers={name: "x"})
    assert harness.requests == []


def test_a_409_key_in_use_is_not_retried_on_ingest(make: Callable[..., Harness]) -> None:
    harness = make(lambda r: problem(409, "idempotency_key_in_use"))
    with pytest.raises(IngestError) as caught:
        harness.ingest([event(0)])
    assert isinstance(caught.value.__cause__, APIError)
    assert len(harness.requests) == 1


@pytest.mark.parametrize("cost", ["1E+401", "1E-401", "10E+400", "1E+999999999", "-1E-999999999"])
def test_a_cost_exponent_beyond_400_is_refused_before_sending(
    make: Callable[..., Harness], cost: str
) -> None:
    harness = make()
    started = time.monotonic()
    with pytest.raises(ValueError, match=r"^events\[1\]: cost is a Decimal whose exponent"):
        harness.ingest([event(0), event(1, cost=Decimal(cost))])
    assert time.monotonic() - started < 0.5
    assert harness.requests == []


@pytest.mark.parametrize(
    ("cost", "text"),
    [("1E+400", "1" + "0" * 400), ("1E-400", "0." + "0" * 399 + "1"), ("12.50", "12.50")],
)
def test_a_cost_exponent_within_400_is_written_in_full(
    make: Callable[..., Harness], cost: str, text: str
) -> None:
    harness = make()
    harness.ingest([event(0, cost=Decimal(cost))])
    assert f'"cost":{text}'.encode() in harness.requests[0].content


def test_the_ingest_url_is_built_once_per_call(
    make: Callable[..., Harness], monkeypatch: pytest.MonkeyPatch
) -> None:
    built: list[str] = []
    original = _request.join_url

    def counting(base: httpx.URL, path: str, query: Any = ()) -> httpx.URL:
        built.append(path)
        return original(base, path, query)

    monkeypatch.setattr(_request, "join_url", counting)
    harness = make(base_url="https://x.test/api?region=eu")
    harness.ingest([event(n) for n in range(1001)])
    assert built == ["/v1/events"]
    assert [str(r.url) for r in harness.requests] == ["https://x.test/api/v1/events?region=eu"] * 3


def test_a_naive_timestamp_keeps_its_message(make: Callable[..., Harness]) -> None:
    harness = make()
    message = "events[1]: timestamp is a naive datetime; give it a time zone, such as datetime.UTC"
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        harness.ingest([event(0), event(1, timestamp=datetime(2026, 1, 1))])
    assert harness.requests == []
