"""Turning the mapping an import ran with into the mapping a commit sends."""

from __future__ import annotations

from typing import cast

from ._generated.requests import ImportMapping
from ._generated.responses import AppliedImportMapping


def to_import_mapping(mapping: AppliedImportMapping, /) -> ImportMapping:
    """Return the mapping an import ran with, read from `imports.get`, as the `mapping` of the
    next `imports.preview` or `imports.commit`.

    It copies the four members and refuses nothing. A delimiter, or a field name in `columns`
    or `constants`, that this SDK does not list is sent as it is, and the API answers it as it
    answers any mapping.
    """
    copied: dict[str, object] = {
        "columns": dict(mapping.columns),
        "constants": dict(mapping.constants),
        "timezone": mapping.timezone,
        # A listed delimiter decodes to an `ImportDelimiter` member; its value is the text.
        "delimiter": str(mapping.delimiter),
    }
    # The response's members are open strings and the request's are closed sets. The API is the
    # check: it refuses a value it does not accept, so each is passed through unchanged.
    return cast("ImportMapping", copied)
