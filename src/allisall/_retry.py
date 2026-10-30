"""The retry decision and the wait. No I/O: both clients share it."""

from __future__ import annotations

import math
import re
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime

RETRYABLE_STATUSES = frozenset({408, 429, 500, 502, 503, 504})
"""Statuses retried. Every other error status fails the same way when repeated."""

MAX_RETRY_AFTER = 60.0
"""The longest `Retry-After`, in seconds, the SDK waits. A longer one is not retried."""

_MAX_RETRY_AFTER_DIGITS = len(str(int(MAX_RETRY_AFTER)))

INITIAL_DELAY = 0.5
MAX_DELAY = 8.0
JITTER = 0.25

_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

# RFC 9110 §5.6.7's obsolete RFC 850 form, the one HTTP-date with a two-digit year.
_RFC850_DATE = re.compile(
    r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), "
    r"(\d{2})-([A-Z][a-z]{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2}) GMT",
    re.ASCII,
)


def parse_retry_after(value: str | None, now: datetime) -> float | None:
    """Return the wait `Retry-After` asks for, in seconds, or `None`.

    The value is delay-seconds or an HTTP-date. `None` means the header is absent, does not
    parse, or names a time in the past; the computed backoff then applies. Delay-seconds with
    more digits than the 60-second ceiling has are not converted: they return `math.inf`,
    which is over the ceiling, so the call ends with the error.
    """
    if value is None:
        return None
    text = value.strip()
    if text.isascii() and text.isdigit():
        digits = text.lstrip("0") or "0"
        if len(digits) > _MAX_RETRY_AFTER_DIGITS:
            return math.inf
        return float(int(digits))
    when = _parse_http_date(text, now)
    if when is None:
        return None
    seconds = (when - now).total_seconds()
    if seconds < 0:
        return None
    return seconds


def _parse_http_date(text: str, now: datetime) -> datetime | None:
    match = _RFC850_DATE.fullmatch(text)
    if match is not None:
        day, month, yy, hour, minute, second = match.groups()
        if month not in _MONTHS:
            return None
        # RFC 9110 §5.6.7: a two-digit year that appears to be more than 50 years in the
        # future is the most recent past year with the same last two digits.
        year = now.year // 100 * 100 + int(yy)
        if year > now.year + 50:
            year -= 100
        elif year <= now.year - 50:
            year += 100
        try:
            return datetime(
                year,
                _MONTHS.index(month) + 1,
                int(day),
                int(hour),
                int(minute),
                int(second),
                tzinfo=UTC,
            )
        except ValueError:
            return None
    try:
        when = parsedate_to_datetime(text)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
    if when.tzinfo is None:
        return None
    return when
    seconds = (when - now).total_seconds()
    if seconds < 0:
        return None
    return seconds


def backoff(retry: int, random_value: float) -> float:
    """Return the wait before retry `retry` (1 for the first) when there is no `Retry-After`.

    `min(0.5 s * 2^(retry-1), 8 s)`, multiplied by a factor between 0.75 and 1 drawn from
    `random_value`, which is in [0, 1).
    """
    delay = min(INITIAL_DELAY * 2.0 ** (retry - 1), MAX_DELAY)
    return delay * (1 - random_value * JITTER)


def is_retryable_status(status: int) -> bool:
    """Whether an error response with this status may be retried."""
    return status in RETRYABLE_STATUSES
