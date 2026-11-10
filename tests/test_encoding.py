"""Encoding: what each value is written as, and what is refused before anything is sent."""

from __future__ import annotations

import asyncio
import math
from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest

from support import Harness, event, json_response


def sent_text(harness: Harness, **members: Any) -> str:
    harness.ingest([event(0, event_id="fixed", **members)])
    return harness.requests[0].content.decode("utf-8")


@pytest.mark.parametrize(
    ("cost", "written"),
    [
        (Decimal("1E+2"), '"cost":100'),
        (Decimal("0.3683"), '"cost":0.3683'),
        (Decimal("-1.500000"), '"cost":-1.500000'),
        (Decimal("1E-6"), '"cost":0.000001'),
        (0.3683, '"cost":0.3683'),
        (12, '"cost":12'),
        (None, '"cost":null'),
    ],
)
def test_cost_is_written_without_a_binary_float(
    make: Callable[..., Harness], cost: object, written: str
) -> None:
    assert written in sent_text(make(), cost=cost)


@pytest.mark.parametrize(
    "cost", [Decimal("NaN"), Decimal("Infinity"), math.nan, math.inf, True, "0.5"]
)
def test_unusable_cost_is_refused_before_sending(
    make: Callable[..., Harness], cost: object
) -> None:
    harness = make()
    with pytest.raises(ValueError, match="cost"):
        harness.ingest([event(0, cost=cost)])
    assert harness.requests == []


@pytest.mark.parametrize("member", ["quantity", "tokens_in", "tokens_out"])
@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf])
def test_non_finite_numbers_are_refused(
    make: Callable[..., Harness], member: str, value: float
) -> None:
    harness = make()
    with pytest.raises(ValueError, match=member):
        harness.ingest([event(0, **{member: value})])
    assert harness.requests == []


def test_a_non_finite_metadata_number_is_refused(make: Callable[..., Harness]) -> None:
    harness = make()
    with pytest.raises(ValueError, match="metadata"):
        harness.ingest([event(0, metadata={"score": math.nan})])
    assert harness.requests == []


def test_a_naive_datetime_is_refused(make: Callable[..., Harness]) -> None:
    harness = make()
    with pytest.raises(ValueError, match="naive"):
        harness.ingest([event(0, timestamp=datetime(2026, 10, 28, 12, 0))])
    assert harness.requests == []


def test_an_aware_datetime_keeps_its_offset(make: Callable[..., Harness]) -> None:
    tokyo = timezone(timedelta(hours=9))
    text = sent_text(make(), timestamp=datetime(2026, 10, 28, 21, 0, 0, 500000, tzinfo=tokyo))
    assert '"timestamp":"2026-10-28T21:00:00.500000+09:00"' in text
    text = sent_text(make(), timestamp=datetime(2026, 10, 28, 12, 0, tzinfo=UTC))
    assert '"timestamp":"2026-10-28T12:00:00+00:00"' in text


def test_a_timestamp_string_is_sent_unchanged(make: Callable[..., Harness]) -> None:
    assert '"timestamp":"not a time"' in sent_text(make(), timestamp="not a time")


def test_text_that_is_not_valid_unicode_is_refused(make: Callable[..., Harness]) -> None:
    harness = make()
    with pytest.raises(ValueError, match="Unicode"):
        harness.ingest([event(0, agent_key="bot\ud800")])
    assert harness.requests == []


def test_a_value_json_cannot_hold_is_refused(make: Callable[..., Harness]) -> None:
    harness = make()
    with pytest.raises(ValueError, match="metadata"):
        harness.ingest([event(0, metadata={"when": datetime(2026, 1, 1, tzinfo=UTC)})])
    assert harness.requests == []


def test_a_bad_event_anywhere_stops_the_whole_call(make: Callable[..., Harness]) -> None:
    events = [event(n) for n in range(600)]
    events[599] = event(599, quantity=math.nan)
    harness = make()
    with pytest.raises(ValueError, match=r"events\[599\]"):
        harness.ingest(events)
    assert harness.requests == []


def test_every_member_is_sent_including_unknown_ones(make: Callable[..., Harness]) -> None:
    text = sent_text(make(), costs=3, model=None, metadata={"é": "ü"})
    assert '"costs":3' in text
    assert '"model":null' in text
    assert '"metadata":{"é":"ü"}' in text


def test_the_body_is_compact_json(make: Callable[..., Harness]) -> None:
    harness = make()
    harness.ingest([event(0, event_id="a"), event(1, event_id="b")])
    body = harness.requests[0].content
    assert body.startswith(b'{"events":[{"timestamp":')
    assert b", " not in body
    assert b": " not in body
    assert body.endswith(b'"event_id":"b"}]}')


# --- A repeatable query parameter, and a date ---


def list_renewals(harness: Harness, **keywords: Any) -> None:
    """`dashboard.list_renewals` with `keywords`, run to its first page on either client."""
    call = harness.client.dashboard.list_renewals
    if harness.mode == "sync":
        call(**keywords)
        return

    async def first() -> object:
        return await call(**keywords)

    asyncio.run(first())


def renewals_query(make: Callable[..., Harness], **keywords: Any) -> list[tuple[str, str]]:
    """The query `dashboard.list_renewals` sends with `keywords`, on either client."""
    body = {"today": "2026-11-08", "page": None, "total": None, "data": []}
    harness = make(lambda request: json_response({**body, "has_more": False, "next_cursor": None}))
    list_renewals(harness, **keywords)
    (request,) = harness.requests
    return request.url.params.multi_items()


def test_a_repeatable_parameter_is_sent_once_per_item_in_order(
    make: Callable[..., Harness],
) -> None:
    # Two different items, so a writer that sent only the first, or joined them, fails.
    assert renewals_query(make, renewal_term=["annual", "none"]) == [
        ("renewal_term", "annual"),
        ("renewal_term", "none"),
    ]
    assert renewals_query(make, renewal_term=("none", "monthly")) == [
        ("renewal_term", "none"),
        ("renewal_term", "monthly"),
    ]


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ([], "renewal_term is empty"),
        ((), "renewal_term is empty"),
        ("annual", "renewal_term is a str"),
        ({"annual"}, "renewal_term is a set"),
    ],
)
def test_a_repeatable_parameter_refuses_an_empty_or_non_sequence_value_before_sending(
    make: Callable[..., Harness], value: object, message: str
) -> None:
    harness = make()
    with pytest.raises(ValueError, match=message):
        list_renewals(harness, renewal_term=value)
    assert harness.requests == []


def test_a_list_at_a_parameter_that_is_not_repeatable_is_still_refused(
    make: Callable[..., Harness],
) -> None:
    harness = make()
    with pytest.raises(ValueError, match="window is a list"):
        list_renewals(harness, window=["overdue"])
    assert harness.requests == []


def test_a_date_is_sent_as_its_calendar_date(make: Callable[..., Harness]) -> None:
    assert renewals_query(make, today=date(2026, 11, 8)) == [("today", "2026-11-08")]
