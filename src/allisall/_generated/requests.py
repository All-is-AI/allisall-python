# Generated from the API's OpenAPI document by scripts/generate.py, with
# datamodel-code-generator. Never edit this file by hand: change the document or
# the script, and regenerate.

from __future__ import annotations

from typing import Any, Literal, NotRequired, TypeAlias, TypedDict

from allisall._types import DateInput, InstantInput, MoneyInput

UuidInput: TypeAlias = str
"""
An id a request sends: the RFC 9562 §4 string form, `8-4-4-4-12` hexadecimal digits in either case, as RFC 9562 allows. Any other spelling is malformed. The server returns every id in lowercase (`Uuid`).
"""


Month: TypeAlias = str
"""
A calendar month, `YYYY-MM`: the UTC range from the first instant of the month to the first instant of the next.
"""


Currency: TypeAlias = str
"""
An ISO 4217 alphabetic currency code, upper case.
"""


PeriodInput = TypedDict(
    "PeriodInput",
    {
        "from": InstantInput,
        "to": InstantInput,
    },
)


ClientStatus: TypeAlias = Literal["active", "churned", "prospect"]
"""
A client's lifecycle status.
"""


AgentStatus: TypeAlias = Literal["active", "paused", "retired"]
"""
An agent's lifecycle status.
"""


ValueModelStatus: TypeAlias = Literal["active", "archived"]
"""
A value model's status. At most one model per client is `active`.
"""


EventCategory: TypeAlias = Literal["session", "task", "model", "outcome", "exception"]
"""
An event category.
"""


CostTargetKind: TypeAlias = Literal["client", "agent"]
"""
What a cost line item is charged to.
"""


DisclosureKind: TypeAlias = Literal[
    "empty",
    "unpriced",
    "key_unset",
    "unmatched",
    "unattributable",
    "precedes",
    "unpriceable",
    "uncosted",
    "token_valued",
    "unattributed",
    "partial",
    "truncated",
]
"""
A coverage finding on a report. Each kind appears at most once per report. `facts` per kind: `empty` `{}`; `unpriced` `{outcome_types: [{outcome_type, quantity}], outcome_types_omitted}`, at most 100 outcome types by quantity, largest first, with `outcome_types_omitted` counting the rest, which a report composed before the count existed lacks; `key_unset` `{}`; `unmatched` `{keys}`; `unattributable` `{events}`; `precedes` `{}`; `unpriceable` `{models}`; `uncosted` `{events}`; `token_valued` `{events}`; `unattributed` `{line_items}`; `partial` `{line_items}`; `truncated` `{prorated_through}`.
"""


class ClientCreate(TypedDict):
    name: str
    """
    Free text, trimmed of white space (the Unicode `White_Space` property) at both ends. The trimmed name is stored. It holds 1 to 200 characters, counted in Unicode code points after trimming: blank after trimming is `required`, and longer than 200 characters after trimming is `too_long`. U+0000 is `invalid_format`, as in every request string. No JSON Schema keyword measures a length after trimming, so the schema states no `maxLength`; a `maxLength` of 200 would refuse a padded name the server accepts.
    """
    status: ClientStatus
    client_key: NotRequired[str | None]
    renewal_date: NotRequired[DateInput | None]
    notes: NotRequired[str | None]


class ClientPatch(TypedDict):
    """
    A JSON Merge Patch (RFC 7396): an absent member is unchanged, `null` clears a member. The merged client is validated whole.
    """

    name: NotRequired[str]
    """
    Free text, trimmed of white space (the Unicode `White_Space` property) at both ends. The trimmed name is stored. It holds 1 to 200 characters, counted in Unicode code points after trimming: blank after trimming is `required`, and longer than 200 characters after trimming is `too_long`. U+0000 is `invalid_format`, as in every request string. No JSON Schema keyword measures a length after trimming, so the schema states no `maxLength`; a `maxLength` of 200 would refuse a padded name the server accepts.
    """
    status: NotRequired[ClientStatus]
    client_key: NotRequired[str | None]
    renewal_date: NotRequired[DateInput | None]
    notes: NotRequired[str | None]


class ClientAgentsSet(TypedDict):
    agent_ids: list[UuidInput]
    """
    The complete set of assigned agents, at most 200. `[]` clears it. An id naming no agent in the workspace is refused with `unknown_reference`. A longer array is refused at its 201st element with one `too_many` at `/agent_ids`.
    """


class AgentCreate(TypedDict):
    agent_key: str
    """
    1 to 200 characters, counted as sent. Not trimmed: a key with white space (the Unicode `White_Space` property) at either end, or white space only, is refused with `invalid_format`. Unique in the workspace. Cannot change later.
    """
    name: str
    """
    Free text, trimmed of white space (the Unicode `White_Space` property) at both ends. The trimmed name is stored. It holds 1 to 200 characters, counted in Unicode code points after trimming: blank after trimming is `required`, and longer than 200 characters after trimming is `too_long`. U+0000 is `invalid_format`, as in every request string. No JSON Schema keyword measures a length after trimming, so the schema states no `maxLength`; a `maxLength` of 200 would refuse a padded name the server accepts.
    """
    framework: NotRequired[str | None]
    version: NotRequired[str | None]
    status: AgentStatus


class AgentPatch(TypedDict):
    """
    A JSON Merge Patch (RFC 7396). `agent_key` is refused with the field code `immutable`, not `unknown_field`: it exists, and this operation cannot change it.
    """

    name: NotRequired[str]
    """
    Free text, trimmed of white space (the Unicode `White_Space` property) at both ends. The trimmed name is stored. It holds 1 to 200 characters, counted in Unicode code points after trimming: blank after trimming is `required`, and longer than 200 characters after trimming is `too_long`. U+0000 is `invalid_format`, as in every request string. No JSON Schema keyword measures a length after trimming, so the schema states no `maxLength`; a `maxLength` of 200 would refuse a padded name the server accepts.
    """
    framework: NotRequired[str | None]
    version: NotRequired[str | None]
    status: NotRequired[AgentStatus]


class ValueModelCreate(TypedDict):
    """
    Creates the client's active model. `template_id` and `copy_from_model_id` are create-only and are not echoed. Setting both is refused with `mutually_exclusive` at `/copy_from_model_id`. With neither, the model starts with no line items.
    """

    name: str
    """
    Free text, trimmed of white space (the Unicode `White_Space` property) at both ends. The trimmed name is stored. It holds 1 to 200 characters, counted in Unicode code points after trimming: blank after trimming is `required`, and longer than 200 characters after trimming is `too_long`. U+0000 is `invalid_format`, as in every request string. No JSON Schema keyword measures a length after trimming, so the schema states no `maxLength`; a `maxLength` of 200 would refuse a padded name the server accepts.
    """
    template_id: NotRequired[str | None]
    copy_from_model_id: NotRequired[UuidInput | None]


class ValueModelPatch(TypedDict):
    """
    A JSON Merge Patch (RFC 7396) of the client's active model. Setting `status` to `archived` frees the client for a new active model.
    """

    name: NotRequired[str]
    """
    Free text, trimmed of white space (the Unicode `White_Space` property) at both ends. The trimmed name is stored. It holds 1 to 200 characters, counted in Unicode code points after trimming: blank after trimming is `required`, and longer than 200 characters after trimming is `too_long`. U+0000 is `invalid_format`, as in every request string. No JSON Schema keyword measures a length after trimming, so the schema states no `maxLength`; a `maxLength` of 200 would refuse a padded name the server accepts.
    """
    status: NotRequired[ValueModelStatus]


class ValueLineItemInput(TypedDict):
    outcome_type: str
    """
    1 to 200 characters, counted as sent. Not trimmed: a value with white space (the Unicode `White_Space` property) at either end, or white space only, is refused with `invalid_format`. Unique within the set, case-insensitively.
    """
    label: str
    """
    Free text, trimmed of white space (the Unicode `White_Space` property) at both ends. The trimmed label is stored. It holds 1 to 200 characters, counted in Unicode code points after trimming: blank after trimming is `required`, and longer than 200 characters after trimming is `too_long`. U+0000 is `invalid_format`, as in every request string. No JSON Schema keyword measures a length after trimming, so the schema states no `maxLength`; a `maxLength` of 200 would refuse a padded label the server accepts.
    """
    unit_value: NotRequired[MoneyInput]
    """
    At least 0 and below 100,000,000, with at most 4 decimal places; more is refused with `too_precise`, never rounded. Absent means 0, because templates ship every unit value as 0 on purpose.
    """
    provenance_note: NotRequired[str | None]


class ValueLineItemsSet(TypedDict):
    version: int
    """
    The `version` of the model the caller read. A different stored version is refused with `value_model_version_stale`. A value of 0 or less is `out_of_range`; an absent or `null` one is `required`.
    """
    line_items: list[ValueLineItemInput]
    """
    The complete set, at most 50. `[]` empties it. Stored `position` follows this order.
    """


class CostTargetInput(TypedDict):
    """
    The writable part of `target`. `name` is read-only.
    """

    kind: CostTargetKind
    id: UuidInput
    """
    An id naming no client or agent in the workspace is refused with `unknown_reference`.
    """


class CostLineItemCreate(TypedDict):
    label: str
    """
    Free text, trimmed of white space (the Unicode `White_Space` property) at both ends. The trimmed label is stored. It holds 1 to 200 characters, counted in Unicode code points after trimming: blank after trimming is `required`, and longer than 200 characters after trimming is `too_long`. U+0000 is `invalid_format`, as in every request string. No JSON Schema keyword measures a length after trimming, so the schema states no `maxLength`; a `maxLength` of 200 would refuse a padded label the server accepts.
    """
    target: CostTargetInput
    monthly_amount: MoneyInput
    """
    In the workspace currency. At least 0 and below 100,000,000, with at most 4 decimal places; more is refused with `too_precise`. Required: absent or `null` is refused with `required`, and `0` must be sent explicitly.
    """
    start_date: DateInput
    end_date: NotRequired[DateInput | None]


class CostLineItemPatch(TypedDict):
    """
    A JSON Merge Patch (RFC 7396). The merged line item is validated whole.
    """

    label: NotRequired[str]
    """
    Free text, trimmed of white space (the Unicode `White_Space` property) at both ends. The trimmed label is stored. It holds 1 to 200 characters, counted in Unicode code points after trimming: blank after trimming is `required`, and longer than 200 characters after trimming is `too_long`. U+0000 is `invalid_format`, as in every request string. No JSON Schema keyword measures a length after trimming, so the schema states no `maxLength`; a `maxLength` of 200 would refuse a padded label the server accepts.
    """
    target: NotRequired[CostTargetInput]
    monthly_amount: NotRequired[MoneyInput]
    """
    In the workspace currency. At least 0 and below 100,000,000, with at most 4 decimal places; more is refused with `too_precise`.
    """
    start_date: NotRequired[DateInput]
    end_date: NotRequired[DateInput | None]


class ModelRateInput(TypedDict):
    model: str
    """
    1 to 200 characters. A name blank after trimming is refused with `required`, and one holding U+0000 with `invalid_format`. Unique within the table after trimming and lower-casing: a name equal to an earlier entry's is refused with `duplicate` at the later entry. Stored as sent.
    """
    input_per_1k: MoneyInput
    """
    The price of 1,000 input tokens. At least 0 and below 100,000,000, with at most 9 decimal places; more is refused with `too_precise`, never rounded. A rate is not money: $0.000001 per million tokens is 0.000000001 per 1,000. Money computed from a rate keeps 6 decimal places, as an event's `cost` does.
    """
    output_per_1k: MoneyInput
    """
    The price of 1,000 output tokens. At least 0 and below 100,000,000, with at most 9 decimal places; more is refused with `too_precise`, never rounded. A rate is not money: $0.000001 per million tokens is 0.000000001 per 1,000. Money computed from a rate keeps 6 decimal places, as an event's `cost` does.
    """


class PriceTableSet(TypedDict):
    currency: NotRequired[Currency]
    """
    Optional, so a caller can `PUT` back the table it read. It cannot change the currency: when sent it must equal the workspace currency, or the request is refused with `400` `validation_failed` and the field code `currency_mismatch` at `/currency`.
    """
    models: list[ModelRateInput]
    """
    The complete table, at most 200. `[]` empties it. A longer array is refused at its 201st entry with one `too_many` at `/models`, before any entry is validated.
    """


class CalculationCreate(TypedDict):
    period: PeriodInput
    """
    The ended period to freeze. Digits below a microsecond are dropped from each bound before any check, because storage keeps no finer. A bound before `1900-01-01T00:00:00Z` is refused with `out_of_range` at its own pointer. `from` must be before `to`: a period with `from` at or after `to` holds no instant, and is refused with `out_of_range` at `/period/from`. `to` may be at most 731 days after `from`; a longer period is refused with `out_of_range` at `/period`. `to` must be at or before the start of the current UTC day, and after the client's first recorded activity; either failure is refused with `out_of_range` at `/period/to`. A client with no recorded events or charges at all is refused with `out_of_range` at `/period`, because no period can succeed.
    """


class DisclosureEdit(TypedDict):
    kind: DisclosureKind
    """
    Names one of the report's stored findings, spelled as a read returns it. A kind that is not one of them is refused with `invalid_value` at `/disclosures/<index>/kind`.
    """
    included: bool
    text: NotRequired[str | None]


class ReportPatch(TypedDict):
    """
    A JSON Merge Patch (RFC 7396). An array replaces the stored array whole. A shared report is refused with `report_shared`.
    """

    client_name: NotRequired[str]
    """
    Free text, 1 to 200 characters counted in Unicode code points, padding included. Not trimmed: the value is stored as sent. Blank after trimming white space is `required`, and longer than 200 characters is `too_long`.
    """
    workspace_name: NotRequired[str]
    """
    Free text, 1 to 200 characters counted in Unicode code points, padding included. Not trimmed: the value is stored as sent. Blank after trimming white space is `required`, and longer than 200 characters is `too_long`.
    """
    note: NotRequired[str | None]
    disclosures: NotRequired[list[DisclosureEdit]]
    """
    Replaces the editorial state of every finding. It must name each stored finding exactly once: a missing one is `required`, an unknown one `invalid_value`, a repeated one `duplicate`. At most 50: a longer array is refused at its 51st element with one `too_many` at `/disclosures`.
    """


class EventInput(TypedDict):
    """
    A canonical event. A problem with one event rejects that event only, as row errors; an unknown member is such a problem. `category` outside `EventCategory` is refused with `invalid_value`. `currency` is not part of the deduplication hash.
    """

    event_id: NotRequired[str | None]
    timestamp: InstantInput
    """
    When the event happened. At most 24 hours in the future.
    """
    agent_key: str
    """
    The agent that acted. An agent not seen before is created. 1 to 200 characters, counted as sent; more is refused with `too_long`.
    """
    client_key: NotRequired[str | None]
    category: EventCategory
    event_type: str
    """
    What the agent did. 1 to 200 characters, counted as sent; more is refused with `too_long`.
    """
    outcome_type: NotRequired[str | None]
    quantity: NotRequired[float | None]
    cost: NotRequired[MoneyInput | None]
    tokens_in: NotRequired[int | None]
    tokens_out: NotRequired[int | None]
    model: NotRequired[str | None]
    currency: NotRequired[Currency | None]
    metadata: NotRequired[dict[str, Any] | None]


class EventBatch(TypedDict):
    events: list[EventInput]
    """
    1 to 500 events. More than 500 is `413` `payload_too_large`.
    """


class ImportMapping(TypedDict):
    """
    How a CSV file maps onto canonical events. Each row's mapped values are held to the rules of `EventInput`. A `cost` with more than 6 decimal places is refused with `too_precise`, as on ingest. A `quantity` or `cost` cell must be a decimal number, `^[+-]?[0-9]+(\\.[0-9]+)?([eE][+-]?[0-9]+)?$` after trimming, and a `tokens_in` or `tokens_out` cell an integer, `^[+-]?[0-9]+$`; anything else, hexadecimal, underscores, `Inf` and `NaN` included, is refused with `invalid_format`. An empty cell is not provided. An empty `currency` cell declares no currency. An `event_id`, `agent_key`, `client_key`, `event_type`, `outcome_type` or `model` value holds at most 200 characters, as on ingest. A cell is counted after trimming, and a constant as given. A longer value refuses its row with `too_long` at its column, or with a `null` column for a constant. A cell bound to `event_id`, `agent_key`, `client_key`, `category`, `event_type`, `outcome_type` or `model` that is not valid UTF-8 refuses its row with `invalid_format` at its column, as one holding U+0000 does.
    """

    columns: NotRequired[
        dict[
            Literal[
                "timestamp",
                "agent_key",
                "client_key",
                "category",
                "event_type",
                "outcome_type",
                "quantity",
                "cost",
                "tokens_in",
                "tokens_out",
                "model",
                "currency",
                "event_id",
            ],
            str,
        ]
    ]
    """
    Canonical field name to the file's column name. `timestamp`, `agent_key`, `event_type` and `category` must each be bound here or in `constants`. A column name is at most 256 bytes of UTF-8; a longer one is refused with `too_long` at its member. `maxLength` counts characters, so the server's byte limit is the tighter.
    """
    constants: NotRequired[
        dict[
            Literal[
                "agent_key",
                "client_key",
                "category",
                "event_type",
                "outcome_type",
                "quantity",
                "cost",
                "tokens_in",
                "tokens_out",
                "model",
                "currency",
            ],
            str,
        ]
    ]
    """
    Canonical field name to a value used for every row. `timestamp` and `event_id` cannot be constants. A field cannot be bound in both maps. A constant for `agent_key`, `client_key`, `event_type`, `outcome_type` or `model` holds at most 200 characters, counted as sent; a longer one refuses every row with `too_long`.
    """
    timezone: NotRequired[str]
    """
    An IANA zone for timestamps without an offset. Default `UTC`. `Local` is refused.
    """
    delimiter: NotRequired[Literal[",", ";", "\t"]]
    """
    The field delimiter. Default `,`.
    """


class ImportUpload(TypedDict):
    """
    Two parts, in this order: `mapping`, then `file`. The server reads them in that order and never buffers the file whole. A request-level problem in this body is located by `part` (see `FieldError`): a mapping member by `part` `mapping` and a `pointer` into the mapping, such as `/columns/client_key`; a mapped column absent from the file header by `part` `file` and that `column`; a missing or misordered part by `part` alone. A part after `file` is refused with `unknown_field` on that part, and a `mapping` part over 65,536 bytes with `too_large`. A header that names a column more than once is refused with `duplicate` on `part` `file` and that `column`, one entry per repeated name in the order each first repeats, before any `required` entry for a mapped column the header lacks. Names compare exactly, untrimmed, so `Bot` and `Bot ` are two columns. Blank header cells may repeat unless the mapping binds the blank name.
    """

    mapping: ImportMapping
    file: str
    """
    The CSV file, with a header row. At most 250,000 data rows. Each header name is at most 256 bytes of UTF-8; a longer one is refused with `too_long` on `part` `file`, located by its position in the `detail` and carrying no `column`, before any repeated-name or missing-column check. A header name that is not valid UTF-8 is accepted, but the mapping cannot bind it, and the response writes each such byte as U+FFFD wherever it names the column. The part's file name is stored with the import, so one that is not valid UTF-8 is refused with `invalid_format` on `part` `file`, as one holding U+0000 is.
    """
