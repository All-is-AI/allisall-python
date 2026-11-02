# allisall

The allisall SDK for Python: a typed client for the allisall API, covering
events, imports, clients, agents, value models, costs, analytics,
calculations, reports and the dashboard. It has a sync client, `Allisall`,
and an async client, `AsyncAllisall`. Requires Python 3.11 or later.

## Install

```sh
pip install allisall
```

## Create a client

The client reads your API key from `AIA_API_KEY`:

```sh
export AIA_API_KEY=aia_...
```

```python
from allisall import Allisall

with Allisall() as client:
    health = client.health.get()
    print(health.status)
```

You can also pass the key yourself, as `Allisall(api_key=...)`. Create one
client and reuse it; `with` closes its connections when you are done, and so
does `client.close()`.

## Ingest events

```python
from datetime import UTC, datetime
from decimal import Decimal

from allisall import Allisall

with Allisall() as client:
    summary = client.events.ingest(
        [
            {
                "timestamp": datetime.now(UTC),
                "agent_key": "support-bot",
                "category": "model",
                "event_type": "completion",
                "model": "gpt-4o",
                "tokens_in": 1200,
                "tokens_out": 300,
                "cost": Decimal("0.0042"),
            }
        ]
    )
    print(summary.accepted, summary.duplicates, summary.rejected)
```

`ingest` takes any number of events and sends them in batches of at most 500
events and 4,000,000 bytes. It retries a failure worth retrying, and returns
one summary for the whole list. A rejected event is counted in
`summary.rejected`, its problems are listed in `summary.errors`, and the
others are still stored. When `summary.errors_truncated` is `True`, the list
omits some problems, and a rejected event may have no entry. Write `cost` as
a `Decimal` to keep it exact.

### Set your own `event_id` for at-least-once delivery

The SDK gives each event without an `event_id` a new UUID, so a retried batch
is never counted twice. That does not catch the same event sent again in a
later call. If your events can be delivered to you more than once, for
example from a queue, set `event_id` yourself, such as to the message id. The
API then stores the event once, however often it arrives.

## Call the API

The client groups its methods by resource: `client.clients`,
`client.agents`, `client.value_models`, `client.cost`, `client.analytics`,
`client.calculations`, `client.reports`, `client.dashboard` and more. Each
method's documentation names the API operation it calls and the scope your
key needs.

```python
from allisall import Allisall

with Allisall() as client:
    created = client.clients.create(
        {"name": "Acme Logistics", "status": "active", "client_key": "acme"}
    )

    # An update is a merge patch: a key you leave out keeps its value, and
    # None clears it.
    updated = client.clients.update(created.id, {"renewal_date": "2026-12-31"})
    print(updated.name, updated.renewal_date)
```

A request body is a plain `dict`, typed as a `TypedDict` your type checker
can check. A response is a frozen dataclass. Amounts of money are a
`Decimal` both ways, and instants and dates come back as the API's RFC 3339
strings.

Each `create` method, and `imports.commit`, sends an `Idempotency-Key`. The
SDK sends the same key again on a retry, so a retry never creates a second
one. The key it generates lasts for one call. To make a create safe across a
restart of your program as well, pass your own key, such as one stored with
the work it belongs to:

```python
from allisall import Allisall

with Allisall() as client:
    created = client.clients.create(
        {"name": "Acme Logistics", "status": "active"},
        idempotency_key="onboarding-acme-logistics",
    )
    print(created.id)
```

## Lists

A list method returns a page. Iterate it with `for` to get every item of
every page; the SDK fetches each page as the loop reaches it:

```python
from allisall import Allisall

with Allisall() as client:
    for agent in client.agents.list():
        print(agent.agent_key, agent.name)
```

To work a page at a time, use the page itself. It holds its items in `data`,
and `has_next_page()` and `get_next_page()` move through the rest:

```python
from allisall import Allisall

with Allisall() as client:
    page = client.agents.list(limit=50)
    print(len(page.data), page.has_next_page())
```

## Async

`AsyncAllisall` takes the same options and has the same methods, each one a
coroutine. A list method's result is walked with `async for`, or awaited for
its first page:

```python
import asyncio

from allisall import AsyncAllisall


async def main() -> None:
    async with AsyncAllisall() as client:
        detail = await client.clients.get("CLIENT_ID")
        print(detail.name)
        async for agent in client.agents.list():
            print(agent.agent_key, agent.name)


asyncio.run(main())
```

## Errors

Every error from the API or the network is an `AllisallError`. An error
response from the API is an `APIError`, with the HTTP `status`, the API's
error `code` and the `request_id` to quote when you report a problem. Branch
on `code`:

```python
from allisall import Allisall, APIError, ErrorCode

with Allisall() as client:
    try:
        client.clients.delete("CLIENT_ID")
    except APIError as err:
        if err.code != ErrorCode.CLIENT_HAS_EVENTS:
            raise
        # Events carry the client's key, so mark the client churned instead.
        client.clients.update("CLIENT_ID", {"status": "churned"})
```

A code this version of the SDK does not list arrives as a plain `str`, so
compare with `==` rather than matching only the listed members.

An `APIConnectionError` means no response arrived, after any retries. A few
errors are not an `AllisallError`. An argument the SDK cannot send raises a
`ValueError` before anything is sent. An error raised by your
`token_provider` reaches you unchanged.

The SDK retries a failure worth retrying, twice by default. Set
`max_retries` on the client, or on one call, to change that. It honours the
API's `Retry-After`. It retries only a request that cannot take effect twice:
a `GET`, `PUT` or `DELETE`; ingest, whose event ids deduplicate; and a call
that carries an `Idempotency-Key`. A `PATCH`, an import preview, and setting
a value model's line items are never retried. Setting line items is guarded
by the model's `version`, which refuses a repeat of a write that already
landed.

Every method also takes `timeout`, `max_retries` and `headers` for that one
call.

## Token providers and sessions

A `token_provider` is a function the client calls before every attempt, to
get the credential it sends. Pass one instead of `api_key`, never with it.

Use one to read your API key at run time, for example from a secret store,
so that a rotated key is picked up without a restart:

```python
from allisall import Allisall


def api_key_from_secret_store() -> str:
    # Your secret store's way to read the current allisall API key.
    raise NotImplementedError


with Allisall(token_provider=api_key_from_secret_store) as client:
    print(client.health.get().status)
```

Or use one to send a signed-in user's session token instead of an API key.
Because the client calls it before every attempt, a refreshed token is picked
up:

```python
from allisall import Allisall


def current_session_token() -> str:
    # Your sign-in library's way to read the signed-in user's session token.
    raise NotImplementedError


with Allisall(token_provider=current_session_token) as client:
    for item in client.clients.list():
        print(item.name)
```

`AsyncAllisall` also accepts a provider that is a coroutine function. Ingest
takes an API key only, whether passed as `api_key` or returned by a provider.

## Documentation

See [https://docs.allisai.ai](https://docs.allisai.ai).

## License

Apache-2.0. See `LICENSE` and `NOTICE`.
