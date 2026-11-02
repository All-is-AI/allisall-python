"""A request body to JSON bytes, written by each value's type.

No I/O: `Allisall` and `AsyncAllisall` share it. Every member the body holds is written,
including any its type does not list. Money needs no table of paths: the SDK uses `Decimal`
for money alone, so every `Decimal` is written as a JSON number with its exact digits.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal

from ._pointer import escape

MAX_EXPONENT = 400
"""The largest exponent magnitude of a `Decimal` the SDK writes. Plain notation writes every
digit, so a larger one would build a string of up to a billion characters before sending. No
amount the API accepts comes near it."""


def encode_body(body: object) -> bytes:
    """Encode a JSON request body as compact UTF-8, writing every member it holds.

    Raises `ValueError` naming the value's JSON Pointer when the body is not a mapping, or
    when a value cannot be sent: a naive `datetime`, a non-finite `float` or `Decimal`, a
    `Decimal` whose exponent's magnitude is over 400, a member name that is not a `str`, text
    that is not valid Unicode, or a value of a type JSON cannot hold.
    """
    if not isinstance(body, Mapping):
        raise ValueError(f"the request body is a {type(body).__name__}; pass a mapping")
    return _encode(body, "", set()).encode("utf-8")


def check_exponent(value: Decimal, where: str) -> None:
    """Raise `ValueError` when `value`'s exponent, as scientific notation writes it, has a
    magnitude over `MAX_EXPONENT`."""
    exponent = value.adjusted()
    if abs(exponent) > MAX_EXPONENT:
        raise ValueError(
            f"{where} is a Decimal whose exponent is {exponent:+d}; "
            f"the SDK sends an exponent between -{MAX_EXPONENT} and +{MAX_EXPONENT}"
        )


def aware_isoformat(value: datetime, where: str) -> str:
    """An aware `datetime` as RFC 3339 text, with the offset it carries. Raises `ValueError`
    naming `where` for a naive one, whose instant the SDK would have to guess."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{where} is a naive datetime; give it a time zone, such as datetime.UTC")
    return value.isoformat()


def _encode(value: object, pointer: str, open_containers: set[int]) -> str:
    where = pointer or "the request body"
    # bool before int, and datetime before date: each is a subclass of the other.
    if value is None or isinstance(value, bool):
        return json.dumps(value)
    if isinstance(value, str):
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as err:
            raise ValueError(f"{where} holds text that is not valid Unicode: {err}") from err
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError(f"{where} is {value!r}; it must be a finite number")
        check_exponent(value, where)
        return format(value, "f")
    if isinstance(value, int):
        try:
            return str(value)
        except ValueError as err:  # more digits than the interpreter converts to text
            raise ValueError(f"{where} cannot be written as JSON: {err}") from err
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{where} is {value!r}; it must be a finite number")
        return repr(value)
    if isinstance(value, datetime):
        return json.dumps(aware_isoformat(value, where))
    if isinstance(value, date):
        return json.dumps(value.isoformat())
    if isinstance(value, Mapping | list | tuple):
        if id(value) in open_containers:
            raise ValueError(f"{where} contains itself")
        open_containers.add(id(value))
        try:
            if isinstance(value, Mapping):
                return _encode_object(value, pointer, open_containers)
            return (
                "["
                + ",".join(
                    _encode(item, f"{pointer}/{index}", open_containers)
                    for index, item in enumerate(value)
                )
                + "]"
            )
        finally:
            open_containers.discard(id(value))
    raise ValueError(f"{where} is a {type(value).__name__}, which JSON cannot hold")


def _encode_object(value: Mapping[object, object], pointer: str, open_containers: set[int]) -> str:
    members: list[str] = []
    for name, member in value.items():
        if not isinstance(name, str):
            raise ValueError(
                f"{pointer or 'the request body'} has a member name {name!r}, which is not a str"
            )
        child = f"{pointer}/{escape(name)}"
        members.append(_encode(name, child, set()) + ":" + _encode(member, child, open_containers))
    return "{" + ",".join(members) + "}"
