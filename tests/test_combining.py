"""Combining each batch's result into one summary over the caller's whole list."""

from __future__ import annotations

from collections.abc import Callable

import httpx
import pytest

from allisall import APIError, FieldErrorCode, IngestError, IngestRowError

from support import Harness, event, result, sent_events, sized


def row(index: int, code: str, member: str = "timestamp") -> dict[str, object]:
    return {
        "index": index,
        "code": code,
        "pointer": f"/events/{index}/{member}",
        "detail": f"{member} is wrong",
    }


def test_row_errors_are_rewritten_by_the_batch_offset(make: Callable[..., Harness]) -> None:
    # Both batches report an error at their own index 3, so a rewrite that ignored the
    # offset would give two errors at index 3.
    def handler(request: httpx.Request) -> httpx.Response:
        count = len(sent_events(request))
        return result(count - 2, rejected=2, errors=[row(3, "invalid_format"), row(7, "required")])

    harness = make(handler)
    summary = harness.ingest([event(n) for n in range(600)])
    assert [len(sent_events(r)) for r in harness.requests] == [500, 100]
    assert summary.errors == (
        IngestRowError(
            3, FieldErrorCode.INVALID_FORMAT, "/events/3/timestamp", "timestamp is wrong"
        ),
        IngestRowError(7, FieldErrorCode.REQUIRED, "/events/7/timestamp", "timestamp is wrong"),
        IngestRowError(
            503, FieldErrorCode.INVALID_FORMAT, "/events/503/timestamp", "timestamp is wrong"
        ),
        IngestRowError(507, FieldErrorCode.REQUIRED, "/events/507/timestamp", "timestamp is wrong"),
    )


def test_counts_are_summed_and_truncation_is_any(make: Callable[..., Harness]) -> None:
    responses = iter(
        [
            result(490, duplicates=6, rejected=4, truncated=False),
            result(1, duplicates=2, rejected=1, truncated=True),
            result(5, duplicates=0, rejected=0, truncated=False),
        ]
    )
    harness = make(lambda request: next(responses))
    summary = harness.ingest([event(n) for n in range(1005)])
    assert (summary.accepted, summary.duplicates, summary.rejected) == (496, 8, 5)
    assert summary.errors_truncated is True
    assert summary.batches == 3


def test_rejected_rows_without_entries_are_accepted_when_truncated(
    make: Callable[..., Harness],
) -> None:
    # The API may omit every entry of a rejected row when the errors list's byte limit
    # leaves entries out; errors_truncated then says so.
    harness = make(lambda request: result(2, rejected=3, truncated=True))
    summary = harness.ingest([event(n) for n in range(5)])
    assert (summary.accepted, summary.duplicates, summary.rejected) == (2, 0, 3)
    assert summary.errors == ()
    assert summary.errors_truncated is True
    assert summary.batches == 1


def test_truncation_from_an_earlier_batch_survives_and_rejected_rows_sum(
    make: Callable[..., Harness],
) -> None:
    # The truncated batch comes first, so a summary that kept only the last batch's flag
    # would read False. The second batch is untruncated, so its one rejected row has its
    # entry, at the caller's index 500.
    responses = iter(
        [
            result(496, rejected=4, truncated=True),
            result(0, rejected=1, errors=[row(0, "required")], truncated=False),
        ]
    )
    harness = make(lambda request: next(responses))
    summary = harness.ingest([event(n) for n in range(501)])
    assert [len(sent_events(r)) for r in harness.requests] == [500, 1]
    assert (summary.accepted, summary.duplicates, summary.rejected) == (496, 0, 5)
    assert summary.errors == (
        IngestRowError(500, FieldErrorCode.REQUIRED, "/events/500/timestamp", "timestamp is wrong"),
    )
    assert summary.errors_truncated is True
    assert summary.batches == 2


def test_an_empty_list_sends_nothing(make: Callable[..., Harness]) -> None:
    harness = make()
    summary = harness.ingest([])
    assert harness.requests == []
    assert (summary.accepted, summary.duplicates, summary.rejected, summary.batches) == (0, 0, 0, 0)
    assert summary.errors == ()
    assert summary.errors_truncated is False


def test_an_event_too_large_between_others_keeps_positions(make: Callable[..., Harness]) -> None:
    # The oversized event is left out of the batch, so the batch's index 1 is the caller's 2.
    harness = make(lambda request: result(1, rejected=1, errors=[row(1, "required")]))
    summary = harness.ingest([event(0), sized(1, 3_999_988), event(2)])
    assert [e["event_type"] for e in sent_events(harness.requests[0])] == ["step_0", "step_2"]
    assert [(e.index, e.code, e.pointer) for e in summary.errors] == [
        (1, FieldErrorCode.TOO_LARGE, "/events/1"),
        (2, FieldErrorCode.REQUIRED, "/events/2/timestamp"),
    ]
    assert (summary.accepted, summary.rejected) == (1, 2)
    assert summary.accepted + summary.duplicates + summary.rejected == 3


@pytest.mark.parametrize("index", [2, -1])
def test_a_row_error_outside_its_batch_is_an_api_error(
    make: Callable[..., Harness], index: int
) -> None:
    # The batch holds two events, so no row can carry index 2 or -1. The SDK refuses the
    # body as one it cannot read, and does not retry it.
    harness = make(lambda request: result(1, rejected=1, errors=[row(index, "required")]))
    with pytest.raises(IngestError) as caught:
        harness.ingest([event(0), event(1)])
    assert len(harness.requests) == 1
    cause = caught.value.__cause__
    assert isinstance(cause, APIError)
    assert cause.status == 200
    assert cause.problem is None
    assert "outside its batch" in str(cause)
    assert caught.value.remaining_from == 0


def test_unknown_members_and_codes_are_tolerated(make: Callable[..., Harness]) -> None:
    unknown_row = {**row(0, "brand_new_code"), "hint": "new member"}
    harness = make(
        lambda request: result(0, rejected=1, errors=[unknown_row], warnings=["new member"])
    )
    summary = harness.ingest([event(0)])
    (error,) = summary.errors
    assert error.code == "brand_new_code"
    assert type(error.code) is str
    assert not isinstance(error.code, FieldErrorCode)
