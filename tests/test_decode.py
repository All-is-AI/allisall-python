"""The response decoder: exact money, open enums, unknown members, and the wrong shape."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import pytest

from allisall import (
    AttributedEvent,
    ClientEventList,
    ClientStatus,
    ClientValue,
    CostLineItem,
    CostTargetKind,
    FieldErrorCode,
    ImportPreview,
    Period,
    ValueLine,
)
from allisall._decode import ShapeError, build, decode, parse
from allisall._encode import encode_body

# More significant digits than a binary float carries.
EXACT = "0.1234567890123456789"


def test_the_exact_fixture_is_beyond_a_float() -> None:
    # The fixture must be one a float would change, or the money test could pass by chance.
    assert Decimal(float(EXACT)) != Decimal(EXACT)
    assert repr(float(EXACT)) != EXACT


def value_line(**members: Any) -> dict[str, Any]:
    line: dict[str, Any] = {
        "outcome_type": "ticket_resolved",
        "label": "Resolved ticket",
        "unit_value": 12,
        "events": 3,
        "quantity": 3,
        "total": 36,
        "provenance_note": "",
    }
    line.update(members)
    return line


def cost_line_item(**members: Any) -> dict[str, Any]:
    item: dict[str, Any] = {
        "id": "5e6f7a8b-9c0d-4e1f-8a2b-4c5d6e7f8091",
        "label": "Hosting",
        "target": {"kind": "client", "id": "7e2d3c4b-5a6f-4d7e-9f80-a1b2c3d4e5f6", "name": "Acme"},
        "monthly_amount": 300,
        "currency": "USD",
        "start_date": "2026-01-01",
        "end_date": None,
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
    }
    item.update(members)
    return item


def period() -> dict[str, Any]:
    return {"from": "2026-08-01T00:00:00Z", "to": "2026-09-01T00:00:00Z"}


COVERAGE: dict[str, Any] = {
    "unpriced_outcome_types": [],
    "unpriced_outcome_types_omitted": 0,
    "unmatched_client_keys": [],
    "unmatched_client_keys_omitted": 0,
    "unattributable_outcome_events": 0,
    "client_key_unset": False,
    "line_items_empty": False,
    "period_precedes_model": False,
}


def client_value(total: str) -> str:
    # Built as text, so each number reaches the decoder exactly as written here.
    return (
        '{"value_model": null, "lines": [], "total": ' + total + ", "
        '"coverage": ' + json.dumps(COVERAGE) + ", "
        '"client_id": "c1", "currency": "USD", "minor_units": 2, '
        '"period": {"from": null, "to": null}}'
    )


def attributed_event(**members: Any) -> dict[str, Any]:
    event: dict[str, Any] = {
        "id": "e1",
        "timestamp": "2026-08-02T10:00:00.123456Z",
        "agent_id": "a1",
        "agent_name": "Support bot",
        "category": "task",
        "event_type": "ticket_triaged",
        "outcome_type": None,
        "quantity": 1,
        "cost": None,
        "tokens_in": None,
        "tokens_out": None,
        "model": None,
        "client_key": None,
        "source": "api",
    }
    event.update(members)
    return event


def event_list(*events: dict[str, Any], total: int = 1) -> dict[str, Any]:
    return {
        "client_id": "c1",
        "period": period(),
        "currency": "USD",
        "page": None,
        "total": total,
        "data": list(events),
        "has_more": False,
        "next_cursor": None,
    }


def as_bytes(value: object) -> bytes:
    return json.dumps(value).encode()


# --- Money ---


def test_money_decodes_exactly_and_a_plain_number_beside_it_to_a_float() -> None:
    body = '{"outcome_type": "x", "label": "x", "unit_value": ' + EXACT + ", "
    body += '"events": 2, "quantity": 0.5, "total": 1, "provenance_note": ""}'
    line = decode(ValueLine, body.encode())
    assert line.unit_value == Decimal(EXACT)
    assert isinstance(line.unit_value, Decimal)
    assert str(line.unit_value) == EXACT
    assert line.quantity == 0.5
    assert type(line.quantity) is float
    # An integer at money is a Decimal too, and at a count stays an int.
    assert line.total == Decimal(1)
    assert isinstance(line.total, Decimal)
    assert type(line.events) is int


def test_total_is_money_in_one_schema_and_a_count_in_another() -> None:
    value = decode(ClientValue, client_value("408000.50").encode())
    assert value.total == Decimal("408000.50")
    assert isinstance(value.total, Decimal)
    events = decode(ClientEventList, as_bytes(event_list(attributed_event(), total=7)))
    assert events.total == 7
    assert type(events.total) is int


def test_an_integer_count_given_with_a_fraction_is_not_turned_into_money() -> None:
    # A float member converts whatever number arrives; it is never left a Decimal.
    line = decode(
        ValueLine,
        b'{"outcome_type":"x","label":"x","unit_value":1,"events":1,'
        b'"quantity":3,"total":1,"provenance_note":""}',
    )
    assert type(line.quantity) is float


def test_exponent_form_keeps_its_exponent_and_is_written_back_plainly() -> None:
    # json.loads keeps the last of a repeated member, so the fixture goes last.
    item = decode(CostLineItem, as_bytes(cost_line_item())[:-1] + b', "monthly_amount": 1e-7}')
    assert item.monthly_amount == Decimal("0.0000001")
    assert item.monthly_amount.as_tuple().exponent == -7
    assert encode_body({"monthly_amount": item.monthly_amount}) == b'{"monthly_amount":0.0000001}'


def test_a_huge_money_exponent_decodes_without_building_its_digits() -> None:
    value = decode(ClientValue, client_value("1e999999999").encode())
    assert value.total == Decimal("1E+999999999")


def test_a_null_money_member_is_none() -> None:
    value = decode(ClientValue, client_value("null").encode())
    assert value.total is None


@pytest.mark.parametrize("bad", ['"12.50"', "true", "[]", "{}"])
def test_anything_but_a_number_at_money_is_the_wrong_shape(bad: str) -> None:
    with pytest.raises(ShapeError, match="money") as caught:
        decode(ClientValue, client_value(bad).encode())
    assert caught.value.pointer == "/total"


def test_money_in_a_nested_array_reports_its_pointer() -> None:
    body = json.loads(client_value("1"))
    body["lines"] = [value_line(), value_line()]
    assert decode(ClientValue, as_bytes(body)).lines[1].total == Decimal(36)  # the control
    body["lines"][1]["total"] = "36"
    with pytest.raises(ShapeError) as caught:
        decode(ClientValue, as_bytes(body))
    assert caught.value.pointer == "/lines/1/total"


# --- Open enums ---


def test_a_known_enum_value_is_the_member_and_an_unknown_one_stays_a_str() -> None:
    known = build(CostLineItem, cost_line_item())
    assert known.target.kind is CostTargetKind.CLIENT
    assert known.target.kind == "client"

    unknown = build(
        CostLineItem, cost_line_item(target={"kind": "workspace", "id": "w", "name": "W"})
    )
    assert unknown.target.kind == "workspace"
    assert type(unknown.target.kind) is str


def test_client_status_decodes_to_the_enum_or_the_unknown_str() -> None:
    from allisall import Client

    def client(status: str) -> Client:
        return build(
            Client,
            {
                "id": "c1",
                "name": "Acme",
                "status": status,
                "client_key": None,
                "renewal_date": None,
                "notes": "",
                "created_at": "2026-01-01T00:00:00Z",
            },
        )

    assert client("active").status is ClientStatus.ACTIVE
    assert client("active").status == "active"
    assert client("dormant").status == "dormant"
    assert not isinstance(client("dormant").status, ClientStatus)


def test_the_kept_field_error_codes_decode_to_their_enum() -> None:
    preview = build(
        ImportPreview,
        {
            "total_rows": 2,
            "valid": 0,
            "rejected": 2,
            "preview": [],
            "errors": [
                {"row": 2, "code": "too_precise", "column": "cost", "detail": "d"},
                {"row": 3, "code": "brand_new_code", "column": "cost", "detail": "d"},
            ],
            "errors_truncated": False,
            "ignored_columns": [],
            "ignored_columns_omitted": 0,
            "timezone_warning": None,
        },
    )
    assert preview.errors[0].code is FieldErrorCode.TOO_PRECISE
    assert preview.errors[1].code == "brand_new_code"


def test_the_event_category_stays_a_str() -> None:
    events = build(ClientEventList, event_list(attributed_event(category="outcome")))
    assert events.data[0].category == "outcome"
    assert type(events.data[0].category) is str


# --- Shapes ---


def test_an_unknown_member_is_ignored() -> None:
    item = build(CostLineItem, cost_line_item(added_later={"x": 1}))
    assert not hasattr(item, "added_later")
    assert item.label == "Hosting"


def test_a_keyword_member_is_read_from_its_wire_name() -> None:
    assert build(Period, period()).from_ == "2026-08-01T00:00:00Z"


def test_instants_and_dates_stay_strings() -> None:
    item = build(CostLineItem, cost_line_item())
    assert item.start_date == "2026-01-01"
    assert item.created_at == "2026-01-01T00:00:00Z"
    event = build(AttributedEvent, attributed_event())
    assert event.timestamp == "2026-08-02T10:00:00.123456Z"


def test_an_array_is_a_tuple_and_the_result_is_frozen() -> None:
    events = build(ClientEventList, event_list(attributed_event(), attributed_event(id="e2")))
    assert isinstance(events.data, tuple)
    assert [e.id for e in events.data] == ["e1", "e2"]
    with pytest.raises(AttributeError):
        # mypy refuses assigning to a frozen dataclass's field, which is the point: the test
        # checks that the run time refuses it too, and the assignment never takes effect.
        events.total = 2  # type: ignore[misc]


def test_free_form_metadata_keeps_plain_numbers() -> None:
    from allisall import PreviewEvent

    # Decoded from the bytes, so its numbers pass through the parser that makes Decimals.
    event = decode(
        PreviewEvent,
        as_bytes(
            {
                "event_id": None,
                "timestamp": "2026-08-02T10:00:00Z",
                "agent_key": "bot",
                "client_key": None,
                "category": "task",
                "event_type": "t",
                "outcome_type": None,
                "quantity": 1,
                "cost": None,
                "tokens_in": None,
                "tokens_out": None,
                "model": None,
                "currency": None,
                "metadata": {"ratio": 0.25, "count": 2, "nested": [{"x": 1.5}]},
            }
        ),
    )
    assert event.metadata == {"ratio": 0.25, "count": 2, "nested": [{"x": 1.5}]}
    assert event.metadata is not None
    assert type(event.metadata["ratio"]) is float
    assert type(event.metadata["nested"][0]["x"]) is float


@pytest.mark.parametrize(
    ("body", "pointer", "message"),
    [
        (event_list(), "", None),  # the valid case, as a control
        ({k: v for k, v in event_list().items() if k != "has_more"}, "", "has_more"),
        ({**event_list(), "data": {}}, "/data", "array"),
        ({**event_list(), "period": []}, "/period", "object"),
        ({**event_list(), "period": None}, "/period", "object"),
        ({**event_list(attributed_event()), "data": [None]}, "/data/0", "object"),
    ],
)
def test_the_wrong_shape_is_refused(
    body: dict[str, Any], pointer: str, message: str | None
) -> None:
    if message is None:
        build(ClientEventList, body)
        return
    with pytest.raises(ShapeError, match=message) as caught:
        build(ClientEventList, body)
    assert caught.value.pointer == pointer


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity"])
def test_a_non_json_number_is_the_wrong_shape(constant: str) -> None:
    with pytest.raises(ShapeError, match="not JSON"):
        parse(client_value(constant).encode())


@pytest.mark.parametrize("body", [b"", b"{", b"\xff", b"[1,]"])
def test_a_body_that_is_not_json_is_the_wrong_shape(body: bytes) -> None:
    with pytest.raises(ShapeError, match="not JSON"):
        decode(ClientValue, body)
