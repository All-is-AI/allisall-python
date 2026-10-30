"""The ingest helper's logic: ids, encoding, splitting and combining.

No I/O: `Allisall` and `AsyncAllisall` share every function here, and differ only in how
they send each batch.
"""

from __future__ import annotations

import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import cast

from ._types import EventInput, FieldErrorCode, IngestRowError, IngestSummary, field_error_code
from ._uuid import uuid4

BODY_LIMIT = 5_000_000
"""The largest request body `POST /v1/events` accepts, in bytes, inclusive."""

MAX_BATCH_EVENTS = 500
"""The most events one batch may hold."""

ENVELOPE_BYTES = len(b'{"events":[') + len(b"]}")
"""The bytes of `{"events":[` and `]}`: 13."""

MAX_EVENT_BYTES = BODY_LIMIT - ENVELOPE_BYTES
"""The largest single event that can be sent, in bytes of encoded JSON: 4,999,987."""

_NUMERIC_MEMBERS = ("quantity", "tokens_in", "tokens_out")


@dataclass(frozen=True)
class Batch:
    """One request body, and the position in the caller's list of each event it holds."""

    indices: tuple[int, ...]
    body: bytes


@dataclass(frozen=True)
class Plan:
    """Everything decided before the first request is sent."""

    events: list[EventInput]
    """A copy of each event, with its `event_id`, by position in the caller's list."""
    batches: list[Batch]
    too_large: list[IngestRowError]


@dataclass(frozen=True)
class BatchResult:
    """One batch's `IngestResult`, with its row errors already in the caller's positions."""

    accepted: int
    duplicates: int
    rejected: int
    errors: list[IngestRowError]
    errors_truncated: bool


def prepare(events: Sequence[EventInput]) -> Plan:
    """Copy each event, give it an `event_id` when it has none, encode it once, and split.

    Raises `ValueError` when any event cannot be encoded, before anything is sent.
    """
    copies: list[EventInput] = []
    encoded: list[bytes] = []
    for position, event in enumerate(events):
        # dict() of a mapping holds the same members; the copy is what is sent and kept.
        copy = cast(EventInput, dict(event))
        if copy.get("event_id") in (None, ""):
            copy["event_id"] = uuid4()
        try:
            encoded.append(encode_event(copy))
        except ValueError as err:
            raise ValueError(f"events[{position}]: {err}") from err
        copies.append(copy)
    batches, oversized = pack(encoded)
    too_large = [
        IngestRowError(
            index=position,
            code=FieldErrorCode.TOO_LARGE,
            pointer=f"/events/{position}",
            detail=(
                f"The event is {len(encoded[position])} bytes as JSON. The SDK sends an event "
                f"of at most {MAX_EVENT_BYTES} bytes, so that its batch fits the "
                f"{BODY_LIMIT}-byte request body limit. It was not sent."
            ),
        )
        for position in oversized
    ]
    return Plan(events=copies, batches=batches, too_large=too_large)


def pack(encoded: Sequence[bytes]) -> tuple[list[Batch], list[int]]:
    """Pack encoded events into batches, greedily and in input order.

    A batch is closed when it holds 500 events, or before an event that would take its body
    over 5,000,000 bytes. An event that cannot fit even alone goes in no batch; its position
    is returned in the second list.
    """
    batches: list[Batch] = []
    oversized: list[int] = []
    indices: list[int] = []
    parts: list[bytes] = []
    size = 0

    def close() -> None:
        batches.append(
            Batch(indices=tuple(indices), body=b'{"events":[' + b",".join(parts) + b"]}")
        )
        indices.clear()
        parts.clear()

    for position, event in enumerate(encoded):
        length = len(event)
        if length > MAX_EVENT_BYTES:
            oversized.append(position)
            continue
        if parts and (len(parts) == MAX_BATCH_EVENTS or size + 1 + length > BODY_LIMIT):
            close()
        size = ENVELOPE_BYTES + length if not parts else size + 1 + length
        indices.append(position)
        parts.append(event)
    if parts:
        close()
    return batches, oversized


def encode_event(event: EventInput) -> bytes:
    """Encode one event as compact JSON in UTF-8, writing every member it holds.

    Raises `ValueError` for a value that cannot be encoded: a naive `datetime`, a non-finite
    number, a `cost` that is not a `Decimal`, `int` or `float`, a value JSON cannot represent,
    or text that is not valid Unicode.
    """
    members: list[str] = []
    for name, value in event.items():
        if not isinstance(name, str):
            raise ValueError(f"member name {name!r} is not a string")
        members.append(_dumps(name, name) + ":" + _encode_member(name, value))
    text = "{" + ",".join(members) + "}"
    try:
        return text.encode("utf-8")
    except UnicodeEncodeError as err:
        raise ValueError(f"the event holds text that is not valid Unicode: {err}") from err


def _encode_member(name: str, value: object) -> str:
    if name == "timestamp" and isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError(
                "timestamp is a naive datetime; give it a time zone, such as datetime.UTC"
            )
        return _dumps(name, value.isoformat())
    if name == "cost":
        return _encode_cost(value)
    if name in _NUMERIC_MEMBERS and isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{name} is {value!r}; it must be a finite number")
    return _dumps(name, value)


def _encode_cost(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        raise ValueError("cost is a bool; pass a Decimal, an int or a float")
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError(f"cost is {value!r}; it must be a finite number")
        return format(value, "f")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"cost is {value!r}; it must be a finite number")
        return repr(value)
    raise ValueError(f"cost is a {type(value).__name__}; pass a Decimal, an int or a float")


def _dumps(name: str, value: object) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    except (TypeError, ValueError) as err:
        raise ValueError(f"{name} cannot be encoded as JSON: {err}") from err


def parse_ingest_result(data: object, batch: Batch) -> BatchResult:
    """Read one batch's `IngestResult`, rewriting each row error to the caller's positions.

    Members the SDK does not know are ignored. Raises `ValueError` when the shape is wrong.
    """
    if not isinstance(data, dict):
        raise ValueError("the body is not a JSON object")
    accepted = _count(data, "accepted")
    duplicates = _count(data, "duplicates")
    rejected = _count(data, "rejected")
    truncated = data.get("errors_truncated")
    if not isinstance(truncated, bool):
        raise ValueError("errors_truncated is not a boolean")
    raw_errors = data.get("errors")
    if not isinstance(raw_errors, list):
        raise ValueError("errors is not an array")
    errors = [_row_error(item, batch) for item in raw_errors]
    return BatchResult(accepted, duplicates, rejected, errors, truncated)


def _count(data: dict[str, object], name: str) -> int:
    value = data.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} is not a non-negative integer")
    return value


def _row_error(item: object, batch: Batch) -> IngestRowError:
    if not isinstance(item, dict):
        raise ValueError("an errors entry is not a JSON object")
    index = item.get("index")
    code = item.get("code")
    pointer = item.get("pointer")
    detail = item.get("detail")
    if isinstance(index, bool) or not isinstance(index, int):
        raise ValueError("an errors entry's index is not an integer")
    if not 0 <= index < len(batch.indices):
        raise ValueError(f"an errors entry's index {index} is outside its batch")
    if not isinstance(code, str) or not isinstance(pointer, str) or not isinstance(detail, str):
        raise ValueError("an errors entry's code, pointer or detail is not a string")
    position = batch.indices[index]
    return IngestRowError(
        index=position,
        code=field_error_code(code),
        pointer=_rewrite_pointer(pointer, index, position),
        detail=detail,
    )


def _rewrite_pointer(pointer: str, index: int, position: int) -> str:
    prefix = f"/events/{index}"
    if pointer == prefix or pointer.startswith(prefix + "/"):
        return f"/events/{position}" + pointer[len(prefix) :]
    return pointer


class Combiner:
    """Folds each batch's result into one `IngestSummary`."""

    def __init__(self, too_large: Sequence[IngestRowError]) -> None:
        self._accepted = 0
        self._duplicates = 0
        self._rejected = len(too_large)
        self._errors: list[IngestRowError] = list(too_large)
        self._truncated = False
        self._batches = 0

    def add(self, result: BatchResult) -> None:
        self._accepted += result.accepted
        self._duplicates += result.duplicates
        self._rejected += result.rejected
        self._errors.extend(result.errors)
        self._truncated = self._truncated or result.errors_truncated
        self._batches += 1

    def summary(self) -> IngestSummary:
        return IngestSummary(
            accepted=self._accepted,
            duplicates=self._duplicates,
            rejected=self._rejected,
            errors=tuple(sorted(self._errors, key=lambda error: error.index)),
            errors_truncated=self._truncated,
            batches=self._batches,
        )


def remaining(plan: Plan, failed: Batch) -> tuple[list[EventInput], int]:
    """The events from the failed batch onward, less any too large to send, and the
    position of the first of them in the caller's list."""
    start = failed.indices[0]
    skipped = {error.index for error in plan.too_large}
    events = [
        event
        for position, event in enumerate(plan.events)
        if position >= start and position not in skipped
    ]
    return events, start
