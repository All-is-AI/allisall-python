"""Calling an operation through the internal request layer, against both clients.

Every operation is driven from the facts the OpenAPI document states, read independently of
the operation table, so a table entry that drifts sends the wrong request and fails here.
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import re
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import httpx
import pytest

from allisall import (
    Allisall,
    AllisallError,
    APIConnectionError,
    APIError,
    AsyncAllisall,
    AsyncPaginator,
    Client,
    ClientAgents,
    ClientEventList,
    ClientValue,
    Health,
    Page,
)
from allisall._options import CallOptions
from samples import item_class, operations, response_class, sample

from support import TEST_KEY, Harness, assert_uuid4, json_response, problem

CONTENT_TYPES = {"json": "application/json", "merge-patch": "application/merge-patch+json"}

BODIES: dict[str, Any] = {
    "json": {"name": "Acme"},
    "merge-patch": {"notes": None},
    "multipart": {"mapping": {"columns": {"timestamp": "Time"}}, "file": b"Time\n1\n"},
}

ALL = sorted(operations())
OWNED = ["Authorization", "content-type", "IDEMPOTENCY-KEY", "X-Request-Id"]
ID = "abc"


def arguments(operation_id: str, *, headers: dict[str, str] | None = None) -> dict[str, Any]:
    """The internal call's arguments for one operation: its path id, and a body of its kind."""
    operation = operations()[operation_id]
    kwargs: dict[str, Any] = {"options": CallOptions(headers=headers)}
    if "{id}" in operation.path:
        kwargs["path"] = [("client_id", ID)]
    if operation.body != "none":
        kwargs["body"] = BODIES[operation.body]
    return kwargs


def run(harness: Harness, operation_id: str, **overrides: Any) -> Any:
    """Call one operation the way its kind calls for, and return what the call returns."""
    kwargs = {**arguments(operation_id), **overrides}
    cls = response_class(operation_id)
    if cls is None:
        harness.call_empty(operation_id, **kwargs)
        return None
    if operations()[operation_id].list_kind is not None:
        # The sync client's Page, or the async client's AsyncPaginator, not yet used.
        return harness.client._transport.call_page(operation_id, cls, item_class(cls), **kwargs)
    return harness.call(operation_id, cls, **kwargs)


def answer(operation_id: str) -> Callable[[httpx.Request], httpx.Response]:
    cls = response_class(operation_id)
    status = operations()[operation_id].status

    def handler(request: httpx.Request) -> httpx.Response:
        if cls is None:
            return httpx.Response(status)
        return json_response(sample(cls), status)

    return handler


def test_every_operation_is_covered_once() -> None:
    assert len(ALL) == 48
    assert len(set(ALL)) == 48


@pytest.mark.parametrize("operation_id", ALL)
def test_each_operation_sends_its_request_and_returns_its_answer(
    make: Callable[..., Harness], operation_id: str
) -> None:
    operation = operations()[operation_id]
    harness = make(answer(operation_id))
    result = run(harness, operation_id, options=CallOptions(headers={"X-Trace": "t-1"}))
    cls = response_class(operation_id)
    if operation.list_kind is not None:
        assert cls is not None
        if harness.mode == "sync":
            assert isinstance(result, Page)
        else:
            # Nothing is sent until the paginator is used.
            assert isinstance(result, AsyncPaginator)
            assert harness.requests == []
            result = asyncio.run(_await(result))
        assert isinstance(result.body, cls)
        assert result.data == result.body.data
    elif cls is None:
        assert result is None
    else:
        assert isinstance(result, cls)

    (request,) = harness.requests
    assert request.method == operation.method
    assert request.url.path == operation.path.replace("{id}", ID)
    content_type = request.headers.get("content-type")
    if operation.body == "none":
        assert content_type is None
        assert request.content == b""
    elif operation.body == "multipart":
        assert content_type is not None
        assert content_type.startswith("multipart/form-data; boundary=")
    else:
        assert content_type == CONTENT_TYPES[operation.body]
        assert json.loads(request.content) == BODIES[operation.body]
    if operation.access == "Public":
        assert "authorization" not in request.headers
    else:
        assert request.headers["authorization"] == f"Bearer {TEST_KEY}"
    if operation.idempotent:
        assert_uuid4(request.headers["idempotency-key"])
    else:
        assert "idempotency-key" not in request.headers
    assert request.headers["x-trace"] == "t-1"
    assert_uuid4(request.headers["x-request-id"])
    assert request.headers["user-agent"].startswith("allisall-python/")


async def _await(paginator: Any) -> Any:
    return await paginator


def send(harness: Harness, operation_id: str) -> None:
    """Call one operation and use its result, so that an async list sends its request."""
    result = run(harness, operation_id)
    if isinstance(result, AsyncPaginator):
        asyncio.run(_await(result))


# --- Path parameters ---


def test_a_path_id_is_sent_as_one_segment(make: Callable[..., Harness]) -> None:
    harness = make(lambda r: json_response(sample(Client)))
    harness.call("getClient", Client, path=[("client_id", "a/b%c?d#e é")])
    (request,) = harness.requests
    assert request.url.raw_path == b"/v1/clients/a%2Fb%25c%3Fd%23e%20%C3%A9"
    assert request.url.query == b""


@pytest.mark.parametrize("value", ["", ".", "..", 7, None])
def test_a_path_id_that_cannot_be_a_segment_is_refused(
    make: Callable[..., Harness], value: object
) -> None:
    harness = make()
    with pytest.raises(ValueError, match="client_id"):
        harness.call_empty("deleteClient", path=[("client_id", value)])
    assert harness.requests == []


def test_the_base_url_path_and_query_come_before_the_call_s(
    make: Callable[..., Harness],
) -> None:
    harness = make(
        lambda r: json_response(sample(ClientValue)), base_url="https://x.test/api/?region=eu"
    )
    harness.call(
        "getClientValue", ClientValue, path=[("client_id", ID)], query={"from_": "2026-01-01"}
    )
    (request,) = harness.requests
    assert request.url.raw_path == b"/api/v1/clients/abc/value?region=eu&from=2026-01-01"


# --- The query ---


def test_the_query_is_written_by_its_wire_names_in_order(make: Callable[..., Harness]) -> None:
    harness = make(lambda r: json_response(sample(ClientEventList)))
    harness.walk(
        "listClientEvents",
        ClientEventList,
        item_class(ClientEventList),
        path=[("client_id", ID)],
        query={
            "from_": datetime(2026, 8, 1, tzinfo=timezone(timedelta(hours=9))),
            "to": "2026-09-01T00:00:00Z",
            "category": None,
            "outcome_type": "a+b &c=d",
            "sort": "cost",
            "dir_": "asc",
            "limit": 20,
            "page": 3,
        },
    )
    (request,) = harness.requests
    assert request.url.query == (
        b"from=2026-08-01T00%3A00%3A00%2B09%3A00&to=2026-09-01T00%3A00%3A00Z"
        b"&outcome_type=a%2Bb%20%26c%3Dd&sort=cost&dir=asc&limit=20&page=3"
    )
    assert httpx.QueryParams(request.url.query.decode())["outcome_type"] == "a+b &c=d"


@pytest.mark.parametrize(
    "value",
    [datetime(2026, 8, 1), True, ["a"], {"a": 1}, 1.5, Decimal(1)],
    ids=["naive", "bool", "list", "dict", "float", "decimal"],
)
def test_a_query_value_of_another_kind_is_refused(
    make: Callable[..., Harness], value: object
) -> None:
    harness = make()
    with pytest.raises(ValueError, match=r"^from_ "):
        harness.call(
            "getClientValue", ClientValue, path=[("client_id", ID)], query={"from_": value}
        )
    assert harness.requests == []


def test_a_lone_surrogate_in_a_path_id_is_refused(make: Callable[..., Harness]) -> None:
    harness = make()
    with pytest.raises(ValueError, match=r"^client_id holds text that is not valid Unicode"):
        harness.call_empty("deleteClient", path=[("client_id", "a\ud800")])
    assert harness.requests == []


def test_a_lone_surrogate_in_a_query_value_is_refused(make: Callable[..., Harness]) -> None:
    harness = make()
    with pytest.raises(ValueError, match=r"^from_ holds text that is not valid Unicode"):
        harness.call(
            "getClientValue",
            ClientValue,
            path=[("client_id", ID)],
            query={"from_": "2026\udfff"},
        )
    assert harness.requests == []


def test_a_naive_query_datetime_has_the_body_s_message(make: Callable[..., Harness]) -> None:
    harness = make()
    message = "from_ is a naive datetime; give it a time zone, such as datetime.UTC"
    with pytest.raises(ValueError, match=f"^{re.escape(message)}$"):
        harness.call(
            "getClientValue",
            ClientValue,
            path=[("client_id", ID)],
            query={"from_": datetime(2026, 8, 1)},
        )


# --- JSON bodies ---


def test_every_member_of_a_body_is_sent(make: Callable[..., Harness]) -> None:
    harness = make(lambda r: json_response(sample(Client), 201))
    harness.call("createClient", Client, body={"name": "Acme", "status": "active", "nmae": "x"})
    (request,) = harness.requests
    assert request.content == b'{"name":"Acme","status":"active","nmae":"x"}'


def test_a_merge_patch_sends_null_to_clear_and_leaves_out_what_is_absent(
    make: Callable[..., Harness],
) -> None:
    harness = make(lambda r: json_response(sample(Client)))
    harness.call("updateClient", Client, path=[("client_id", ID)], body={"notes": None})
    harness.call("updateClient", Client, path=[("client_id", ID)], body={"name": "Acme"})
    first, second = harness.requests
    assert first.headers["content-type"] == "application/merge-patch+json"
    assert first.content == b'{"notes":null}'
    assert second.content == b'{"name":"Acme"}'


@pytest.mark.parametrize("body", [[{"name": "x"}], "x", None, b"{}"])
def test_a_body_that_is_not_a_mapping_is_refused(
    make: Callable[..., Harness], body: object
) -> None:
    harness = make()
    with pytest.raises(ValueError, match="pass a mapping"):
        harness.call("createClient", Client, body=body)
    assert harness.requests == []


@pytest.mark.parametrize(
    ("value", "pointer"),
    [
        (datetime(2026, 1, 1), "/agent_ids/1"),
        (float("nan"), "/agent_ids/1"),
        (Decimal("Infinity"), "/agent_ids/1"),
    ],
)
def test_a_value_that_cannot_be_sent_is_refused_by_its_path(
    make: Callable[..., Harness], value: object, pointer: str
) -> None:
    harness = make()
    with pytest.raises(ValueError, match=pointer):
        harness.call(
            "setClientAgents",
            ClientAgents,
            path=[("client_id", ID)],
            body={"agent_ids": ["a", value]},
        )
    assert harness.requests == []


# --- Credentials ---


def test_get_health_does_not_call_the_token_provider(make: Callable[..., Harness]) -> None:
    calls: list[int] = []

    def provider() -> str:
        calls.append(1)
        return "aia_from_provider"

    def handler(request: httpx.Request) -> httpx.Response:
        return json_response(sample(Health if request.url.path == "/healthz" else Client))

    harness = make(handler, token_provider=provider)
    harness.call("getHealth", Health)
    assert calls == []
    assert "authorization" not in harness.requests[0].headers
    harness.call("getClient", Client, path=[("client_id", ID)])
    assert calls == [1]


def test_the_provider_s_token_is_read_on_every_attempt(make: Callable[..., Harness]) -> None:
    tokens = iter(["aia_one", "aia_two"])
    responses = iter([httpx.Response(503), json_response(sample(Client))])
    harness = make(lambda r: next(responses), token_provider=lambda: next(tokens))
    harness.call("getClient", Client, path=[("client_id", ID)])
    assert [r.headers["authorization"] for r in harness.requests] == [
        "Bearer aia_one",
        "Bearer aia_two",
    ]


class ProviderFailedError(Exception):
    pass


def test_a_provider_error_propagates_unchanged(make: Callable[..., Harness]) -> None:
    calls: list[int] = []

    def provider() -> str:
        calls.append(1)
        raise ProviderFailedError("no session")

    harness = make(token_provider=provider)
    with pytest.raises(ProviderFailedError):
        harness.call("getClient", Client, path=[("client_id", ID)])
    assert calls == [1]
    assert harness.requests == []


def test_a_refused_provider_token_is_an_sdk_error(make: Callable[..., Harness]) -> None:
    harness = make(token_provider=lambda: "  ")
    with pytest.raises(AllisallError, match="empty token"):
        harness.call("getClient", Client, path=[("client_id", ID)])
    assert harness.requests == []


def test_an_async_provider_s_cancellation_propagates_unwrapped() -> None:
    async def provider() -> str:
        raise asyncio.CancelledError

    harness = Harness("async", token_provider=provider)
    with pytest.raises(asyncio.CancelledError):
        harness.call("getClient", Client, path=[("client_id", ID)])
    assert harness.requests == []


# --- Answers ---


@pytest.mark.parametrize(
    ("status", "content"),
    [(204, b""), (200, b"not json"), (202, b'{"unexpected": true}')],
)
def test_an_empty_answer_returns_none_whatever_2xx_body_arrives(
    make: Callable[..., Harness], status: int, content: bytes
) -> None:
    harness = make(lambda r: httpx.Response(status, content=content))
    harness.call_empty("deleteClient", path=[("client_id", ID)])
    assert len(harness.requests) == 1


@pytest.mark.parametrize(
    ("content", "pointer"),
    [
        (b'{"name": "Acme"}', "the required member 'id'"),
        (b"[]", "expected an object"),
        (b"not json", "not JSON"),
        (b'{"value": NaN}', "not JSON"),
    ],
)
def test_a_2xx_body_of_the_wrong_shape_is_an_api_error_not_retried(
    make: Callable[..., Harness], content: bytes, pointer: str
) -> None:
    harness = make(lambda r: httpx.Response(200, content=content, headers={"X-Request-Id": "r1"}))
    with pytest.raises(APIError, match=pointer) as caught:
        harness.call("getClient", Client, path=[("client_id", ID)])
    assert caught.value.status == 200
    assert caught.value.problem is None
    assert caught.value.code is None
    assert caught.value.request_id == "r1"
    assert len(harness.requests) == 1
    assert harness.sleeps == []


def test_a_wrong_money_value_names_its_pointer(make: Callable[..., Harness]) -> None:
    body = sample(ClientValue)
    body["total"] = "12.5"
    harness = make(lambda r: json_response(body))
    with pytest.raises(APIError, match="/total") as caught:
        harness.call("getClientValue", ClientValue, path=[("client_id", ID)])
    assert caught.value.status == 200


def test_money_in_an_answer_is_exact(make: Callable[..., Harness]) -> None:
    body = json.dumps(sample(ClientValue)).replace("12.5", "0.1234567890123456789", 1)
    harness = make(lambda r: httpx.Response(200, content=body.encode()))
    value = harness.call("getClientValue", ClientValue, path=[("client_id", ID)])
    assert Decimal("0.1234567890123456789") in _decimals(value)


def _decimals(value: object) -> list[Decimal]:
    if isinstance(value, Decimal):
        return [value]
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return [d for f in dataclasses.fields(value) for d in _decimals(getattr(value, f.name))]
    if isinstance(value, tuple):
        return [d for item in value for d in _decimals(item)]
    return []


def test_an_error_answer_is_an_api_error_with_its_problem(make: Callable[..., Harness]) -> None:
    harness = make(lambda r: problem(403, "insufficient_scope"))
    with pytest.raises(APIError) as caught:
        harness.call("getClient", Client, path=[("client_id", ID)])
    assert caught.value.status == 403
    assert caught.value.code == "insufficient_scope"
    assert len(harness.requests) == 1


# --- Retries ---


@pytest.mark.parametrize("operation_id", ALL)
def test_three_500s_give_three_attempts_only_when_eligible(
    make: Callable[..., Harness], operation_id: str
) -> None:
    ineligible = {
        "updateClient",
        "updateAgent",
        "updateValueModel",
        "updateCostLineItem",
        "updateReport",
        "previewImport",
        "setValueModelLineItems",
    }
    harness = make(lambda r: httpx.Response(500))
    with pytest.raises(APIError):
        send(harness, operation_id)
    assert len(harness.requests) == (1 if operation_id in ineligible else 3)


def test_an_ineligible_request_is_not_retried_after_a_connection_failure(
    make: Callable[..., Harness],
) -> None:
    def reset(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadError("reset", request=request)

    harness = make(reset)
    with pytest.raises(APIConnectionError):
        harness.call("updateClient", Client, path=[("client_id", ID)], body={"name": "x"})
    assert len(harness.requests) == 1
    harness.requests.clear()
    with pytest.raises(APIConnectionError):
        harness.call("getClient", Client, path=[("client_id", ID)])
    assert len(harness.requests) == 3


def test_an_idempotent_call_reuses_its_key_and_body_on_every_attempt(
    make: Callable[..., Harness],
) -> None:
    responses = iter([httpx.Response(503), httpx.Response(502)])

    def handler(request: httpx.Request) -> httpx.Response:
        return next(responses, None) or json_response(sample(Client), 201)

    harness = make(handler)
    harness.call("createClient", Client, body={"name": "Acme", "status": "active"})
    harness.call("createClient", Client, body={"name": "Acme", "status": "active"})
    first_call, second_call = harness.requests[:3], harness.requests[3:]
    keys = {r.headers["idempotency-key"] for r in first_call}
    assert len(keys) == 1
    assert_uuid4(next(iter(keys)))
    assert len({r.content for r in first_call}) == 1
    assert len({r.headers["x-request-id"] for r in first_call}) == 3
    assert second_call[0].headers["idempotency-key"] not in keys


def test_a_caller_s_idempotency_key_is_sent_on_every_attempt(make: Callable[..., Harness]) -> None:
    responses = iter([httpx.Response(503)])
    harness = make(lambda r: next(responses, None) or json_response(sample(Client), 201))
    harness.call(
        "createClient",
        Client,
        body={"name": "Acme"},
        options=CallOptions(idempotency_key="job-42"),
    )
    assert [r.headers["idempotency-key"] for r in harness.requests] == ["job-42", "job-42"]


@pytest.mark.parametrize("key", ["a\nb", "café", " padded", "padded\t", 42])
def test_an_idempotency_key_that_cannot_be_sent_is_refused(
    make: Callable[..., Harness], key: object
) -> None:
    harness = make()
    with pytest.raises(ValueError, match="idempotency_key"):
        harness.call(
            "createClient",
            Client,
            body={"name": "Acme"},
            # A key of the wrong type on purpose: the check refuses it before sending.
            options=CallOptions(idempotency_key=key),  # type: ignore[arg-type]
        )
    assert harness.requests == []


def test_a_409_key_in_use_is_retried_with_the_same_key(make: Callable[..., Harness]) -> None:
    responses = iter([problem(409, "idempotency_key_in_use")])
    harness = make(lambda r: next(responses, None) or json_response(sample(Client), 201))
    client = harness.call("createClient", Client, body={"name": "Acme"})
    assert isinstance(client, Client)
    first, second = harness.requests
    assert first.headers["idempotency-key"] == second.headers["idempotency-key"]
    assert harness.sleeps == [0.5]


def test_a_409_key_in_use_honours_retry_after(make: Callable[..., Harness]) -> None:
    responses = iter([problem(409, "idempotency_key_in_use", headers={"Retry-After": "3"})])
    harness = make(lambda r: next(responses, None) or json_response(sample(Client), 201))
    harness.call("createClient", Client, body={"name": "Acme"})
    assert harness.sleeps == [3.0]


def test_a_retry_after_of_60_seconds_is_waited(make: Callable[..., Harness]) -> None:
    answers = iter([problem(503, "internal_error", headers={"Retry-After": "60"})])
    harness = make(lambda r: next(answers, None) or json_response(sample(Client)))
    harness.call("getClient", Client, path=[("client_id", ID)])
    assert harness.sleeps == [60.0]
    assert len(harness.requests) == 2


def test_a_retry_after_over_60_seconds_ends_the_call(make: Callable[..., Harness]) -> None:
    harness = make(lambda r: problem(503, "internal_error", headers={"Retry-After": "61"}))
    with pytest.raises(APIError) as caught:
        harness.call("getClient", Client, path=[("client_id", ID)])
    assert caught.value.retry_after == 61.0
    assert harness.sleeps == []
    assert len(harness.requests) == 1


def test_another_409_is_not_retried(make: Callable[..., Harness]) -> None:
    harness = make(lambda r: problem(409, "client_key_in_use"))
    with pytest.raises(APIError):
        harness.call("createClient", Client, body={"name": "Acme"})
    assert len(harness.requests) == 1


def test_a_409_key_in_use_is_not_retried_where_no_key_is_sent(
    make: Callable[..., Harness],
) -> None:
    harness = make(lambda r: problem(409, "idempotency_key_in_use"))
    with pytest.raises(APIError):
        harness.call("setClientAgents", ClientAgents, path=[("client_id", ID)], body={})
    assert len(harness.requests) == 1


# --- Per-call options ---


def test_a_call_s_options_reach_its_request(make: Callable[..., Harness]) -> None:
    seen: list[object] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.extensions["timeout"])
        return httpx.Response(503)

    harness = make(handler, default_headers={"X-Team": "a"})
    with pytest.raises(APIError):
        harness.call(
            "getClient",
            Client,
            path=[("client_id", ID)],
            options=CallOptions(timeout=1.5, max_retries=1, headers={"X-Call": "c"}),
        )
    assert len(harness.requests) == 2
    assert seen[0] == {"connect": 1.5, "read": 1.5, "write": 1.5, "pool": 1.5}
    assert harness.requests[0].headers["x-team"] == "a"
    assert harness.requests[0].headers["x-call"] == "c"


def test_the_client_s_timeout_applies_without_a_call_s(make: Callable[..., Harness]) -> None:
    seen: list[object] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.extensions["timeout"])
        return json_response(sample(Client))

    harness = make(handler, timeout=7.0)
    harness.call("getClient", Client, path=[("client_id", ID)])
    assert seen == [{"connect": 7.0, "read": 7.0, "write": 7.0, "pool": 7.0}]


def test_max_retries_cannot_make_a_patch_eligible(make: Callable[..., Harness]) -> None:
    harness = make(lambda r: httpx.Response(503))
    with pytest.raises(APIError):
        harness.call(
            "updateClient",
            Client,
            path=[("client_id", ID)],
            body={"name": "x"},
            options=CallOptions(max_retries=5),
        )
    assert len(harness.requests) == 1


@pytest.mark.parametrize(
    "options",
    [CallOptions(timeout=0), CallOptions(timeout=float("inf")), CallOptions(max_retries=-1)],
)
def test_a_limit_the_constructor_would_refuse_is_refused(
    make: Callable[..., Harness], options: CallOptions
) -> None:
    harness = make()
    with pytest.raises(AllisallError):
        harness.call("getClient", Client, path=[("client_id", ID)], options=options)
    assert harness.requests == []


@pytest.mark.parametrize("name", OWNED)
def test_a_call_may_not_set_a_header_the_sdk_owns(make: Callable[..., Harness], name: str) -> None:
    harness = make()
    with pytest.raises(ValueError, match="the SDK sets it"):
        harness.call(
            "getClient", Client, path=[("client_id", ID)], options=CallOptions(headers={name: "x"})
        )
    assert harness.requests == []


@pytest.mark.parametrize("name", OWNED)
def test_default_headers_may_not_set_a_header_the_sdk_owns(mode: str, name: str) -> None:
    with pytest.raises(ValueError, match="default_headers may not set"):
        Harness(mode, default_headers={name: "x"})


@pytest.mark.parametrize(
    "headers",
    [
        {"X-A": "line\nbreak"},
        {"X-A": "café"},
        {"X-A": " padded"},
        {"X-A": "padded\t"},
        {"X-A": "nul\x00"},
        {"X A": "x"},
        {"X-é": "x"},
        {"": "x"},
        {"X-A": 1},
        {1: "x"},
        [("X-A", "x")],
        "X-A: x",
    ],
)
def test_headers_that_cannot_be_sent_are_refused(
    make: Callable[..., Harness], headers: object
) -> None:
    harness = make()
    with pytest.raises(ValueError, match=r"^headers "):
        harness.call(
            "getClient",
            Client,
            path=[("client_id", ID)],
            # Headers of the wrong shape on purpose: the check refuses them before sending.
            options=CallOptions(headers=headers),  # type: ignore[arg-type]
        )
    assert harness.requests == []
    with pytest.raises(ValueError, match=r"^default_headers "):
        Harness(harness.mode, default_headers=headers)


def test_a_tab_inside_a_value_and_an_empty_value_are_sent(make: Callable[..., Harness]) -> None:
    harness = make(lambda r: json_response(sample(Client)))
    harness.call(
        "getClient",
        Client,
        path=[("client_id", ID)],
        options=CallOptions(headers={"X-A": "a\tb", "X-B": ""}),
    )
    assert harness.requests[0].headers["x-a"] == "a\tb"
    assert harness.requests[0].headers["x-b"] == ""


def test_a_call_s_header_replaces_a_default_in_another_case(mode: str) -> None:
    defaults = {"X-Team": "a", "X-Keep": "k"}
    harness = Harness(mode, lambda r: json_response(sample(Client)), default_headers=defaults)
    harness.call(
        "getClient",
        Client,
        path=[("client_id", ID)],
        options=CallOptions(headers={"x-team": "b", "user-agent": "wrapper/1"}),
    )
    raw = harness.requests[0].headers.raw
    assert [value for name, value in raw if name.lower() == b"x-team"] == [b"b"]
    assert [value for name, value in raw if name.lower() == b"user-agent"] == [b"wrapper/1"]
    assert harness.requests[0].headers["x-keep"] == "k"


def test_a_header_named_twice_in_one_mapping_sends_the_later(mode: str) -> None:
    harness = Harness(
        mode, lambda r: json_response(sample(Client)), default_headers={"X-D": "1", "x-d": "2"}
    )
    harness.call(
        "getClient",
        Client,
        path=[("client_id", ID)],
        options=CallOptions(headers={"X-C": "1", "x-c": "2"}),
    )
    raw = harness.requests[0].headers.raw
    assert [(k, v) for k, v in raw if k.lower() == b"x-d"] == [(b"x-d", b"2")]
    assert [(k, v) for k, v in raw if k.lower() == b"x-c"] == [(b"x-c", b"2")]


def test_headers_may_be_any_mapping(make: Callable[..., Harness]) -> None:
    harness = make(lambda r: json_response(sample(Client)))
    harness.call(
        "getClient",
        Client,
        path=[("client_id", ID)],
        options=CallOptions(headers=httpx.Headers({"X-A": "1"})),
    )
    assert harness.requests[0].headers["x-a"] == "1"


def test_the_clients_take_default_headers() -> None:
    sync = Allisall(api_key="aia_k", default_headers={"X-A": "1"})
    asynchronous = AsyncAllisall(api_key="aia_k", default_headers={"X-A": "1"})
    assert sync._transport.config.default_headers == {"X-A": "1"}
    assert asynchronous._transport.config.default_headers == {"X-A": "1"}
    sync.close()
    asyncio.run(asynchronous.close())
