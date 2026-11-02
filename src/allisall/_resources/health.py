"""The `health` group."""

from __future__ import annotations

from collections.abc import Mapping

from .._generated.responses import Health
from .._options import CallOptions
from .._transport import AsyncTransport, SyncTransport


class HealthResource:
    """The `health` operations of `Allisall`."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def get(
        self,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Health:
        """Check liveness.

        Needs no credential: the request sends no `Authorization`, and the token provider is
        not called. The client still needs a credential to be constructed.

        Operation `getHealth`.
        """
        return self._transport.call(
            "getHealth",
            Health,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )


class AsyncHealthResource:
    """The `health` operations of `AsyncAllisall`."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def get(
        self,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Health:
        """Check liveness; see `Allisall.health.get`.

        Needs no credential: the request sends no `Authorization`, and the token provider is
        not called. The client still needs a credential to be constructed.

        Operation `getHealth`.
        """
        return await self._transport.call(
            "getHealth",
            Health,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )
