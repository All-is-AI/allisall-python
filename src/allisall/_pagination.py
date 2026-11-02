"""A list call's result: a page, and the walk over every page after it.

The walk is the same for both clients. The first request sends the caller's query as given.
While a page's `has_more` is true, the next request sends the same query with `cursor` set to
that page's `next_cursor` and without `page`, so every filter and sort the cursor was issued
under is sent unchanged.

The walk records every cursor of the list call with the position of the page it requests, the
caller's own cursor at the first. A page that has another page and names a cursor recorded for
a different position would make the walk repeat itself without end, so it ends the walk with an
`APIError` carrying that page's status and no problem. Walking again from an earlier page meets
each cursor at its own position, and is not refused.
"""

from __future__ import annotations

import asyncio
from collections.abc import (
    AsyncIterator,
    Awaitable,
    Callable,
    Generator,
    Iterator,
    Mapping,
    Sequence,
)
from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar, cast

from ._decode import ShapeError
from ._errors import AllisallError
from ._options import CallOptions

ItemT = TypeVar("ItemT")
ItemT_co = TypeVar("ItemT_co", covariant=True)


class ListBody(Protocol[ItemT_co]):
    """The envelope every list response shares."""

    @property
    def data(self) -> Sequence[ItemT_co]: ...

    @property
    def has_more(self) -> bool: ...

    @property
    def next_cursor(self) -> str | None: ...


BodyT = TypeVar("BodyT", bound=ListBody[object])

_LAST_PAGE = "this is the last page; no page follows it"


def next_query(query: Mapping[str, object], cursor: str) -> dict[str, object]:
    """The query of the next page: the same members, `page` dropped, `cursor` set."""
    following = {name: value for name, value in query.items() if name != "page"}
    following["cursor"] = cursor
    return following


def check_cursor(body: ListBody[object], position: int, positions: Mapping[str, int]) -> None:
    """Refuse the page at `position` when it has another page and names a cursor the walk has
    recorded for a different position: following it would repeat pages without end. Raises
    `ShapeError`, which the transport reports as an `APIError` with the page's status."""
    if not body.has_more or body.next_cursor is None:
        return
    recorded = positions.get(body.next_cursor)
    if recorded is not None and recorded != position + 1:
        raise ShapeError(
            "/next_cursor",
            "the page names a cursor this walk has already sent for another page, so the walk "
            "would not end",
        )


@dataclass(frozen=True)
class Step:
    """One request of a walk: its query, the position of the page it requests (`0` for the
    list call's own), and the cursors of the whole list call, each with the position of the
    page it requests. Every page and every `get_next_page` of one list call share that map, so
    walking again from an earlier page records the same positions and is not refused."""

    query: Mapping[str, object]
    position: int
    positions: dict[str, int]

    @classmethod
    def start(cls, query: Mapping[str, object]) -> Step:
        """The list call's own request. A cursor the caller passes is recorded at position 0."""
        positions: dict[str, int] = {}
        cursor = query.get("cursor")
        if isinstance(cursor, str):
            positions[cursor] = 0
        return cls(query, 0, positions)

    def check(self, body: ListBody[object]) -> None:
        """Refuse a page that repeats the walk; see `check_cursor`."""
        check_cursor(body, self.position, self.positions)

    def following(self, body: ListBody[object]) -> Step | None:
        """The request after `body`'s page, or `None` when it is the last. Its cursor is
        recorded at the next position."""
        cursor = next_cursor_of(body)
        if cursor is None:
            return None
        self.positions.setdefault(cursor, self.position + 1)
        return Step(next_query(self.query, cursor), self.position + 1, self.positions)


def next_cursor_of(body: ListBody[object]) -> str | None:
    """The cursor of the page after `body`, or `None` when it is the last. The envelope was
    checked when the body was read, so a page with `has_more` has a non-empty cursor."""
    return body.next_cursor if body.has_more else None


class Page(Generic[ItemT, BodyT]):
    """One page of a list, from `Allisall`.

    `data` holds the page's items, and `body` the whole decoded response, such as the event
    list's `total`. Iterating a page yields its items and then every following page's,
    fetching each page as the walk reaches it.

    Only a list method makes a page. Its constructor is not part of the SDK's promise, and a
    minor release may change it.
    """

    def __init__(
        self, body: BodyT, following: Callable[[CallOptions], Page[ItemT, BodyT]] | None
    ) -> None:
        self.body: BodyT = body
        """The whole decoded response."""
        # The list method's signature names the item type of its body's `data`.
        self.data: Sequence[ItemT] = cast("Sequence[ItemT]", body.data)
        """The page's items."""
        self._following = following

    def has_next_page(self) -> bool:
        """Whether another page follows this one: the response's `has_more`."""
        return self._following is not None

    def get_next_page(
        self,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Page[ItemT, BodyT]:
        """Fetch the next page, with the same query as this one.

        The options apply to this one request, over the call's: an option left at `None`
        keeps the call's, and `headers` are laid over the call's name by name. Raises
        `AllisallError` when this is the last page.
        """
        if self._following is None:
            raise AllisallError(_LAST_PAGE)
        return self._following(
            CallOptions(timeout=timeout, max_retries=max_retries, headers=headers)
        )

    def __iter__(self) -> Iterator[ItemT]:
        """Yield this page's items, then each following page's. An error fetching a page
        ends the walk; the items already yielded stay yielded."""
        page = self
        while True:
            yield from page.data
            if not page.has_next_page():
                return
            page = page.get_next_page()


class AsyncPage(Generic[ItemT, BodyT]):
    """One page of a list, from `AsyncAllisall`.

    Behaves as `Page`, except that `get_next_page` is a coroutine and the page is iterated
    with `async for`.

    Only a list method makes a page. Its constructor is not part of the SDK's promise, and a
    minor release may change it.
    """

    def __init__(
        self,
        body: BodyT,
        following: Callable[[CallOptions], Awaitable[AsyncPage[ItemT, BodyT]]] | None,
    ) -> None:
        self.body: BodyT = body
        """The whole decoded response."""
        # The list method's signature names the item type of its body's `data`.
        self.data: Sequence[ItemT] = cast("Sequence[ItemT]", body.data)
        """The page's items."""
        self._following = following

    def has_next_page(self) -> bool:
        """Whether another page follows this one: the response's `has_more`."""
        return self._following is not None

    async def get_next_page(
        self,
        *,
        timeout: float | None = None,
        max_retries: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> AsyncPage[ItemT, BodyT]:
        """Fetch the next page; see `Page.get_next_page`."""
        if self._following is None:
            raise AllisallError(_LAST_PAGE)
        return await self._following(
            CallOptions(timeout=timeout, max_retries=max_retries, headers=headers)
        )

    def __aiter__(self) -> AsyncIterator[ItemT]:
        """Yield this page's items, then each following page's."""
        return self._walk()

    async def _walk(self) -> AsyncIterator[ItemT]:
        page = self
        while True:
            for item in page.data:
                yield item
            if not page.has_next_page():
                return
            page = await page.get_next_page()


class AsyncPaginator(Generic[ItemT, BodyT]):
    """The result of an `AsyncAllisall` list method.

    Await it for the first `AsyncPage`, or iterate it with `async for` for every item of every
    page. Nothing is sent until it is awaited or iterated, so a list call whose result is never
    used sends no request. Awaiting it and then iterating it, or awaiting it from several tasks
    at once, sends the first request once: they share it, and the page once it has arrived. A
    failure is not kept: after the first request raises, the next await sends it again.
    Cancelling one awaiting task does not cancel the request the others share. It is an
    awaitable, not a coroutine: `asyncio.gather` accepts it, and `asyncio.create_task` does
    not.

    Only a list method makes one. Its constructor is not part of the SDK's promise, and a
    minor release may change it.
    """

    def __init__(self, load: Callable[[], Awaitable[AsyncPage[ItemT, BodyT]]]) -> None:
        self._load = load
        self._first: asyncio.Future[AsyncPage[ItemT, BodyT]] | None = None
        """The first request, in flight or succeeded. A failed one is dropped."""

    async def _first_page(self) -> AsyncPage[ItemT, BodyT]:
        first = self._first
        if first is not None and first.done():
            # Only a success stays: a failure is dropped as it completes.
            return first.result()
        if first is None:
            first = asyncio.ensure_future(self._load())
            first.add_done_callback(self._drop_failure)
            self._first = first
        # Shielded, so one awaiting task's cancellation leaves the request the others share.
        return await asyncio.shield(first)

    def _drop_failure(self, first: asyncio.Future[AsyncPage[ItemT, BodyT]]) -> None:
        # Reading the exception also marks it retrieved, so asyncio does not log it.
        if (first.cancelled() or first.exception() is not None) and self._first is first:
            self._first = None

    def __await__(self) -> Generator[object, None, AsyncPage[ItemT, BodyT]]:
        return self._first_page().__await__()

    def __aiter__(self) -> AsyncIterator[ItemT]:
        """Yield every item of every page, from the first."""
        return self._walk()

    async def _walk(self) -> AsyncIterator[ItemT]:
        page = await self._first_page()
        async for item in page:
            yield item
