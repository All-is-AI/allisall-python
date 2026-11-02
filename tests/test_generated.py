"""Holds the generated wire types to the OpenAPI document they are generated from.

The committed `_generated/requests.py` and `_generated/responses.py` must equal a fresh run of
`scripts/generate.py`. Every `Money` value the document puts in a response must be a `Decimal`
annotation, and every request `Money` member the widened `MoneyInput`, found by a walk of the
document that does not use the generator. Each check is shown able to fail against a changed
copy of the document.

Like the other spec tests, these run in the monorepo and skip outside it.
"""

from __future__ import annotations

import copy
import dataclasses
import functools
import importlib.util
import inspect
import keyword
import sys
import types
import typing
from collections.abc import Iterator, Mapping, Sequence
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from types import ModuleType
from typing import Any, Literal, NotRequired, Required

import pytest
import yaml

import allisall
from allisall import _types
from allisall._decode import check_supported, wire_name
from allisall._generated import requests, responses
from test_spec import load_spec

HERE = Path(__file__).resolve()
PACKAGE = HERE.parents[1]
COMMITTED = PACKAGE / "src" / "allisall" / "_generated"
MONEY = "#/components/schemas/Money"
SCHEMA_REF = "#/components/schemas/"

MONEY_INPUT = Decimal | int | float


@functools.cache
def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "allisall_generate_script", PACKAGE / "scripts" / "generate.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def script() -> ModuleType:
    """The generator script. It needs the document, so it skips where `load_spec` skips: the
    sdist ships neither."""
    _spec_present()
    return _load_script()


@functools.cache
def _spec_present() -> None:
    # Cached, because `script()` is called inside the walks. A skip is raised again each time.
    load_spec()


_counter = iter(range(1_000_000))


def write_spec(tmp_path: Path, document: dict[str, Any]) -> Path:
    path = tmp_path / "openapi.yaml"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return path


def generate_modules(tmp_path: Path, document: dict[str, Any]) -> tuple[ModuleType, ModuleType]:
    """Generate both files from `document` into `tmp_path`, and import them."""
    out = tmp_path / "generated"
    script().generate(write_spec(tmp_path, document), out)
    loaded = []
    for name in ("requests", "responses"):
        module_name = f"allisall._generated._copy{next(_counter)}_{name}"
        spec = importlib.util.spec_from_file_location(module_name, out / f"{name}.py")
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        loaded.append(module)
    return loaded[0], loaded[1]


def schemas_of(document: dict[str, Any]) -> dict[str, Any]:
    found: dict[str, Any] = document["components"]["schemas"]
    return found


def ref_name(schema: Mapping[str, Any]) -> str:
    ref: str = schema["$ref"]
    assert ref.startswith(SCHEMA_REF), ref
    return ref.removeprefix(SCHEMA_REF)


def response_roots(document: dict[str, Any]) -> Iterator[tuple[str, str]]:
    """(operationId, schema name) of each `2xx` JSON answer of the operations the SDK calls."""
    for operation in script().operations(document):
        for status, response in operation["responses"].items():
            if not str(status).startswith("2"):
                continue
            content = script().resolve(document, response).get("content", {})
            for media in content.values():
                yield operation["operationId"], ref_name(media["schema"])


def request_roots(document: dict[str, Any]) -> Iterator[tuple[str, str]]:
    """(operationId, schema name) of each JSON request body of the operations the SDK calls."""
    for operation in script().operations(document):
        if "requestBody" not in operation:
            continue
        content = script().resolve(document, operation["requestBody"])["content"]
        for media_type, media in content.items():
            if media_type != "multipart/form-data":
                yield operation["operationId"], ref_name(media["schema"])


def paths_to(
    document: dict[str, Any],
    schema: Mapping[str, Any],
    is_target: typing.Callable[[Mapping[str, Any]], bool],
    path: tuple[str, ...] = (),
    seen: tuple[str, ...] = (),
) -> Iterator[tuple[str, ...]]:
    """Each path from `schema` to a schema `is_target` accepts. `*` stands for an array item."""
    if is_target(schema):
        yield path
        return
    if "$ref" in schema:
        name = ref_name(schema)
        if name not in seen:
            yield from paths_to(
                document, schemas_of(document)[name], is_target, path, (*seen, name)
            )
        return
    for key in ("allOf", "anyOf", "oneOf"):
        for branch in schema.get(key, []):
            yield from paths_to(document, branch, is_target, path, seen)
    for name, member in schema.get("properties", {}).items():
        yield from paths_to(document, member, is_target, (*path, name), seen)
    if isinstance(schema.get("items"), dict):
        yield from paths_to(document, schema["items"], is_target, (*path, "*"), seen)
    extra = schema.get("additionalProperties")
    if isinstance(extra, dict):
        yield from paths_to(document, extra, is_target, (*path, "{}"), seen)


def is_money(schema: Mapping[str, Any]) -> bool:
    return schema.get("$ref") == MONEY


def strip(hint: object) -> object:
    """The hint without `Required`, `NotRequired` or `None`."""
    while True:
        origin = typing.get_origin(hint)
        if origin in (Required, NotRequired):
            hint = typing.get_args(hint)[0]
        elif origin in (types.UnionType, typing.Union) and type(None) in typing.get_args(hint):
            rest = tuple(a for a in typing.get_args(hint) if a is not type(None))
            hint = rest[0] if len(rest) == 1 else typing.Union[rest]  # noqa: UP007
        else:
            return hint


def follow(root: object, path: Sequence[str]) -> tuple[object, str]:
    """The annotation at `path` from `root`, and where it was found, as `Class.member`."""
    hint: object = root
    where = getattr(root, "__name__", repr(root))
    for segment in path:
        hint = strip(hint)
        if segment == "*":
            assert typing.get_origin(hint) in (Sequence, list), f"{where} is not an array"
            hint = typing.get_args(hint)[0]
            continue
        assert isinstance(hint, type), f"{where} is {hint!r}, not a class"
        if dataclasses.is_dataclass(hint):
            hints = typing.get_type_hints(hint)
            fields = {wire_name(f.name): f.name for f in dataclasses.fields(hint)}
            assert segment in fields, f"{hint.__name__} has no member {segment!r}"
            # Named after the class that declares the field, not the one inheriting it.
            owner = next(
                c for c in hint.__mro__ if fields[segment] in vars(c).get("__annotations__", {})
            )
            where = f"{owner.__name__}.{fields[segment]}"
            hint = hints[fields[segment]]
        elif typing.is_typeddict(hint):
            hints = typing.get_type_hints(hint, include_extras=True)
            assert segment in hints, f"{hint.__name__} has no member {segment!r}"
            where = f"{hint.__name__}.{segment}"
            hint = hints[segment]
        else:
            raise AssertionError(f"{where} is {hint!r}, which has no members")
    return hint, where


def response_money(document: dict[str, Any], module: ModuleType) -> tuple[int, set[str], list[str]]:
    """Walk every response `Money` path. Returns the count of paths, the operations holding
    one, and each path whose annotation is not `Decimal`."""
    count = 0
    operations: set[str] = set()
    wrong: list[str] = []
    for operation_id, name in response_roots(document):
        for path in paths_to(document, schemas_of(document)[name], is_money):
            count += 1
            operations.add(operation_id)
            hint, where = follow(getattr(module, name), path)
            if strip(hint) is not Decimal:
                wrong.append(f"{operation_id} /{'/'.join(path)} ({where}) is {strip(hint)!r}")
    return count, operations, wrong


def request_money(document: dict[str, Any], module: ModuleType) -> tuple[set[str], list[str]]:
    """Walk every request `Money` member. Returns where each is, and each that is not the
    widened `MoneyInput`."""
    found: set[str] = set()
    wrong: list[str] = []
    for operation_id, name in request_roots(document):
        for path in paths_to(document, schemas_of(document)[name], is_money):
            hint, where = follow(getattr(module, name), path)
            found.add(where)
            if strip(hint) != MONEY_INPUT:
                wrong.append(f"{operation_id} /{'/'.join(path)} ({where}) is {strip(hint)!r}")
    return found, wrong


def classes(module: ModuleType) -> list[type]:
    return [
        cls
        for _, cls in inspect.getmembers(module, inspect.isclass)
        if cls.__module__ == module.__name__
    ]


def dataclasses_of(module: ModuleType) -> list[type]:
    return [cls for cls in classes(module) if dataclasses.is_dataclass(cls)]


# --- The committed files are fresh ---


def test_the_committed_files_equal_a_fresh_generation() -> None:
    load_spec()  # skips outside the monorepo
    assert script().stale(script().SPEC, COMMITTED) == []


@pytest.mark.parametrize(
    ("mutate", "stale"),
    [
        # A response member turned from Money into a plain number.
        (
            lambda s: s["ValueResult"]["properties"]["total"].update(
                {"anyOf": [{"type": "number"}, {"type": "null"}]}
            ),
            ["responses.py"],
        ),
        # A new request member.
        (
            lambda s: s["ClientCreate"]["properties"].update({"tier": {"type": "string"}}),
            ["requests.py"],
        ),
        # The prose reaches the doc comments: a response member's description,
        (
            lambda s: s["Client"]["properties"]["notes"].update({"description": "Changed."}),
            ["responses.py"],
        ),
        # a request member's,
        (
            lambda s: s["ClientCreate"]["properties"]["name"].update({"description": "Changed."}),
            ["requests.py"],
        ),
        # and a schema's.
        (lambda s: s["ClientPatch"].update({"description": "Changed."}), ["requests.py"]),
    ],
    ids=[
        "response-type",
        "request-member",
        "response-member-description",
        "request-member-description",
        "schema-description",
    ],
)
def test_a_changed_spec_makes_the_committed_files_stale(
    tmp_path: Path, mutate: Any, stale: list[str]
) -> None:
    document = copy.deepcopy(load_spec())
    mutate(document["components"]["schemas"])
    assert script().stale(write_spec(tmp_path, document), COMMITTED) == stale


# --- Money ---


def test_every_response_money_value_is_a_decimal() -> None:
    count, operations, wrong = response_money(load_spec(), responses)
    assert wrong == []
    assert (count, len(operations)) == (122, 24)


def test_every_request_money_member_is_widened() -> None:
    found, wrong = request_money(load_spec(), requests)
    assert wrong == []
    assert found == {
        "EventInput.cost",
        "ValueLineItemInput.unit_value",
        "CostLineItemCreate.monthly_amount",
        "CostLineItemPatch.monthly_amount",
        "ModelRateInput.input_per_1k",
        "ModelRateInput.output_per_1k",
    }
    # The script names each of them, so it widens no member the walk does not find.
    assert set(script().REQUEST_MONEY_MEMBERS) == found


def test_no_generated_annotation_is_a_bare_float_where_the_spec_says_money(
    tmp_path: Path,
) -> None:
    # A Money member made plain in a copy of the document fails the walk.
    document = copy.deepcopy(load_spec())
    total = document["components"]["schemas"]["ValueResult"]["properties"]["total"]
    total["anyOf"] = [{"type": "number"}, {"type": "null"}]
    _, mutated_responses = generate_modules(tmp_path, document)
    _, _, wrong = response_money(load_spec(), mutated_responses)
    assert wrong
    assert all("ValueResult.total" in line for line in wrong)


def test_a_request_money_member_the_script_does_not_name_is_found(tmp_path: Path) -> None:
    # A seventh request Money member, with a keyword beside its $ref, as the six have.
    document = copy.deepcopy(load_spec())
    document["components"]["schemas"]["ClientCreate"]["properties"]["budget"] = {
        "$ref": MONEY,
        "minimum": 0,
    }
    mutated_requests, _ = generate_modules(tmp_path, document)
    found, wrong = request_money(document, mutated_requests)
    assert "ClientCreate.budget" in found
    assert wrong == [f"createClient /budget (ClientCreate.budget) is {float!r}"]


# --- Open sets of codes ---


def is_open_site(document: dict[str, Any]) -> typing.Callable[[Mapping[str, Any]], bool]:
    def closed(schema: Mapping[str, Any]) -> bool:
        if "$ref" in schema:
            schema = schemas_of(document)[ref_name(schema)]
        return "enum" in schema or (
            "oneOf" in schema and all("const" in b for b in schema["oneOf"])
        )

    def bare_string(schema: Mapping[str, Any]) -> bool:
        return schema.get("type") == "string" and not {"enum", "const", "$ref"} & set(schema)

    def accept(schema: Mapping[str, Any]) -> bool:
        branches = schema.get("anyOf", [])
        return (
            len(branches) == 2
            and any(closed(b) for b in branches)
            and any(bare_string(b) for b in branches)
        )

    return accept


def is_union_with_str(hint: object) -> bool:
    return typing.get_origin(hint) in (types.UnionType, typing.Union) and str in typing.get_args(
        hint
    )


def test_every_open_site_in_a_response_is_an_enum_or_a_string() -> None:
    document = load_spec()
    sites: set[str] = set()
    for _, name in response_roots(document):
        for path in paths_to(document, schemas_of(document)[name], is_open_site(document)):
            hint, where = follow(getattr(responses, name), path)
            sites.add(where)
            args = typing.get_args(strip(hint))
            assert str in args, where
            enum = next(arg for arg in args if arg is not str)
            if where in ("AttributedEvent.category", "PreviewEvent.category"):
                # The event category keeps its Literal, and decodes to str.
                assert enum == _types.EventCategory, where
            else:
                assert isinstance(enum, type), where
                assert issubclass(enum, StrEnum), where
    assert len(sites) == 21

    # And no annotation is open that the document does not make open.
    generated_open = {
        f"{cls.__name__}.{name}"
        for cls in dataclasses_of(responses)
        for name, hint in typing.get_type_hints(cls).items()
        if name in cls.__annotations__ and is_union_with_str(strip(hint))
    }
    assert generated_open == sites


# --- Names ---


@pytest.mark.parametrize("module", [requests, responses])
def test_no_generated_class_name_ends_in_a_digit(module: ModuleType) -> None:
    assert [cls.__name__ for cls in classes(module) if cls.__name__[-1].isdigit()] == []


def test_the_inline_client_of_an_agent_detail_has_its_mapped_name() -> None:
    hint = typing.get_type_hints(responses.AgentDetail)["clients"]
    assert typing.get_args(hint) == (responses.AgentDetailClient,)


def properties_of(document: dict[str, Any], schema: Mapping[str, Any]) -> set[str]:
    """Every member a schema declares, through `$ref` and `allOf`."""
    if "$ref" in schema:
        return properties_of(document, schemas_of(document)[ref_name(schema)])
    found = set(schema.get("properties", {}))
    for branch in schema.get("allOf", []):
        found |= properties_of(document, branch)
    return found


def test_every_response_field_reads_its_wire_name() -> None:
    document = load_spec()
    named = schemas_of(document)
    for cls in dataclasses_of(responses):
        for field in dataclasses.fields(cls):
            wire = wire_name(field.name)
            assert wire == field.name or keyword.iskeyword(wire), f"{cls.__name__}.{field.name}"
        if cls.__name__ in named:
            assert {wire_name(f.name) for f in dataclasses.fields(cls)} == properties_of(
                document, named[cls.__name__]
            ), cls.__name__
    renamed = [
        f"{cls.__name__}.{f.name}"
        for cls in dataclasses_of(responses)
        for f in dataclasses.fields(cls)
        if wire_name(f.name) != f.name
    ]
    assert renamed == ["Period.from_"]


# --- The decoder supports every annotation ---


@pytest.mark.parametrize("cls", dataclasses_of(responses), ids=lambda cls: cls.__name__)
def test_the_decoder_supports_every_response_class(cls: type) -> None:
    check_supported(cls)


def test_a_union_of_two_objects_is_refused_by_the_check(tmp_path: Path) -> None:
    document = copy.deepcopy(load_spec())
    document["components"]["schemas"]["Health"]["properties"]["owner"] = {
        "oneOf": [{"$ref": f"{SCHEMA_REF}Client"}, {"$ref": f"{SCHEMA_REF}Agent"}]
    }
    document["components"]["schemas"]["Health"]["required"].append("owner")
    _, mutated_responses = generate_modules(tmp_path, document)
    with pytest.raises(TypeError, match="does not support"):
        check_supported(mutated_responses.Health)


@pytest.mark.parametrize(
    "branches",
    [
        [{"type": "string"}, {"type": "integer"}],
        [{"type": "string"}, {"type": "boolean"}, {"type": "null"}],
    ],
    ids=["str-or-int", "str-or-bool-or-null"],
)
def test_a_union_of_unconverted_scalars_is_refused_by_the_check(
    tmp_path: Path, branches: list[dict[str, str]]
) -> None:
    # The decoder would pass such a value through without knowing which branch it holds.
    document = copy.deepcopy(load_spec())
    document["components"]["schemas"]["Health"]["properties"]["build"] = {"anyOf": branches}
    document["components"]["schemas"]["Health"]["required"].append("build")
    _, mutated_responses = generate_modules(tmp_path, document)
    hint = typing.get_type_hints(mutated_responses.Health)["build"]
    assert str in typing.get_args(hint)  # the fixture is the union it names
    with pytest.raises(TypeError, match="does not support"):
        check_supported(mutated_responses.Health)


# --- The kept 0.1.0 names against the generated ones ---


def required_keys(typed_dict: type) -> set[str]:
    """The required members, read from the annotations rather than `__required_keys__`."""
    hints = typing.get_type_hints(typed_dict, include_extras=True)
    total = getattr(typed_dict, "__total__", True)
    required: set[str] = set()
    for name, hint in hints.items():
        origin = typing.get_origin(hint)
        if origin is Required or (total and origin is not NotRequired):
            required.add(name)
    return required


def test_event_input_equals_the_generated_one() -> None:
    kept = typing.get_type_hints(allisall.EventInput, include_extras=True)
    generated = typing.get_type_hints(requests.EventInput, include_extras=True)
    assert set(kept) == set(generated)
    assert required_keys(allisall.EventInput) == required_keys(requests.EventInput)
    assert required_keys(requests.EventInput) == {
        "timestamp",
        "agent_key",
        "category",
        "event_type",
    }


def test_event_category_equals_the_generated_one() -> None:
    assert typing.get_args(allisall.EventCategory) == typing.get_args(requests.EventCategory)
    # The responses refer to the kept Literal itself.
    hint = typing.get_type_hints(responses.AttributedEvent)["category"]
    assert typing.get_args(hint) == (allisall.EventCategory, str)
    assert typing.get_origin(allisall.EventCategory) is Literal


def test_the_codes_are_the_kept_enums() -> None:
    hint = typing.get_type_hints(responses.ImportRowError)["code"]
    assert typing.get_args(hint) == (allisall.FieldErrorCode, str)
    assert not hasattr(responses, "ErrorCode")
    assert not hasattr(responses, "FieldErrorCode") or (
        responses.FieldErrorCode is allisall.FieldErrorCode
    )


def test_the_ingest_result_types_match_the_generated_ones() -> None:
    def names(cls: type) -> set[str]:
        return {f.name for f in dataclasses.fields(cls)}

    assert names(allisall.IngestRowError) == names(responses.IngestRowError)
    assert names(allisall.IngestSummary) - {"batches"} == names(responses.IngestResult)


def test_the_input_aliases() -> None:
    assert _types.MoneyInput == MONEY_INPUT
    hints = typing.get_type_hints(requests.ClientPatch, include_extras=True)
    assert strip(hints["renewal_date"]) == _types.DateInput
    hints = typing.get_type_hints(requests.PeriodInput, include_extras=True)
    assert hints["from"] == _types.InstantInput


# --- The public names ---

PUBLIC_NAMES = {
    # 0.1.0's names.
    "APIConnectionError",
    "APIError",
    "Allisall",
    "AllisallError",
    "AsyncAllisall",
    "ErrorCode",
    "EventCategory",
    "EventInput",
    "FieldError",
    "FieldErrorCode",
    "IngestError",
    "IngestRowError",
    "IngestSummary",
    "Problem",
    "__version__",
    # 0.2's own names: the pages, and the upload the import methods take.
    "AsyncPage",
    "AsyncPaginator",
    "ImportUpload",
    "Page",
    # The request bodies.
    "AgentCreate",
    "AgentPatch",
    "CalculationCreate",
    "ClientAgentsSet",
    "ClientCreate",
    "ClientPatch",
    "CostLineItemCreate",
    "CostLineItemPatch",
    "CostTargetInput",
    "DisclosureEdit",
    "ImportMapping",
    "ModelRateInput",
    "PeriodInput",
    "PriceTableSet",
    "ReportPatch",
    "ValueLineItemInput",
    "ValueLineItemsSet",
    "ValueModelCreate",
    "ValueModelPatch",
    # The responses and their enums.
    "Agent",
    "AgentCostLine",
    "AgentDetail",
    "AgentList",
    "AgentListItem",
    "AgentStats",
    "AgentStatus",
    "Anomalies",
    "AssignedAgent",
    "AttributedEvent",
    "Calculation",
    "CalculationList",
    "CalculationSnapshot",
    "CalculationState",
    "CalculationSummary",
    "Checklist",
    "Client",
    "ClientAgents",
    "ClientCost",
    "ClientDetail",
    "ClientEventList",
    "ClientList",
    "ClientStatus",
    "ClientValue",
    "CostCoverage",
    "CostLineItem",
    "CostLineItemList",
    "CostResult",
    "CostTarget",
    "CostTargetKind",
    "Dashboard",
    "Disclosure",
    "DisclosureKind",
    "EventSource",
    "Health",
    "HealthDirection",
    "HealthUnavailable",
    "ImportPreview",
    "ImportResult",
    "ImportRowError",
    "ManualCostLine",
    "ModelRate",
    "OutcomeTypeList",
    "OutcomeTypeUsage",
    "Period",
    "PortfolioClient",
    "PortfolioExclusionReason",
    "PreviewEvent",
    "PreviewRow",
    "PriceTable",
    "PublicReport",
    "Ratios",
    "Renewal",
    "RenewalList",
    "Report",
    "ReportList",
    "ReportSummary",
    "ReportWithPreview",
    "RoiResult",
    "TokenCostLine",
    "UnattributedLineItem",
    "UndefinedReason",
    "ValueCoverage",
    "ValueLine",
    "ValueLineItem",
    "ValueModel",
    "ValueModelList",
    "ValueModelRef",
    "ValueModelStatus",
    "ValueModelSummary",
    "ValueResult",
    "ValueTemplate",
    "ValueTemplateLineItem",
    "ValueTemplateList",
}


def test_the_public_names() -> None:
    assert len(PUBLIC_NAMES) == 15 + 4 + 93
    assert set(allisall.__all__) == PUBLIC_NAMES
    assert len(allisall.__all__) == len(PUBLIC_NAMES)
    for name in allisall.__all__:
        assert hasattr(allisall, name), name


def test_the_schema_names_follow_the_export_rule() -> None:
    # Every schema the operations reach, less the scalars, the kept names and the internal ones.
    document = load_spec()
    reached = script().reached(document, script().request_roots(document)) | script().reached(
        document, script().response_roots(document)
    )
    assert len(reached) == 111
    scalars = {
        "Uuid",
        "UuidInput",
        "Instant",
        "InstantInput",
        "Date",
        "DateInput",
        "Month",
        "Currency",
        "MinorUnits",
        "Money",
        "Ratio",
    }
    kept = {"EventCategory", "EventInput", "IngestRowError", "FieldErrorCode"}
    internal = {"EventBatch", "IngestResult", "ImportUpload"}
    exported = reached - scalars - kept - internal
    assert len(exported) == 93
    assert exported <= PUBLIC_NAMES


def test_an_enum_in_both_directions_is_exported_as_the_response_enum() -> None:
    assert allisall.ClientStatus is responses.ClientStatus
    assert issubclass(allisall.ClientStatus, StrEnum)
    assert allisall.ClientCreate is requests.ClientCreate
