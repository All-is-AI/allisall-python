"""Response bodies built from the generated dataclasses' annotations, and each operation's
facts read from the OpenAPI document, for the tests that run every operation."""

from __future__ import annotations

import collections.abc
import dataclasses
import functools
import types
import typing
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal

from allisall._decode import wire_name
from allisall._generated import responses
from test_operations import spec_operations
from test_spec import load_spec


def sample(annotation: object, money: object = 12.5) -> Any:
    """A JSON value the decoder accepts for `annotation`, with every member present. Each
    money value is `money`."""
    if isinstance(annotation, type) and dataclasses.is_dataclass(annotation):
        hints = typing.get_type_hints(annotation)
        return {
            wire_name(field.name): sample(hints[field.name], money)
            for field in dataclasses.fields(annotation)
        }
    if annotation is Decimal:
        return money
    if annotation is float:
        return 0.5
    if annotation is int:
        return 1
    if annotation is bool:
        return False
    if annotation is str:
        return "text"
    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)
    if origin is Literal:
        return args[0]
    if origin in (types.UnionType, typing.Union):
        rest = [arg for arg in args if arg is not type(None) and arg is not str]
        if not rest:
            return "text"
        first = rest[0]
        if isinstance(first, type) and issubclass(first, StrEnum):
            return next(iter(first)).value
        return sample(first, money)
    if origin is collections.abc.Sequence:
        return [sample(args[0], money)]
    if origin is collections.abc.Mapping:
        return {}
    raise TypeError(f"no sample for {annotation!r}")


@functools.cache
def document() -> dict[str, Any]:
    return load_spec()


@functools.cache
def response_class(operation_id: str) -> type | None:
    """The generated class of an operation's `2xx` body, named by the document; `None` for
    an answer with no body."""
    for item in document()["paths"].values():
        for operation in item.values():
            if not isinstance(operation, dict) or operation.get("operationId") != operation_id:
                continue
            for code, response in operation["responses"].items():
                if str(code)[0] != "2":
                    continue
                content = response.get("content")
                if not content:
                    return None
                ref: str = content["application/json"]["schema"]["$ref"]
                cls: type = getattr(responses, ref.rsplit("/", 1)[1])
                return cls
    raise KeyError(operation_id)


def item_class(cls: type) -> type:
    """The type of the items of a list body's `data`."""
    data = typing.get_type_hints(cls)["data"]
    item: type = typing.get_args(data)[0]
    return item


@functools.cache
def operations() -> dict[str, Any]:
    return spec_operations(document())
