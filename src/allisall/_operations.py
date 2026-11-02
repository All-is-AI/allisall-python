"""The operations the SDK calls, and what it needs to know about each beyond its types.

Written by hand, and held to the API's OpenAPI document by a test: an entry that drifts from
the document fails it.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

Method = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
Access = Literal["KeyOnly", "KeyOrSession", "Public"]
Scope = Literal["ingest", "read", "write"]
ListKind = Literal["keyset", "offset"]
BodyKind = Literal["none", "json", "merge-patch", "multipart"]


@dataclass(frozen=True)
class Operation:
    """One operation of the API."""

    method: Method
    path: str
    """The path template, such as `/v1/clients/{id}`."""
    access: Access
    """Who may call it. `Public` sends no credential; every other policy sends `Bearer`."""
    scope: Scope | None
    """The scope an API key needs, or `None` when the policy names none."""
    idempotent: bool
    """Whether it takes an `Idempotency-Key`."""
    list_kind: ListKind | None
    """The list kind, or `None` when it is not a list."""
    body: BodyKind
    """The request body it takes."""
    status: int
    """The status of its success response."""


def _get(path: str, *, list_kind: ListKind | None = None) -> Operation:
    return Operation("GET", path, "KeyOrSession", "read", False, list_kind, "none", 200)


def _create(path: str, *, body: BodyKind = "json") -> Operation:
    return Operation("POST", path, "KeyOrSession", "write", True, None, body, 201)


def _patch(path: str) -> Operation:
    return Operation("PATCH", path, "KeyOrSession", "write", False, None, "merge-patch", 200)


def _put(path: str) -> Operation:
    return Operation("PUT", path, "KeyOrSession", "write", False, None, "json", 200)


def _delete(path: str) -> Operation:
    return Operation("DELETE", path, "KeyOrSession", "write", False, None, "none", 204)


OPERATIONS: Mapping[str, Operation] = {
    # Events
    "ingestEvents": Operation("POST", "/v1/events", "KeyOnly", "ingest", False, None, "json", 200),
    "listClientEvents": _get("/v1/clients/{id}/events", list_kind="offset"),
    # Imports
    "previewImport": Operation(
        "POST", "/v1/imports/preview", "KeyOrSession", "ingest", False, None, "multipart", 200
    ),
    "commitImport": Operation(
        "POST", "/v1/imports", "KeyOrSession", "ingest", True, None, "multipart", 200
    ),
    # Clients
    "listClients": _get("/v1/clients", list_kind="keyset"),
    "createClient": _create("/v1/clients"),
    "getClient": _get("/v1/clients/{id}"),
    "updateClient": _patch("/v1/clients/{id}"),
    "deleteClient": _delete("/v1/clients/{id}"),
    "setClientAgents": _put("/v1/clients/{id}/agents"),
    # Agents
    "listAgents": _get("/v1/agents", list_kind="keyset"),
    "createAgent": _create("/v1/agents"),
    "getAgent": _get("/v1/agents/{id}"),
    "updateAgent": _patch("/v1/agents/{id}"),
    "deleteAgent": _delete("/v1/agents/{id}"),
    # Value models
    "listValueModels": _get("/v1/value-models", list_kind="keyset"),
    "getValueModel": _get("/v1/value-models/{id}"),
    "getClientValueModel": _get("/v1/clients/{id}/value-model"),
    "createValueModel": _create("/v1/clients/{id}/value-model"),
    "updateValueModel": _patch("/v1/clients/{id}/value-model"),
    "deleteValueModel": _delete("/v1/clients/{id}/value-model"),
    "setValueModelLineItems": _put("/v1/clients/{id}/value-model/line-items"),
    "listValueTemplates": _get("/v1/value-templates", list_kind="offset"),
    # Outcome types
    "listOutcomeTypes": _get("/v1/outcome-types", list_kind="offset"),
    "listClientOutcomeTypes": _get("/v1/clients/{id}/outcome-types", list_kind="offset"),
    # Cost
    "listCostLineItems": _get("/v1/cost-line-items", list_kind="keyset"),
    "createCostLineItem": _create("/v1/cost-line-items"),
    "getCostLineItem": _get("/v1/cost-line-items/{id}"),
    "updateCostLineItem": _patch("/v1/cost-line-items/{id}"),
    "deleteCostLineItem": _delete("/v1/cost-line-items/{id}"),
    "getPriceTable": _get("/v1/price-table"),
    "setPriceTable": _put("/v1/price-table"),
    # Analytics
    "getClientValue": _get("/v1/clients/{id}/value"),
    "getClientCost": _get("/v1/clients/{id}/cost"),
    "getClientRoi": _get("/v1/clients/{id}/roi"),
    "getClientAnomalies": _get("/v1/clients/{id}/anomalies"),
    # Calculations
    "createCalculation": _create("/v1/clients/{id}/calculations"),
    "listClientCalculations": _get("/v1/clients/{id}/calculations", list_kind="keyset"),
    "getCalculation": _get("/v1/calculations/{id}"),
    "deleteCalculation": _delete("/v1/calculations/{id}"),
    # Reports
    "createReport": _create("/v1/calculations/{id}/reports", body="none"),
    "listCalculationReports": _get("/v1/calculations/{id}/reports", list_kind="keyset"),
    "getReport": _get("/v1/reports/{id}"),
    "updateReport": _patch("/v1/reports/{id}"),
    "deleteReport": _delete("/v1/reports/{id}"),
    # Dashboard
    "getDashboard": _get("/v1/dashboard"),
    "listRenewals": _get("/v1/dashboard/renewals", list_kind="offset"),
    # Health
    "getHealth": Operation("GET", "/healthz", "Public", None, False, None, "none", 200),
}


VERSION_GUARDED = frozenset({"setValueModelLineItems"})
"""Writes guarded by a `version` the caller sends. The server refuses a stale version and does
not replay a success, so a retry after a lost response would report a failure for a write that
landed. They are never retried."""


def is_eligible(operation_id: str, operation: Operation) -> bool:
    """Whether a retry cannot apply the request twice, nor misreport one that landed: a method
    RFC 9110 defines as idempotent, unless a `version` guards the write, an operation sent with
    an `Idempotency-Key`, or ingest, whose `event_id`s deduplicate."""
    if operation_id in VERSION_GUARDED:
        return False
    if operation.method in ("GET", "PUT", "DELETE"):
        return True
    if operation.method == "PATCH":
        return False
    return operation.idempotent or operation_id == "ingestEvents"
