"""The walk over a list's pages, for `Page` and for `AsyncPage` and `AsyncPaginator`."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

import httpx
import pytest

from allisall import (
    AllisallError,
    APIError,
    AsyncAllisall,
    AsyncPage,
    AsyncPaginator,
    Client,
    ClientEventList,
    ClientList,
    Page,
    _options,
)
from allisall._options import CallOptions
from samples import item_class, sample

from support import Harness, json_response, problem

EVENT = item_class(ClientEventList)


def client(name: str) -> dict[str, Any]:
    return {**sample(Client), "name": name}


def pages(*bodies: dict[str, Any]) -> Callable[[httpx.Request], httpx.Response]:
    """Answer each request with the next page."""
    remaining = iter(bodies)
    return lambda request: json_response(next(remaining))


def client_page(names: list[str], cursor: str | None) -> dict[str, Any]:
    return {
        "data": [client(name) for name in names],
        "has_more": cursor is not None,
        "next_cursor": cursor,
    }


THREE_PAGES = (
    client_page(["a", "b"], "cur-1"),
    client_page(["c"], "cur-2"),
    client_page(["d"], None),
)


def test_a_walk_sends_the_filters_and_each_page_s_own_cursor(
    make: Callable[..., Harness],
) -> None:
    harness = make(pages(*THREE_PAGES))
    items = harness.walk("listClients", ClientList, Client, query={"limit": 2})
    assert [item.name for item in items] == ["a", "b", "c", "d"]
    assert [request.url.query for request in harness.requests] == [
        b"limit=2",
        b"limit=2&cursor=cur-1",
        b"limit=2&cursor=cur-2",
    ]


def test_a_walk_continues_by_cursor_without_page(make: Callable[..., Harness]) -> None:
    first = {**sample(ClientEventList), "page": 3, "has_more": True, "next_cursor": "off-60"}
    last = {**sample(ClientEventList), "page": None, "has_more": False, "next_cursor": None}
    harness = make(pages(first, last))
    items = harness.walk(
        "listClientEvents",
        ClientEventList,
        EVENT,
        path=[("client_id", "c1")],
        query={"from_": "2026-08-01", "to": "2026-09-01", "dir_": "asc", "page": 3},
    )
    assert len(items) == 2
    assert [request.url.query for request in harness.requests] == [
        b"from=2026-08-01&to=2026-09-01&dir=asc&page=3",
        b"from=2026-08-01&to=2026-09-01&dir=asc&cursor=off-60",
    ]


@pytest.mark.parametrize("cursor", [None, ""])
def test_has_more_without_a_cursor_is_an_api_error(
    make: Callable[..., Harness], cursor: str | None
) -> None:
    body = {"data": [], "has_more": True, "next_cursor": cursor}
    harness = make(pages(body))
    with pytest.raises(APIError, match="next_cursor") as caught:
        harness.first_page("listClients", ClientList, Client)
    assert caught.value.status == 200
    assert caught.value.problem is None
    assert len(harness.requests) == 1


@pytest.mark.parametrize(
    "body",
    [
        {"data": [], "has_more": "yes", "next_cursor": None},
        {"data": [], "has_more": False, "next_cursor": 7},
    ],
)
def test_an_envelope_of_the_wrong_types_is_an_api_error(
    make: Callable[..., Harness], body: dict[str, Any]
) -> None:
    harness = make(pages(body))
    with pytest.raises(APIError) as caught:
        harness.first_page("listClients", ClientList, Client)
    assert caught.value.status == 200


def test_a_sync_list_call_sends_its_first_request_at_once() -> None:
    harness = Harness("sync", pages(*THREE_PAGES))
    page = harness.client._transport.call_page("listClients", ClientList, Client)
    assert isinstance(page, Page)
    assert len(harness.requests) == 1
    assert isinstance(page.body, ClientList)
    assert [item.name for item in page.data] == ["a", "b"]
    assert page.has_next_page()


def test_an_unused_async_paginator_sends_nothing() -> None:
    harness = Harness("async", pages(*THREE_PAGES))
    assert isinstance(harness.client, AsyncAllisall)
    paginator = harness.client._transport.call_page("listClients", ClientList, Client)
    assert isinstance(paginator, AsyncPaginator)
    del paginator
    assert harness.requests == []


def test_an_awaited_then_iterated_paginator_sends_the_first_request_once() -> None:
    harness = Harness("async", pages(*THREE_PAGES))
    assert isinstance(harness.client, AsyncAllisall)
    transport = harness.client._transport

    async def run() -> tuple[AsyncPage[Client, ClientList], list[str]]:
        paginator = transport.call_page("listClients", ClientList, Client)
        page = await paginator
        names = [item.name async for item in paginator]
        return page, names

    page, names = asyncio.run(run())
    assert isinstance(page, AsyncPage)
    assert names == ["a", "b", "c", "d"]
    assert len(harness.requests) == 3


def test_get_next_page_fetches_the_next_and_raises_on_the_last(
    make: Callable[..., Harness],
) -> None:
    harness = make(pages(*THREE_PAGES))
    page = harness.first_page("listClients", ClientList, Client)
    page = harness.next_page(page)
    assert [item.name for item in page.data] == ["c"]
    page = harness.next_page(page)
    assert not page.has_next_page()
    with pytest.raises(AllisallError, match="last page"):
        harness.next_page(page)
    assert len(harness.requests) == 3


def test_get_next_page_s_options_apply_to_its_request_alone(
    make: Callable[..., Harness],
) -> None:
    timeouts: list[object] = []
    bodies = iter(THREE_PAGES)

    def handler(request: httpx.Request) -> httpx.Response:
        timeouts.append(request.extensions["timeout"]["read"])
        return json_response(next(bodies))

    harness = make(handler)
    options = CallOptions(timeout=9.0, headers={"X-Call": "c", "X-Shared": "call"})
    page = harness.first_page("listClients", ClientList, Client, options=options)
    page = harness.next_page(page, headers={"x-shared": "page", "X-Page": "p"}, timeout=2.0)
    harness.next_page(page)
    first, second, third = (request.headers for request in harness.requests)
    assert timeouts == [9.0, 2.0, 9.0]
    assert (first["x-call"], first["x-shared"], first.get("x-page")) == ("c", "call", None)
    assert (second["x-call"], second["x-shared"], second["x-page"]) == ("c", "page", "p")
    assert [v for k, v in harness.requests[1].headers.raw if k.lower() == b"x-shared"] == [b"page"]
    assert (third["x-call"], third["x-shared"], third.get("x-page")) == ("c", "call", None)


def test_get_next_page_refuses_an_owned_header_before_sending(
    make: Callable[..., Harness],
) -> None:
    harness = make(pages(*THREE_PAGES))
    page = harness.first_page("listClients", ClientList, Client)
    with pytest.raises(ValueError, match="the SDK sets it"):
        harness.next_page(page, headers={"Authorization": "x"})
    assert len(harness.requests) == 1


def test_an_error_on_the_second_page_ends_the_walk_after_the_first_page(mode: str) -> None:
    answers = iter([json_response(THREE_PAGES[0])])
    harness = Harness(mode, lambda r: next(answers, None) or problem(404, "not_found"))
    seen: list[str] = []
    transport = harness.client._transport

    async def walk_async() -> None:
        async for item in transport.call_page("listClients", ClientList, Client):
            seen.append(item.name)

    def walk() -> None:
        if mode == "sync":
            for item in transport.call_page("listClients", ClientList, Client):
                seen.append(item.name)
        else:
            asyncio.run(walk_async())

    with pytest.raises(APIError) as caught:
        walk()
    assert seen == ["a", "b"]
    assert caught.value.status == 404


# --- A repeated cursor ---


def walk_until_refused(harness: Harness, **kwargs: Any) -> tuple[list[str], APIError]:
    """Walk `listClients`, collecting names, until the walk raises an `APIError`."""
    seen: list[str] = []
    transport = harness.client._transport

    async def walk_async() -> None:
        async for item in transport.call_page("listClients", ClientList, Client, **kwargs):
            seen.append(item.name)

    def walk() -> None:
        if harness.mode == "sync":
            for item in transport.call_page("listClients", ClientList, Client, **kwargs):
                seen.append(item.name)
        else:
            asyncio.run(walk_async())

    with pytest.raises(APIError) as caught:
        walk()
    return seen, caught.value


def test_a_page_naming_the_cursor_its_request_sent_ends_the_walk(mode: str) -> None:
    harness = Harness(mode, pages(client_page(["a"], "A"), client_page(["b"], "A")))
    seen, error = walk_until_refused(harness)
    assert seen == ["a"]
    assert error.status == 200
    assert error.problem is None
    assert "already sent" in str(error)
    assert [r.url.query for r in harness.requests] == [b"", b"cursor=A"]


def test_a_two_page_cycle_ends_the_walk(mode: str) -> None:
    harness = Harness(
        mode,
        pages(client_page(["a"], "A"), client_page(["b"], "B"), client_page(["c"], "A")),
    )
    seen, error = walk_until_refused(harness)
    assert seen == ["a", "b"]
    assert error.status == 200
    assert error.problem is None
    assert [r.url.query for r in harness.requests] == [b"", b"cursor=A", b"cursor=B"]


def test_the_caller_s_own_cursor_counts_as_sent(mode: str) -> None:
    harness = Harness(mode, pages(client_page(["a"], "A")))
    seen, error = walk_until_refused(harness, query={"cursor": "A"})
    assert seen == []
    assert error.status == 200
    assert len(harness.requests) == 1


def test_a_cursor_on_the_last_page_is_neither_followed_nor_refused(
    make: Callable[..., Harness],
) -> None:
    # has_more is false, so the walk ends there whatever next_cursor holds.
    last = {**client_page(["b"], None), "next_cursor": "A"}
    harness = make(pages(client_page(["a"], "A"), last))
    assert [c.name for c in harness.walk("listClients", ClientList, Client)] == ["a", "b"]


def test_a_repeated_cursor_is_refused_through_get_next_page(make: Callable[..., Harness]) -> None:
    harness = make(pages(client_page(["a"], "A"), client_page(["b"], "A")))
    page = harness.first_page("listClients", ClientList, Client)
    with pytest.raises(APIError, match="already sent"):
        harness.next_page(page)


def by_cursor(request: httpx.Request) -> httpx.Response:
    """A server that answers each cursor with the same page, every time it is asked."""
    cursor = request.url.params.get("cursor")
    return json_response(
        {
            None: client_page(["a"], "A"),
            "A": client_page(["b"], "B"),
            "B": client_page(["c"], None),
        }[cursor]
    )


def test_walking_again_from_the_first_page_is_not_refused(mode: str) -> None:
    harness = Harness(mode, by_cursor)
    transport = harness.client._transport

    async def twice_async() -> list[str]:
        page = await transport.call_page("listClients", ClientList, Client)
        return [c.name async for c in page] + [c.name async for c in page]

    if mode == "sync":
        page = transport.call_page("listClients", ClientList, Client)
        names = [c.name for c in page] + [c.name for c in page]
    else:
        names = asyncio.run(twice_async())
    assert names == ["a", "b", "c", "a", "b", "c"]
    assert [r.url.query for r in harness.requests] == [
        b"",
        b"cursor=A",
        b"cursor=B",
        b"cursor=A",
        b"cursor=B",
    ]


def test_get_next_page_again_on_an_earlier_page_is_not_refused(mode: str) -> None:
    harness = Harness(mode, by_cursor)
    first = harness.first_page("listClients", ClientList, Client)
    second = harness.next_page(first)
    harness.next_page(second)
    again = harness.next_page(first)
    last = harness.next_page(again)
    assert [c.name for c in last.data] == ["c"]
    assert len(harness.requests) == 5


def test_every_page_of_one_list_call_shares_the_recorded_cursors(mode: str) -> None:
    # The first walk records B for the third page. A second walk from the first page meets B
    # as the fourth page's cursor, which the walk would repeat, so it is refused there.
    harness = Harness(
        mode,
        pages(
            client_page(["a"], "A"),
            client_page(["b"], "B"),
            client_page(["c"], None),
            client_page(["b2"], "C"),
            client_page(["c2"], "B"),
        ),
    )
    first = harness.first_page("listClients", ClientList, Client)
    harness.next_page(harness.next_page(first))
    again = harness.next_page(first)
    with pytest.raises(APIError, match="already sent") as caught:
        harness.next_page(again)
    assert caught.value.status == 200
    assert len(harness.requests) == 5


# --- Sharing the first request ---


def test_concurrent_awaits_share_one_first_request() -> None:
    harness = Harness("async", pages(*THREE_PAGES))
    assert isinstance(harness.client, AsyncAllisall)
    transport = harness.client._transport

    async def run() -> list[AsyncPage[Client, ClientList]]:
        paginator = transport.call_page("listClients", ClientList, Client)
        return list(await asyncio.gather(paginator, paginator, paginator))

    first, second, third = asyncio.run(run())
    assert first is second
    assert second is third
    assert len(harness.requests) == 1


def test_concurrent_awaits_share_a_failure_and_a_later_await_sends_again() -> None:
    answers = iter([problem(404, "not_found")])
    harness = Harness("async", lambda r: next(answers, None) or json_response(THREE_PAGES[2]))
    assert isinstance(harness.client, AsyncAllisall)
    transport = harness.client._transport

    async def run() -> tuple[list[object], AsyncPage[Client, ClientList]]:
        paginator = transport.call_page("listClients", ClientList, Client)
        failures = await asyncio.gather(paginator, paginator, return_exceptions=True)
        return failures, await paginator

    failures, page = asyncio.run(run())
    assert len(failures) == 2
    assert all(isinstance(f, APIError) and f.status == 404 for f in failures)
    assert [item.name for item in page.data] == ["d"]
    assert len(harness.requests) == 2


def test_cancelling_one_awaiter_leaves_the_shared_request_to_the_others() -> None:
    requests: list[httpx.Request] = []

    async def run() -> AsyncPage[Client, ClientList]:
        release = asyncio.Event()

        async def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            await release.wait()
            return json_response(THREE_PAGES[2])

        http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        client = AsyncAllisall(api_key="aia_k", http_client=http)
        paginator = client._transport.call_page("listClients", ClientList, Client)

        async def first() -> AsyncPage[Client, ClientList]:
            return await paginator

        cancelled = asyncio.create_task(first())
        kept = asyncio.create_task(first())
        while not requests:
            await asyncio.sleep(0)
        cancelled.cancel()
        with pytest.raises(asyncio.CancelledError):
            await cancelled
        release.set()
        return await kept

    page = asyncio.run(run())
    assert [item.name for item in page.data] == ["d"]
    assert len(requests) == 1


def test_get_next_page_checks_each_set_of_headers_once(
    make: Callable[..., Harness], monkeypatch: pytest.MonkeyPatch
) -> None:
    checked: list[object] = []
    original = _options.check_headers

    def counting(headers: object, option: str) -> dict[str, str]:
        if headers is not None:
            checked.append(headers)
        return original(headers, option)

    monkeypatch.setattr(_options, "check_headers", counting)
    call_headers = {"X-Call": "c"}
    page_headers = {"X-Page": "p"}
    harness = make(pages(*THREE_PAGES))
    page = harness.first_page(
        "listClients", ClientList, Client, options=CallOptions(headers=call_headers)
    )
    checked.clear()
    harness.next_page(page, headers=page_headers)
    assert checked == [call_headers, page_headers]
