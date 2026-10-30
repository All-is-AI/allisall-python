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
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import TypeVar

import httpx

from ._errors import AllisallError, APIConnectionError, APIError
from ._retry import MAX_RETRY_AFTER, backoff, is_retryable_status, parse_retry_after
from ._types import FieldError, Problem, error_code, field_error_code
from ._uuid import uuid4
from ._version import __version__

T = TypeVar("T")

TokenProvider = Callable[[], str]
AsyncTokenProvider = Callable[[], str | Awaitable[str]]


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


def request_headers(token: str, request_id: str, agent: str) -> dict[str, str]:
    """The headers every attempt carries."""
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Request-Id": request_id,
        "User-Agent": agent,
    }


def utcnow() -> datetime:
    return datetime.now(UTC)


def read_success(response: httpx.Response, parse: Callable[[object], T]) -> T:
    """Parse a `2xx` body. A body that is not the expected shape is an `APIError`."""
    try:
        return parse(json.loads(response.content))
    except ValueError as err:
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
    error: APIError, attempt: int, max_retries: int, random_value: float
) -> float | None:
    """The wait before retrying after `error`, or `None` when it is not retried.

    `attempt` counts the retries already made.
    """
    if attempt >= max_retries or not is_retryable_status(error.status):
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
        self,
        *,
        http_client: httpx.Client,
        token: TokenProvider,
        timeout: float,
        max_retries: int,
    ) -> None:
        self._client = http_client
        self._token = token
        self._timeout = httpx.Timeout(timeout)
        self._max_retries = max_retries
        self._user_agent = user_agent()
        self.sleep: Callable[[float], None] = time.sleep
        self.random: Callable[[], float] = random.random
        self.now: Callable[[], datetime] = utcnow

    def post(self, url: httpx.URL, body: bytes, parse: Callable[[object], T]) -> T:
        attempt = 0
        while True:
            token = clean_token(self._token())
            request_id = uuid4()
            try:
                response = self._client.post(
                    url,
                    content=body,
                    headers=request_headers(token, request_id, self._user_agent),
                    timeout=self._timeout,
                    follow_redirects=False,
                )
            except httpx.RequestError as err:
                if isinstance(err, httpx.TransportError) and attempt < self._max_retries:
                    attempt += 1
                    self.sleep(backoff(attempt, self.random()))
                    continue
                raise connection_error(url, err, request_id) from err
            if response.is_success:
                return read_success(response, parse)
            error = api_error(response, self.now())
            wait = retry_wait(error, attempt, self._max_retries, self.random())
            if wait is None:
                raise error
            attempt += 1
            self.sleep(wait)


class AsyncTransport:
    """Sends a request from `AsyncAllisall`, retrying as the SDK's rules allow."""

    def __init__(
        self,
        *,
        http_client: httpx.AsyncClient,
        token: AsyncTokenProvider,
        timeout: float,
        max_retries: int,
    ) -> None:
        self._client = http_client
        self._token = token
        self._timeout = httpx.Timeout(timeout)
        self._max_retries = max_retries
        self._user_agent = user_agent()
        self.sleep: Callable[[float], Awaitable[None]] = asyncio.sleep
        self.random: Callable[[], float] = random.random
        self.now: Callable[[], datetime] = utcnow

    async def _resolve_token(self) -> str:
        token = self._token()
        if inspect.isawaitable(token):
            return await token
        return token

    async def post(self, url: httpx.URL, body: bytes, parse: Callable[[object], T]) -> T:
        attempt = 0
        while True:
            token = clean_token(await self._resolve_token())
            request_id = uuid4()
            try:
                response = await self._client.post(
                    url,
                    content=body,
                    headers=request_headers(token, request_id, self._user_agent),
                    timeout=self._timeout,
                    follow_redirects=False,
                )
            except httpx.RequestError as err:
                if isinstance(err, httpx.TransportError) and attempt < self._max_retries:
                    attempt += 1
                    await self.sleep(backoff(attempt, self.random()))
                    continue
                raise connection_error(url, err, request_id) from err
            if response.is_success:
                return read_success(response, parse)
            error = api_error(response, self.now())
            wait = retry_wait(error, attempt, self._max_retries, self.random())
            if wait is None:
                raise error
            attempt += 1
            await self.sleep(wait)
