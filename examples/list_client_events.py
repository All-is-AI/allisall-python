import sys

from allisall import Allisall, APIError

# Replace CLIENT_ID with the id of one of your clients.
client_id = "CLIENT_ID"

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # Every event attributed to the client in August 2026, page by page.
        events = client.events.list_for_client(
            client_id, from_="2026-08-01T00:00:00Z", to="2026-09-01T00:00:00Z"
        )
        for event in events:
            print(f"{event.timestamp} {event.agent_name}: {event.category} {event.event_type}")
    except APIError as err:
        # The API refused the request, for example an unknown id.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
