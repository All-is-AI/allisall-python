import sys

from allisall import Allisall, APIError

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # Every event of August 2026 in the workspace, newest first, page by page. Every page
        # reads the same events, however many arrive meanwhile.
        for event in client.events.list(from_="2026-08-01T00:00:00Z", to="2026-09-01T00:00:00Z"):
            client_name = event.client_name or "no client"
            print(f"{event.timestamp} {event.event_type} for {client_name}")
    except APIError as err:
        # The API refused the request, for example a key without the read scope.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
