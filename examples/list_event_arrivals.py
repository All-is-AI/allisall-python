import sys

from allisall import Allisall, APIError

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # The latest arrivals, newest first.
        latest = client.events.list_arrivals(limit=20)
        for event in latest.data:
            print(f"{event.created_at} {event.event_type}")
        # Later, ask how many arrived since: send the previous as_of as since.
        since = client.events.list_arrivals(since=latest.body.as_of, limit=1)
        print(f"{since.body.count} new events")
    except APIError as err:
        # The API refused the request, for example a key without the read scope.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
