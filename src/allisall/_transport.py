"""Sending one request, with its retries.

The functions at module level do no I/O and serve both clients. `SyncTransport` and
`AsyncTransport` differ only in how they send an attempt and how they wait.
"""

from __future__ import annotations

import asyncio
import inspect
import json
import platform
import random
import time
from collections.abc import Awaitable, Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import TypeVar

import httpx

from ._decode import ShapeError
from ._errors import AllisallError, APIConnectionError, APIError
from ._multipart import FilePart
from ._operations import OPERATIONS
from ._options import CallOptions, overlay
from ._pagination import (
    AsyncPage,
    AsyncPaginator,
    BodyT,
    ItemT,
    Page,
    Step,
)
from ._request import NO_BODY, Call, ClientConfig, attempt_headers, prepare, reader
from ._retry import MAX_RETRY_AFTER, backoff, is_retryable_status, parse_retry_after
from ._types import ErrorCode, FieldError, Problem, error_code, field_error_code
from ._uuid import uuid4
from ._version import __version__

T = TypeVar("T")

TokenProvider = Callable[[], str]
AsyncTokenProvider = Callable[[], str | Awaitable[str]]

NO_OPTIONS = CallOptions()
"""A call that sets no option of its own."""


def user_agent() -> str:
    """`allisall-python/<version> python/<version> httpx/<version>`."""
    python = platform.python_version()
    return f"allisall-python/{__version__} python/{python} httpx/{httpx.__version__}"


CREDENTIAL_CHARACTERS = "U+0021 to U+007E"
"""The characters a credential may hold: printable ASCII, without the space."""


def has_invalid_credential_character(value: str) -> bool:
    """Whether `value` holds a character outside U+0021 to U+007E.

    That refuses control characters, which would split or end a header, spaces, and any
    character outside ASCII.
    """
    return any(not 0x21 <= ord(char) <= 0x7E for char in value)


def clean_token(token: str) -> str:
    """Return a provider's token without leading and trailing whitespace, or refuse it.

    The trimmed token is the one sent. It is refused when it is empty, or holds a character
    outside U+0021 to U+007E. The check runs before the token is sent, and the message never
    contains the token or any part of it.
    """
    trimmed = token.strip()
    if not trimmed:
        raise AllisallError("the token provider returned an empty token")
    if has_invalid_credential_character(trimmed):
        raise AllisallError(
            "the token provider returned a token that contains a character outside "
            f"{CREDENTIAL_CHARACTERS}"
        )
    return trimmed


def utcnow() -> datetime:
    return datetime.now(UTC)


@contextmanager
def parts_of(call: Call) -> Iterator[list[tuple[str, FilePart]] | None]:
    """The multipart parts of one attempt, or `None` for a call without a form. A path is
    opened for the attempt and closed after it."""
    if call.upload is None:
        yield None
        return
    with call.upload.parts() as parts:
        yield parts


def ignore_body(operation_id: str) -> Callable[[bytes], None]:
    """How the `2xx` of an operation that answers with no body is read: not at all, whatever
    body it carries."""
    if OPERATIONS[operation_id].status != 204:
        raise TypeError(f"{operation_id} answers with a body")

    def read(content: bytes) -> None:
        return None

    return read


def read_success(response: httpx.Response, parse: Callable[[bytes], T]) -> T:
    """Read a `2xx` body. A body that is not the expected shape is an `APIError`, which is
    not retried."""
    try:
        return parse(response.content)
    except (ValueError, ShapeError) as err:
        raise APIError(
            f"{response.status_code}: the response body is not the expected shape: {err}",
            status=response.status_code,
            problem=None,
            request_id=response.headers.get("x-request-id"),
            retry_after=None,
            headers=response.headers,
        ) from err


def api_error(response: httpx.Response, now: datetime) -> APIError:
    """Build the `APIError` for an error response."""
    problem = parse_problem(response)
    status = response.status_code
    if problem is not None:
        message = f"{status} {problem.code}: {problem.detail}"
    else:
        message = f"{status} {response.reason_phrase}: the response is not a problem document"
    request_id = (
        problem.request_id
        if problem is not None and problem.request_id
        else response.headers.get("x-request-id")
    )
    return APIError(
        message,
        status=status,
        problem=problem,
        request_id=request_id,
        retry_after=parse_retry_after(response.headers.get("retry-after"), now),
        headers=response.headers,
    )


def parse_problem(response: httpx.Response) -> Problem | None:
    """Read an `application/problem+json` body, or return `None` when it is not one."""
    media_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
    if media_type != "application/problem+json":
        return None
    try:
        data = json.loads(response.content)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    # Each member of the wrong type is ignored on its own; the document is kept.
    strings: dict[str, str | None] = {}
    for name in ("type", "title", "detail", "code", "request_id"):
        value = data.get(name)
        strings[name] = value if isinstance(value, str) else None
    status = data.get("status")
    if isinstance(status, bool) or not isinstance(status, int):
        status = None
    raw_errors = data.get("errors")
    errors = (
        tuple(e for e in (_field_error(item) for item in raw_errors) if e is not None)
        if isinstance(raw_errors, list)
        else None
    )
    code = strings["code"]
    return Problem(
        type=strings["type"],
        title=strings["title"],
        status=status,
        detail=strings["detail"],
        code=error_code(code) if code is not None else None,
        request_id=strings["request_id"],
        errors=errors,
    )


def _field_error(item: object) -> FieldError | None:
    if not isinstance(item, dict):
        return None
    code = item.get("code")
    detail = item.get("detail")
    if not isinstance(code, str) or not isinstance(detail, str):
        return None
    locators: dict[str, str | None] = {}
    for name in ("pointer", "parameter", "header", "part", "column"):
        value = item.get(name)
        locators[name] = value if isinstance(value, str) else None
    return FieldError(code=field_error_code(code), detail=detail, **locators)


def retry_wait(
    error: APIError,
    attempt: int,
    max_retries: int,
    random_value: float,
    retry_key_in_use: bool,
) -> float | None:
    """The wait before retrying after `error`, or `None` when it is not retried.

    `attempt` counts the retries already made. With `retry_key_in_use`, a `409` whose code is
    `idempotency_key_in_use` is retried too: the first request with the same key is still
    running, and a later attempt can collect its outcome.
    """
    if attempt >= max_retries:
        return None
    key_in_use = (
        retry_key_in_use and error.status == 409 and error.code == ErrorCode.IDEMPOTENCY_KEY_IN_USE
    )
    if not (key_in_use or is_retryable_status(error.status)):
        return None
    if error.retry_after is not None:
        return None if error.retry_after > MAX_RETRY_AFTER else error.retry_after
    return backoff(attempt + 1, random_value)


def connection_error(
    url: httpx.URL, err: httpx.RequestError, request_id: str
) -> APIConnectionError:
    return APIConnectionError(
        f"no response from {url}: {type(err).__name__}: {err}", request_id=request_id
    )


class SyncTransport:
    """Sends a request from `Allisall`, retrying as the SDK's rules allow."""

    def __init__(
        self, *, http_client: httpx.Client, token: TokenProvider, config: ClientConfig
    ) -> None:
        self._client = http_client
        self._token = token
        self.config = config
        self.sleep: Callable[[float], None] = time.sleep
        self.random: Callable[[], float] = random.random
        self.now: Callable[[], datetime] = utcnow

    def send(self, call: Call, parse: Callable[[bytes], T]) -> T:
        """Send `call`, retrying as its eligibility and options allow, and read its `2xx`
        body with `parse`. An error from the token provider propagates unchanged."""
        attempt = 0
        while True:
            token = clean_token(self._token()) if call.bearer else None
            request_id = uuid4()
            headers = attempt_headers(call, token, request_id, self.config.user_agent)
            try:
                with parts_of(call) as files:
                    response = self._client.request(
                        call.method,
                        call.url,
                        content=call.content,
                        files=files,
                        headers=headers,
                        timeout=httpx.Timeout(call.timeout),
                        follow_redirects=False,
                    )
            except httpx.RequestError as err:
                if isinstance(err, httpx.TransportError) and attempt < call.max_retries:
                    attempt += 1
                    self.sleep(backoff(attempt, self.random()))
                    continue
                raise connection_error(call.url, err, request_id) from err
            if response.is_success:
                return read_success(response, parse)
            error = api_error(response, self.now())
            wait = retry_wait(
                error, attempt, call.max_retries, self.random(), call.retry_key_in_use
            )
            if wait is None:
                raise error
            attempt += 1
            self.sleep(wait)

    def call(
        self,
        operation_id: str,
        cls: type[T],
        *,
        path: Sequence[tuple[str, object]] = (),
        query: Mapping[str, object] | None = None,
        body: object = NO_BODY,
        options: CallOptions = NO_OPTIONS,
        check: Callable[[T], None] | None = None,
    ) -> T:
        """Call an operation and decode its answer into `cls`. `check` runs on the decoded
        answer, and a `ShapeError` it raises is an `APIError` with the answer's status."""
        call = prepare(
            self.config, operation_id, path=path, query=query, body=body, options=options
        )
        return self.send(call, reader(operation_id, cls, check))

    def call_empty(
        self,
        operation_id: str,
        *,
        path: Sequence[tuple[str, object]] = (),
        options: CallOptions = NO_OPTIONS,
    ) -> None:
        """Call an operation whose success has no body. Any `2xx` returns `None`."""
        reader_ = ignore_body(operation_id)
        call = prepare(self.config, operation_id, path=path, options=options)
        self.send(call, reader_)

    def call_page(
        self,
        operation_id: str,
        cls: type[BodyT],
        item: type[ItemT],
        *,
        path: Sequence[tuple[str, object]] = (),
        query: Mapping[str, object] | None = None,
        options: CallOptions = NO_OPTIONS,
    ) -> Page[ItemT, BodyT]:
        """Call a list operation and return its first page, from which the walk continues.
        `item` is the type of the items in `cls`'s `data`."""

        def load(step: Step, override: CallOptions | None) -> Page[ItemT, BodyT]:
            request_options = options if override is None else overlay(options, override)
            body = self.call(
                operation_id,
                cls,
                path=path,
                query=step.query,
                options=request_options,
                check=step.check,
            )
            following = step.following(body)
            if following is None:
                return Page(body, None)
            return Page(body, lambda next_options: load(following, next_options))

        return load(Step.start(query or {}), None)


class AsyncTransport:
    """Sends a request from `AsyncAllisall`, retrying as the SDK's rules allow."""

    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient,
        token: AsyncTokenProvider,
        config: ClientConfig,
    ) -> None:
        self._client = http_client
        self._token = token
        self.config = config
        self.sleep: Callable[[float], Awaitable[None]] = asyncio.sleep
        self.random: Callable[[], float] = random.random
        self.now: Callable[[], datetime] = utcnow

    async def _resolve_token(self) -> str:
        token = self._token()
        if inspect.isawaitable(token):
            return await token
        return token

    async def send(self, call: Call, parse: Callable[[bytes], T]) -> T:
        """As `SyncTransport.send`. Cancellation propagates unwrapped."""
        attempt = 0
        while True:
            token = clean_token(await self._resolve_token()) if call.bearer else None
            request_id = uuid4()
            headers = attempt_headers(call, token, request_id, self.config.user_agent)
            try:
                with parts_of(call) as files:
                    response = await self._client.request(
                        call.method,
                        call.url,
                        content=call.content,
                        files=files,
                        headers=headers,
                        timeout=httpx.Timeout(call.timeout),
                        follow_redirects=False,
                    )
            except httpx.RequestError as err:
                if isinstance(err, httpx.TransportError) and attempt < call.max_retries:
                    attempt += 1
                    await self.sleep(backoff(attempt, self.random()))
                    continue
                raise connection_error(call.url, err, request_id) from err
            if response.is_success:
                return read_success(response, parse)
            error = api_error(response, self.now())
            wait = retry_wait(
                error, attempt, call.max_retries, self.random(), call.retry_key_in_use
            )
            if wait is None:
                raise error
            attempt += 1
            await self.sleep(wait)

    async def call(
        self,
        operation_id: str,
        cls: type[T],
        *,
        path: Sequence[tuple[str, object]] = (),
        query: Mapping[str, object] | None = None,
        body: object = NO_BODY,
        options: CallOptions = NO_OPTIONS,
        check: Callable[[T], None] | None = None,
    ) -> T:
        """As `SyncTransport.call`."""
        call = prepare(
            self.config, operation_id, path=path, query=query, body=body, options=options
        )
        return await self.send(call, reader(operation_id, cls, check))

    async def call_empty(
        self,
        operation_id: str,
        *,
        path: Sequence[tuple[str, object]] = (),
        options: CallOptions = NO_OPTIONS,
    ) -> None:
        """As `SyncTransport.call_empty`."""
        reader_ = ignore_body(operation_id)
        call = prepare(self.config, operation_id, path=path, options=options)
        await self.send(call, reader_)

    def call_page(
        self,
        operation_id: str,
        cls: type[BodyT],
        item: type[ItemT],
        *,
        path: Sequence[tuple[str, object]] = (),
        query: Mapping[str, object] | None = None,
        options: CallOptions = NO_OPTIONS,
    ) -> AsyncPaginator[ItemT, BodyT]:
        """As `SyncTransport.call_page`, except that nothing is sent until the result is
        awaited or iterated."""

        async def load(step: Step, override: CallOptions | None) -> AsyncPage[ItemT, BodyT]:
            request_options = options if override is None else overlay(options, override)
            body = await self.call(
                operation_id,
                cls,
                path=path,
                query=step.query,
                options=request_options,
                check=step.check,
            )
            following = step.following(body)
            if following is None:
                return AsyncPage(body, None)
            return AsyncPage(body, lambda next_options: load(following, next_options))

        first = Step.start(query or {})
        return AsyncPaginator(lambda: load(first, None))
