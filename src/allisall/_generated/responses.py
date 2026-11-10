# Generated from the API's OpenAPI document by scripts/generate.py, with
# datamodel-code-generator. Never edit this file by hand: change the document or
# the script, and regenerate.

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal, TypeAlias

from allisall._types import EventCategory, FieldErrorCode

Uuid: TypeAlias = str
"""
A resource id: a UUID in lowercase canonical form (RFC 9562). Clients treat it as opaque.
"""


Instant: TypeAlias = str
"""
An instant, RFC 3339 `date-time`. Responses give it in UTC with `Z`, with fractional seconds only when non-zero, up to six digits and no trailing zeros. A stored calculation snapshot is served as it was stored, so instants inside a `snapshot` may carry the offset they were written with.
"""


Date: TypeAlias = str
"""
A calendar date, RFC 3339 `full-date` (`YYYY-MM-DD`), a UTC day.
"""


Month: TypeAlias = str
"""
A calendar month, `YYYY-MM`: the UTC range from the first instant of the month to the first instant of the next.
"""


Currency: TypeAlias = str
"""
An ISO 4217 alphabetic currency code, upper case.
"""


MinorUnits: TypeAlias = int
"""
The number of decimal places the money figures beside it were rounded to: the ISO 4217 exponent of `currency`.
"""


Ratio: TypeAlias = float
"""
A ratio as a fraction, not a percentage: `0.25` means 25%.
"""


@dataclass(frozen=True, kw_only=True)
class Period:
    """
    A half-open range of instants, `[from, to)`. An unbounded side is `null`.
    """

    from_: Instant | None
    to: Instant | None


class ClientStatus(StrEnum):
    """
    A client's lifecycle status.
    """

    ACTIVE = "active"
    CHURNED = "churned"
    PROSPECT = "prospect"


class AgentStatus(StrEnum):
    """
    An agent's lifecycle status.
    """

    ACTIVE = "active"
    PAUSED = "paused"
    RETIRED = "retired"


class ValueModelStatus(StrEnum):
    """
    A value model's status. At most one model per client is `active`.
    """

    ACTIVE = "active"
    ARCHIVED = "archived"


class CalculationState(StrEnum):
    """
    A calculation's position in its lifecycle: `draft` → `validated` → `published`; `validated` → `draft` on reopen. Publication is terminal.
    """

    DRAFT = "draft"
    VALIDATED = "validated"
    PUBLISHED = "published"


class ReportState(StrEnum):
    """
    A report's position in its lifecycle: `draft` until it is shared, `shared` while its link works, and `revoked` once the link is revoked. A state only moves forward.
    """

    DRAFT = "draft"
    SHARED = "shared"
    REVOKED = "revoked"


class RenewalTerm(StrEnum):
    """
    How often a client's renewal recurs: every month, or every year. Each renewal is the date as set plus whole terms, on the same day of the month, or on the month's last day when the month is shorter: a monthly renewal set on 31 January falls on 28 February, then 31 March.
    """

    MONTHLY = "monthly"
    ANNUAL = "annual"


class CostTargetKind(StrEnum):
    """
    What a cost line item is charged to.
    """

    CLIENT = "client"
    AGENT = "agent"


class EventSource(StrEnum):
    """
    How an event arrived: `api` for `POST /v1/events`, `csv` for a CSV import.
    """

    API = "api"
    CSV = "csv"


class UndefinedReason(StrEnum):
    """
    Why the ratios are `null`. `no_value_model`: the client has no active value model. `zero_cost`: operating cost is zero or negative, so neither ratio has a denominator. `no_counted_clients` (dashboard only): no client is counted in the month's totals.
    """

    NO_VALUE_MODEL = "no_value_model"
    ZERO_COST = "zero_cost"
    NO_COUNTED_CLIENTS = "no_counted_clients"


class DisclosureKind(StrEnum):
    """
    A coverage finding on a report. Each kind appears at most once per report. `facts` per kind: `empty` `{}`; `unpriced` `{outcome_types: [{outcome_type, quantity}], outcome_types_omitted}`, at most 100 outcome types by quantity, largest first, with `outcome_types_omitted` counting the rest, which a report composed before the count existed lacks; `key_unset` `{}`; `unmatched` `{keys}`; `unattributable` `{events}`; `precedes` `{}`; `unpriceable` `{models}`; `uncosted` `{events}`; `token_valued` `{events}`; `unattributed` `{line_items}`; `partial` `{line_items}`; `truncated` `{prorated_through}`.
    """

    EMPTY = "empty"
    UNPRICED = "unpriced"
    KEY_UNSET = "key_unset"
    UNMATCHED = "unmatched"
    UNATTRIBUTABLE = "unattributable"
    PRECEDES = "precedes"
    UNPRICEABLE = "unpriceable"
    UNCOSTED = "uncosted"
    TOKEN_VALUED = "token_valued"
    UNATTRIBUTED = "unattributed"
    PARTIAL = "partial"
    TRUNCATED = "truncated"


class PortfolioExclusionReason(StrEnum):
    """
    Why a client is not counted in the dashboard totals. `not_published_this_period`: it has published, but not for this month. `never_published`: no published calculation for any period. `published_off_grid`: a published calculation overlaps the month without equalling it. `no_value_model` and `zero_cost`: the published figure has no ratio.
    """

    NOT_PUBLISHED_THIS_PERIOD = "not_published_this_period"
    NEVER_PUBLISHED = "never_published"
    PUBLISHED_OFF_GRID = "published_off_grid"
    NO_VALUE_MODEL = "no_value_model"
    ZERO_COST = "zero_cost"


class HealthDirection(StrEnum):
    """
    Which way a client's return moved against its own abutting prior published period, compared at one decimal place of percentage points.
    """

    IMPROVING = "improving"
    STEADY = "steady"
    DECLINING = "declining"


class HealthUnavailable(StrEnum):
    """
    Why a renewal row has no health signal. `never_published`: no published calculation. `no_prior_period`: nothing published abuts the latest period. `ratio_undefined`: a ratio on either side is undefined.
    """

    NEVER_PUBLISHED = "never_published"
    NO_PRIOR_PERIOD = "no_prior_period"
    RATIO_UNDEFINED = "ratio_undefined"


@dataclass(frozen=True, kw_only=True)
class Client:
    """
    A client: the roster record value is delivered to.
    """

    id: Uuid
    name: str
    """
    Free text, at most 200 characters.
    """
    status: ClientStatus | str
    client_key: str | None
    """
    The external identifier partners use for this client in event data. `null` when unset.
    """
    renewal_date: Date | None
    """
    For an active client with a `renewal_term`, the next renewal on or after the current UTC date: the date as set, rolled forward by whole terms once it passes, keeping its day of the month, or the month's last day when the month is shorter. Otherwise the date as set, which may be past. `null` when unset.
    """
    renewal_term: RenewalTerm | str | None
    """
    How often the renewal recurs. `null` when the client has no term, and its renewal date stays as set. A client can hold a term without a renewal date; the term applies once a date is set.
    """
    notes: str
    """
    Free text, `""` when empty.
    """
    created_at: Instant


@dataclass(frozen=True, kw_only=True)
class AssignedAgent:
    """
    An agent assigned to a client.
    """

    id: Uuid
    agent_key: str
    name: str
    status: AgentStatus | str


@dataclass(frozen=True, kw_only=True)
class ClientDetail(Client):
    """
    A client with its assigned agents, as the single read returns it.
    """

    agents: Sequence[AssignedAgent]
    """
    The assigned agents, ordered by name, case-insensitively.
    """
    earliest_activity_at: Instant | None
    """
    The first instant anything about this client could be true: its earliest attributed event, or the start of the earliest charge reaching it. `null` when it has neither.
    """


@dataclass(frozen=True, kw_only=True)
class ClientAgents:
    agents: Sequence[AssignedAgent]
    """
    The stored set, ordered by name, case-insensitively.
    """


@dataclass(frozen=True, kw_only=True)
class Agent:
    """
    An agent: a registry entry for something that delivers value. Ingest creates agents it has not seen.
    """

    id: Uuid
    agent_key: str
    """
    The external identity events carry. Immutable through this API.
    """
    name: str
    """
    Free text.
    """
    framework: str
    """
    Free text, `""` when empty.
    """
    version: str
    """
    Free text, `""` when empty.
    """
    status: AgentStatus | str
    created_at: Instant


@dataclass(frozen=True, kw_only=True)
class AgentListItem(Agent):
    """
    An agent as the list returns it.
    """

    client_count: int
    """
    How many clients the agent is assigned to.
    """


@dataclass(frozen=True, kw_only=True)
class AgentStats:
    """
    The agent's activity over the `from`/`to` range of the request, or all time.
    """

    events: int
    """
    Events from this agent in the requested range.
    """
    cost_total: Decimal
    """
    The sum of event `cost` in the requested range, rounded to `minor_units`.
    """
    currency: Currency
    minor_units: MinorUnits
    """
    The scale `cost_total` is rounded to.
    """


@dataclass(frozen=True, kw_only=True)
class AgentDetailClient:
    id: Uuid
    name: str
    status: ClientStatus | str


@dataclass(frozen=True, kw_only=True)
class AgentDetail(Agent):
    """
    An agent with its assigned clients and statistics, as the single read returns it.
    """

    clients: Sequence[AgentDetailClient]
    """
    The clients the agent is assigned to, ordered by name, case-insensitively, then by id. At most 1,000: `clients_omitted` counts the rest.
    """
    clients_omitted: int
    """
    How many clients `clients` leaves out, `0` when it lists every one.
    """
    stats: AgentStats


@dataclass(frozen=True, kw_only=True)
class ValueLineItem:
    """
    One outcome type priced by a value model.
    """

    id: Uuid
    outcome_type: str
    """
    The outcome type this line prices. Matched against events case-insensitively, after trimming.
    """
    label: str
    """
    Free text.
    """
    unit_value: Decimal
    """
    The value of one unit of the outcome, at most 4 decimal places.
    """
    provenance_note: str
    """
    How the unit value was agreed. Free text, `""` when empty.
    """
    position: int
    """
    Display order, from 0.
    """


@dataclass(frozen=True, kw_only=True)
class ValueModel:
    """
    A value model: how one client's outcomes are priced.
    """

    id: Uuid
    client_id: Uuid
    name: str
    """
    Free text.
    """
    status: ValueModelStatus | str
    version: int
    """
    The optimistic-concurrency version. Replacing the line items requires the current value.
    """
    currency: Currency
    created_at: Instant
    updated_at: Instant
    archived_at: Instant | None
    """
    When the model was archived; `null` unless `status` is `archived`.
    """
    line_items: Sequence[ValueLineItem]
    """
    At most 50, ordered by `position`.
    """


@dataclass(frozen=True, kw_only=True)
class ValueModelSummary:
    """
    A value model as the list returns it.
    """

    id: Uuid
    client_id: Uuid
    client_name: str
    name: str
    status: ValueModelStatus | str
    version: int
    line_items: int
    """
    How many line items the model has.
    """
    created_at: Instant
    updated_at: Instant


@dataclass(frozen=True, kw_only=True)
class ValueTemplateLineItem:
    outcome_type: str
    label: str
    unit_value: Decimal
    """
    Always 0: a template supplies structure, never a number.
    """
    provenance_note: str


@dataclass(frozen=True, kw_only=True)
class ValueTemplate:
    """
    A built-in starting point for a value model.
    """

    id: str
    """
    A stable slug.
    """
    name: str
    description: str
    line_items: Sequence[ValueTemplateLineItem]
    """
    In display order.
    """


@dataclass(frozen=True, kw_only=True)
class OutcomeTypeUsage:
    """
    An outcome type seen in events, with its volume.
    """

    outcome_type: str
    """
    As events carry it.
    """
    events: int
    quantity: float
    """
    The summed event quantity.
    """
    priced: bool | None
    """
    Whether the client's active value model prices this outcome type. `null` where no single client's model applies: the workspace-wide list and value coverage findings.
    """


@dataclass(frozen=True, kw_only=True)
class CostTarget:
    """
    What a cost line item is charged to: a client or an agent.
    """

    kind: CostTargetKind | str
    id: Uuid
    name: str
    """
    The target's display name.
    """


@dataclass(frozen=True, kw_only=True)
class CostLineItem:
    """
    A standing monthly charge the event stream never sees. Its dates include both ends.
    """

    id: Uuid
    label: str
    """
    Free text.
    """
    target: CostTarget
    monthly_amount: Decimal
    currency: Currency
    start_date: Date
    end_date: Date | None
    """
    Inclusive. `null` while the charge is still running.
    """
    created_at: Instant
    updated_at: Instant


@dataclass(frozen=True, kw_only=True)
class ModelRate:
    """
    One model's token prices.
    """

    model: str
    """
    The model name events carry in `model`. Matched case-insensitively, after trimming.
    """
    input_per_1k: Decimal
    """
    The price of 1,000 input tokens, with at most 9 decimal places.
    """
    output_per_1k: Decimal
    """
    The price of 1,000 output tokens, with at most 9 decimal places.
    """


@dataclass(frozen=True, kw_only=True)
class PriceTable:
    """
    The workspace's token prices for valuing model events that carry tokens and no cost.
    """

    currency: Currency
    models: Sequence[ModelRate]
    """
    At most 200. Ascending by `model`, compared case-insensitively.
    """


@dataclass(frozen=True, kw_only=True)
class Ratios:
    """
    The two return ratios. Both are `null` together, exactly when `undefined_reason` is set.
    """

    roi: Ratio | None
    """
    `(value − cost) / cost`, from the rounded totals.
    """
    value_to_cost: Ratio | None
    """
    `value / cost`, from the rounded totals.
    """
    undefined_reason: UndefinedReason | str | None


@dataclass(frozen=True, kw_only=True)
class ValueModelRef:
    """
    The value model a figure was computed with.
    """

    id: Uuid
    name: str
    version: int


@dataclass(frozen=True, kw_only=True)
class ValueLine:
    """
    One priced outcome type in a value computation.
    """

    outcome_type: str
    label: str
    unit_value: Decimal
    events: int
    quantity: float
    total: Decimal
    provenance_note: str


@dataclass(frozen=True, kw_only=True)
class ValueCoverageUnmatchedClientKey:
    client_key: str
    events: int


@dataclass(frozen=True, kw_only=True)
class ValueCoverage:
    """
    Every way value could be missing from the total.
    """

    unpriced_outcome_types: Sequence[OutcomeTypeUsage]
    """
    Outcome types attributed to the client that no line item prices, by quantity, largest first, then by outcome type compared by Unicode code point. At most 100: `unpriced_outcome_types_omitted` counts the rest.
    """
    unpriced_outcome_types_omitted: int
    """
    How many unpriced outcome types `unpriced_outcome_types` leaves out, `0` when it lists every one. The totals and counts in the response cover every one.
    """
    unmatched_client_keys: Sequence[ValueCoverageUnmatchedClientKey]
    """
    Event client keys that match no client in the workspace, by event count, largest first, then by client key compared by Unicode code point. At most 100: `unmatched_client_keys_omitted` counts the rest.
    """
    unmatched_client_keys_omitted: int
    """
    How many unmatched client keys `unmatched_client_keys` leaves out, `0` when it lists every one.
    """
    unattributable_outcome_events: int
    """
    Outcome events in the workspace that attribute to no client.
    """
    client_key_unset: bool
    """
    Whether the client has no `client_key`, so only solo-agent attribution reaches it.
    """
    line_items_empty: bool
    """
    Whether the active model has no line items.
    """
    period_precedes_model: bool
    """
    Whether the period holds events from before the model was created.
    """


@dataclass(frozen=True, kw_only=True)
class ValueResult:
    """
    A value computation.
    """

    value_model: ValueModelRef | None
    lines: Sequence[ValueLine]
    """
    One line for each line item of the model, in line-item order, so at most 50. An outcome type no line item prices is never a line; it is listed in `coverage.unpriced_outcome_types`.
    """
    total: Decimal | None
    """
    `null` together with `value_model` when the client has no active model: not priced, which differs from zero.
    """
    coverage: ValueCoverage


@dataclass(frozen=True, kw_only=True)
class ManualCostLine:
    """
    A cost line item prorated over the period.
    """

    id: Uuid
    label: str
    target: CostTarget
    monthly_amount: Decimal
    covered_days: int
    """
    Days of the period the charge covers.
    """
    total: Decimal
    """
    The prorated amount for the period.
    """


@dataclass(frozen=True, kw_only=True)
class TokenCostLine:
    """
    Model events valued from their tokens at the price table.
    """

    model: str
    events: int
    tokens_in: int
    tokens_out: int
    in_rate: Decimal
    """
    The price of 1,000 input tokens used.
    """
    out_rate: Decimal
    """
    The price of 1,000 output tokens used.
    """
    total: Decimal


@dataclass(frozen=True, kw_only=True)
class AgentCostLine:
    """
    One agent's share of the cost.
    """

    agent_id: Uuid
    agent_name: str
    pass_through: Decimal
    token_valued: Decimal
    manual: Decimal
    total: Decimal


@dataclass(frozen=True, kw_only=True)
class UnattributedLineItem:
    """
    An agent-targeted line item that reaches no client.
    """

    id: Uuid
    label: str
    agent_id: Uuid
    agent_name: str


@dataclass(frozen=True, kw_only=True)
class CostCoverageUnpriceableModel:
    model: str
    events: int


@dataclass(frozen=True, kw_only=True)
class CostCoverage:
    """
    Every way cost could be missing from the total.
    """

    uncosted_model_events: int
    """
    Model events with no `cost`.
    """
    unpriceable_models: Sequence[CostCoverageUnpriceableModel]
    """
    Models on uncosted events that the price table does not price, by event count, largest first, then by model compared by Unicode code point. At most 100: `unpriceable_models_omitted` counts the rest.
    """
    unpriceable_models_omitted: int
    """
    How many unpriceable models `unpriceable_models` leaves out, `0` when it lists every one. `uncosted_model_events` counts the events of every one.
    """
    token_valued_events: int
    """
    Uncosted model events valued from their tokens.
    """
    unattributed_line_items: Sequence[UnattributedLineItem]
    """
    By label compared by Unicode code point, then by `id`. At most 100: `unattributed_line_items_omitted` counts the rest.
    """
    unattributed_line_items_omitted: int
    """
    How many unattributed line items `unattributed_line_items` leaves out, `0` when it lists every one.
    """
    partially_covered_line_items: Sequence[ManualCostLine]
    """
    Line items covering only part of the period, by `total`, largest first, then by `id`. At most 100: `partially_covered_line_items_omitted` counts the rest.
    """
    partially_covered_line_items_omitted: int
    """
    How many partly covering line items `partially_covered_line_items` leaves out, `0` when it lists every one.
    """
    prorated_through: Date
    period_truncated: bool
    """
    Whether proration stopped before the end of the period because the period has not ended.
    """


@dataclass(frozen=True, kw_only=True)
class CostResult:
    """
    A cost computation.
    """

    pass_through: Decimal
    """
    The sum of event `cost`.
    """
    token_valued: Decimal
    """
    Uncosted model events valued at the price table.
    """
    manual: Decimal
    """
    Cost line items, prorated. The sum covers every line item, listed or not.
    """
    total: Decimal
    manual_lines: Sequence[ManualCostLine]
    """
    The cost line items reaching the client in the period, by `total`, largest first, then by `id`. At most 100: `manual_lines_omitted` counts the rest.
    """
    manual_lines_omitted: int
    """
    How many line items `manual_lines` leaves out, `0` when it lists every one.
    """
    token_lines: Sequence[TokenCostLine]
    """
    One line for each model the price table prices, so at most 200, as the price table holds at most 200 models. By `total`, largest first, then by model compared by Unicode code point.
    """
    agent_lines: Sequence[AgentCostLine]
    """
    Cost per agent, by `total`, largest first, then by `agent_id`. At most 100: `agent_lines_omitted` counts the rest.
    """
    agent_lines_omitted: int
    """
    How many agents `agent_lines` leaves out, `0` when it lists every one.
    """
    coverage: CostCoverage


@dataclass(frozen=True, kw_only=True)
class ClientValue(ValueResult):
    """
    A client's value over a period.
    """

    client_id: Uuid
    currency: Currency
    minor_units: MinorUnits
    period: Period


@dataclass(frozen=True, kw_only=True)
class ClientCost(CostResult):
    """
    A client's operating cost over a period.
    """

    client_id: Uuid
    currency: Currency
    minor_units: MinorUnits
    period: Period


@dataclass(frozen=True, kw_only=True)
class RoiResult:
    """
    A client's ROI over a period: value and cost, composed and divided.
    """

    client_id: Uuid
    currency: Currency
    minor_units: MinorUnits
    period: Period
    ratios: Ratios
    value: ValueResult
    cost: CostResult


@dataclass(frozen=True, kw_only=True)
class AnomaliesCostSpike:
    date: Date
    cost: Decimal
    """
    The day's cost, rounded to `minor_units`.
    """
    baseline: Decimal
    """
    The baseline the day is compared with, rounded to `minor_units`. The spike is judged on the unrounded figures, so a rounded `cost` near three times the rounded `baseline` can still be a spike.
    """


@dataclass(frozen=True, kw_only=True)
class AnomaliesUnmappedOutcomeType:
    outcome_type: str
    events: int
    quantity: float


@dataclass(frozen=True, kw_only=True)
class Anomalies:
    """
    Pre-validation flags for a period, computed live and stored nowhere.
    """

    client_id: Uuid
    period: Period
    currency: Currency
    """
    The currency of `cost_spikes`.
    """
    minor_units: MinorUnits
    """
    The scale `cost` and `baseline` in `cost_spikes` are rounded to.
    """
    zero_outcome_days: Sequence[Date]
    """
    Days in the period with no outcome events, ascending.
    """
    cost_spikes: Sequence[AnomaliesCostSpike]
    """
    Ascending by date.
    """
    unmapped_outcome_types: Sequence[AnomaliesUnmappedOutcomeType]
    """
    Outcome types no line item prices, by quantity, largest first, then by outcome type compared by Unicode code point. At most 100: `unmapped_outcome_types_omitted` counts the rest.
    """
    unmapped_outcome_types_omitted: int
    """
    How many unmapped outcome types `unmapped_outcome_types` leaves out, `0` when it lists every one.
    """


@dataclass(frozen=True, kw_only=True)
class AttributedEvent:
    """
    An event as stored, with its agent's name and the client it counts toward.
    """

    id: str
    """
    The event id: a 64-bit integer as a decimal string, because JavaScript numbers lose precision above 2^53.
    """
    timestamp: Instant
    agent_id: Uuid
    agent_name: str
    category: EventCategory | str
    event_type: str
    outcome_type: str | None
    quantity: float
    cost: Decimal | None
    """
    In the response's `currency`.
    """
    tokens_in: int | None
    tokens_out: int | None
    model: str | None
    client_key: str | None
    """
    The key the event carried, as stored: as sent to `POST /v1/events`, trimmed by a CSV import. `null` when it carried none, or only whitespace.
    """
    source: EventSource | str
    created_at: Instant
    """
    When the API stored the event. An imported or late event arrives after its `timestamp`, sometimes long after.
    """
    import_batch_id: Uuid | None
    """
    The CSV import that wrote the event, or `null` when it was sent to `POST /v1/events`.
    """
    client_id: Uuid | None
    """
    The client the event counts toward: the client whose key it carried, or, when it carried none, the one client its agent is assigned to. `null` when it counts toward no client: its key names none, or it carried no key and its agent is assigned to no client or to several.
    """
    client_name: str | None
    """
    The name of the client in `client_id`, or `null` with it.
    """


@dataclass(frozen=True, kw_only=True)
class ClientEventList:
    """
    The events behind a client's totals. The shared list envelope plus this list's own members. It is the one list that returns `total` on every request, and the one whose `page` and cursor are one offset with two spellings.
    """

    client_id: Uuid
    period: Period
    currency: Currency
    """
    The currency of every `cost` in `data`, given once here. An event's stored `currency` is not exposed: it is always `null` or the workspace currency, because a mismatching event is refused.
    """
    page: int | None
    """
    The page requested, or `null` when the request used `cursor`.
    """
    total: int
    """
    Every event matching the filters, not only this page.
    """
    data: Sequence[AttributedEvent]
    """
    At most `limit`, in the requested order; ties break on the event id, descending.
    """
    has_more: bool
    next_cursor: str | None
    """
    Opaque. Encodes the offset after this page.
    """


@dataclass(frozen=True, kw_only=True)
class EventList:
    """
    The workspace's events: newest first by `timestamp`, then by id, unless `sort` asks for another order.
    """

    as_of: Instant
    """
    The arrival limit this page was read under: the `as_of` sent, the cursor's, or the one issued. Send it on later requests to read the same events.
    """
    period: Period
    """
    The period sent. Both bounds are `null` when neither was sent.
    """
    client_id: Uuid | None
    """
    The `client_id` filter, or `null` when none was sent.
    """
    currency: Currency
    """
    The currency of every `cost` in `data`, given once here.
    """
    page: int | None
    """
    The page requested, or `null` when the request did not send `page`.
    """
    total: int | None
    """
    Every event matching the filters, up to 10,000, or `null` when the request did not send `page`. With `import_batch_id` it is exact, and may pass 10,000.
    """
    total_capped: bool | None
    """
    `true` when more than 10,000 events matched and `total` is 10,000; `false` when `total` is exact; `null` when the request did not send `page`.
    """
    data: Sequence[AttributedEvent]
    """
    At most `limit`, in the requested order; ties break on the event id, descending.
    """
    has_more: bool
    """
    Whether another page exists.
    """
    next_cursor: str | None
    """
    The opaque cursor for the next page. It carries `as_of`. Clients must not parse it.
    """


@dataclass(frozen=True, kw_only=True)
class EventDayCount:
    """
    The events whose `timestamp` falls in one day of the period.
    """

    start: Instant
    """
    Where the day starts. It ends 24 hours later, or at the period's end.
    """
    count: int


@dataclass(frozen=True, kw_only=True)
class EventCategoryCount:
    """
    The events of one category.
    """

    category: EventCategory | str
    count: int


@dataclass(frozen=True, kw_only=True)
class EventArrivalList:
    """
    The workspace's events in the order the API stored them, newest first, then by id descending.
    """

    as_of: Instant
    """
    The end of the arrival window, exclusive. Send it as the next poll's `since`.
    """
    since: Instant | None
    """
    The start of the arrival window, inclusive, or `null` when none was sent.
    """
    period: Period
    """
    The bounds sent. A bound not sent is `null`.
    """
    client_id: Uuid | None
    """
    The `client_id` filter, or `null` when none was sent.
    """
    currency: Currency
    """
    The currency of every `cost` in `data`, given once here.
    """
    count: int | None
    """
    The matching events in the window, from `since` to `as_of`, up to 10,000; `null` without `since`.
    """
    count_capped: bool | None
    """
    `true` when more than 10,000 events matched and `count` is 10,000; `null` without `since`.
    """
    data: Sequence[AttributedEvent]
    """
    At most `limit`, newest arrival first; ties break on the event id, descending.
    """
    has_more: bool
    """
    Whether another page exists.
    """
    next_cursor: str | None
    """
    The opaque cursor for the next page. It carries `as_of`. Clients must not parse it.
    """


@dataclass(frozen=True, kw_only=True)
class Checklist:
    """
    The validation checklist: the attestation recorded when the calculation was validated. All four checks are `false` until the calculation is validated.
    """

    coverage_confirmed: bool
    counts_spot_checked: bool
    costs_reviewed: bool
    unit_values_current: bool
    note: str
    """
    Free text, `""` when empty.
    """


@dataclass(frozen=True, kw_only=True)
class CalculationSnapshot(RoiResult):
    """
    The ROI result frozen when the calculation was created, never rewritten. It is served with the field names it was stored with. A change to its shape increments `snapshot_version`, and this spec describes every version still stored. Version 1 is the `RoiResult` shape. Every list is stored whole. When served, each list the live ROI read limits is put in the same order and limited the same way, and its count of omitted entries is added beside it, so a snapshot and a live read of the same data match. The frozen totals cover every entry.
    """

    snapshot_version: Literal[1]


@dataclass(frozen=True, kw_only=True)
class Calculation:
    """
    A calculation: a client's ROI for one ended period, frozen for validation and publication.
    """

    id: Uuid
    client_id: Uuid
    state: CalculationState | str
    period: Period
    currency: Currency
    minor_units: MinorUnits
    value_total: Decimal | None
    """
    `null` when the client had no active value model.
    """
    cost_total: Decimal
    ratios: Ratios
    checklist: Checklist
    created_at: Instant
    validated_at: Instant | None
    published_at: Instant | None
    snapshot: CalculationSnapshot


@dataclass(frozen=True, kw_only=True)
class CalculationSummary:
    """
    A calculation as the lists return it: without `snapshot`, with `is_current`, the client's name and the number of coverage findings.
    """

    id: Uuid
    client_id: Uuid
    client_name: str
    """
    The client's name as its record holds it now.
    """
    state: CalculationState | str
    period: Period
    currency: Currency
    minor_units: MinorUnits
    value_total: Decimal | None
    """
    `null` when the client had no active value model.
    """
    cost_total: Decimal
    ratios: Ratios
    checklist: Checklist
    created_at: Instant
    validated_at: Instant | None
    published_at: Instant | None
    is_current: bool | None
    """
    Whether this is the figure for its period: the latest publication covering it. `null` when the calculation is not published.
    """
    coverage_findings: int
    """
    How many coverage findings the calculation's frozen figures hold: the disclosures a report on it would list, including those a report leaves out of the shared copy by default.
    """


@dataclass(frozen=True, kw_only=True)
class Disclosure:
    """
    One coverage finding as it appears on a report.
    """

    kind: DisclosureKind | str
    facts: Mapping[str, Any]
    """
    The facts a caller needs to write the sentence for this finding. Its members depend on `kind`, as `DisclosureKind` lists.
    """
    included: bool
    """
    Whether the finding goes out on the shared report.
    """
    text: str | None
    """
    The owner's own wording. `null` means use the default sentence, which `""` would not.
    """


@dataclass(frozen=True, kw_only=True)
class Report:
    """
    A report: the editorial layer over a published calculation.
    """

    id: Uuid
    calculation_id: Uuid
    client_id: Uuid
    """
    The client of the report's calculation.
    """
    client_name: str
    """
    The client's name as its record holds it now, so renaming the client renames it on every report. The recipient sees `letterhead_client_name` instead.
    """
    period: Period
    """
    The period of the report's calculation.
    """
    state: ReportState | str
    letterhead_client_name: str
    """
    Free text, as the recipient sees it: the letterhead's "For" line. It starts as the client's name and may differ from it.
    """
    letterhead_workspace_name: str
    """
    Free text, as the recipient sees it: the letterhead's "From" line. It starts as the workspace's name and may differ from it.
    """
    note: str
    """
    Free text, `""` when empty.
    """
    disclosures: Sequence[Disclosure]
    """
    In the order the calculation's coverage produced them. At most 12: each kind appears at most once.
    """
    share_token: str | None
    """
    The link token, once shared. `null` before the report is shared.
    """
    shared_at: Instant | None
    revoked_at: Instant | None
    first_viewed_at: Instant | None
    last_viewed_at: Instant | None
    created_at: Instant


@dataclass(frozen=True, kw_only=True)
class ReportSummary:
    """
    A report as the list returns it: without `disclosures`. Read the report for its findings.
    """

    id: Uuid
    calculation_id: Uuid
    client_id: Uuid
    """
    The client of the report's calculation.
    """
    client_name: str
    """
    The client's name as its record holds it now, so renaming the client renames it on every report. The recipient sees `letterhead_client_name` instead.
    """
    period: Period
    """
    The period of the report's calculation.
    """
    state: ReportState | str
    letterhead_client_name: str
    """
    Free text, as the recipient sees it: the letterhead's "For" line. It starts as the client's name and may differ from it.
    """
    letterhead_workspace_name: str
    """
    Free text, as the recipient sees it: the letterhead's "From" line. It starts as the workspace's name and may differ from it.
    """
    note: str
    """
    Free text, `""` when empty.
    """
    share_token: str | None
    """
    The link token, once shared. `null` before the report is shared.
    """
    shared_at: Instant | None
    revoked_at: Instant | None
    first_viewed_at: Instant | None
    last_viewed_at: Instant | None
    created_at: Instant


@dataclass(frozen=True, kw_only=True)
class PublicReportSnapshotValueValueModel:
    name: str
    version: int


@dataclass(frozen=True, kw_only=True)
class PublicReportSnapshotValue:
    value_model: PublicReportSnapshotValueValueModel | None
    lines: Sequence[ValueLine]
    total: Decimal | None


@dataclass(frozen=True, kw_only=True)
class PublicReportSnapshotCost:
    pass_through: Decimal
    token_valued: Decimal
    manual: Decimal
    total: Decimal


@dataclass(frozen=True, kw_only=True)
class PublicReportSnapshot:
    """
    The calculation's snapshot, narrowed to what a recipient sees.
    """

    snapshot_version: Literal[1]
    currency: Currency
    minor_units: MinorUnits
    period: Period
    ratios: Ratios
    value: PublicReportSnapshotValue
    cost: PublicReportSnapshotCost


@dataclass(frozen=True, kw_only=True)
class PublicReportComparedTo:
    """
    The client's abutting prior published period.
    """

    period: Period
    value_total: Decimal | None
    cost_total: Decimal
    roi: Ratio | None


@dataclass(frozen=True, kw_only=True)
class PublicReport:
    """
    A shared report as its recipient reads it.
    """

    client_name: str
    workspace_name: str
    note: str
    """
    Free text, `""` when empty.
    """
    disclosures: Sequence[Disclosure]
    """
    The included findings only, in report order. At most 12: each kind appears at most once.
    """
    period: Period
    currency: Currency
    minor_units: MinorUnits
    snapshot: PublicReportSnapshot
    """
    The calculation's snapshot, narrowed to what a recipient sees.
    """
    compared_to: PublicReportComparedTo | None
    """
    The client's abutting prior published period.
    """


@dataclass(frozen=True, kw_only=True)
class PortfolioClient:
    """
    One client's published figure for the month. `reason` is `null` exactly when the client is counted in the totals.
    """

    client_id: Uuid
    name: str
    status: ClientStatus | str
    renewal_date: Date | None
    value_total: Decimal | None
    cost_total: Decimal | None
    roi: Ratio | None
    reason: PortfolioExclusionReason | str | None


@dataclass(frozen=True, kw_only=True)
class DashboardCostComponents:
    pass_through: Decimal
    token_valued: Decimal
    manual: Decimal


@dataclass(frozen=True, kw_only=True)
class DashboardValueByOutcomeItem:
    outcome_type: str
    label: str
    total: Decimal
    events: int


@dataclass(frozen=True, kw_only=True)
class DashboardUnpricedOutcomeType:
    outcome_type: str
    events: int


@dataclass(frozen=True, kw_only=True)
class DashboardUnallocatedCharge:
    id: Uuid
    label: str
    agent_id: Uuid
    agent_name: str
    total: Decimal


@dataclass(frozen=True, kw_only=True)
class DashboardOnboarding:
    has_client: bool
    has_assigned_agent: bool
    has_priced_outcomes: bool
    has_events: bool
    has_published: bool


@dataclass(frozen=True, kw_only=True)
class Dashboard:
    """
    The workspace's published figures for one month. `GET /v1/dashboard`, which returns it, and `GET /v1/dashboard/renewals` are expected to change shape before `/v1` is declared stable.
    """

    currency: Currency
    minor_units: MinorUnits
    period: Period
    period_ended: bool
    """
    Whether the month has ended.
    """
    latest_published_month: Month | None
    value_total: Decimal
    """
    The sum of the counted clients' value totals, added as decimals. It equals the `total` of every `value_by_outcome` entry plus `value_by_outcome_omitted_total`, for figures of up to 15 significant digits.
    """
    cost_total: Decimal
    ratios: Ratios
    counted: int
    """
    Clients counted in the totals.
    """
    clients: Sequence[PortfolioClient]
    """
    In the requested sort order; clients with no value for the sort key last, then by name, then by id. At most 1,000: `clients_omitted` counts the rest.
    """
    clients_omitted: int
    """
    How many clients `clients` leaves out, `0` when it lists every one. `counted` and the totals cover every client.
    """
    top_clients: Sequence[PortfolioClient]
    """
    The five counted clients with the highest `value_total`, largest first, then by `client_id`, chosen from every client whether or not `clients` lists it, and whatever `sort` and `dir` say. Fewer than five when fewer are counted. Each entry has the shape of a `clients` entry, with a `value_total` and a `reason` of `null`.
    """
    cost_components: DashboardCostComponents
    value_by_outcome: Sequence[DashboardValueByOutcomeItem]
    """
    Value by priced outcome type across the counted clients, by `total`, largest first, then by outcome type compared by Unicode code point. An outcome type is grouped ignoring case and surrounding spaces, with its value and events summed across spellings. At most 100: `value_by_outcome_omitted` counts the rest.
    """
    value_by_outcome_omitted: int
    """
    How many outcome types `value_by_outcome` leaves out, `0` when it lists every one. `value_total` covers every one.
    """
    value_by_outcome_omitted_total: Decimal
    """
    The value of the outcome types `value_by_outcome` leaves out, `0` when it lists every one. The `total` of every listed entry plus this equals `value_total` exactly, as decimals, for figures of up to 15 significant digits, so a chart can show the rest as one share without adding money itself.
    """
    agent_costs: Sequence[AgentCostLine]
    """
    The five agents with the highest cost, by `total`, largest first, then by `agent_id`.
    """
    agent_costs_recorded: int
    """
    Agents with recorded cost in the month.
    """
    unpriced_outcome_types: Sequence[DashboardUnpricedOutcomeType]
    """
    Unpriced outcome types across the counted clients' figures, by event count, largest first, then by outcome type compared by Unicode code point. An outcome type is grouped ignoring case and surrounding spaces, with its events summed across spellings. At most 100: `unpriced_outcome_types_omitted` counts the rest.
    """
    unpriced_outcome_types_omitted: int
    """
    How many unpriced outcome types `unpriced_outcome_types` leaves out, `0` when it lists every one.
    """
    unallocated_charges: Sequence[DashboardUnallocatedCharge]
    """
    Charges on agents serving several clients or none, which reach no client, by `total`, largest first, then by label compared by Unicode code point, then by `id`. At most 100: `unallocated_charges_omitted` counts the rest.
    """
    unallocated_charges_omitted: int
    """
    How many charges `unallocated_charges` leaves out, `0` when it lists every one.
    """
    onboarding: DashboardOnboarding


@dataclass(frozen=True, kw_only=True)
class RenewalHealth:
    direction: HealthDirection | str
    delta_points: float
    """
    The change in percentage points, one decimal place.
    """
    current_roi: Ratio
    prior_roi: Ratio


@dataclass(frozen=True, kw_only=True)
class Renewal:
    """
    A client's renewal readiness, from its latest published figures. `health` and `unavailable` are never both set.
    """

    client_id: Uuid
    name: str
    renewal_date: Date
    """
    For a client with a `renewal_term`, the next renewal on or after the list's `today`. Otherwise the date as set, which may be before `today`.
    """
    renewal_term: RenewalTerm | str | None
    """
    How often the renewal recurs. `null` when the client has no term.
    """
    roi: Ratio | None
    period: Period | None
    """
    The client's latest published period. `null` when it has none.
    """
    calculation_id: Uuid | None
    """
    The published calculation `roi` and `period` come from. `null` exactly when `period` is.
    """
    health: RenewalHealth | None
    unavailable: HealthUnavailable | str | None
    prior_period: Month | None


@dataclass(frozen=True, kw_only=True)
class IngestRowError:
    """
    One problem with a rejected ingest row. A row with several problems has one entry for each, all carrying its `index`; its `pointer` locates the problem, so it starts `/events/<index>`.
    """

    index: int
    """
    The zero-based position of the row in `events`.
    """
    code: FieldErrorCode | str
    pointer: str
    """
    An RFC 6901 JSON Pointer, absolute within the request body.
    """
    detail: str


@dataclass(frozen=True, kw_only=True)
class IngestResult:
    """
    The outcome of an ingest batch. Partial acceptance is a success.
    """

    accepted: int
    """
    Rows stored.
    """
    duplicates: int
    """
    Rows already stored, by `event_id` or content hash.
    """
    rejected: int
    """
    Rows refused, counted once each however many problems they have, and however many of their entries `errors` holds. Each has at least one entry in `errors` unless `errors_truncated` is `true`. `accepted`, `duplicates` and `rejected` sum to the batch's length.
    """
    errors: Sequence[IngestRowError]
    """
    One entry per problem, ascending by `index` whichever check rejected the row. A row's entries are contiguous, in the order the row's checks run: first whether the row is a JSON object, then its shape (unknown, mistyped and repeated members, excess decimal places and malformed timestamps, in the order they appear in the row), then the field rules in field order, then the attribution guard. A row that fails one check is not checked by the later ones. At most 20 entries per row; a row with more keeps its first 20. The whole list is also at most 1,000,000 bytes, counted as the array is written in the response, brackets and commas included. Within that limit, each rejected row's first entry is kept in preference to any row's later entries. The first entries are taken in `index` order, and one that does not fit in the space left is skipped. The later entries of the rows that kept their first are then taken in order, and the first that does not fit ends them. The list stays in `index` order. So the entries kept for a row are always its first ones, and a rejected row has none only when its first entry did not fit. Either limit sets `errors_truncated`. `[]` when no row was rejected.
    """
    errors_truncated: bool
    """
    Whether `errors` omits any problem: a rejected row had more than 20, or the 1,000,000-byte limit left entries out. The counts always cover the whole batch.
    """


@dataclass(frozen=True, kw_only=True)
class ImportRowError:
    """
    One problem with a rejected CSV row. A row with several problems has one entry for each, all carrying its `row`.
    """

    row: int
    """
    The one-based line number in the file, counting the header.
    """
    column: str | None
    """
    The file's column the problem is in. `null` when the value came from a constant or the problem has no column.
    """
    code: FieldErrorCode | str
    detail: str


@dataclass(frozen=True, kw_only=True)
class PreviewEvent:
    """
    A mapped event as commit would store it. Every field is present; an unset one is `null`.
    """

    event_id: str | None
    timestamp: Instant
    agent_key: str
    client_key: str | None
    category: EventCategory | str
    event_type: str
    outcome_type: str | None
    quantity: float
    cost: Decimal | None
    tokens_in: int | None
    tokens_out: int | None
    model: str | None
    currency: Currency | None
    metadata: Mapping[str, Any] | None


@dataclass(frozen=True, kw_only=True)
class PreviewRow:
    """
    One of the first 20 data rows. A valid row has its `event` and `errors` `[]`; a rejected row has `event` `null` and 1 to 13 `errors`.
    """

    row: int
    """
    The one-based line number, counting the header.
    """
    event: PreviewEvent | None
    errors: Sequence[ImportRowError]
    """
    The row's problems, in the order the row's entries take in the response's `errors`. `[]` for a valid row. At most 13: one for each field a mapping can bind.
    """


@dataclass(frozen=True, kw_only=True)
class ImportPreview:
    """
    What committing the file would do. Nothing is written.
    """

    total_rows: int
    valid: int
    rejected: int
    """
    Rows the file would reject, counted once each however many problems they have.
    """
    preview: Sequence[PreviewRow]
    """
    The first 20 data rows, in file order, broken rows included.
    """
    errors: Sequence[ImportRowError]
    """
    One entry per problem, ascending by `row`. A row's entries follow the order its checks run: first whether the record can be read as CSV, then each field's cell and rules in field order, then the attribution guard. A row that fails one check is not checked by the later ones. At most 1,000 in all: the first 1,000 in that order, which may end partway through a row. A CSV row has at most 13 entries, one for each field a mapping can bind.
    """
    errors_truncated: bool
    """
    Whether `errors` omits any problem because of the 1,000 cap. The counts always cover the whole file.
    """
    ignored_columns: Sequence[str]
    """
    The first 100 columns the mapping does not bind, in the header's order, left to right. A blank header cell is a column too, listed as `""`. `ignored_columns_omitted` counts the rest.
    """
    ignored_columns_omitted: int
    """
    How many columns the mapping does not bind beyond the 100 in `ignored_columns`. `0` when the list is complete.
    """
    timezone_warning: str | None
    """
    Set when the file has timestamps without an offset and the last import used a different timezone, so re-imported rows would not deduplicate. Human text.
    """


@dataclass(frozen=True, kw_only=True)
class ImportResult:
    """
    The outcome of a CSV import. Partial acceptance is a success.
    """

    import_batch_id: Uuid
    accepted: int
    duplicates: int
    rejected: int
    """
    Rows rejected, counted once each however many problems they have.
    """
    errors: Sequence[ImportRowError]
    """
    As on the preview: one entry per problem, by `row`, at most 1,000 in all. `[]` when no row was rejected.
    """
    errors_truncated: bool
    """
    Whether `errors` omits any problem, as on the preview.
    """


@dataclass(frozen=True, kw_only=True)
class ImportSummary:
    """
    One CSV import and its counts. `total_rows` is `accepted` plus `duplicates` plus `rejected`.
    """

    id: Uuid
    filename: str
    """
    The file part's file name, without a directory part separated by `/`: a part named `exports/august.csv` is stored as `august.csv`. A backslash is not a separator, so `C:\\ops\\august.csv` is stored whole. `""` when the file part named none.
    """
    total_rows: int
    """
    The file's data rows, not counting the header.
    """
    accepted: int
    """
    The events this import wrote, counted when the import is read: the `import_batch_id` of each is the import's `id`.
    """
    duplicates: int
    """
    `total_rows` less `rejected` and `accepted`. At the commit, these are the valid rows that wrote no event: an event with the same `event_id`, or the same content hash, was already stored, or an earlier row of the same file had the same `event_id`. Identical rows of one file without an `event_id` are each written, so they are not counted here.
    """
    rejected: int
    """
    Rows refused, counted once each however many problems they had.
    """
    created_at: Instant


class ImportDelimiter(StrEnum):
    """
    A CSV field delimiter, a comma, a semicolon or a tab.
    """

    COMMA = ","
    SEMICOLON = ";"
    TAB = "\t"


class HealthStatus(StrEnum):
    OK = "ok"


@dataclass(frozen=True, kw_only=True)
class Health:
    """
    Liveness.
    """

    status: HealthStatus | str
    version: str
    """
    The build version.
    """


@dataclass(frozen=True, kw_only=True)
class ImportList:
    """
    The workspace's imports: newest first, then id.
    """

    page: int | None
    """
    The page requested, or `null` when the request did not send `page`.
    """
    total: int | None
    """
    Every import in the workspace, not only this page, or `null` when the request did not send `page`.
    """
    data: Sequence[ImportSummary]
    """
    One page of items, at most `limit`, in the documented order.
    """
    has_more: bool
    """
    Whether another page exists.
    """
    next_cursor: str | None
    """
    The opaque cursor for the next page. Clients must not parse it.
    """


@dataclass(frozen=True, kw_only=True)
class ClientList:
    """
    Clients, ordered by name case-insensitively, then id.
    """

    page: int | None
    """
    The page requested, or `null` when the request did not send `page`.
    """
    total: int | None
    """
    Every client matching the filters and search, not only this page, or `null` when the request did not send `page`.
    """
    data: Sequence[Client]
    """
    One page of items, at most `limit`, in the documented order.
    """
    has_more: bool
    """
    Whether another page exists.
    """
    next_cursor: str | None
    """
    The opaque cursor for the next page. Clients must not parse it.
    """


@dataclass(frozen=True, kw_only=True)
class AgentList:
    """
    Agents, ordered by name case-insensitively, then id. Includes agents ingest created.
    """

    page: int | None
    """
    The page requested, or `null` when the request did not send `page`.
    """
    total: int | None
    """
    Every agent matching the filters and search, not only this page, or `null` when the request did not send `page`.
    """
    data: Sequence[AgentListItem]
    """
    One page of items, at most `limit`, in the documented order.
    """
    has_more: bool
    """
    Whether another page exists.
    """
    next_cursor: str | None
    """
    The opaque cursor for the next page. Clients must not parse it.
    """


@dataclass(frozen=True, kw_only=True)
class ValueModelList:
    """
    Value models: active first, then newest first, then id.
    """

    page: int | None
    """
    The page requested, or `null` when the request did not send `page`.
    """
    total: int | None
    """
    Every value model matching the filters and search, not only this page, or `null` when the request did not send `page`.
    """
    data: Sequence[ValueModelSummary]
    """
    One page of items, at most `limit`, in the documented order.
    """
    has_more: bool
    """
    Whether another page exists.
    """
    next_cursor: str | None
    """
    The opaque cursor for the next page. Clients must not parse it.
    """


@dataclass(frozen=True, kw_only=True)
class OutcomeTypeList:
    """
    Outcome types by summed quantity, largest first, then by name.
    """

    data: Sequence[OutcomeTypeUsage]
    """
    One page of items, at most `limit`, in the documented order.
    """
    has_more: bool
    """
    Whether another page exists.
    """
    next_cursor: str | None
    """
    The opaque cursor for the next page. Clients must not parse it.
    """


@dataclass(frozen=True, kw_only=True)
class ValueTemplateList:
    """
    Templates in display order.
    """

    data: Sequence[ValueTemplate]
    """
    One page of items, at most `limit`, in the documented order.
    """
    has_more: bool
    """
    Whether another page exists.
    """
    next_cursor: str | None
    """
    The opaque cursor for the next page. Clients must not parse it.
    """


@dataclass(frozen=True, kw_only=True)
class CostLineItemList:
    """
    Line items, newest first, then id.
    """

    page: int | None
    """
    The page requested, or `null` when the request did not send `page`.
    """
    total: int | None
    """
    Every line item matching the filters and search, not only this page, or `null` when the request did not send `page`.
    """
    data: Sequence[CostLineItem]
    """
    One page of items, at most `limit`, in the documented order.
    """
    has_more: bool
    """
    Whether another page exists.
    """
    next_cursor: str | None
    """
    The opaque cursor for the next page. Clients must not parse it.
    """


@dataclass(frozen=True, kw_only=True)
class CalculationList:
    """
    A client's calculations: latest period first, then newest first, then id.
    """

    data: Sequence[CalculationSummary]
    """
    One page of items, at most `limit`, in the documented order.
    """
    has_more: bool
    """
    Whether another page exists.
    """
    next_cursor: str | None
    """
    The opaque cursor for the next page. Clients must not parse it.
    """


@dataclass(frozen=True, kw_only=True)
class ReportList:
    """
    A calculation's reports, newest first, then id.
    """

    data: Sequence[ReportSummary]
    """
    One page of items, at most `limit`, in the documented order.
    """
    has_more: bool
    """
    Whether another page exists.
    """
    next_cursor: str | None
    """
    The opaque cursor for the next page. Clients must not parse it.
    """


@dataclass(frozen=True, kw_only=True)
class WorkspaceCalculationList:
    """
    The workspace's calculations: latest period first, then newest first, then id.
    """

    page: int | None
    """
    The page requested, or `null` when the request did not send `page`.
    """
    total: int | None
    """
    Every calculation matching the filters, not only this page, or `null` when the request did not send `page`.
    """
    data: Sequence[CalculationSummary]
    """
    One page of items, at most `limit`, in the documented order.
    """
    has_more: bool
    """
    Whether another page exists.
    """
    next_cursor: str | None
    """
    The opaque cursor for the next page. Clients must not parse it.
    """


@dataclass(frozen=True, kw_only=True)
class WorkspaceReportList:
    """
    The workspace's reports: newest first, then id.
    """

    page: int | None
    """
    The page requested, or `null` when the request did not send `page`.
    """
    total: int | None
    """
    Every report matching the filters, not only this page, or `null` when the request did not send `page`.
    """
    data: Sequence[ReportSummary]
    """
    One page of items, at most `limit`, in the documented order.
    """
    has_more: bool
    """
    Whether another page exists.
    """
    next_cursor: str | None
    """
    The opaque cursor for the next page. Clients must not parse it.
    """


@dataclass(frozen=True, kw_only=True)
class RenewalList:
    """
    Active clients with a renewal date, by the renewal date shown, then by name case-insensitively, then by id.
    """

    page: int | None
    """
    The page requested, or `null` when the request did not send `page`.
    """
    total: int | None
    """
    Every client matching `window` and `renewal_term`, not only this page, or `null` when the request did not send `page`.
    """
    today: Date
    """
    The date the renewal dates were rolled against and `window` measured from: the `today` sent, or the current UTC date.
    """
    data: Sequence[Renewal]
    """
    One page of items, at most `limit`, in the documented order.
    """
    has_more: bool
    """
    Whether another page exists.
    """
    next_cursor: str | None
    """
    The opaque cursor for the next page. Clients must not parse it.
    """


@dataclass(frozen=True, kw_only=True)
class Workspace:
    """
    The workspace a credential belongs to.
    """

    id: Uuid
    name: str
    """
    Free text.
    """
    currency: Currency
    minor_units: MinorUnits
    created_at: Instant


class OnboardingStep(StrEnum):
    """
    A guided-setup step, in its fixed order: `add_client`, `add_agent`, `price_outcomes`, `bring_in_data`, `create_draft_calculation`.
    """

    ADD_CLIENT = "add_client"
    ADD_AGENT = "add_agent"
    PRICE_OUTCOMES = "price_outcomes"
    BRING_IN_DATA = "bring_in_data"
    CREATE_DRAFT_CALCULATION = "create_draft_calculation"


@dataclass(frozen=True, kw_only=True)
class OnboardingStepProgress:
    step: OnboardingStep | str
    completed: bool
    """
    Whether the workspace's data completes the step: a client; an agent assigned to a client; a line item on an active value model; an event; a calculation in any state.
    """
    skipped_at: Instant | None
    """
    When the step was skipped, or `null` when it is not skipped.
    """


@dataclass(frozen=True, kw_only=True)
class Onboarding:
    """
    The guided setup's progress.
    """

    steps: Sequence[OnboardingStepProgress]
    """
    Every step, in the fixed order of `OnboardingStep`.
    """
    current_step: OnboardingStep | str | None
    """
    The first step neither completed nor skipped: where the owner resumes. `null` once every step is completed or skipped.
    """
    has_published: bool
    """
    Whether any calculation in the workspace is published.
    """


@dataclass(frozen=True, kw_only=True)
class EventSummary:
    """
    How many events a view of the workspace's events holds: in all, per day and per category.
    """

    as_of: Instant
    """
    The arrival limit the counts were read under, as on the list.
    """
    period: Period
    client_id: Uuid | None
    """
    The `client_id` filter, or `null` when none was sent.
    """
    total: int
    """
    Every event the view holds, counted exactly. Under the same parameters it equals the list's `total` whenever the list's `total_capped` is `false`.
    """
    days: Sequence[EventDayCount]
    """
    One entry per 24 hours from `from`, ascending, zeros included. The last is shorter when the period is not a whole number of days. Empty when `from` equals `to`.
    """
    categories: Sequence[EventCategoryCount]
    """
    One entry per category, in the order `session`, `task`, `model`, `outcome`, `exception`, zeros included. With `category` sent, the others are `0`.
    """


@dataclass(frozen=True, kw_only=True)
class ReportWithPreview(Report):
    """
    A report with its recipient preview, as the single read returns it.
    """

    preview: PublicReport | None
    """
    Exactly what `GET /report` would return. `null` when the preview cannot be rendered.
    """


@dataclass(frozen=True, kw_only=True)
class AppliedImportMapping:
    """
    The mapping an import ran with, with every member present: a member the import did not send holds the value it applied. It has the members of `ImportMapping`, so it can be sent as the next import's `mapping`. A value the server's current rules refuse is refused then as in any mapping.
    """

    columns: Mapping[str, str]
    """
    Canonical field name to the file's column name, as in `ImportMapping`. `{}` when the import bound none.
    """
    constants: Mapping[str, str]
    """
    Canonical field name to the value used for every row, as in `ImportMapping`. `{}` when the import had none.
    """
    timezone: str
    """
    The IANA zone applied to timestamps without an offset. `UTC` when the import named none.
    """
    delimiter: ImportDelimiter | str
    """
    The field delimiter. `,` when the import named none.
    """


@dataclass(frozen=True, kw_only=True)
class Import:
    """
    One CSV import, its counts and the mapping it ran with.
    """

    id: Uuid
    filename: str
    """
    The file part's file name, without a directory part separated by `/`: a part named `exports/august.csv` is stored as `august.csv`. A backslash is not a separator, so `C:\\ops\\august.csv` is stored whole. `""` when the file part named none.
    """
    total_rows: int
    """
    The file's data rows, not counting the header.
    """
    accepted: int
    """
    The events this import wrote, counted when the import is read: the `import_batch_id` of each is the import's `id`.
    """
    duplicates: int
    """
    `total_rows` less `rejected` and `accepted`. At the commit, these are the valid rows that wrote no event: an event with the same `event_id`, or the same content hash, was already stored, or an earlier row of the same file had the same `event_id`. Identical rows of one file without an `event_id` are each written, so they are not counted here.
    """
    rejected: int
    """
    Rows refused, counted once each however many problems they had.
    """
    created_at: Instant
    mapping: AppliedImportMapping
