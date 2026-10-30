"""UUID version 4, for each generated `event_id` and each attempt's `X-Request-Id`."""

import uuid


def uuid4() -> str:
    """Return a new random UUID version 4, lowercase, in the 8-4-4-4-12 form."""
    return str(uuid.uuid4())
