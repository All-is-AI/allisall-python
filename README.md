# allisall

The Python client of the allisall API. It sends events:
`client.events.ingest`.

```sh
pip install allisall
```

```python
from datetime import UTC, datetime

from allisall import Allisall

with Allisall() as client:  # reads AIA_API_KEY
    summary = client.events.ingest(
        [
            {
                "timestamp": datetime.now(UTC),
                "agent_key": "support-bot",
                "category": "task",
                "event_type": "ticket_triaged",
            }
        ]
    )
    print(summary.accepted, summary.duplicates, summary.rejected)
```

`AsyncAllisall` takes the same options, and `await client.events.ingest(...)`.

`ingest` takes any number of events and sends them in batches of at most 500
events and 5,000,000 bytes. It gives each event without an `event_id` a new
UUID, so a retried batch is never counted twice. If your events can be
delivered to you more than once, for example from a queue, set your own
`event_id`, such as the message id: a new UUID is generated on every call.

Requires Python 3.11 or later. Licensed under Apache-2.0.
