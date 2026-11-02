"""The request encoder: money written by value, the exponent bound, and what it refuses."""

from __future__ import annotations

import json
import time
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest

from allisall import CostLineItemCreate
from allisall._encode import MAX_EXPONENT, encode_body

EXACT = "0.1234567890123456789"


def line_item(amount: object) -> dict[str, object]:
    return {
        "label": "Hosting",
        "target": {"kind": "client", "id": "7e2d3c4b-5a6f-4d7e-9f80-a1b2c3d4e5f6"},
        "monthly_amount": amount,
        "start_date": date(2026, 1, 1),
    }


def amount_text(body: bytes) -> str:
    """The raw text the encoder wrote for `monthly_amount`, read from the bytes themselves."""
    text = body.decode()
    start = text.index('"monthly_amount":') + len('"monthly_amount":')
    end = text.index(",", start)
    return text[start:end]


@pytest.mark.parametrize(
    ("amount", "written"),
    [
        (Decimal(EXACT), EXACT),
        (Decimal("12.50"), "12.50"),
        (Decimal("-0"), "-0"),
        (Decimal("1E-7"), "0.0000001"),
        (Decimal("1.5E+3"), "1500"),
        (300, "300"),
        (12.5, "12.5"),
        (0.1, "0.1"),
    ],
)
def test_money_is_written_unquoted_with_its_digits(amount: object, written: str) -> None:
    body = encode_body(line_item(amount))
    assert amount_text(body) == written
    # The bytes are JSON, and the number reads back as the same Decimal.
    assert json.loads(body, parse_float=Decimal)["monthly_amount"] == Decimal(written)


def test_a_typed_body_is_accepted() -> None:
    # The generated request type takes a Decimal, an int or a float at money.
    body: CostLineItemCreate = {
        "label": "Hosting",
        "target": {"kind": "agent", "id": "a1"},
        "monthly_amount": Decimal(EXACT),
        "start_date": "2026-01-01",
    }
    assert amount_text(encode_body(body)) == EXACT


@pytest.mark.parametrize(
    "amount",
    [
        Decimal(f"1E+{MAX_EXPONENT}"),
        Decimal(f"-1E+{MAX_EXPONENT}"),
        Decimal(f"1E-{MAX_EXPONENT}"),
        Decimal(f"9.99E+{MAX_EXPONENT}"),
    ],
)
def test_an_exponent_at_the_bound_is_written_out(amount: Decimal) -> None:
    written = amount_text(encode_body(line_item(amount)))
    assert "E" not in written.upper()
    assert Decimal(written) == amount


def test_the_bound_writes_every_digit() -> None:
    assert amount_text(encode_body(line_item(Decimal("1E+400")))) == "1" + "0" * 400
    assert amount_text(encode_body(line_item(Decimal("1E-400")))) == "0." + "0" * 399 + "1"


@pytest.mark.parametrize(
    "amount",
    [
        Decimal(f"1E+{MAX_EXPONENT + 1}"),
        Decimal(f"1E-{MAX_EXPONENT + 1}"),
        Decimal(f"10E+{MAX_EXPONENT}"),  # 1.0E+401: the exponent as scientific notation writes it
        Decimal("1E+999999999"),
        Decimal("-1E-999999999"),
    ],
)
def test_an_exponent_beyond_the_bound_is_refused_naming_its_path(amount: Decimal) -> None:
    started = time.monotonic()
    with pytest.raises(ValueError, match=r"^/monthly_amount is a Decimal whose exponent"):
        encode_body(line_item(amount))
    # Refused before any digit is built.
    assert time.monotonic() - started < 0.5


def test_the_bound_applies_wherever_a_decimal_sits() -> None:
    body = {"line_items": [{"unit_value": 1}, {"unit_value": 2}, {"unit_value": Decimal("1E+401")}]}
    with pytest.raises(ValueError, match=r"^/line_items/2/unit_value "):
        encode_body(body)


def test_a_decimal_in_free_form_metadata_is_a_number() -> None:
    body = encode_body({"metadata": {"rate": Decimal("0.25"), "tags": ["a", Decimal("2")]}})
    assert body == b'{"metadata":{"rate":0.25,"tags":["a",2]}}'


def test_a_bool_at_money_is_written_as_a_bool() -> None:
    # A bool is an int to mypy; the server refuses it, and the SDK does not re-check it.
    assert amount_text(encode_body(line_item(True))) == "true"


def test_every_member_is_written_including_an_unknown_one() -> None:
    body = json.loads(encode_body({**line_item(1), "monthly_amout": 2, "end_date": None}))
    assert body["monthly_amout"] == 2
    assert body["end_date"] is None


def test_instants_and_dates() -> None:
    aware = datetime(2026, 8, 1, 9, 30, tzinfo=timezone(timedelta(hours=9)))
    body = json.loads(
        encode_body(
            {
                "period": {"from": aware, "to": datetime(2026, 9, 1, tzinfo=UTC)},
                "start_date": date(2026, 1, 2),
                "text": "2026-01-02",
            }
        )
    )
    assert body["period"] == {
        "from": "2026-08-01T09:30:00+09:00",
        "to": "2026-09-01T00:00:00+00:00",
    }
    assert body["start_date"] == "2026-01-02"
    assert body["text"] == "2026-01-02"


def test_text_is_utf8_and_names_are_escaped_in_pointers() -> None:
    assert encode_body({"name": "Café ☃"}) == '{"name":"Café ☃"}'.encode()
    with pytest.raises(ValueError, match=r"^/a~1b/x~0y is a naive datetime"):
        encode_body({"a/b": {"x~y": datetime(2026, 1, 1)}})


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ({"period": {"from": datetime(2026, 8, 1)}}, r"^/period/from is a naive datetime"),
        ({"values": [1, float("nan")]}, r"^/values/1 is nan; it must be a finite number"),
        ({"values": [float("inf")]}, r"^/values/0 is inf"),
        ({"amount": Decimal("Infinity")}, r"^/amount is Decimal\('Infinity'\)"),
        ({"amount": Decimal("NaN")}, r"^/amount is Decimal\('NaN'\)"),
        ({"amount": Decimal("sNaN")}, r"^/amount is Decimal\('sNaN'\)"),
        ({"name": "\ud800"}, r"^/name holds text that is not valid Unicode"),
        ({"tags": {"a", "b"}}, r"^/tags is a set, which JSON cannot hold"),
        ({"blob": b"x"}, r"^/blob is a bytes"),
        ({"x": object()}, r"^/x is a object"),
        ({1: "one"}, r"^the request body has a member name 1"),
        ({"nested": {2: "two"}}, r"^/nested has a member name 2"),
    ],
)
def test_a_value_that_cannot_be_sent_is_refused_naming_its_path(
    body: dict[Any, Any], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        encode_body(body)


@pytest.mark.parametrize("body", [[1, 2], "text", None, 3, b"{}"])
def test_a_body_that_is_not_a_mapping_is_refused(body: object) -> None:
    with pytest.raises(ValueError, match="pass a mapping"):
        encode_body(body)


def test_a_body_that_contains_itself_is_refused() -> None:
    body: dict[str, Any] = {"a": []}
    body["a"].append(body)
    with pytest.raises(ValueError, match=r"^/a/0 contains itself"):
        encode_body(body)


def test_the_same_list_twice_is_not_a_cycle() -> None:
    shared = [1]
    assert encode_body({"a": shared, "b": shared}) == b'{"a":[1],"b":[1]}'


def test_an_int_too_long_for_text_is_refused_naming_its_path() -> None:
    with pytest.raises(ValueError, match=r"^/n cannot be written as JSON"):
        encode_body({"n": 10**5000})
