"""One call, without I/O: its URL and query, its headers, its body encoded once, and how its
answer is read.

`Allisall` and `AsyncAllisall` build every call through these functions, and differ only in
how they send it and how they wait between attempts.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import TypeVar
from urllib.parse import quote

import httpx

from ._decode import ShapeError, decode
from ._encode import aware_isoformat, encode_body
from ._multipart import Upload, upload_of
from ._operations import OPERATIONS, Operation, is_eligible
from ._options import CallOptions, Resolved, check_idempotency_key, merge_headers, resolve
from ._uuid import uuid4

T = TypeVar("T")

INGEST = "ingestEvents"

CONTENT_TYPES = {"json": "application/json", "merge-patch": "application/merge-patch+json"}

QUERY_WIRE_NAMES = {"from_": "from", "dir_": "dir"}
"""The keyword arguments whose wire name is not a Python name: `from` is a keyword, and `dir`
a built-in."""

_PATH_PARAMETER = re.compile(r"\{([^{}]+)\}")


class _NoBody:
    """The body of a call to an operation that takes none."""


NO_BODY = _NoBody()


@dataclass(frozen=True)
class ClientConfig:
    """What every call of one client shares, fixed at construction."""

    base_url: httpx.URL
    timeout: float
    max_retries: int
    default_headers: Mapping[str, str]
    """Already checked."""
    user_agent: str


@dataclass(frozen=True)
class Call:
    """One request, fixed before the first attempt and sent unchanged on each."""

    method: str
    url: httpx.URL
    bearer: bool
    """Whether each attempt sends `Bearer` and the client's credential."""
    content: bytes | None
    """A JSON or merge-patch body, encoded once."""
    content_type: str | None
    upload: Upload | None
    """A multipart body, whose parts are fixed once."""
    idempotency_key: str | None
    """Sent on every attempt."""
    headers: Mapping[str, str]
    """The client's `default_headers` and the call's `headers`, over the SDK's own."""
    timeout: float
    max_retries: int
    """The retries this call may make: `0` when its request is not eligible."""
    retry_key_in_use: bool
    """Whether a `409` `idempotency_key_in_use` is retried: the request carries a reused key."""


def join_url(base: httpx.URL, path: str, query: Sequence[tuple[str, str]] = ()) -> httpx.URL:
    """Join the base URL and an operation's path with exactly one `/`, then the query.

    The base URL's own path and query survive, and the call's query parameters follow the
    base URL's: `https://example.test/api?region=eu` sends ingest to
    `https://example.test/api/v1/events?region=eu`. `path` is already percent-encoded.
    """
    raw_path, _, base_query = base.raw_path.partition(b"?")
    joined = raw_path.rstrip(b"/") + path.encode("ascii")
    parameters = [base_query] if base_query else []
    parameters.extend(
        f"{quote(name, safe='')}={quote(value, safe='')}".encode("ascii") for name, value in query
    )
    if parameters:
        joined += b"?" + b"&".join(parameters)
    return base.copy_with(raw_path=joined, fragment=None)


def fill_path(template: str, values: Sequence[tuple[str, object]]) -> str:
    """Fill a path template's parameters, in order, each percent-encoded as one segment.

    Each value comes with the name to give it in a message. Raises `ValueError` for a value
    that is not a `str`, or is `""`, `.` or `..`: an empty segment names another path, and a
    URL resolves `.` and `..` as steps through the path, even percent-encoded.
    """
    names = _PATH_PARAMETER.findall(template)
    if len(names) != len(values):
        raise TypeError(f"{template} takes {len(names)} path parameters, not {len(values)}")
    remaining = iter(values)

    def segment(match: re.Match[str]) -> str:
        name, value = next(remaining)
        if not isinstance(value, str):
            raise ValueError(f"{name} is a {type(value).__name__}; pass a str")
        if value in ("", ".", ".."):
            raise ValueError(f"{name} is {value!r}, which cannot be sent as a path segment")
        try:
            return quote(value, safe="")
        except UnicodeEncodeError as err:
            raise ValueError(f"{name} holds text that is not valid Unicode: {err}") from err

    return _PATH_PARAMETER.sub(segment, template)


def query_of(params: Mapping[str, object]) -> list[tuple[str, str]]:
    """The query, from keyword arguments in the method's order, by their wire names.

    A value of `None` is not sent. A `str` is sent as it is, an `int` as its decimal text, and
    an aware `datetime` with `isoformat()`. Raises `ValueError` naming the parameter for any
    other value, a naive `datetime`, a `bool`, a `list` and a `dict` among them.
    """
    query: list[tuple[str, str]] = []
    for name, value in params.items():
        if value is None:
            continue
        query.append((QUERY_WIRE_NAMES.get(name, name), _query_text(name, value)))
    return query


def _query_text(name: str, value: object) -> str:
    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as err:
            raise ValueError(f"{name} holds text that is not valid Unicode: {err}") from err
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, datetime):
        return aware_isoformat(value, name)
    raise ValueError(f"{name} is a {type(value).__name__}; pass a str, an int or a datetime")


def prepare(
    config: ClientConfig,
    operation_id: str,
    *,
    path: Sequence[tuple[str, object]] = (),
    query: Mapping[str, object] | None = None,
    body: object = NO_BODY,
    options: CallOptions,
) -> Call:
    """Fix everything one call sends before its first attempt: its URL, its body's bytes or
    parts, its `Idempotency-Key`, and its options over the client's.

    Raises `AllisallError` for a `timeout` or `max_retries` the client's constructor would
    refuse, and `ValueError` for a value that cannot be sent.
    """
    operation = OPERATIONS[operation_id]
    resolved = resolve_options(config, options)
    if options.idempotency_key is not None and not operation.idempotent:
        raise TypeError(f"{operation_id} takes no idempotency key")
    key = check_idempotency_key(options.idempotency_key)
    url = join_url(config.base_url, fill_path(operation.path, path), query_of(query or {}))
    content, content_type, upload = _encode(operation_id, operation, body)
    return Call(
        method=operation.method,
        url=url,
        bearer=operation.access != "Public",
        content=content,
        content_type=content_type,
        upload=upload,
        # One key per call, the same on every attempt.
        idempotency_key=(uuid4() if key is None else key) if operation.idempotent else None,
        headers=resolved.headers,
        timeout=resolved.timeout,
        max_retries=resolved.max_retries if is_eligible(operation_id, operation) else 0,
        retry_key_in_use=operation.idempotent,
    )


def resolve_options(config: ClientConfig, options: CallOptions) -> Resolved:
    """A call's options over the client's; see `resolve`."""
    return resolve(
        options,
        timeout=config.timeout,
        max_retries=config.max_retries,
        default_headers=config.default_headers,
    )


def ingest_call(config: ClientConfig, options: Resolved) -> Call:
    """An ingest call with its URL and options fixed once, for every batch of one `ingest`.
    Each batch is sent as `dataclasses.replace(call, content=batch)`, the batch already
    encoded by the ingest helper."""
    operation = OPERATIONS[INGEST]
    return Call(
        method=operation.method,
        url=join_url(config.base_url, operation.path),
        bearer=True,
        content=b"",
        content_type=CONTENT_TYPES["json"],
        upload=None,
        idempotency_key=None,
        headers=options.headers,
        timeout=options.timeout,
        max_retries=options.max_retries if is_eligible(INGEST, operation) else 0,
        retry_key_in_use=False,
    )


def _encode(
    operation_id: str, operation: Operation, body: object
) -> tuple[bytes | None, str | None, Upload | None]:
    if operation.body == "none":
        if body is not NO_BODY:
            raise TypeError(f"{operation_id} takes no request body")
        return None, None, None
    if body is NO_BODY:
        raise TypeError(f"{operation_id} takes a request body")
    if operation.body == "multipart":
        # httpx writes the form's boundary, and the Content-Type that carries it.
        return None, None, upload_of(body)
    return encode_body(body), CONTENT_TYPES[operation.body], None


def attempt_headers(
    call: Call, token: str | None, request_id: str, user_agent: str
) -> dict[str, str]:
    """The headers of one attempt: the SDK's, then the call's over them, in any letter case."""
    headers: dict[str, str] = {}
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if call.content_type is not None:
        headers["Content-Type"] = call.content_type
    headers["X-Request-Id"] = request_id
    headers["User-Agent"] = user_agent
    if call.idempotency_key is not None:
        headers["Idempotency-Key"] = call.idempotency_key
    merge_headers(headers, call.headers)
    return headers


def reader(
    operation_id: str, cls: type[T], check: Callable[[T], None] | None = None
) -> Callable[[bytes], T]:
    """How a `2xx` body of the operation is read: decoded into `cls`. For a list, the
    envelope is checked too, and then `check`, such as the walk's cursor rule. Raises
    `ShapeError` when the body is not the expected shape."""
    operation = OPERATIONS[operation_id]
    if operation.status == 204:
        raise TypeError(f"{operation_id} answers with no body")

    def read(content: bytes) -> T:
        value = decode(cls, content)
        if operation.list_kind is not None:
            check_envelope(value)
        if check is not None:
            check(value)
        return value

    return read


def check_envelope(body: object) -> None:
    """Check a list's envelope: a boolean `has_more`, and a `next_cursor` that is a string or
    `None`, and a non-empty string when `has_more` is true."""
    has_more = getattr(body, "has_more", None)
    next_cursor = getattr(body, "next_cursor", None)
    if not isinstance(has_more, bool):
        raise ShapeError("/has_more", "expected a boolean")
    if next_cursor is not None and not isinstance(next_cursor, str):
        raise ShapeError("/next_cursor", "expected a string or null")
    if has_more and not next_cursor:
        raise ShapeError("/next_cursor", "has_more is true, but no next_cursor names the next page")
