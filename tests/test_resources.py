"""The operation groups of both clients: their names, their signatures, and what each method
sends and returns.

Each method's request is written out here by hand, as the method, path, query and body the
API expects, so a method that calls the wrong operation or drops an argument fails. The tests
that hold the names and signatures to the OpenAPI document run in the monorepo only.
"""

from __future__ import annotations

import asyncio
import copy
import dataclasses
import inspect
import json
import re
import typing
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Literal

import httpx
import pytest

import allisall
from allisall import (
    Agent,
    AgentDetail,
    AgentList,
    AgentListItem,
    Allisall,
    Anomalies,
    AsyncAllisall,
    AsyncPage,
    AsyncPaginator,
    AttributedEvent,
    Calculation,
    CalculationList,
    CalculationSummary,
    Client,
    ClientAgents,
    ClientCost,
    ClientDetail,
    ClientEventList,
    ClientList,
    ClientValue,
    CostLineItem,
    CostLineItemList,
    Dashboard,
    Health,
    ImportPreview,
    ImportResult,
    IngestSummary,
    OutcomeTypeList,
    OutcomeTypeUsage,
    Page,
    PriceTable,
    Renewal,
    RenewalList,
    Report,
    ReportList,
    ReportSummary,
    ReportWithPreview,
    RoiResult,
    ValueModel,
    ValueModelList,
    ValueModelSummary,
    ValueTemplate,
    ValueTemplateList,
)
from allisall._generated import requests as request_types
from allisall._generated import responses
from allisall._operations import OPERATIONS
from samples import item_class, response_class, sample
from test_generated import response_money
from test_operations import spec_operations
from test_spec import load_spec

from support import TEST_KEY, Harness

GROUPS = [
    "events",
    "imports",
    "clients",
    "agents",
    "value_models",
    "outcome_types",
    "cost",
    "analytics",
    "calculations",
    "reports",
    "dashboard",
    "health",
]

CLIENT = "client-1"
AGENT = "agent-1"
MODEL = "model-1"
LINE_ITEM = "item-1"
CALCULATION = "calc-1"
REPORT = "report-1"

KEY = "caller-key-1"
"""The `idempotency_key` passed to each of the seven idempotent methods."""

OPTIONS: dict[str, Any] = {"headers": {"X-Trace": "t-1"}, "timeout": 7.5}
"""Passed to every method, which must forward them to its request."""

EXACT = "0.1234567890123456789"
"""Money no float holds: the decoder must keep its text."""

# Listed here, not read from the code under test.
IDEMPOTENT = {
    "commitImport",
    "createClient",
    "createAgent",
    "createValueModel",
    "createCostLineItem",
    "createCalculation",
    "createReport",
}
MONEY_OPERATIONS = {
    "createCalculation",
    "createCostLineItem",
    "createValueModel",
    "getAgent",
    "getCalculation",
    "getClientAnomalies",
    "getClientCost",
    "getClientRoi",
    "getClientValue",
    "getClientValueModel",
    "getCostLineItem",
    "getDashboard",
    "getPriceTable",
    "getReport",
    "getValueModel",
    "listClientCalculations",
    "listClientEvents",
    "listCostLineItems",
    "listValueTemplates",
    "previewImport",
    "setPriceTable",
    "setValueModelLineItems",
    "updateCostLineItem",
    "updateValueModel",
}
"""The operations whose answer holds money."""

CSV = b"Time,Agent\n2026-08-14 12:12:40,support-bot\n"
UPLOAD: dict[str, Any] = {
    "mapping": {"columns": {"timestamp": "Time", "agent_key": "Agent"}},
    "file": CSV,
}


class _Multipart:
    """The expected body of an import: a form holding the mapping and the file."""


MULTIPART = _Multipart()


@dataclass(frozen=True)
class Case:
    """One method, called with every kind of argument it takes, and the request it must send."""

    operation_id: str
    method: str
    """`group.method`, for the test's id."""
    call: Callable[[Any], Any]
    http: str
    path: str
    returns: type | None
    """The decoded answer's class, a list's body, or `None` for an empty answer."""
    item: type | None = None
    """A list's item class."""
    query: tuple[tuple[str, str], ...] = ()
    body: object = None
    """The JSON sent, `MULTIPART`, or `None` for no body."""


def _ingest(c: Any) -> Any:
    return c.events.ingest(
        [
            {
                "event_id": "e-1",
                "timestamp": "2026-08-14T03:12:40Z",
                "agent_key": "support-bot",
                "category": "task",
                "event_type": "triage",
            }
        ],
        **OPTIONS,
    )


TOKYO = timezone(timedelta(hours=9))
FROM = datetime(2026, 8, 1, tzinfo=TOKYO)
FROM_TEXT = "2026-08-01T00:00:00+09:00"
TO = "2026-09-01T00:00:00Z"
PERIOD = (("from", FROM_TEXT), ("to", TO))

CASES = [
    Case(
        "ingestEvents",
        "events.ingest",
        _ingest,
        "POST",
        "/v1/events",
        IngestSummary,
        body={
            "events": [
                {
                    "event_id": "e-1",
                    "timestamp": "2026-08-14T03:12:40Z",
                    "agent_key": "support-bot",
                    "category": "task",
                    "event_type": "triage",
                }
            ]
        },
    ),
    Case(
        "listClientEvents",
        "events.list_for_client",
        lambda c: c.events.list_for_client(
            CLIENT,
            from_=FROM,
            to=TO,
            category="model",
            outcome_type="ticket_resolved",
            agent_id=AGENT,
            sort="cost",
            dir_="asc",
            limit=2,
            page=3,
            **OPTIONS,
        ),
        "GET",
        "/v1/clients/client-1/events",
        ClientEventList,
        AttributedEvent,
        query=(
            *PERIOD,
            ("category", "model"),
            ("outcome_type", "ticket_resolved"),
            ("agent_id", AGENT),
            ("sort", "cost"),
            ("dir", "asc"),
            ("limit", "2"),
            ("page", "3"),
        ),
    ),
    Case(
        "previewImport",
        "imports.preview",
        lambda c: c.imports.preview(UPLOAD, **OPTIONS),
        "POST",
        "/v1/imports/preview",
        ImportPreview,
        body=MULTIPART,
    ),
    Case(
        "commitImport",
        "imports.commit",
        lambda c: c.imports.commit(UPLOAD, idempotency_key=KEY, **OPTIONS),
        "POST",
        "/v1/imports",
        ImportResult,
        body=MULTIPART,
    ),
    Case(
        "listClients",
        "clients.list",
        lambda c: c.clients.list(limit=2, cursor="from-caller", **OPTIONS),
        "GET",
        "/v1/clients",
        ClientList,
        Client,
        query=(("limit", "2"), ("cursor", "from-caller")),
    ),
    Case(
        "createClient",
        "clients.create",
        lambda c: c.clients.create(
            {"name": "Acme", "status": "active", "renewal_date": date(2026, 12, 31)},
            idempotency_key=KEY,
            **OPTIONS,
        ),
        "POST",
        "/v1/clients",
        Client,
        body={"name": "Acme", "status": "active", "renewal_date": "2026-12-31"},
    ),
    Case(
        "getClient",
        "clients.get",
        lambda c: c.clients.get(CLIENT, **OPTIONS),
        "GET",
        "/v1/clients/client-1",
        ClientDetail,
    ),
    Case(
        "updateClient",
        "clients.update",
        lambda c: c.clients.update(CLIENT, {"notes": None, "status": "churned"}, **OPTIONS),
        "PATCH",
        "/v1/clients/client-1",
        Client,
        body={"notes": None, "status": "churned"},
    ),
    Case(
        "deleteClient",
        "clients.delete",
        lambda c: c.clients.delete(CLIENT, **OPTIONS),
        "DELETE",
        "/v1/clients/client-1",
        None,
    ),
    Case(
        "setClientAgents",
        "clients.set_agents",
        lambda c: c.clients.set_agents(CLIENT, {"agent_ids": [AGENT]}, **OPTIONS),
        "PUT",
        "/v1/clients/client-1/agents",
        ClientAgents,
        body={"agent_ids": [AGENT]},
    ),
    Case(
        "listAgents",
        "agents.list",
        lambda c: c.agents.list(limit=2, **OPTIONS),
        "GET",
        "/v1/agents",
        AgentList,
        AgentListItem,
        query=(("limit", "2"),),
    ),
    Case(
        "createAgent",
        "agents.create",
        lambda c: c.agents.create(
            {"agent_key": "support-bot", "name": "Support bot", "status": "active"},
            idempotency_key=KEY,
            **OPTIONS,
        ),
        "POST",
        "/v1/agents",
        Agent,
        body={"agent_key": "support-bot", "name": "Support bot", "status": "active"},
    ),
    Case(
        "getAgent",
        "agents.get",
        lambda c: c.agents.get(AGENT, from_=FROM, to=TO, **OPTIONS),
        "GET",
        "/v1/agents/agent-1",
        AgentDetail,
        query=PERIOD,
    ),
    Case(
        "updateAgent",
        "agents.update",
        lambda c: c.agents.update(AGENT, {"status": "retired", "framework": None}, **OPTIONS),
        "PATCH",
        "/v1/agents/agent-1",
        Agent,
        body={"status": "retired", "framework": None},
    ),
    Case(
        "deleteAgent",
        "agents.delete",
        lambda c: c.agents.delete(AGENT, **OPTIONS),
        "DELETE",
        "/v1/agents/agent-1",
        None,
    ),
    Case(
        "listValueModels",
        "value_models.list",
        lambda c: c.value_models.list(limit=2, **OPTIONS),
        "GET",
        "/v1/value-models",
        ValueModelList,
        ValueModelSummary,
        query=(("limit", "2"),),
    ),
    Case(
        "getValueModel",
        "value_models.get",
        lambda c: c.value_models.get(MODEL, **OPTIONS),
        "GET",
        "/v1/value-models/model-1",
        ValueModel,
    ),
    Case(
        "getClientValueModel",
        "value_models.get_for_client",
        lambda c: c.value_models.get_for_client(CLIENT, **OPTIONS),
        "GET",
        "/v1/clients/client-1/value-model",
        ValueModel,
    ),
    Case(
        "createValueModel",
        "value_models.create_for_client",
        lambda c: c.value_models.create_for_client(
            CLIENT, {"name": "Acme value"}, idempotency_key=KEY, **OPTIONS
        ),
        "POST",
        "/v1/clients/client-1/value-model",
        ValueModel,
        body={"name": "Acme value"},
    ),
    Case(
        "updateValueModel",
        "value_models.update_for_client",
        lambda c: c.value_models.update_for_client(CLIENT, {"status": "archived"}, **OPTIONS),
        "PATCH",
        "/v1/clients/client-1/value-model",
        ValueModel,
        body={"status": "archived"},
    ),
    Case(
        "deleteValueModel",
        "value_models.delete_for_client",
        lambda c: c.value_models.delete_for_client(CLIENT, **OPTIONS),
        "DELETE",
        "/v1/clients/client-1/value-model",
        None,
    ),
    Case(
        "setValueModelLineItems",
        "value_models.set_line_items_for_client",
        lambda c: c.value_models.set_line_items_for_client(
            CLIENT,
            {
                "version": 3,
                "line_items": [
                    {"outcome_type": "resolved", "label": "Resolved", "unit_value": Decimal(EXACT)}
                ],
            },
            **OPTIONS,
        ),
        "PUT",
        "/v1/clients/client-1/value-model/line-items",
        ValueModel,
        body={
            "version": 3,
            "line_items": [
                {"outcome_type": "resolved", "label": "Resolved", "unit_value": Decimal(EXACT)}
            ],
        },
    ),
    Case(
        "listValueTemplates",
        "value_models.list_templates",
        lambda c: c.value_models.list_templates(limit=2, **OPTIONS),
        "GET",
        "/v1/value-templates",
        ValueTemplateList,
        ValueTemplate,
        query=(("limit", "2"),),
    ),
    Case(
        "listOutcomeTypes",
        "outcome_types.list",
        lambda c: c.outcome_types.list(from_=FROM, to=TO, limit=2, **OPTIONS),
        "GET",
        "/v1/outcome-types",
        OutcomeTypeList,
        OutcomeTypeUsage,
        query=(*PERIOD, ("limit", "2")),
    ),
    Case(
        "listClientOutcomeTypes",
        "outcome_types.list_for_client",
        lambda c: c.outcome_types.list_for_client(CLIENT, from_=FROM, to=TO, limit=2, **OPTIONS),
        "GET",
        "/v1/clients/client-1/outcome-types",
        OutcomeTypeList,
        OutcomeTypeUsage,
        query=(*PERIOD, ("limit", "2")),
    ),
    Case(
        "listCostLineItems",
        "cost.list_line_items",
        lambda c: c.cost.list_line_items(limit=2, **OPTIONS),
        "GET",
        "/v1/cost-line-items",
        CostLineItemList,
        CostLineItem,
        query=(("limit", "2"),),
    ),
    Case(
        "createCostLineItem",
        "cost.create_line_item",
        lambda c: c.cost.create_line_item(
            {
                "label": "Hosting",
                "target": {"kind": "client", "id": CLIENT},
                "monthly_amount": Decimal(EXACT),
                "start_date": date(2026, 7, 1),
            },
            idempotency_key=KEY,
            **OPTIONS,
        ),
        "POST",
        "/v1/cost-line-items",
        CostLineItem,
        body={
            "label": "Hosting",
            "target": {"kind": "client", "id": CLIENT},
            "monthly_amount": Decimal(EXACT),
            "start_date": "2026-07-01",
        },
    ),
    Case(
        "getCostLineItem",
        "cost.get_line_item",
        lambda c: c.cost.get_line_item(LINE_ITEM, **OPTIONS),
        "GET",
        "/v1/cost-line-items/item-1",
        CostLineItem,
    ),
    Case(
        "updateCostLineItem",
        "cost.update_line_item",
        lambda c: c.cost.update_line_item(
            LINE_ITEM, {"end_date": None, "monthly_amount": 1200}, **OPTIONS
        ),
        "PATCH",
        "/v1/cost-line-items/item-1",
        CostLineItem,
        body={"end_date": None, "monthly_amount": 1200},
    ),
    Case(
        "deleteCostLineItem",
        "cost.delete_line_item",
        lambda c: c.cost.delete_line_item(LINE_ITEM, **OPTIONS),
        "DELETE",
        "/v1/cost-line-items/item-1",
        None,
    ),
    Case(
        "getPriceTable",
        "cost.get_price_table",
        lambda c: c.cost.get_price_table(**OPTIONS),
        "GET",
        "/v1/price-table",
        PriceTable,
    ),
    Case(
        "setPriceTable",
        "cost.set_price_table",
        lambda c: c.cost.set_price_table(
            {"models": [{"model": "gpt-4o", "input_per_1k": 0.375, "output_per_1k": 1.5}]},
            **OPTIONS,
        ),
        "PUT",
        "/v1/price-table",
        PriceTable,
        body={"models": [{"model": "gpt-4o", "input_per_1k": 0.375, "output_per_1k": 1.5}]},
    ),
    Case(
        "getClientValue",
        "analytics.get_value_for_client",
        lambda c: c.analytics.get_value_for_client(CLIENT, from_=FROM, to=TO, **OPTIONS),
        "GET",
        "/v1/clients/client-1/value",
        ClientValue,
        query=PERIOD,
    ),
    Case(
        "getClientCost",
        "analytics.get_cost_for_client",
        lambda c: c.analytics.get_cost_for_client(CLIENT, from_=FROM, to=TO, **OPTIONS),
        "GET",
        "/v1/clients/client-1/cost",
        ClientCost,
        query=PERIOD,
    ),
    Case(
        "getClientRoi",
        "analytics.get_roi_for_client",
        lambda c: c.analytics.get_roi_for_client(CLIENT, from_=FROM, to=TO, **OPTIONS),
        "GET",
        "/v1/clients/client-1/roi",
        RoiResult,
        query=PERIOD,
    ),
    Case(
        "getClientAnomalies",
        "analytics.get_anomalies_for_client",
        lambda c: c.analytics.get_anomalies_for_client(CLIENT, from_=FROM, to=TO, **OPTIONS),
        "GET",
        "/v1/clients/client-1/anomalies",
        Anomalies,
        query=PERIOD,
    ),
    Case(
        "createCalculation",
        "calculations.create_for_client",
        lambda c: c.calculations.create_for_client(
            CLIENT,
            {"period": {"from": datetime(2026, 8, 1, tzinfo=UTC), "to": TO}},
            idempotency_key=KEY,
            **OPTIONS,
        ),
        "POST",
        "/v1/clients/client-1/calculations",
        Calculation,
        body={"period": {"from": "2026-08-01T00:00:00+00:00", "to": TO}},
    ),
    Case(
        "listClientCalculations",
        "calculations.list_for_client",
        lambda c: c.calculations.list_for_client(CLIENT, limit=2, **OPTIONS),
        "GET",
        "/v1/clients/client-1/calculations",
        CalculationList,
        CalculationSummary,
        query=(("limit", "2"),),
    ),
    Case(
        "getCalculation",
        "calculations.get",
        lambda c: c.calculations.get(CALCULATION, **OPTIONS),
        "GET",
        "/v1/calculations/calc-1",
        Calculation,
    ),
    Case(
        "deleteCalculation",
        "calculations.delete",
        lambda c: c.calculations.delete(CALCULATION, **OPTIONS),
        "DELETE",
        "/v1/calculations/calc-1",
        None,
    ),
    Case(
        "createReport",
        "reports.create_for_calculation",
        lambda c: c.reports.create_for_calculation(CALCULATION, idempotency_key=KEY, **OPTIONS),
        "POST",
        "/v1/calculations/calc-1/reports",
        Report,
    ),
    Case(
        "listCalculationReports",
        "reports.list_for_calculation",
        lambda c: c.reports.list_for_calculation(CALCULATION, limit=2, **OPTIONS),
        "GET",
        "/v1/calculations/calc-1/reports",
        ReportList,
        ReportSummary,
        query=(("limit", "2"),),
    ),
    Case(
        "getReport",
        "reports.get",
        lambda c: c.reports.get(REPORT, **OPTIONS),
        "GET",
        "/v1/reports/report-1",
        ReportWithPreview,
    ),
    Case(
        "updateReport",
        "reports.update",
        lambda c: c.reports.update(REPORT, {"note": None}, **OPTIONS),
        "PATCH",
        "/v1/reports/report-1",
        Report,
        body={"note": None},
    ),
    Case(
        "deleteReport",
        "reports.delete",
        lambda c: c.reports.delete(REPORT, **OPTIONS),
        "DELETE",
        "/v1/reports/report-1",
        None,
    ),
    Case(
        "getDashboard",
        "dashboard.get",
        lambda c: c.dashboard.get(month="2026-08", sort="roi", dir_="desc", **OPTIONS),
        "GET",
        "/v1/dashboard",
        Dashboard,
        query=(("month", "2026-08"), ("sort", "roi"), ("dir", "desc")),
    ),
    Case(
        "listRenewals",
        "dashboard.list_renewals",
        lambda c: c.dashboard.list_renewals(limit=2, **OPTIONS),
        "GET",
        "/v1/dashboard/renewals",
        RenewalList,
        Renewal,
        query=(("limit", "2"),),
    ),
    Case(
        "getHealth",
        "health.get",
        lambda c: c.health.get(**OPTIONS),
        "GET",
        "/healthz",
        Health,
    ),
]

LISTS = [case for case in CASES if case.item is not None]


def _id(case: Case) -> str:
    return case.method


INGEST_ANSWER = {
    "accepted": 1,
    "duplicates": 0,
    "rejected": 0,
    "errors": [],
    "errors_truncated": False,
}


def answer_body(cls: type) -> bytes:
    """A whole answer of `cls`, every money value the exact text `EXACT`."""
    marker = "__money__"
    text = json.dumps(sample(cls, money=marker))
    return text.replace(json.dumps(marker), EXACT).encode()


def answer(case: Case) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        if case.returns is None:
            return httpx.Response(204)
        if case.returns is IngestSummary:
            return httpx.Response(200, json=INGEST_ANSWER)
        return httpx.Response(
            200, content=answer_body(case.returns), headers={"Content-Type": "application/json"}
        )

    return handler


async def _await(value: Any) -> Any:
    return await value


def invoke(harness: Harness, case: Case) -> Any:
    """Call the case's method and return what the caller ends up with: a sync result, or the
    awaited async one. An async list method must hand back an unsent `AsyncPaginator`."""
    result = case.call(harness.client)
    if harness.mode == "sync":
        assert not inspect.isawaitable(result)
        return result
    if case.item is not None:
        assert isinstance(result, AsyncPaginator)
        assert harness.requests == []
    else:
        assert inspect.iscoroutine(result)
    return asyncio.run(_await(result))


def decimals(value: object) -> list[Decimal]:
    """Every `Decimal` in a decoded value."""
    if isinstance(value, Decimal):
        return [value]
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return [d for f in dataclasses.fields(value) for d in decimals(getattr(value, f.name))]
    if isinstance(value, tuple | list):
        return [d for item in value for d in decimals(item)]
    if isinstance(value, Mapping):
        return [d for item in value.values() for d in decimals(item)]
    return []


# --- The groups ---


def test_every_operation_has_one_case() -> None:
    ids = [case.operation_id for case in CASES]
    assert len(ids) == 48
    assert set(ids) == set(OPERATIONS)


@pytest.mark.parametrize("client_class", [Allisall, AsyncAllisall])
def test_the_client_has_exactly_the_twelve_groups(client_class: type) -> None:
    client = client_class(api_key=TEST_KEY)
    public = [name for name in vars(client) if not name.startswith("_")]
    assert sorted(public) == sorted(GROUPS)
    for name in GROUPS:
        group = getattr(client, name)
        assert type(group).__module__.startswith("allisall._resources."), name


# --- Every method ---


@pytest.mark.parametrize("case", CASES, ids=_id)
def test_each_method_sends_its_request_and_returns_its_answer(
    make: Callable[..., Harness], case: Case
) -> None:
    harness = make(answer(case))
    result = invoke(harness, case)

    (request,) = harness.requests
    assert request.method == case.http
    assert request.url.raw_path.split(b"?")[0].decode() == case.path
    assert request.url.params.multi_items() == list(case.query)
    content_type = request.headers.get("content-type")
    if case.body is None:
        assert content_type is None
        assert request.content == b""
    elif case.body is MULTIPART:
        assert content_type is not None
        assert content_type.startswith("multipart/form-data; boundary=")
        assert CSV in request.content
        assert b'"timestamp":"Time"' in request.content
    else:
        expected_type = (
            "application/merge-patch+json" if case.http == "PATCH" else "application/json"
        )
        assert content_type == expected_type
        assert json.loads(request.content, parse_float=Decimal) == case.body
    if case.operation_id in IDEMPOTENT:
        assert request.headers["idempotency-key"] == KEY
    else:
        assert "idempotency-key" not in request.headers
    if case.operation_id == "getHealth":
        assert "authorization" not in request.headers
    else:
        assert request.headers["authorization"] == f"Bearer {TEST_KEY}"
    assert request.headers["x-trace"] == "t-1"
    assert request.extensions["timeout"] == {
        "connect": 7.5,
        "read": 7.5,
        "write": 7.5,
        "pool": 7.5,
    }

    if case.returns is None:
        assert result is None
        return
    if case.item is not None:
        assert isinstance(result, Page if harness.mode == "sync" else AsyncPage)
        assert isinstance(result.body, case.returns)
        assert result.data
        assert all(isinstance(item, case.item) for item in result.data)
        decoded = result.body
    else:
        assert isinstance(result, case.returns)
        decoded = result
    found = decimals(decoded)
    if case.operation_id in MONEY_OPERATIONS:
        assert found
        for value in found:
            assert value == Decimal(EXACT)
            assert format(value, "f") == EXACT
    else:
        assert found == []


def test_the_money_operations_are_the_document_s() -> None:
    _, operations, _ = response_money(load_spec(), responses)
    assert operations == MONEY_OPERATIONS
    assert len(MONEY_OPERATIONS) == 24


def complete(harness: Harness, call: Callable[[Any], Any]) -> Any:
    """Call a method that is not a list, and await it on the async client."""
    result = call(harness.client)
    if harness.mode == "async":
        return asyncio.run(_await(result))
    return result


def test_a_patch_method_is_not_retried(make: Callable[..., Harness]) -> None:
    harness = make(lambda r: httpx.Response(503))
    with pytest.raises(allisall.APIError):
        complete(harness, lambda c: c.clients.update(CLIENT, {"notes": None}, max_retries=5))
    assert len(harness.requests) == 1


def test_setting_line_items_is_never_retried(make: Callable[..., Harness]) -> None:
    harness = make(lambda r: httpx.Response(503))
    with pytest.raises(allisall.APIError):
        complete(
            harness,
            lambda c: c.value_models.set_line_items_for_client(
                CLIENT, {"version": 3, "line_items": []}, max_retries=5
            ),
        )
    assert len(harness.requests) == 1


@pytest.mark.parametrize(
    "call",
    [
        lambda c: c.clients.set_agents(CLIENT, {"agent_ids": []}, max_retries=2),
        lambda c: c.cost.set_price_table({"models": []}, max_retries=2),
    ],
    ids=["clients.set_agents", "cost.set_price_table"],
)
def test_the_other_put_methods_are_retried(
    make: Callable[..., Harness], call: Callable[[Any], Any]
) -> None:
    harness = make(lambda r: httpx.Response(503))
    with pytest.raises(allisall.APIError):
        complete(harness, call)
    assert len(harness.requests) == 3


def flat_doc(method: Callable[..., Any]) -> str:
    """A method's docstring with its line breaks folded into spaces."""
    return " ".join((inspect.getdoc(method) or "").split())


@pytest.mark.parametrize("client_class", [Allisall, AsyncAllisall])
def test_each_put_method_says_whether_it_is_retried(client_class: type) -> None:
    client = client_class(api_key=TEST_KEY)
    line_items = flat_doc(client.value_models.set_line_items_for_client)
    assert "Never retried" in line_items
    assert "read the value model again for its current `version` before trying again" in (
        line_items
    )
    for method in (client.clients.set_agents, client.cost.set_price_table):
        assert "Retried as `max_retries` allows, because sending the same" in flat_doc(method)


def test_a_get_method_is_retried(make: Callable[..., Harness]) -> None:
    harness = make(lambda r: httpx.Response(503))
    with pytest.raises(allisall.APIError):
        complete(harness, lambda c: c.clients.get(CLIENT, max_retries=2))
    assert len(harness.requests) == 3


# --- Walks ---


def two_pages(case: Case) -> Callable[[httpx.Request], httpx.Response]:
    """Answer the list call with a page naming `next-1`, and that cursor with the last page."""
    assert case.returns is not None

    def handler(request: httpx.Request) -> httpx.Response:
        body = sample(case.returns)
        last = request.url.params.get("cursor") == "next-1"
        body["has_more"] = not last
        body["next_cursor"] = None if last else "next-1"
        return httpx.Response(200, json=body)

    return handler


@pytest.mark.parametrize("case", LISTS, ids=_id)
def test_a_list_method_walks_every_page(make: Callable[..., Harness], case: Case) -> None:
    harness = make(two_pages(case))
    result = case.call(harness.client)
    if harness.mode == "sync":
        items = list(result)
    else:

        async def walk() -> list[Any]:
            return [item async for item in result]

        items = asyncio.run(walk())
    assert len(items) == 2
    assert all(isinstance(item, case.item) for item in items)
    first, second = harness.requests
    assert first.url.params.multi_items() == list(case.query)
    # The same filters, without `page`, and the first page's cursor.
    expected = {name: value for name, value in case.query if name != "page"}
    expected["cursor"] = "next-1"
    sent = second.url.params.multi_items()
    assert len(sent) == len(expected)
    assert dict(sent) == expected
    assert second.url.raw_path.split(b"?")[0].decode() == case.path
    assert second.headers["x-trace"] == "t-1"


REPORT_SUMMARY: dict[str, object] = {
    "id": "report-1",
    "calculation_id": CALCULATION,
    "client_name": "Acme",
    "workspace_name": "Northwind",
    "note": "",
    "share_token": None,
    "shared_at": None,
    "revoked_at": None,
    "first_viewed_at": None,
    "last_viewed_at": None,
    "created_at": "2026-09-01T00:00:00Z",
}


def test_a_report_list_item_is_a_summary_without_disclosures(
    make: Callable[..., Harness],
) -> None:
    # The second item still carries `disclosures`, as an older server sent it: a member the
    # summary does not list is ignored, never refused.
    with_disclosures = {
        **REPORT_SUMMARY,
        "id": "report-2",
        "disclosures": [{"kind": "unpriced", "facts": {}, "included": True, "text": None}],
    }
    body = {"data": [REPORT_SUMMARY, with_disclosures], "has_more": False, "next_cursor": None}
    harness = make(lambda r: httpx.Response(200, json=body))
    result = harness.client.reports.list_for_calculation(CALCULATION)
    page = result if harness.mode == "sync" else asyncio.run(_await(result))
    assert [type(item) for item in page.data] == [ReportSummary, ReportSummary]
    assert [item.id for item in page.data] == ["report-1", "report-2"]
    assert page.data[0].client_name == "Acme"
    assert page.data[0].created_at == "2026-09-01T00:00:00Z"
    for item in page.data:
        assert not hasattr(item, "disclosures")
    assert "disclosures" not in {f.name for f in dataclasses.fields(ReportSummary)}


def test_eleven_methods_are_lists() -> None:
    assert len(LISTS) == 11


# --- The two classes of a group ---


def methods(group: object) -> dict[str, Callable[..., Any]]:
    """The public methods of a group's class, by name."""
    return {
        name: member
        for name, member in inspect.getmembers(type(group), inspect.isfunction)
        if not name.startswith("_")
    }


@pytest.mark.parametrize("group", GROUPS)
def test_the_sync_and_async_classes_of_a_group_have_the_same_methods(group: str) -> None:
    sync = methods(getattr(Allisall(api_key=TEST_KEY), group))
    async_ = methods(getattr(AsyncAllisall(api_key=TEST_KEY), group))
    assert sync
    assert sorted(sync) == sorted(async_)
    for name, function in sync.items():
        sync_signature = inspect.signature(function)
        async_signature = inspect.signature(async_[name])
        # The parameters, with their kinds, defaults and annotations; the return type aside.
        assert list(sync_signature.parameters.values()) == list(
            async_signature.parameters.values()
        ), f"{group}.{name}"
        assert not inspect.iscoroutinefunction(function), f"{group}.{name}"
        is_list = str(async_signature.return_annotation).startswith("AsyncPaginator[")
        assert str(sync_signature.return_annotation).startswith("Page[") == is_list
        # A list method hands back an AsyncPaginator; every other method is a coroutine.
        assert inspect.iscoroutinefunction(async_[name]) != is_list, f"{group}.{name}"


def test_the_group_classes_are_named_for_their_group() -> None:
    sync = Allisall(api_key=TEST_KEY)
    async_ = AsyncAllisall(api_key=TEST_KEY)
    for group in GROUPS:
        stem = "".join(word.capitalize() for word in group.split("_"))
        assert type(getattr(sync, group)).__name__ == f"{stem}Resource"
        assert type(getattr(async_, group)).__name__ == f"Async{stem}Resource"
        assert not hasattr(allisall, f"{stem}Resource")


# --- Names and signatures against the document ---

PARENTS = {"clients": "Client", "calculations": "Calculation"}
"""A path beginning with one of these and `{id}` names a parent, unless it is the group's own."""

NAMED_APART = {"listValueTemplates": "list_templates"}
"""The one name the rule does not give: `Value`, its noun, repeats the group's first word."""


def snake(name: str) -> str:
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def method_of(operation_id: str, tag: str, path: str) -> str:
    """The naming rule, as `group.method`: the group is the tag in snake_case; the verb comes
    from the operationId; the group's own noun is dropped; a path id naming a parent adds
    `ForClient` or `ForCalculation`; any other noun stays."""
    words = tag.split(" ")
    group = "_".join(word.lower() for word in words)
    if operation_id in NAMED_APART:
        return f"{group}.{NAMED_APART[operation_id]}"
    verb = re.match(r"[a-z]+", operation_id)
    assert verb is not None
    rest = operation_id[verb.end() :]
    plural = "".join(word.capitalize() for word in words)
    singular = plural.removesuffix("s")
    for noun in (plural, singular):
        if noun in rest:
            rest = rest.replace(noun, "", 1)
            break
    segments = [s for s in path.split("/") if s not in ("", "v1")]
    if len(segments) > 1 and segments[1] == "{id}" and segments[0] in PARENTS:
        parent = PARENTS[segments[0]]
        if segments[0] != group:
            rest = rest.replace(parent, "", 1) + f"For{parent}"
    return f"{group}.{snake(verb.group() + rest)}"


def tagged(document: dict[str, Any]) -> dict[str, tuple[str, str]]:
    """The tag and path of each operation the SDK calls."""
    wanted = spec_operations(document)
    found: dict[str, tuple[str, str]] = {}
    for path, item in document["paths"].items():
        for operation in item.values():
            if isinstance(operation, dict) and operation.get("operationId") in wanted:
                found[operation["operationId"]] = (operation["tags"][0], path)
    return found


def expected_methods(document: dict[str, Any]) -> dict[str, str]:
    """The method the naming rule gives each operation, as `group.method`."""
    return {op: method_of(op, tag, path) for op, (tag, path) in tagged(document).items()}


def actual_methods(client: object) -> set[str]:
    return {
        f"{group}.{name}"
        for group in vars(client)
        if not group.startswith("_")
        for name in methods(getattr(client, group))
    }


def naming_differences(document: dict[str, Any], client: object) -> list[str]:
    expected = set(expected_methods(document).values())
    actual = actual_methods(client)
    return [f"{m} is missing" for m in sorted(expected - actual)] + [
        f"{m} is not named by the rule" for m in sorted(actual - expected)
    ]


@pytest.mark.parametrize("client_class", [Allisall, AsyncAllisall])
def test_the_method_names_follow_the_naming_rule_both_ways(client_class: type) -> None:
    document = load_spec()
    client = client_class(api_key=TEST_KEY)
    assert len(expected_methods(document)) == 48
    assert naming_differences(document, client) == []
    assert len(actual_methods(client)) == 48


def test_the_naming_rule_reports_a_new_operation_missing() -> None:
    document = copy.deepcopy(load_spec())
    agents = document["paths"]["/v1/agents"]["get"]
    document["paths"]["/v1/widgets"] = {"get": {**agents, "operationId": "listWidgets"}}
    differences = naming_differences(document, Allisall(api_key=TEST_KEY))
    assert differences == ["agents.list_widgets is missing"]


def test_the_naming_rule_without_its_exception_names_list_templates_otherwise() -> None:
    assert method_of("listValueTemplates", "Value models", "/v1/value-templates") == (
        "value_models.list_templates"
    )
    NAMED_APART.pop("listValueTemplates")
    try:
        assert method_of("listValueTemplates", "Value models", "/v1/value-templates") == (
            "value_models.list_value_templates"
        )
    finally:
        NAMED_APART["listValueTemplates"] = "list_templates"


def test_the_groups_are_the_document_s_tags_with_a_method() -> None:
    document = load_spec()
    tags = {tag for tag, _ in tagged(document).values()}
    assert sorted("_".join(t.lower().split(" ")) for t in tags) == sorted(GROUPS)
    every_tag = {tag["name"] for tag in document["tags"]}
    # Session-only, share-token only, and the problem-type pages, which no SDK calls.
    assert every_tag - tags == {"API keys", "Shared reports", "Problem types"}


PATH_NAMES = {
    "clients": "client_id",
    "agents": "agent_id",
    "value-models": "value_model_id",
    "cost-line-items": "line_item_id",
    "calculations": "calculation_id",
    "reports": "report_id",
}
BODY_NAMES = {"json": "body", "merge-patch": "patch", "multipart": "upload"}
OPTION_NAMES = ("timeout", "max_retries", "headers")
OPTION_TYPES: dict[str, object] = {
    "timeout": float | None,
    "max_retries": int | None,
    "headers": Mapping[str, str] | None,
    "idempotency_key": str | None,
}
WIRE_TO_KEYWORD = {"from": "from_", "dir": "dir_"}


def resolve(document: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    while "$ref" in node:
        target: Any = document
        for part in node["$ref"].removeprefix("#/").split("/"):
            target = target[part]
        node = target
    return node


def query_type(document: dict[str, Any], schema: dict[str, Any]) -> object:
    """The Python type a query parameter's schema calls for."""
    ref = schema.get("$ref", "").rsplit("/", 1)[-1]
    if ref == "InstantInput":
        return datetime | str
    if ref in ("UuidInput", "Month"):
        return str
    schema = resolve(document, schema)
    if "enum" in schema:
        return Literal[tuple(schema["enum"])]
    return {"integer": int, "string": str}[schema["type"]]


def operation_of(document: dict[str, Any], operation_id: str) -> dict[str, Any]:
    for item in document["paths"].values():
        for operation in item.values():
            if isinstance(operation, dict) and operation.get("operationId") == operation_id:
                return operation
    raise KeyError(operation_id)


def body_type(document: dict[str, Any], operation: dict[str, Any]) -> object:
    content = resolve(document, operation["requestBody"])["content"]
    if "multipart/form-data" in content:
        return allisall.ImportUpload
    name = content["application/json"]["schema"]["$ref"].rsplit("/", 1)[1]
    return getattr(request_types, name)


def method_function(client: object, method: str) -> Callable[..., Any]:
    group, name = method.split(".")
    function: Callable[..., Any] = getattr(type(getattr(client, group)), name)
    return function


@pytest.mark.parametrize("client_class", [Allisall, AsyncAllisall])
def test_each_signature_equals_the_document_s_parameters(client_class: type) -> None:
    document = load_spec()
    client = client_class(api_key=TEST_KEY)
    facts = spec_operations(document)
    for operation_id, method in expected_methods(document).items():
        operation = operation_of(document, operation_id)
        fact = facts[operation_id]
        function = method_function(client, method)
        parameters = list(inspect.signature(function).parameters.values())[1:]  # without self
        hints = typing.get_type_hints(function)

        if operation_id == "ingestEvents":
            # Ingest keeps its parameter, positional or keyword, and takes no query.
            first = parameters.pop(0)
            assert (first.name, first.kind) == ("events", first.POSITIONAL_OR_KEYWORD)
        positional = [p for p in parameters if p.kind == p.POSITIONAL_ONLY]
        expected_positional: list[tuple[str, object]] = []
        if "{id}" in fact.path:
            segment = fact.path.split("/")[2]
            expected_positional.append((PATH_NAMES[segment], str))
        if fact.body != "none" and operation_id != "ingestEvents":
            expected_positional.append((BODY_NAMES[fact.body], body_type(document, operation)))
        assert [(p.name, hints[p.name]) for p in positional] == expected_positional, method
        assert all(p.default is p.empty for p in positional), method

        keywords = [p for p in parameters if p.kind == p.KEYWORD_ONLY]
        assert len(positional) + len(keywords) == len(parameters), method
        query = [
            resolve(document, p)
            for p in operation.get("parameters", [])
            if resolve(document, p)["in"] == "query"
        ]
        options = [*OPTION_NAMES, *(["idempotency_key"] if fact.idempotent else [])]
        assert [p.name for p in keywords] == [
            *(WIRE_TO_KEYWORD.get(q["name"], q["name"]) for q in query),
            *options,
        ], method
        for parameter, spec_parameter in zip(keywords, query, strict=False):
            python_type = query_type(document, spec_parameter["schema"])
            if spec_parameter.get("required"):
                assert parameter.default is parameter.empty, f"{method} {parameter.name}"
                assert hints[parameter.name] == python_type, f"{method} {parameter.name}"
            else:
                assert parameter.default is None, f"{method} {parameter.name}"
                assert hints[parameter.name] == python_type | None, f"{method} {parameter.name}"
        for parameter in keywords[len(query) :]:
            assert parameter.default is None, f"{method} {parameter.name}"
            assert hints[parameter.name] == OPTION_TYPES[parameter.name], method

        cls = response_class(operation_id)
        if operation_id == "ingestEvents":
            expected_return: object = IngestSummary
        elif cls is None:
            expected_return = type(None)
        elif fact.list_kind is not None:
            pages = Page if client_class is Allisall else AsyncPaginator
            expected_return = pages[item_class(cls), cls]
        else:
            expected_return = cls
        assert hints["return"] == expected_return, method


@pytest.mark.parametrize("client_class", [Allisall, AsyncAllisall])
def test_each_docstring_names_its_operation_and_scope(client_class: type) -> None:
    document = load_spec()
    client = client_class(api_key=TEST_KEY)
    facts = spec_operations(document)
    for operation_id, method in expected_methods(document).items():
        if operation_id == "ingestEvents":
            continue  # Ingest keeps its 0.1.0 docstrings.
        doc = inspect.getdoc(method_function(client, method)) or ""
        fact = facts[operation_id]
        assert f"Operation `{operation_id}`." in doc, method
        if fact.access == "Public":
            assert "Needs no credential" in doc, method
            assert "still needs a credential to be constructed" in doc, method
        else:
            assert f"Needs the `{fact.scope}` scope." in doc, method
        if fact.body == "merge-patch":
            assert "`None` clears the member" in doc, method
