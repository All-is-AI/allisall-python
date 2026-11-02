"""A response body to its dataclass, driven by the dataclass's annotations.

No I/O: `Allisall` and `AsyncAllisall` share it. The body is parsed with every JSON number that
has a fraction or an exponent read as a `Decimal` from its text, so money is exact before any
binary float exists. A member is money exactly when its annotation is `Decimal`. At a member
annotated `float`, a number, whether parsed as a `Decimal` or an `int`, is converted to a
`float`; any other value passes unchecked.

The decoder reads each class's annotations once, and builds a plan of small functions from them.
A response member the class does not declare is ignored. An open set of codes, annotated
`SomeEnum | str`, gives the enum's member when the enum lists the value, and the `str` itself
otherwise. Scalars the decoder need not convert are not checked.
"""

from __future__ import annotations

import collections.abc
import dataclasses
import functools
import json
import keyword
import types
import typing
from collections.abc import Callable
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal, TypeVar, cast

from ._pointer import escape

T = TypeVar("T")

Builder = Callable[[object, str], object]
"""Builds one value from its parsed JSON; the second argument is its JSON Pointer."""


class ShapeError(Exception):
    """A response body the decoder cannot build its type from. `pointer` names the value."""

    def __init__(self, pointer: str, message: str) -> None:
        super().__init__(f"{pointer or 'the body'}: {message}")
        self.pointer = pointer


def parse(content: bytes | str) -> object:
    """Parse a JSON body, reading each number with a fraction or an exponent as a `Decimal`.

    Raises `ShapeError` when the body is not JSON, including `NaN` and `Infinity`, which
    Python's `json` otherwise accepts although JSON does not.
    """
    try:
        parsed: object = json.loads(content, parse_float=Decimal, parse_constant=_refuse_constant)
    except ValueError as err:
        raise ShapeError("", f"the body is not JSON: {err}") from err
    return parsed


def decode(cls: type[T], content: bytes | str) -> T:
    """Parse a JSON body and build `cls` from it. Raises `ShapeError` on the wrong shape."""
    return build(cls, parse(content))


def build(cls: type[T], value: object) -> T:
    """Build `cls`, a generated response dataclass, from parsed JSON."""
    annotation: object = cls
    # The builder for a dataclass returns an instance of it.
    return cast(T, _builder(annotation)(value, ""))


def check_supported(cls: type) -> None:
    """Raise `TypeError` when an annotation reachable from `cls` is one the decoder does not
    support, such as a union of two dataclasses."""
    _builder(cls)


def wire_name(field_name: str) -> str:
    """The JSON member a dataclass field reads: the field's name, less the `_` appended to a
    Python keyword such as `from`."""
    if field_name.endswith("_") and keyword.iskeyword(field_name[:-1]):
        return field_name[:-1]
    return field_name


def _refuse_constant(name: str) -> object:
    raise ValueError(f"{name} is not a JSON number")


@functools.cache
def _builder(annotation: object) -> Builder:
    if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
        return _dataclass_builder(annotation)
    if annotation is Decimal:
        return _money
    if annotation is float:
        return _float
    if annotation in (int, str, bool, type(None)):
        return _as_is
    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)
    if origin is Literal:
        return _as_is
    if origin in (types.UnionType, typing.Union):
        return _union_builder(args, annotation)
    if origin is collections.abc.Sequence and len(args) == 1:
        return _sequence_builder(_builder(args[0]))
    if origin is collections.abc.Mapping and args == (str, Any):
        return _free_form
    raise TypeError(f"the response decoder does not support the annotation {annotation!r}")


def _dataclass_builder(cls: type) -> Builder:
    hints = typing.get_type_hints(cls)
    plan: list[tuple[str, str, Builder, bool]] = []
    for field in dataclasses.fields(cls):
        has_default = (
            field.default is not dataclasses.MISSING
            or field.default_factory is not dataclasses.MISSING
        )
        plan.append((field.name, wire_name(field.name), _builder(hints[field.name]), has_default))

    def build_dataclass(value: object, pointer: str) -> object:
        if not isinstance(value, dict):
            raise ShapeError(pointer, f"expected an object, found {_kind(value)}")
        members: dict[str, object] = {}
        for name, wire, member_builder, has_default in plan:
            if wire in value:
                members[name] = member_builder(value[wire], f"{pointer}/{escape(wire)}")
            elif not has_default:
                raise ShapeError(pointer, f"the required member {wire!r} is absent")
        return cls(**members)

    return build_dataclass


def _union_builder(args: tuple[object, ...], annotation: object) -> Builder:
    nullable = type(None) in args
    rest = tuple(arg for arg in args if arg is not type(None))
    if len(rest) == 1:
        inner = _builder(rest[0])
    elif _is_open_enum(rest):
        enum = next(arg for arg in rest if arg is not str)
        inner = _open_enum_builder(cast(type[StrEnum], enum))
    elif _is_open_literal(rest):
        # The event category: an open set kept as its Literal, so the value stays a str.
        inner = _as_is
    else:
        # Any other union, such as two dataclasses or `str | int`, would need the decoder to
        # choose a branch. Refused here, so a spec change that brings one fails the check.
        raise TypeError(f"the response decoder does not support the annotation {annotation!r}")
    if not nullable:
        return inner

    def build_nullable(value: object, pointer: str) -> object:
        return None if value is None else inner(value, pointer)

    return build_nullable


def _is_open_literal(args: tuple[object, ...]) -> bool:
    """A `Literal` of strings joined with `str`."""
    return (
        len(args) == 2
        and str in args
        and any(
            typing.get_origin(arg) is Literal
            and all(isinstance(value, str) for value in typing.get_args(arg))
            for arg in args
        )
    )


def _is_open_enum(args: tuple[object, ...]) -> bool:
    return (
        len(args) == 2
        and str in args
        and any(isinstance(arg, type) and issubclass(arg, StrEnum) for arg in args)
    )


def _open_enum_builder(enum: type[StrEnum]) -> Builder:
    def build_open_enum(value: object, pointer: str) -> object:
        if isinstance(value, str):
            try:
                return enum(value)
            except ValueError:
                return value
        return value

    return build_open_enum


def _sequence_builder(item: Builder) -> Builder:
    def build_sequence(value: object, pointer: str) -> object:
        if not isinstance(value, list):
            raise ShapeError(pointer, f"expected an array, found {_kind(value)}")
        return tuple(item(element, f"{pointer}/{index}") for index, element in enumerate(value))

    return build_sequence


def _money(value: object, pointer: str) -> object:
    if isinstance(value, Decimal):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return Decimal(value)
    raise ShapeError(pointer, f"expected a number for an amount of money, found {_kind(value)}")


def _float(value: object, pointer: str) -> object:
    if isinstance(value, Decimal | int) and not isinstance(value, bool):
        return float(value)
    return value


def _as_is(value: object, pointer: str) -> object:
    return value


def _free_form(value: object, pointer: str) -> object:
    if not isinstance(value, dict):
        raise ShapeError(pointer, f"expected an object, found {_kind(value)}")
    return _plain_numbers(value)


def _plain_numbers(value: object) -> object:
    """Free-form JSON as `json.loads` gives it by default: every `Decimal` becomes a `float`."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, dict):
        return {name: _plain_numbers(member) for name, member in value.items()}
    if isinstance(value, list):
        return [_plain_numbers(item) for item in value]
    return value


def _kind(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "a boolean"
    if isinstance(value, str):
        return "a string"
    if isinstance(value, Decimal | int):
        return "a number"
    if isinstance(value, list):
        return "an array"
    return "an object"
