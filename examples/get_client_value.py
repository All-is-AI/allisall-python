import sys

from allisall import Allisall, APIError

# Replace CLIENT_ID with the id of one of your clients.
client_id = "CLIENT_ID"

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # The value the client's outcomes produced in August 2026.
        value = client.analytics.get_value_for_client(
            client_id, from_="2026-08-01T00:00:00Z", to="2026-09-01T00:00:00Z"
        )
        total = "none" if value.total is None else value.total
        print(f"value: {total} {value.currency}")
        for line in value.lines:
            print(
                f"{line.label}: {line.quantity} at {line.unit_value}, {line.total} {value.currency}"
            )
    except APIError as err:
        # The API refused the request, for example an unknown id.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
