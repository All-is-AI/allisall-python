"""`Allisall` and `AsyncAllisall`: options, credential and base URL resolution, and ingest."""

from __future__ import annotations

import math
import os
from collections.abc import Awaitable, Callable, Sequence
from functools import partial
from types import TracebackType
from typing import Self

import httpx

from ._errors import AllisallError, IngestError
from ._ingest import Batch, Combiner, Plan, parse_ingest_result, prepare, remaining
from ._transport import (
    CREDENTIAL_CHARACTERS,
    AsyncTransport,
    SyncTransport,
    has_invalid_credential_character,
)
from ._types import EventInput, IngestSummary

DEFAULT_BASE_URL = "https://api.allisai.ai"
DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_RETRIES = 2
INGEST_PATH = "/v1/events"


def _check_one_credential(api_key: str | None, has_provider: bool) -> None:
    if api_key is not None and has_provider:
        raise AllisallError("pass api_key or token_provider, not both")


def _resolve_api_key(api_key: str | None) -> str:
    """The API key, without leading and trailing whitespace.

    The option comes first, then `AIA_API_KEY` when it is set and not blank. An option that
    is empty or only whitespace is an error rather than a fall back on the environment.
    """
    if api_key is not None:
        key = api_key.strip()
        if not key:
            raise AllisallError("api_key is empty")
        _check_key(key, "api_key")
        return key
    from_env = os.environ.get("AIA_API_KEY", "").strip()
    if from_env:
        _check_key(from_env, "AIA_API_KEY")
        return from_env
    raise AllisallError(
        "no credential: pass api_key or token_provider, or set the AIA_API_KEY environment variable"
    )


def _check_key(key: str, source: str) -> None:
    """Refuse a key that holds a character outside U+0021 to U+007E.

    The message names only the source, never the key or any part of it.
    """
    if has_invalid_credential_character(key):
        raise AllisallError(f"{source} contains a character outside {CREDENTIAL_CHARACTERS}")


def _constant(key: str) -> Callable[[], str]:
    return lambda: key


def _resolve_base_url(base_url: str | None) -> httpx.URL:
    """The base URL: the option, then `AIA_BASE_URL`, then the default."""
    value = base_url if base_url is not None else os.environ.get("AIA_BASE_URL") or DEFAULT_BASE_URL
    try:
        url = httpx.URL(value)
    except httpx.InvalidURL as err:
        raise AllisallError(f"base_url {value!r} is not a valid URL: {err}") from err
    if url.scheme not in ("http", "https") or not url.host:
        raise AllisallError(f"base_url {value!r} is not an absolute http or https URL")
    return url


def _operation_url(base: httpx.URL, path: str) -> httpx.URL:
    """Join the base URL and an operation's path with exactly one `/`.

    The base URL's own path and query survive: `https://example.test/api?region=eu` sends
    ingest to `https://example.test/api/v1/events?region=eu`.
    """
    raw_path, _, query = base.raw_path.partition(b"?")
    joined = raw_path.rstrip(b"/") + path.encode("ascii")
    if query:
        joined += b"?" + query
    return base.copy_with(raw_path=joined, fragment=None)


def _check_limits(timeout: float, max_retries: int) -> None:
    if not (math.isfinite(timeout) and timeout > 0):
        raise AllisallError(
            f"timeout must be a finite, positive number of seconds, not {timeout!r}"
        )
    if max_retries < 0:
        raise AllisallError(f"max_retries must not be negative, not {max_retries!r}")


def _failed(plan: Plan, batch: Batch, combiner: Combiner, err: Exception) -> IngestError:
    rest, start = remaining(plan, batch)
    return IngestError(
        f"ingest stopped at the batch starting at events[{start}]: {err}",
        summary=combiner.summary(),
        remaining=rest,
        remaining_from=start,
    )


class Events:
    """The `Events` operations of `Allisall`."""

    def __init__(self, transport: SyncTransport, url: httpx.URL) -> None:
        self._transport = transport
        self._url = url

    def ingest(self, events: Sequence[EventInput]) -> IngestSummary:
        """Send any number of events, in as many batches as the API's limits require.

        Each event without an `event_id` is given a UUID version 4; the objects passed in are
        never modified. A batch holds at most 500 events and a 5,000,000-byte body. Batches are
        sent one at a time, each retried as the client's `max_retries` allows. An event too
        large to send even alone is not sent, and is reported as a rejected row with the code
        `too_large`.

        Raises `ValueError`, before sending anything, when an event cannot be encoded. Raises
        `IngestError` when a batch fails, including when the token provider raises for one of
        its attempts; the batches after it are not sent, and the error that failed the batch is
        its `__cause__`.
        """
        plan = prepare(events)
        combiner = Combiner(plan.too_large)
        for batch in plan.batches:
            try:
                result = self._transport.post(
                    self._url, batch.body, partial(parse_ingest_result, batch=batch)
                )
            except Exception as err:  # not BaseException: cancellation propagates unwrapped
                raise _failed(plan, batch, combiner, err) from err
            combiner.add(result)
        return combiner.summary()


class AsyncEvents:
    """The `Events` operations of `AsyncAllisall`."""

    def __init__(self, transport: AsyncTransport, url: httpx.URL) -> None:
        self._transport = transport
        self._url = url

    async def ingest(self, events: Sequence[EventInput]) -> IngestSummary:
        """Send any number of events, in as many batches as the API's limits require.

        Behaves as `Allisall.events.ingest`. Cancelling the task cancels the call: the
        `asyncio.CancelledError` propagates unwrapped, from the transport or from the token
        provider, and the partial summary is lost.
        """
        plan = prepare(events)
        combiner = Combiner(plan.too_large)
        for batch in plan.batches:
            try:
                result = await self._transport.post(
                    self._url, batch.body, partial(parse_ingest_result, batch=batch)
                )
            except Exception as err:  # not BaseException: cancellation propagates unwrapped
                raise _failed(plan, batch, combiner, err) from err
            combiner.add(result)
        return combiner.summary()


class Allisall:
    """A client of the allisall API. Construct one and reuse it.

    The credential is `api_key`, or `token_provider`, a callable returning the bearer token,
    which is called before every attempt. Without either, the `AIA_API_KEY` environment
    variable is used. `base_url` defaults to `AIA_BASE_URL`, then `https://api.allisai.ai`.
    `timeout` bounds each attempt, in seconds. `max_retries` is the number of retries after a
    failed attempt; `0` sends one attempt. `http_client` is an `httpx.Client` to send with;
    the caller keeps ownership of it, and `close()` leaves it open.

    Raises `AllisallError` when the options are not usable.
    """

    events: Events

    def __init__(
        self,
        *,
        api_key: str | None = None,
        token_provider: Callable[[], str] | None = None,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_client: httpx.Client | None = None,
    ) -> None:
        _check_one_credential(api_key, token_provider is not None)
        token: Callable[[], str] = (
            token_provider if token_provider is not None else _constant(_resolve_api_key(api_key))
        )
        base = _resolve_base_url(base_url)
        _check_limits(timeout, max_retries)
        self._owns_client = http_client is None
        self._http = http_client if http_client is not None else httpx.Client()
        self._transport = SyncTransport(
            http_client=self._http, token=token, timeout=timeout, max_retries=max_retries
        )
        self.events = Events(self._transport, _operation_url(base, INGEST_PATH))

    def close(self) -> None:
        """Close the HTTP connections the client opened. A caller's `http_client` stays open."""
        if self._owns_client:
            self._http.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()


class AsyncAllisall:
    """An asyncio client of the allisall API. Construct one and reuse it.

    Takes the options of `Allisall`, except that `token_provider` may also return an
    awaitable, and `http_client` is an `httpx.AsyncClient`.

    Raises `AllisallError` when the options are not usable.
    """

    events: AsyncEvents

    def __init__(
        self,
        *,
        api_key: str | None = None,
        token_provider: Callable[[], str] | Callable[[], Awaitable[str]] | None = None,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        _check_one_credential(api_key, token_provider is not None)
        token: Callable[[], str | Awaitable[str]] = (
            token_provider if token_provider is not None else _constant(_resolve_api_key(api_key))
        )
        base = _resolve_base_url(base_url)
        _check_limits(timeout, max_retries)
        self._owns_client = http_client is None
        self._http = http_client if http_client is not None else httpx.AsyncClient()
        self._transport = AsyncTransport(
            http_client=self._http, token=token, timeout=timeout, max_retries=max_retries
        )
        self.events = AsyncEvents(self._transport, _operation_url(base, INGEST_PATH))

    async def close(self) -> None:
        """Close the HTTP connections the client opened. A caller's `http_client` stays open."""
        if self._owns_client:
            await self._http.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()
