"""The options of one call: how they are checked, and how they combine with the client's.

No I/O: `Allisall` and `AsyncAllisall` share it.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass

from ._errors import AllisallError

OWNED_HEADERS = frozenset({"authorization", "content-type", "idempotency-key", "x-request-id"})
"""The headers the SDK sets itself, in lower case. Each has an option of its own, or is the
SDK's to set."""

# RFC 9110 §5.6.2: a field name is a token.
_TOKEN = re.compile(r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+")


def check_limits(timeout: float, max_retries: int) -> None:
    """Refuse a timeout that is not a finite, positive number of seconds, or a negative
    number of retries."""
    if not (math.isfinite(timeout) and timeout > 0):
        raise AllisallError(
            f"timeout must be a finite, positive number of seconds, not {timeout!r}"
        )
    if max_retries < 0:
        raise AllisallError(f"max_retries must not be negative, not {max_retries!r}")


def sendable_value(value: str) -> bool:
    """Whether `value` can be sent as a header value: ASCII with no control character but a
    horizontal tab, and no space or tab at either end. httpx refuses text outside ASCII with
    a `UnicodeEncodeError`, and h11 refuses the rest as a transport error, which would read as
    a connection failure and be retried."""
    if value != value.strip(" \t"):
        return False
    return all(char == "\t" or 0x20 <= ord(char) <= 0x7E for char in value)


def check_headers(headers: object, option: str) -> dict[str, str]:
    """Check caller headers and return a copy. `option` names the option, for the message.

    Raises `ValueError` when `headers` is not a mapping of `str` to `str`, or names a header
    the SDK sets, or holds a name or value that cannot be sent.
    """
    if headers is None:
        return {}
    if not isinstance(headers, Mapping):
        raise ValueError(
            f"{option} is a {type(headers).__name__}; pass a mapping of header names to values"
        )
    copy: dict[str, str] = {}
    for name, value in headers.items():
        if not isinstance(name, str):
            raise ValueError(f"{option} has a header name {name!r}, which is not a str")
        if name.lower() in OWNED_HEADERS:
            raise ValueError(f"{option} may not set {name}; the SDK sets it")
        if _TOKEN.fullmatch(name) is None:
            raise ValueError(f"{option} has the header name {name!r}, which cannot be sent")
        if not isinstance(value, str):
            raise ValueError(
                f"{option} sets {name} to a {type(value).__name__}; a header value is a str"
            )
        if not sendable_value(value):
            raise ValueError(
                f"{option} sets {name} to a value that cannot be sent: it must be ASCII, hold "
                "no control character but a tab, and not begin or end with a space or a tab"
            )
        merge_headers(copy, {name: value})
    return copy


def check_idempotency_key(key: object) -> str | None:
    """A caller's `Idempotency-Key`, checked only as far as it can be sent. Its syntax is the
    API's to judge.

    Raises `ValueError` when the key is not a `str`, or cannot be sent as a header value.
    """
    if key is None:
        return None
    if not isinstance(key, str):
        raise ValueError(f"idempotency_key is a {type(key).__name__}; pass a str")
    if not sendable_value(key):
        raise ValueError(
            "idempotency_key cannot be sent as a header value: it must be ASCII, hold no "
            "control character but a tab, and not begin or end with a space or a tab"
        )
    return key


def merge_headers(target: dict[str, str], extra: Mapping[str, str]) -> None:
    """Set each of `extra` in `target`, replacing a header of the same name in any letter
    case, so that one header is sent."""
    for name, value in extra.items():
        lower = name.lower()
        for existing in [key for key in target if key.lower() == lower]:
            del target[existing]
        target[name] = value


@dataclass(frozen=True)
class CallOptions:
    """The per-call options as the caller passed them. `None` keeps the client's."""

    timeout: float | None = None
    max_retries: int | None = None
    headers: Mapping[str, str] | None = None
    idempotency_key: str | None = None
    page_headers: Mapping[str, str] | None = None
    """One page's `headers`, from `get_next_page`, laid over `headers` for its request."""


@dataclass(frozen=True)
class Resolved:
    """A call's options, checked, over the client's."""

    timeout: float
    max_retries: int
    headers: dict[str, str]
    """The client's `default_headers`, then the call's `headers` over them, then a page's."""


def resolve(
    options: CallOptions,
    *,
    timeout: float,
    max_retries: int,
    default_headers: Mapping[str, str],
) -> Resolved:
    """Resolve a call's options over the client's.

    Each set of headers is checked here, once for the request. Raises `AllisallError` for a
    `timeout` or `max_retries` the client's constructor would refuse, and `ValueError` for
    headers `check_headers` refuses.
    """
    resolved_timeout = timeout if options.timeout is None else options.timeout
    resolved_retries = max_retries if options.max_retries is None else options.max_retries
    check_limits(resolved_timeout, resolved_retries)
    headers = dict(default_headers)
    merge_headers(headers, check_headers(options.headers, "headers"))
    merge_headers(headers, check_headers(options.page_headers, "headers"))
    return Resolved(timeout=resolved_timeout, max_retries=resolved_retries, headers=headers)


def overlay(call: CallOptions, override: CallOptions) -> CallOptions:
    """Lay one request's options over a call's. An option left at `None` keeps the call's;
    `headers` are kept apart as `page_headers`, which `resolve` checks and lays over the
    call's name by name. Nothing is checked here."""
    return CallOptions(
        timeout=call.timeout if override.timeout is None else override.timeout,
        max_retries=call.max_retries if override.max_retries is None else override.max_retries,
        headers=call.headers,
        idempotency_key=call.idempotency_key,
        page_headers=override.headers,
    )
