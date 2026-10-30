"""Holds the hand-written wire types to the OpenAPI document they were written from.

Until a generated core replaces `_types.py`, this test reads the OpenAPI document from its place
in the monorepo and compares: the `const` values of the `ErrorCode` and `FieldErrorCode`
catalogues, the `EventCategory` values, and the member names of `EventInput`, `IngestRowError` and
`IngestResult`. A second test removes an entry from a copy of the spec, so the comparison is
shown able to fail.

The spec exists only in the monorepo. Outside it, for example in an unpacked sdist, these
tests skip. Inside it, marked by `pnpm-workspace.yaml` at the repository root, a missing spec
fails them, so a moved spec cannot switch the check off in silence.
"""

from __future__ import annotations

import copy
import dataclasses
import typing
from pathlib import Path
from typing import Any

import pytest
import yaml

from allisall import (
    ErrorCode,
    EventCategory,
    EventInput,
    FieldErrorCode,
    IngestRowError,
    IngestSummary,
)

HERE = Path(__file__).resolve()
SPEC = HERE.parents[2] / "openapi" / "openapi.yaml"
MONOREPO_MARKER = HERE.parents[3] / "pnpm-workspace.yaml"

# Members of IngestSummary that IngestResult does not have.
SUMMARY_ONLY = {"batches"}


def find_spec(spec: Path, marker: Path) -> Path | None:
    """The spec's path; `None` outside the monorepo. Inside it, a missing spec is an error."""
    if spec.is_file():
        return spec
    if marker.is_file():
        raise FileNotFoundError(
            f"{spec} is missing, but {marker} marks this as the monorepo, where it must exist"
        )
    return None


def load_spec() -> dict[str, Any]:
    try:
        path = find_spec(SPEC, MONOREPO_MARKER)
    except FileNotFoundError as err:
        pytest.fail(str(err))
    if path is None:
        pytest.skip("the OpenAPI spec is only in the monorepo")
    spec: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return spec


def test_find_spec_reads_the_spec_when_present(tmp_path: Path) -> None:
    spec = tmp_path / "openapi.yaml"
    spec.write_text("openapi: 3.1.0\n")
    assert find_spec(spec, tmp_path / "pnpm-workspace.yaml") == spec


def test_find_spec_skips_outside_the_monorepo(tmp_path: Path) -> None:
    assert find_spec(tmp_path / "openapi.yaml", tmp_path / "pnpm-workspace.yaml") is None


def test_find_spec_fails_inside_the_monorepo_when_the_spec_is_missing(tmp_path: Path) -> None:
    marker = tmp_path / "pnpm-workspace.yaml"
    marker.write_text("packages: []\n")
    with pytest.raises(FileNotFoundError, match="monorepo"):
        find_spec(tmp_path / "openapi.yaml", marker)


def test_this_checkout_is_the_monorepo() -> None:
    # In the repository the spec test must run, never skip: pin that the paths resolve.
    if not MONOREPO_MARKER.is_file():
        pytest.skip("not in the monorepo")
    assert SPEC.is_file()


def catalogue(schemas: dict[str, Any], name: str) -> set[str]:
    branches = schemas[name]["oneOf"]
    assert all(set(branch) >= {"const"} for branch in branches), f"{name} is not all const"
    return {branch["const"] for branch in branches}


def mismatches(spec: dict[str, Any]) -> list[str]:
    schemas = spec["components"]["schemas"]
    found: list[str] = []

    def compare(what: str, ours: set[str], theirs: set[str]) -> None:
        if ours != theirs:
            found.append(
                f"{what}: only in the SDK {sorted(ours - theirs)}, "
                f"only in the spec {sorted(theirs - ours)}"
            )

    compare("ErrorCode", {c.value for c in ErrorCode}, catalogue(schemas, "ErrorCode"))
    compare(
        "FieldErrorCode", {c.value for c in FieldErrorCode}, catalogue(schemas, "FieldErrorCode")
    )
    compare(
        "EventCategory", set(typing.get_args(EventCategory)), set(schemas["EventCategory"]["enum"])
    )

    event_input = schemas["EventInput"]
    compare("EventInput members", set(EventInput.__annotations__), set(event_input["properties"]))
    compare("EventInput required", set(EventInput.__required_keys__), set(event_input["required"]))

    compare(
        "IngestRowError members",
        {f.name for f in dataclasses.fields(IngestRowError)},
        set(schemas["IngestRowError"]["properties"]),
    )
    compare(
        "IngestSummary members",
        {f.name for f in dataclasses.fields(IngestSummary)} - SUMMARY_ONLY,
        set(schemas["IngestResult"]["properties"]),
    )
    return found


def test_the_hand_written_types_match_the_spec() -> None:
    assert mismatches(load_spec()) == []


def test_the_use_sites_of_the_codes_are_open() -> None:
    # The spec writes each code member as an anyOf of the catalogue and a plain string, which
    # is why the SDK keeps an unknown code as a str.
    schemas = load_spec()["components"]["schemas"]
    open_shape = [{"$ref": "#/components/schemas/FieldErrorCode"}, {"type": "string"}]
    assert schemas["IngestRowError"]["properties"]["code"]["anyOf"] == open_shape
    assert schemas["Problem"]["properties"]["code"]["anyOf"] == [
        {"$ref": "#/components/schemas/ErrorCode"},
        {"type": "string"},
    ]


def _drop_const(schemas: dict[str, Any], name: str, value: str) -> None:
    schemas[name]["oneOf"] = [b for b in schemas[name]["oneOf"] if b["const"] != value]


@pytest.mark.parametrize(
    ("mutate", "expected"),
    [
        (lambda s: _drop_const(s, "ErrorCode", "rate_limited"), "ErrorCode"),
        (lambda s: _drop_const(s, "FieldErrorCode", "too_large"), "FieldErrorCode"),
        (lambda s: s["ErrorCode"]["oneOf"].append({"const": "new_code"}), "ErrorCode"),
        (lambda s: s["EventCategory"]["enum"].remove("outcome"), "EventCategory"),
        (lambda s: s["EventInput"]["properties"].pop("currency"), "EventInput members"),
        (lambda s: s["EventInput"]["required"].append("event_id"), "EventInput required"),
        (lambda s: s["IngestRowError"]["properties"].pop("pointer"), "IngestRowError members"),
        (lambda s: s["IngestResult"]["properties"].pop("errors_truncated"), "IngestSummary"),
    ],
)
def test_a_changed_spec_fails_the_comparison(mutate: Any, expected: str) -> None:
    spec = copy.deepcopy(load_spec())
    mutate(spec["components"]["schemas"])
    found = mismatches(spec)
    assert len(found) == 1
    assert found[0].startswith(expected)
