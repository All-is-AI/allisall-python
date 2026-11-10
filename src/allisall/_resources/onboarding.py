"""The `onboarding` group: the guided setup's progress."""

from __future__ import annotations

from collections.abc import Mapping

from .._generated.requests import OnboardingSkippedStepsSet
from .._generated.responses import Onboarding
from .._options import CallOptions
from .._transport import AsyncTransport, SyncTransport


class OnboardingResource:
    """The `onboarding` operations of `Allisall`."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def get(
        self,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Onboarding:
        """Read the guided setup's progress: the five steps in their fixed order, each with
        whether the workspace's data completes it and when it was skipped, and `current_step`,
        the first step neither completed nor skipped. This is the read for the guided setup's
        progress.

        Needs the `read` scope. Operation `getOnboarding`.
        """
        return self._transport.call(
            "getOnboarding",
            Onboarding,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    def set_skipped_steps(
        self,
        body: OnboardingSkippedStepsSet,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Onboarding:
        """Replace the set of skipped steps, and return the whole progress.

        `steps` replaces the whole set: a step left out is no longer skipped, and `[]` clears
        every skip. A step already skipped keeps its `skipped_at`.

        Retried as `max_retries` allows, because sending the same set again leaves the same
        set.

        Needs the `write` scope. Operation `setOnboardingSkippedSteps`.
        """
        return self._transport.call(
            "setOnboardingSkippedSteps",
            Onboarding,
            body=body,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )


class AsyncOnboardingResource:
    """The `onboarding` operations of `AsyncAllisall`."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def get(
        self,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Onboarding:
        """Read the guided setup's progress; see `Allisall.onboarding.get`.

        Needs the `read` scope. Operation `getOnboarding`.
        """
        return await self._transport.call(
            "getOnboarding",
            Onboarding,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )

    async def set_skipped_steps(
        self,
        body: OnboardingSkippedStepsSet,
        /,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Onboarding:
        """Replace the set of skipped steps; see `Allisall.onboarding.set_skipped_steps`.

        `steps` replaces the whole set, and `[]` clears every skip. Retried as `max_retries`
        allows, because sending the same set again leaves the same set.

        Needs the `write` scope. Operation `setOnboardingSkippedSteps`.
        """
        return await self._transport.call(
            "setOnboardingSkippedSteps",
            Onboarding,
            body=body,
            options=CallOptions(timeout=timeout, max_retries=max_retries, headers=headers),
        )
