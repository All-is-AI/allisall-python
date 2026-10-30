"""Errors: the API error built from a problem document, or from a body that is not one."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable

import httpx
import pytest

from allisall import (
    Allisall,
    AllisallError,
    APIConnectionError,
    APIError,
    AsyncAllisall,
    ErrorCode,
    FieldError,
    FieldErrorCode,
    IngestError,
)

from support import Harness, event


def api_error(harness: Harness) -> APIError:
    with pytest.raises(IngestError) as caught:
        harness.ingest([event(0)])
    cause = caught.value.__cause__
    assert isinstance(cause, APIError)
    return cause


def test_a_problem_document_becomes_an_api_error(make: Callable[..., Harness]) -> None:
    body = {
        "type": "https://api.allisai.ai/errors/validation_failed",
        "title": "The request is invalid",
        "status": 400,
        "detail": "The request has 2 problems.",
        "code": "validation_failed",
        "request_id": "req-123",
        "errors": [
            {"code": "required", "pointer": "/events", "detail": "events is required"},
            {"code": "invalid_value", "header": "Content-Type", "detail": "not JSON"},
        ],
        "added_later": True,
    }
    response = httpx.Response(
        400,
        content=json.dumps(body).encode(),
        headers={"Content-Type": "application/problem+json; charset=utf-8", "X-Request-Id": "x"},
    )
    error = api_error(make(lambda request: response))
    assert error.status == 400
    assert error.code == ErrorCode.VALIDATION_FAILED
    assert error.code == "validation_failed"
    assert error.request_id == "req-123"
    assert error.retry_after is None
    assert error.headers["x-request-id"] == "x"
    assert error.problem is not None
    assert error.problem.type == "https://api.allisai.ai/errors/validation_failed"
    assert error.problem.title == "The request is invalid"
    assert error.problem.detail == "The request has 2 problems."
    assert error.problem.errors == (
        FieldError(code=FieldErrorCode.REQUIRED, detail="events is required", pointer="/events"),
        FieldError(code=FieldErrorCode.INVALID_VALUE, detail="not JSON", header="Content-Type"),
    )
    assert "validation_failed" in str(error)


def test_an_unknown_code_is_kept_as_a_string(make: Callable[..., Harness]) -> None:
    body = {
        "type": "https://api.allisai.ai/errors/brand_new",
        "title": "New",
        "status": 409,
        "detail": "A condition this SDK version does not know.",
        "code": "brand_new",
        "request_id": "req-9",
    }
    response = httpx.Response(
        409, content=json.dumps(body).encode(), headers={"Content-Type": "application/problem+json"}
    )
    error = api_error(make(lambda request: response))
    assert error.code == "brand_new"
    assert type(error.code) is str
    assert error.status == 409
    assert error.problem is not None
    assert error.problem.errors is None


def test_a_body_that_is_not_a_problem(make: Callable[..., Harness]) -> None:
    response = httpx.Response(
        404,
        text="<html>Not here</html>",
        headers={"Content-Type": "text/html", "X-Request-Id": "proxy-id"},
    )
    error = api_error(make(lambda request: response))
    assert error.status == 404
    assert error.code is None
    assert error.problem is None
    assert error.request_id == "proxy-id"


@pytest.mark.parametrize("body", ["[1, 2]", "not json", '"a string"'])
def test_a_problem_media_type_whose_body_is_not_an_object(
    make: Callable[..., Harness], body: str
) -> None:
    response = httpx.Response(400, text=body, headers={"Content-Type": "application/problem+json"})
    error = api_error(make(lambda request: response))
    assert error.status == 400
    assert error.code is None
    assert error.problem is None


def test_a_member_of_the_wrong_type_is_ignored_alone(make: Callable[..., Harness]) -> None:
    body = {
        "type": "https://api.allisai.ai/errors/validation_failed",
        "status": "400",
        "detail": 5,
        "code": "validation_failed",
        "request_id": "req-7",
        "errors": [
            {"code": "required", "pointer": "/events", "detail": "events is required"},
            {"code": 3, "detail": "a malformed entry"},
            "not an object",
        ],
    }
    response = httpx.Response(
        400, content=json.dumps(body).encode(), headers={"Content-Type": "application/problem+json"}
    )
    error = api_error(make(lambda request: response))
    assert error.problem is not None
    assert error.code == ErrorCode.VALIDATION_FAILED
    assert error.request_id == "req-7"
    assert error.problem.type == "https://api.allisai.ai/errors/validation_failed"
    assert error.problem.detail is None
    assert error.problem.status is None
    assert error.problem.title is None
    assert error.problem.errors == (
        FieldError(code=FieldErrorCode.REQUIRED, detail="events is required", pointer="/events"),
    )


def test_a_problem_object_with_no_code(make: Callable[..., Harness]) -> None:
    response = httpx.Response(
        400, text='{"status": 400}', headers={"Content-Type": "application/problem+json"}
    )
    error = api_error(make(lambda request: response))
    assert error.status == 400
    assert error.code is None
    assert error.problem is not None
    assert error.problem.status == 400


@pytest.mark.parametrize("request_id", ["", None, 42])
def test_an_unusable_problem_request_id_falls_back_on_the_header(
    make: Callable[..., Harness], request_id: object
) -> None:
    body = {"status": 404, "code": "not_found", "detail": "gone", "request_id": request_id}
    response = httpx.Response(
        404,
        content=json.dumps(body).encode(),
        headers={"Content-Type": "application/problem+json", "X-Request-Id": "from-header"},
    )
    error = api_error(make(lambda request: response))
    assert error.code == ErrorCode.NOT_FOUND
    assert error.request_id == "from-header"


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_a_redirect_is_an_api_error_and_not_followed(
    make: Callable[..., Harness], status: int
) -> None:
    redirect = httpx.Response(
        status, headers={"Location": "https://elsewhere.test/v1/events", "X-Request-Id": "r-1"}
    )
    harness = make(lambda request: redirect)
    error = api_error(harness)
    assert error.status == status
    assert error.request_id == "r-1"
    assert len(harness.requests) == 1
    assert harness.sleeps == []


def test_a_callers_client_that_follows_redirects_does_not_follow_ours(mode: str) -> None:
    # The caller's client is built to follow redirects; the SDK still refuses them per request.
    target = "https://elsewhere.test/v1/events"
    seen: list[str] = []
    sleeps: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        if str(request.url) == target:
            return httpx.Response(200, json={"accepted": 1})
        return httpx.Response(307, headers={"Location": target, "X-Request-Id": "r-307"})

    transport = httpx.MockTransport(handler)
    if mode == "sync":
        http = httpx.Client(transport=transport, follow_redirects=True)
        client = Allisall(api_key="aia_x", http_client=http)
        client._transport.sleep = sleeps.append
        run = lambda: client.events.ingest([event(0)])  # noqa: E731
    else:
        ahttp = httpx.AsyncClient(transport=transport, follow_redirects=True)
        aclient = AsyncAllisall(api_key="aia_x", http_client=ahttp)

        async def record(seconds: float) -> None:
            sleeps.append(seconds)

        aclient._transport.sleep = record
        run = lambda: asyncio.run(aclient.events.ingest([event(0)]))  # noqa: E731

    with pytest.raises(IngestError) as caught:
        run()
    cause = caught.value.__cause__
    assert isinstance(cause, APIError)
    assert cause.status == 307
    assert cause.request_id == "r-307"
    assert seen == ["https://api.allisai.ai/v1/events"]
    assert target not in seen
    assert sleeps == []


def test_the_error_hierarchy() -> None:
    for kind in (APIError, APIConnectionError, IngestError):
        assert issubclass(kind, AllisallError)
    assert issubclass(AllisallError, Exception)
    assert not issubclass(APIConnectionError, ConnectionError)


def test_codes_compare_equal_to_their_strings() -> None:
    assert ErrorCode.RATE_LIMITED == "rate_limited"
    assert FieldErrorCode.TOO_LARGE == "too_large"
    assert ErrorCode("internal_error") is ErrorCode.INTERNAL_ERROR
