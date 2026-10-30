"""Helpers the tests share: event builders, canned responses, and `Harness`."""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any

import httpx

from allisall import Allisall, AsyncAllisall, EventInput, IngestSummary

NOW = datetime(2026, 10, 28, 12, 0, 0, tzinfo=UTC)
TEST_KEY = "aia_testkey"

Handler = Callable[[httpx.Request], httpx.Response]

UUID4 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def assert_uuid4(value: object) -> None:
    """A UUID version 4, lowercase, in the 8-4-4-4-12 form."""
    assert isinstance(value, str)
    assert UUID4.match(value), value
    # The version nibble is 4, and the variant's top two bits are 10.
    assert value[14] == "4"
    assert int(value[19], 16) >> 2 == 0b10


def event(n: int = 0, **members: Any) -> EventInput:
    """A small valid event. Members passed in replace or add to the defaults."""
    base: dict[str, Any] = {
        "timestamp": "2026-10-28T12:00:00Z",
        "agent_key": "support-bot",
        "category": "task",
        "event_type": f"step_{n}",
    }
    base.update(members)
    return base  # type: ignore[return-value]


def sent_events(request: httpx.Request) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = json.loads(request.content)["events"]
    return events


def result(
    accepted: int,
    duplicates: int = 0,
    rejected: int = 0,
    errors: Sequence[dict[str, Any]] = (),
    truncated: bool = False,
    **extra: Any,
) -> httpx.Response:
    body = {
        "accepted": accepted,
        "duplicates": duplicates,
        "rejected": rejected,
        "errors": list(errors),
        "errors_truncated": truncated,
        **extra,
    }
    return httpx.Response(200, json=body)


def accept_all(request: httpx.Request) -> httpx.Response:
    return result(len(sent_events(request)))


def problem(status: int, code: str, *, headers: dict[str, str] | None = None) -> httpx.Response:
    body = {
        "type": f"https://api.allisai.ai/errors/{code}",
        "title": "A title",
        "status": status,
        "detail": f"detail for {code}",
        "code": code,
        "request_id": "req-from-problem",
    }
    return httpx.Response(
        status,
        content=json.dumps(body).encode(),
        headers={"Content-Type": "application/problem+json", **(headers or {})},
    )


class Harness:
    """A client of either kind on a mock transport, with a fake clock.

    `requests` records every request the transport received, and `sleeps` every wait.
    """

    def __init__(
        self,
        mode: str,
        handler: Handler = accept_all,
        *,
        random_value: float | None = 0.0,
        **options: Any,
    ) -> None:
        self.mode = mode
        self.requests: list[httpx.Request] = []
        self.sleeps: list[float] = []

        def record(request: httpx.Request) -> httpx.Response:
            # Read the body now: the test inspects it after the call.
            request.read()
            self.requests.append(request)
            return handler(request)

        transport = httpx.MockTransport(record)
        if "api_key" not in options and "token_provider" not in options:
            options["api_key"] = TEST_KEY
        self.client: Allisall | AsyncAllisall
        if mode == "sync":
            self.http: httpx.Client | httpx.AsyncClient = httpx.Client(transport=transport)
            self.client = Allisall(http_client=self.http, **options)
            self.client._transport.sleep = self.sleeps.append
        else:
            self.http = httpx.AsyncClient(transport=transport)
            self.client = AsyncAllisall(http_client=self.http, **options)

            async def sleep(seconds: float) -> None:
                self.sleeps.append(seconds)

            self.client._transport.sleep = sleep
        if random_value is not None:
            fixed = random_value
            self.client._transport.random = lambda: fixed
        self.client._transport.now = lambda: NOW

    def ingest(self, events: Sequence[EventInput]) -> IngestSummary:
        if isinstance(self.client, Allisall):
            return self.client.events.ingest(events)
        return asyncio.run(self.client.events.ingest(events))


def encoded_size(members: dict[str, Any]) -> int:
    """The event's size as compact UTF-8 JSON, computed without the SDK's encoder."""
    text = json.dumps(members, ensure_ascii=False, separators=(",", ":"))
    return len(text.encode("utf-8"))


def sized(n: int, size: int, pad_char: str = "x", prefix: str = "") -> EventInput:
    """An event of exactly `size` bytes as JSON, padded in `metadata.pad`.

    `event_id` is set so the SDK adds nothing, and `pad_char` is one UTF-8 byte unless
    `prefix` says otherwise.
    """
    members: dict[str, Any] = dict(event(n, event_id=f"id-{n:04d}", metadata={"pad": prefix}))
    fill = size - encoded_size(members)
    assert fill >= 0
    members["metadata"] = {"pad": prefix + pad_char * fill}
    assert encoded_size(members) == size
    return members  # type: ignore[return-value]
