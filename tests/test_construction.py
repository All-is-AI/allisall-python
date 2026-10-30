"""Constructing a client: credential and base URL resolution, limits, headers and closing."""

from __future__ import annotations

import asyncio
import platform
import re
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

import allisall
from allisall import Allisall, AllisallError, AsyncAllisall

from support import Harness, accept_all, event


def construct(mode: str, **options: Any) -> Allisall | AsyncAllisall:
    if mode == "sync":
        return Allisall(**options)
    return AsyncAllisall(**options)


def test_the_option_wins_over_the_environment(
    make: Callable[..., Harness], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AIA_API_KEY", "aia_from_env")
    harness = make(api_key="aia_from_option")
    harness.ingest([event(0)])
    assert harness.requests[0].headers["authorization"] == "Bearer aia_from_option"


def test_the_environment_supplies_the_key(
    make: Callable[..., Harness], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AIA_API_KEY", "aia_from_env")
    harness = make(api_key=None)
    harness.ingest([event(0)])
    assert harness.requests[0].headers["authorization"] == "Bearer aia_from_env"


def test_a_key_and_a_provider_fail(mode: str) -> None:
    with pytest.raises(AllisallError, match="not both"):
        construct(mode, api_key="aia_x", token_provider=lambda: "aia_y")


@pytest.mark.parametrize("env", [None, ""])
def test_no_credential_fails(mode: str, monkeypatch: pytest.MonkeyPatch, env: str | None) -> None:
    if env is not None:
        monkeypatch.setenv("AIA_API_KEY", env)
    with pytest.raises(AllisallError, match="no credential"):
        construct(mode)


def test_an_empty_key_option_fails(mode: str) -> None:
    with pytest.raises(AllisallError, match="empty"):
        construct(mode, api_key="")


def test_a_provider_ignores_the_environment(
    make: Callable[..., Harness], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AIA_API_KEY", "aia_from_env")
    harness = make(token_provider=lambda: "aia_from_provider")
    harness.ingest([event(0)])
    assert harness.requests[0].headers["authorization"] == "Bearer aia_from_provider"


def test_the_default_base_url(make: Callable[..., Harness]) -> None:
    harness = make()
    harness.ingest([event(0)])
    assert str(harness.requests[0].url) == "https://api.allisai.ai/v1/events"


def test_the_base_url_from_the_environment(
    make: Callable[..., Harness], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AIA_BASE_URL", "http://localhost:8081")
    harness = make()
    harness.ingest([event(0)])
    assert str(harness.requests[0].url) == "http://localhost:8081/v1/events"


@pytest.mark.parametrize(
    ("base_url", "sent_to"),
    [
        ("https://example.test/api", "https://example.test/api/v1/events"),
        ("https://example.test/api/", "https://example.test/api/v1/events"),
        ("https://example.test", "https://example.test/v1/events"),
        ("https://example.test/api?region=eu", "https://example.test/api/v1/events?region=eu"),
        ("https://example.test/api/?a=1&b=2", "https://example.test/api/v1/events?a=1&b=2"),
        ("https://example.test?region=eu", "https://example.test/v1/events?region=eu"),
        ("https://example.test/a%20b", "https://example.test/a%20b/v1/events"),
        ("https://example.test/api#frag", "https://example.test/api/v1/events"),
    ],
)
def test_the_base_url_keeps_its_path(
    make: Callable[..., Harness], monkeypatch: pytest.MonkeyPatch, base_url: str, sent_to: str
) -> None:
    monkeypatch.setenv("AIA_BASE_URL", "https://ignored.test")
    harness = make(base_url=base_url)
    harness.ingest([event(0)])
    assert str(harness.requests[0].url) == sent_to


@pytest.mark.parametrize(
    "base_url", ["/api", "api.allisai.ai", "ftp://example.test", "", "http://"]
)
def test_a_base_url_that_is_not_absolute_http_fails(mode: str, base_url: str) -> None:
    with pytest.raises(AllisallError, match="base_url"):
        construct(mode, api_key="aia_x", base_url=base_url)


@pytest.mark.parametrize(
    ("timeout", "max_retries"),
    [(0, 2), (-1, 2), (float("nan"), 2), (float("inf"), 2), (float("-inf"), 2), (1, -1)],
)
def test_unusable_limits_fail(mode: str, timeout: float, max_retries: int) -> None:
    with pytest.raises(AllisallError):
        construct(mode, api_key="aia_x", timeout=timeout, max_retries=max_retries)


def test_each_attempt_carries_the_headers(make: Callable[..., Harness]) -> None:
    harness = make(timeout=12.5)
    harness.ingest([event(0)])
    request = harness.requests[0]
    assert request.method == "POST"
    assert request.headers["content-type"] == "application/json"
    assert request.headers["user-agent"] == (
        f"allisall-python/{allisall.__version__} python/{platform.python_version()} "
        f"httpx/{httpx.__version__}"
    )
    assert request.extensions["timeout"] == {
        "connect": 12.5,
        "read": 12.5,
        "write": 12.5,
        "pool": 12.5,
    }


def test_the_default_timeout_is_60_seconds(make: Callable[..., Harness]) -> None:
    harness = make()
    harness.ingest([event(0)])
    assert set(harness.requests[0].extensions["timeout"].values()) == {60.0}


def test_the_version_is_the_one_the_build_reads() -> None:
    # The build takes the package version from the file pyproject.toml names, with hatchling's
    # default pattern. Reading it the same way pins the runtime and the built package to one
    # value, whatever that value is after a release.
    root = Path(__file__).resolve().parents[1]
    pyproject = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    source = (root / pyproject["tool"]["hatch"]["version"]["path"]).read_text(encoding="utf-8")
    match = re.search(
        r"""(?i)^(__version__|VERSION) *= *(['"])v?(?P<version>.+?)\2""", source, re.MULTILINE
    )
    assert match is not None
    assert allisall.__version__ == match.group("version")
    # A PEP 440 public version in canonical form: a three-part release, then an optional
    # pre-release, post-release and development release, such as 0.2.0rc1 or 0.2.0.dev1.
    assert re.fullmatch(
        r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)((a|b|rc)\d+)?(\.post\d+)?(\.dev\d+)?",
        allisall.__version__,
    )


def test_close_closes_the_clients_own_connections() -> None:
    client = Allisall(api_key="aia_x")
    client.close()
    assert client._http.is_closed

    with Allisall(api_key="aia_x") as managed:
        pass
    assert managed._http.is_closed


def test_close_leaves_a_callers_http_client_open() -> None:
    http = httpx.Client(transport=httpx.MockTransport(accept_all))
    with Allisall(api_key="aia_x", http_client=http) as client:
        client.events.ingest([event(0)])
    assert not http.is_closed
    http.close()


def test_async_close_and_context_manager() -> None:
    async def run() -> None:
        client = AsyncAllisall(api_key="aia_x")
        await client.close()
        assert client._http.is_closed

        async with AsyncAllisall(api_key="aia_x") as managed:
            pass
        assert managed._http.is_closed

        http = httpx.AsyncClient(transport=httpx.MockTransport(accept_all))
        async with AsyncAllisall(api_key="aia_x", http_client=http) as borrowed:
            await borrowed.events.ingest([event(0)])
        assert not http.is_closed
        await http.aclose()

    asyncio.run(run())
