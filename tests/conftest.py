"""Shared fixtures. Every behaviour test runs against both clients through `Harness`.

No test reaches the network: requests go to an `httpx.MockTransport`, and the autouse
`no_network` fixture makes any real socket connection fail the test.
"""

from __future__ import annotations

import socket
from collections.abc import Callable
from typing import Any

import pytest

from support import Handler, Harness, accept_all


@pytest.fixture(autouse=True)
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("a test tried to open a network connection")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AIA_API_KEY", raising=False)
    monkeypatch.delenv("AIA_BASE_URL", raising=False)


@pytest.fixture(params=["sync", "async"])
def mode(request: pytest.FixtureRequest) -> str:
    mode: str = request.param
    return mode


@pytest.fixture
def make(mode: str) -> Callable[..., Harness]:
    def build(handler: Handler = accept_all, **options: Any) -> Harness:
        return Harness(mode, handler, **options)

    return build
