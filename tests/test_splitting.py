"""Splitting: 500 events or 5,000,000 bytes of body, whichever comes first."""

from __future__ import annotations

import json
from collections.abc import Callable

import pytest

from allisall import FieldErrorCode

from support import Harness, event, sent_events, sized

LIMIT = 5_000_000


def body_sizes(harness: Harness) -> list[int]:
    return [len(request.content) for request in harness.requests]


def batch_lengths(harness: Harness) -> list[int]:
    return [len(sent_events(request)) for request in harness.requests]


def test_500_events_make_one_batch(make: Callable[..., Harness]) -> None:
    harness = make()
    summary = harness.ingest([event(n) for n in range(500)])
    assert batch_lengths(harness) == [500]
    assert summary.batches == 1
    assert summary.accepted == 500


def test_501_events_make_500_then_1(make: Callable[..., Harness]) -> None:
    harness = make()
    summary = harness.ingest([event(n) for n in range(501)])
    assert batch_lengths(harness) == [500, 1]
    assert summary.batches == 2
    assert summary.accepted == 501
    # Input order is kept across the split.
    sent = [e["event_type"] for request in harness.requests for e in sent_events(request)]
    assert sent == [f"step_{n}" for n in range(501)]


# Two events whose batch is exactly the limit: 13 + s1 + 1 + s2 == 5,000,000.
FIRST = 2_500_000
SECOND_EXACT = LIMIT - 13 - 1 - FIRST


def test_a_batch_of_exactly_the_limit_is_one_batch(make: Callable[..., Harness]) -> None:
    harness = make()
    harness.ingest([sized(0, FIRST), sized(1, SECOND_EXACT)])
    assert batch_lengths(harness) == [2]
    assert body_sizes(harness) == [LIMIT]


def test_one_byte_more_splits_before_the_crossing_event(make: Callable[..., Harness]) -> None:
    harness = make()
    harness.ingest([sized(0, FIRST), sized(1, SECOND_EXACT + 1)])
    assert batch_lengths(harness) == [1, 1]
    assert body_sizes(harness) == [13 + FIRST, 13 + SECOND_EXACT + 1]
    assert [sent_events(r)[0]["event_id"] for r in harness.requests] == ["id-0000", "id-0001"]


def test_the_largest_single_event_is_sent_alone(make: Callable[..., Harness]) -> None:
    harness = make()
    summary = harness.ingest([sized(0, 4_999_987)])
    assert body_sizes(harness) == [LIMIT]
    assert summary.accepted == 1
    assert summary.errors == ()


def test_an_event_one_byte_larger_is_not_sent(make: Callable[..., Harness]) -> None:
    harness = make()
    summary = harness.ingest([sized(0, 4_999_988)])
    assert harness.requests == []
    assert summary.batches == 0
    assert (summary.accepted, summary.duplicates, summary.rejected) == (0, 0, 1)
    (row,) = summary.errors
    assert row.index == 0
    assert row.code == FieldErrorCode.TOO_LARGE
    assert row.pointer == "/events/0"
    assert "4999987" in row.detail


def test_sizes_are_utf8_bytes_not_characters(make: Callable[..., Harness]) -> None:
    # "é" is 2 bytes and the emoji 4, but each is one character. The second event is sized
    # so that in bytes the batch is one byte over the limit; counted in characters it would
    # be 4 under, and the two events would go in one batch.
    second = sized(1, SECOND_EXACT + 1, prefix="é\U0001f600")
    text = json.dumps(second, ensure_ascii=False, separators=(",", ":"))
    assert 13 + FIRST + 1 + len(text) == LIMIT - 3
    harness = make()
    harness.ingest([sized(0, FIRST), second])
    assert batch_lengths(harness) == [1, 1]
    assert json.loads(harness.requests[1].content)["events"][0]["metadata"]["pad"].startswith(
        "é\U0001f600"
    )


@pytest.mark.parametrize("count", [499, 500, 501, 1000, 1001])
def test_batch_boundaries(make: Callable[..., Harness], count: int) -> None:
    harness = make()
    harness.ingest([event(n) for n in range(count)])
    expected = [500] * (count // 500) + ([count % 500] if count % 500 else [])
    assert batch_lengths(harness) == expected
