"""`event_id`: generated when absent, kept when set, and identical across attempts."""

from __future__ import annotations

import copy
from collections.abc import Callable

import httpx
import pytest

from allisall import EventInput

from support import Harness, accept_all, assert_uuid4, event, problem, sent_events


@pytest.mark.parametrize("given", ["absent", None, ""])
def test_a_missing_id_is_a_uuid4(make: Callable[..., Harness], given: object) -> None:
    source = event(0) if given == "absent" else event(0, event_id=given)
    harness = make()
    harness.ingest([source])
    (sent,) = sent_events(harness.requests[0])
    assert_uuid4(sent["event_id"])


def test_each_event_gets_its_own_id(make: Callable[..., Harness]) -> None:
    harness = make()
    harness.ingest([event(n) for n in range(50)])
    ids = [e["event_id"] for e in sent_events(harness.requests[0])]
    assert len(set(ids)) == 50


def test_a_callers_id_is_kept_and_the_callers_objects_are_unchanged(
    make: Callable[..., Harness],
) -> None:
    events: list[EventInput] = [event(0, event_id="caller-chosen"), event(1), event(2, event_id="")]
    before = copy.deepcopy(events)
    harness = make()
    harness.ingest(events)
    sent = sent_events(harness.requests[0])
    assert sent[0]["event_id"] == "caller-chosen"
    assert_uuid4(sent[1]["event_id"])
    assert_uuid4(sent[2]["event_id"])
    assert events == before
    assert "event_id" not in events[1]


def test_every_attempt_sends_identical_bytes(make: Callable[..., Harness]) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return problem(503, "internal_error")
        return accept_all(request)

    harness = make(handler)
    harness.ingest([event(n) for n in range(3)])
    assert len(harness.requests) == 2
    assert harness.requests[0].content == harness.requests[1].content
    for e in sent_events(harness.requests[0]):
        assert_uuid4(e["event_id"])
