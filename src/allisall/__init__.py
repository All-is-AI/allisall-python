"""The allisall API client for Python.

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
```
"""

from ._client import Allisall, AsyncAllisall
from ._errors import AllisallError, APIConnectionError, APIError, IngestError
from ._types import (
    ErrorCode,
    EventCategory,
    EventInput,
    FieldError,
    FieldErrorCode,
    IngestRowError,
    IngestSummary,
    Problem,
)
from ._version import __version__

__all__ = [
    "APIConnectionError",
    "APIError",
    "Allisall",
    "AllisallError",
    "AsyncAllisall",
    "ErrorCode",
    "EventCategory",
    "EventInput",
    "FieldError",
    "FieldErrorCode",
    "IngestError",
    "IngestRowError",
    "IngestSummary",
    "Problem",
    "__version__",
]
