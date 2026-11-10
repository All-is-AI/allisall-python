"""The `workspace` group."""

from __future__ import annotations

from collections.abc import Mapping

from .._generated.responses import Workspace
from .._options import CallOptions
from .._transport import AsyncTransport, SyncTransport


class WorkspaceResource:
    """The `workspace` operations of `Allisall`."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def get(
        self,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Workspace:
        """Read the workspace the credential belongs to: its name, its currency and when it was
        created.

        Needs the `read` scope. Operation `getWorkspace`.
        """
        return self._transport.call(
            "getWorkspace",
            Workspace,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )


class AsyncWorkspaceResource:
    """The `workspace` operations of `AsyncAllisall`."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def get(
        self,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Workspace:
        """Read the workspace the credential belongs to; see `Allisall.workspace.get`.

        Needs the `read` scope. Operation `getWorkspace`.
        """
        return await self._transport.call(
            "getWorkspace",
            Workspace,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )
