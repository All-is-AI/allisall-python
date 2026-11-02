"""`Allisall` and `AsyncAllisall`: options, credential and base URL resolution, and the
operation groups."""

from __future__ import annotations

import os
from collections.abc import Awaitable, Callable, Mapping
from types import TracebackType
from typing import Self

import httpx

from ._errors import AllisallError
from ._options import check_headers, check_limits
from ._request import ClientConfig
from ._resources.agents import AgentsResource, AsyncAgentsResource
from ._resources.analytics import AnalyticsResource, AsyncAnalyticsResource
from ._resources.calculations import AsyncCalculationsResource, CalculationsResource
from ._resources.clients import AsyncClientsResource, ClientsResource
from ._resources.cost import AsyncCostResource, CostResource
from ._resources.dashboard import AsyncDashboardResource, DashboardResource
from ._resources.events import AsyncEventsResource, EventsResource
from ._resources.health import AsyncHealthResource, HealthResource
from ._resources.imports import AsyncImportsResource, ImportsResource
from ._resources.outcome_types import AsyncOutcomeTypesResource, OutcomeTypesResource
from ._resources.reports import AsyncReportsResource, ReportsResource
from ._resources.value_models import AsyncValueModelsResource, ValueModelsResource
from ._transport import (
    CREDENTIAL_CHARACTERS,
    AsyncTransport,
    SyncTransport,
    has_invalid_credential_character,
    user_agent,
)

DEFAULT_BASE_URL = "https://api.allisai.ai"
DEFAULT_TIMEOUT = 60.0
DEFAULT_MAX_RETRIES = 2


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


def _config(
    base_url: str | None,
    timeout: float,
    max_retries: int,
    default_headers: Mapping[str, str] | None,
) -> ClientConfig:
    base = _resolve_base_url(base_url)
    check_limits(timeout, max_retries)
    return ClientConfig(
        base_url=base,
        timeout=timeout,
        max_retries=max_retries,
        default_headers=check_headers(default_headers, "default_headers"),
        user_agent=user_agent(),
    )


class Allisall:
    """A client of the allisall API. Construct one and reuse it.

    The credential is `api_key`, or `token_provider`, a callable returning the bearer token,
    which is called before every attempt. Without either, the `AIA_API_KEY` environment
    variable is used. `base_url` defaults to `AIA_BASE_URL`, then `https://api.allisai.ai`.
    `timeout` bounds each attempt, in seconds. `max_retries` is the number of retries after a
    failed attempt; `0` sends one attempt. `default_headers` are sent on every request; they
    may not name `Authorization`, `Content-Type`, `Idempotency-Key` or `X-Request-Id`, which
    the SDK sets. `http_client` is an `httpx.Client` to send with; the caller keeps ownership
    of it, and `close()` leaves it open.

    Raises `AllisallError` when the options are not usable, and `ValueError` when
    `default_headers` cannot be sent.
    """

    events: EventsResource
    """Ingest, and the events behind a client's totals."""
    imports: ImportsResource
    """CSV imports."""
    clients: ClientsResource
    agents: AgentsResource
    value_models: ValueModelsResource
    """Value models and value templates."""
    outcome_types: OutcomeTypesResource
    cost: CostResource
    """Cost line items and the price table."""
    analytics: AnalyticsResource
    """A client's value, cost, ROI and anomalies over a period."""
    calculations: CalculationsResource
    reports: ReportsResource
    dashboard: DashboardResource
    health: HealthResource

    def __init__(
        self,
        *,
        api_key: str | None = None,
        token_provider: Callable[[], str] | None = None,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        _check_one_credential(api_key, token_provider is not None)
        token: Callable[[], str] = (
            token_provider if token_provider is not None else _constant(_resolve_api_key(api_key))
        )
        config = _config(base_url, timeout, max_retries, default_headers)
        self._owns_client = http_client is None
        self._http = http_client if http_client is not None else httpx.Client()
        transport = SyncTransport(http_client=self._http, token=token, config=config)
        self._transport = transport
        self.events = EventsResource(transport)
        self.imports = ImportsResource(transport)
        self.clients = ClientsResource(transport)
        self.agents = AgentsResource(transport)
        self.value_models = ValueModelsResource(transport)
        self.outcome_types = OutcomeTypesResource(transport)
        self.cost = CostResource(transport)
        self.analytics = AnalyticsResource(transport)
        self.calculations = CalculationsResource(transport)
        self.reports = ReportsResource(transport)
        self.dashboard = DashboardResource(transport)
        self.health = HealthResource(transport)

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

    Raises `AllisallError` when the options are not usable, and `ValueError` when
    `default_headers` cannot be sent.
    """

    events: AsyncEventsResource
    """Ingest, and the events behind a client's totals."""
    imports: AsyncImportsResource
    """CSV imports."""
    clients: AsyncClientsResource
    agents: AsyncAgentsResource
    value_models: AsyncValueModelsResource
    """Value models and value templates."""
    outcome_types: AsyncOutcomeTypesResource
    cost: AsyncCostResource
    """Cost line items and the price table."""
    analytics: AsyncAnalyticsResource
    """A client's value, cost, ROI and anomalies over a period."""
    calculations: AsyncCalculationsResource
    reports: AsyncReportsResource
    dashboard: AsyncDashboardResource
    health: AsyncHealthResource

    def __init__(
        self,
        *,
        api_key: str | None = None,
        token_provider: Callable[[], str] | Callable[[], Awaitable[str]] | None = None,
        base_url: str | None = None,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        default_headers: Mapping[str, str] | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        _check_one_credential(api_key, token_provider is not None)
        token: Callable[[], str | Awaitable[str]] = (
            token_provider if token_provider is not None else _constant(_resolve_api_key(api_key))
        )
        config = _config(base_url, timeout, max_retries, default_headers)
        self._owns_client = http_client is None
        self._http = http_client if http_client is not None else httpx.AsyncClient()
        transport = AsyncTransport(http_client=self._http, token=token, config=config)
        self._transport = transport
        self.events = AsyncEventsResource(transport)
        self.imports = AsyncImportsResource(transport)
        self.clients = AsyncClientsResource(transport)
        self.agents = AsyncAgentsResource(transport)
        self.value_models = AsyncValueModelsResource(transport)
        self.outcome_types = AsyncOutcomeTypesResource(transport)
        self.cost = AsyncCostResource(transport)
        self.analytics = AsyncAnalyticsResource(transport)
        self.calculations = AsyncCalculationsResource(transport)
        self.reports = AsyncReportsResource(transport)
        self.dashboard = AsyncDashboardResource(transport)
        self.health = AsyncHealthResource(transport)

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
