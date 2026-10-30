"""The wire types the ingest release uses, written to match the API's OpenAPI document.

`EventInput` is what a caller sends. `IngestSummary`, `IngestRowError`, `Problem` and
`FieldError` are what the SDK returns. `ErrorCode` and `FieldErrorCode` are open: a code
this version does not list is kept as a plain `str`, never refused.
"""

# No `from __future__ import annotations` here: on Python 3.11 it hides `Required` from
# `TypedDict`, and `EventInput.__required_keys__` would come out empty.
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal, Required, TypedDict

EventCategory = Literal["session", "task", "model", "outcome", "exception"]
"""An event category."""


class EventInput(TypedDict, total=False):
    """One event to ingest.

    Members keep the API's snake_case names. Every member of the mapping is sent, including
    any this type does not list, so a misspelt member reaches the API and comes back as a row
    error rather than being dropped.
    """

    event_id: str | None
    timestamp: Required[datetime | str]
    agent_key: Required[str]
    client_key: str | None
    category: Required[EventCategory]
    event_type: Required[str]
    outcome_type: str | None
    quantity: int | float | None
    cost: Decimal | int | float | None
    tokens_in: int | None
    tokens_out: int | None
    model: str | None
    currency: str | None
    metadata: Mapping[str, Any] | None


class ErrorCode(StrEnum):
    """The request-level error codes. New codes are additive, so a caller also handles a
    code this version does not list, by falling back on the HTTP status."""

    INVALID_JSON = "invalid_json"
    VALIDATION_FAILED = "validation_failed"
    UNAUTHENTICATED = "unauthenticated"
    INSUFFICIENT_SCOPE = "insufficient_scope"
    SESSION_REQUIRED = "session_required"
    ACCOUNT_NOT_PROVISIONED = "account_not_provisioned"
    NOT_FOUND = "not_found"
    NO_ACTIVE_VALUE_MODEL = "no_active_value_model"
    METHOD_NOT_ALLOWED = "method_not_allowed"
    IDEMPOTENCY_KEY_IN_USE = "idempotency_key_in_use"
    CLIENT_KEY_IN_USE = "client_key_in_use"
    AGENT_KEY_IN_USE = "agent_key_in_use"
    CLIENT_HAS_EVENTS = "client_has_events"
    CLIENT_HAS_CALCULATIONS = "client_has_calculations"
    AGENT_HAS_EVENTS = "agent_has_events"
    CLIENT_KEY_HAS_EVENTS = "client_key_has_events"
    VALUE_MODEL_EXISTS = "value_model_exists"
    VALUE_MODEL_VERSION_STALE = "value_model_version_stale"
    CALCULATION_TRANSITION_INVALID = "calculation_transition_invalid"
    CALCULATION_NOT_DRAFT = "calculation_not_draft"
    CALCULATION_NOT_PUBLISHED = "calculation_not_published"
    REPORT_SHARED = "report_shared"
    REPORT_NOT_SHARED = "report_not_shared"
    API_KEY_REVOKED = "api_key_revoked"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    URI_TOO_LONG = "uri_too_long"
    UNSUPPORTED_MEDIA_TYPE = "unsupported_media_type"
    IDEMPOTENCY_KEY_REUSED = "idempotency_key_reused"
    RATE_LIMITED = "rate_limited"
    INTERNAL_ERROR = "internal_error"


class FieldErrorCode(StrEnum):
    """The field-level codes of a problem's `errors` entry or an ingest row error. New codes
    are additive."""

    REQUIRED = "required"
    UNKNOWN_FIELD = "unknown_field"
    IMMUTABLE = "immutable"
    INVALID_TYPE = "invalid_type"
    INVALID_FORMAT = "invalid_format"
    INVALID_VALUE = "invalid_value"
    TOO_LONG = "too_long"
    TOO_MANY = "too_many"
    OUT_OF_RANGE = "out_of_range"
    TOO_PRECISE = "too_precise"
    DUPLICATE = "duplicate"
    TOO_LARGE = "too_large"
    MUTUALLY_EXCLUSIVE = "mutually_exclusive"
    UNKNOWN_REFERENCE = "unknown_reference"
    CLIENT_KEY_REQUIRED = "client_key_required"
    CURRENCY_MISMATCH = "currency_mismatch"


def error_code(value: str) -> ErrorCode | str:
    """Return the `ErrorCode` member for `value`, or `value` itself when none matches."""
    try:
        return ErrorCode(value)
    except ValueError:
        return value


def field_error_code(value: str) -> FieldErrorCode | str:
    """Return the `FieldErrorCode` member for `value`, or `value` itself when none matches."""
    try:
        return FieldErrorCode(value)
    except ValueError:
        return value


@dataclass(frozen=True)
class IngestRowError:
    """One problem with a rejected event.

    `index` is the event's zero-based position in the list passed to `ingest`, and `pointer`
    is a JSON Pointer that starts `/events/<index>`.
    """

    index: int
    code: FieldErrorCode | str
    pointer: str
    detail: str


@dataclass(frozen=True)
class IngestSummary:
    """The combined outcome of one `ingest` call, over every batch it sent.

    `accepted + duplicates + rejected` equals the number of events passed in. `errors` holds
    one entry per problem, ascending by `index`. `batches` is the number of batches sent.
    """

    accepted: int
    duplicates: int
    rejected: int
    errors: tuple[IngestRowError, ...]
    errors_truncated: bool
    batches: int


@dataclass(frozen=True)
class FieldError:
    """One entry of a problem's `errors`. It carries one primary locator: `pointer`,
    `parameter`, `header` or `part`. `pointer` or `column` may accompany `part`."""

    code: FieldErrorCode | str
    detail: str
    pointer: str | None = None
    parameter: str | None = None
    header: str | None = None
    part: str | None = None
    column: str | None = None


@dataclass(frozen=True)
class Problem:
    """An RFC 9457 problem document, as the API sends with every error status.

    The API sends every member but `errors`. A member that is absent or of the wrong type,
    as a proxy might send it, is `None` rather than a reason to drop the document.
    """

    type: str | None = None
    title: str | None = None
    status: int | None = None
    detail: str | None = None
    code: ErrorCode | str | None = None
    request_id: str | None = None
    errors: tuple[FieldError, ...] | None = None
