"""The SDK's errors: one base, `AllisallError`, and three conditions under it."""

from __future__ import annotations

from collections.abc import Sequence

import httpx

from ._types import ErrorCode, EventInput, IngestSummary, Problem


class AllisallError(Exception):
    """The base of every error the SDK raises.

    A client that cannot be constructed raises it directly: a missing credential, two
    credentials, a base URL that is not an absolute `http` or `https` URL, a negative retry
    count, or a timeout that is not positive.
    """


class APIError(AllisallError):
    """The API answered with an error status, or with a success body the SDK cannot read.

    Branch on `code`. For a code this version does not list, `code` is a plain `str`; fall
    back on `status`. `code` and `problem` are `None` when the body was not a problem
    document, for example a proxy's HTML page. `code` is also `None` when a problem document
    carries no string `code`. `request_id` is the problem's when it is a non-empty string,
    and otherwise the response's `X-Request-Id`. `retry_after` is `math.inf` for a
    `Retry-After` too large to convert.
    """

    status: int
    code: ErrorCode | str | None
    problem: Problem | None
    request_id: str | None
    retry_after: float | None
    headers: httpx.Headers

    def __init__(
        self,
        message: str,
        *,
        status: int,
        problem: Problem | None,
        request_id: str | None,
        retry_after: float | None,
        headers: httpx.Headers,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.problem = problem
        self.code = problem.code if problem is not None else None
        self.request_id = request_id
        self.retry_after = retry_after
        self.headers = headers


class APIConnectionError(AllisallError):
    """No response arrived: the connection failed or was reset, or the attempt timed out.

    `request_id` is the `X-Request-Id` the SDK sent on the last attempt, to quote when
    reporting the failure. The underlying error is the exception's `__cause__`.
    """

    request_id: str

    def __init__(self, message: str, *, request_id: str) -> None:
        super().__init__(message)
        self.request_id = request_id


class IngestError(AllisallError):
    """A batch failed, and `ingest` stopped without sending the batches after it.

    The error that failed the batch is the exception's `__cause__`: an `APIError`, an
    `APIConnectionError`, or the exception the token provider raised, unchanged.
    `asyncio.CancelledError` is never wrapped.

    `summary` is the combined outcome of the batches that succeeded before it, together with
    every event too large to send. `remaining` holds copies of every event from the failed
    batch onward, less any too large to send, each with the `event_id` it was given, so
    sending `remaining` again resumes the call. `remaining_from` is the position, in the list
    passed to `ingest`, of `remaining[0]`.

    After it, `remaining[i]` is the caller's event `remaining_from + i` only when no event too
    large to send lies between them. Those events are exactly the `summary.errors` rows whose
    `index` is `remaining_from` or more: to map `remaining` back, walk the caller's list from
    `remaining_from` and skip those indices.
    """

    summary: IngestSummary
    remaining: list[EventInput]
    remaining_from: int

    def __init__(
        self,
        message: str,
        *,
        summary: IngestSummary,
        remaining: Sequence[EventInput],
        remaining_from: int,
    ) -> None:
        super().__init__(message)
        self.summary = summary
        self.remaining = list(remaining)
        self.remaining_from = remaining_from
