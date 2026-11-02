"""Holds the hand-written operation table to the OpenAPI document.

The operations the SDK calls are read from the document independently of the table: every
operation that is not a `HEAD`, less the problem-type page, the session-only operations and
the shared report. Each entry's method, path, access policy and scope, idempotency, list kind,
body kind and success status must equal the document's. A copy of the document with one fact
changed shows the comparison able to fail.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

from allisall._operations import OPERATIONS, BodyKind, Method, Operation, is_eligible
from test_spec import load_spec

METHODS: dict[str, Method] = {
    "get": "GET",
    "put": "PUT",
    "post": "POST",
    "delete": "DELETE",
    "patch": "PATCH",
}
NOT_CALLED_POLICIES = {"SessionOnly", "ShareToken"}


def body_kind(operation: dict[str, Any]) -> BodyKind:
    body = operation.get("requestBody")
    if body is None:
        return "none"
    content = body["content"]
    if "multipart/form-data" in content:
        return "multipart"
    if "application/merge-patch+json" in content:
        return "merge-patch"
    assert list(content) == ["application/json"], content
    return "json"


def spec_operations(document: dict[str, Any]) -> dict[str, Operation]:
    """The operations the SDK calls, as the document states them."""
    found: dict[str, Operation] = {}
    for path, item in document["paths"].items():
        for method, method_name in METHODS.items():
            operation = item.get(method)
            if operation is None:
                continue
            access = operation["x-access"]
            if access["policy"] in NOT_CALLED_POLICIES or operation["operationId"] == (
                "getProblemType"
            ):
                continue
            successes = [int(code) for code in operation["responses"] if str(code)[0] == "2"]
            assert len(successes) == 1, operation["operationId"]
            found[operation["operationId"]] = Operation(
                method=method_name,
                path=path,
                access=access["policy"],
                scope=access.get("scope"),
                idempotent=bool(operation.get("x-idempotent", False)),
                list_kind=operation.get("x-list"),
                body=body_kind(operation),
                status=successes[0],
            )
    return found


def differences(document: dict[str, Any]) -> list[str]:
    expected = spec_operations(document)
    found: list[str] = []
    for name in sorted(expected.keys() - OPERATIONS.keys()):
        found.append(f"{name} is missing from the table")
    for name in sorted(OPERATIONS.keys() - expected.keys()):
        found.append(f"{name} is in the table but not called by the SDK")
    for name in sorted(expected.keys() & OPERATIONS.keys()):
        if expected[name] != OPERATIONS[name]:
            found.append(f"{name}: the table has {OPERATIONS[name]}, the document {expected[name]}")
    return found


def test_the_table_equals_the_document() -> None:
    document = load_spec()
    assert len(spec_operations(document)) == 48
    assert len(OPERATIONS) == 48
    assert differences(document) == []


@pytest.mark.parametrize(
    ("change", "reported"),
    [
        (lambda d: d["paths"]["/v1/agents"]["post"].update({"x-idempotent": False}), "createAgent"),
        (lambda d: d["paths"]["/v1/clients"]["get"].update({"x-list": "offset"}), "listClients"),
        (
            lambda d: d["paths"]["/v1/reports/{id}"]["delete"]["responses"].update(
                {"200": d["paths"]["/v1/reports/{id}"]["delete"]["responses"].pop("204")}
            ),
            "deleteReport",
        ),
        (
            lambda d: d["paths"]["/v1/price-table"]["get"]["x-access"].update({"scope": "write"}),
            "getPriceTable",
        ),
        (
            lambda d: d["paths"].update(
                {"/v1/widgets": {"get": {**d["paths"]["/v1/agents"]["get"], "operationId": "w"}}}
            ),
            "w is missing",
        ),
    ],
)
def test_a_changed_document_is_reported(change: Any, reported: str) -> None:
    document = copy.deepcopy(load_spec())
    change(document)
    assert any(reported in line for line in differences(document)), differences(document)


# Listed here, not read from the code under test: a PATCH is not idempotent, a POST is
# retried only with an Idempotency-Key or as ingest, and a write guarded by `version` would
# report a failure for a retried write that landed.
INELIGIBLE = {
    "updateClient",
    "updateAgent",
    "updateValueModel",
    "updateCostLineItem",
    "updateReport",
    "previewImport",
    "setValueModelLineItems",
}


def test_the_eligible_operations() -> None:
    assert len(OPERATIONS) == 48
    assert {name for name, op in OPERATIONS.items() if not is_eligible(name, op)} == INELIGIBLE
    assert len(INELIGIBLE) == 7
    assert sum(is_eligible(name, op) for name, op in OPERATIONS.items()) == 41
