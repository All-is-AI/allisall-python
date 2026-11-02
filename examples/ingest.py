import sys
from datetime import UTC, datetime

from allisall import Allisall, APIError, EventInput, IngestError

event: EventInput = {
    # A fixed id: run the program again and the API counts a duplicate.
    "event_id": "quickstart-py-1",
    "timestamp": datetime.now(UTC),
    "agent_key": "quickstart-agent",
    "category": "session",
    "event_type": "session_started",
}

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        summary = client.events.ingest([event])
    except IngestError as err:
        # The API refused the batch, for example an unknown key.
        cause = err.__cause__
        if isinstance(cause, APIError):
            sys.exit(
                f"the API refused the batch: {cause.status} {cause.code}"
                f" (request {cause.request_id})"
            )
        raise

print(f"accepted {summary.accepted}, duplicates {summary.duplicates}, rejected {summary.rejected}")
for row in summary.errors:
    print(f"event {row.index}: {row.code} at {row.pointer}: {row.detail}")
