import sys

from allisall import Allisall, APIError

# Replace CLIENT_ID with the id of one of your clients.
client_id = "CLIENT_ID"

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # Every outcome type the client's events carry, page by page.
        for usage in client.outcome_types.list_for_client(client_id):
            print(f"{usage.outcome_type}: {usage.events} events, quantity {usage.quantity}")
    except APIError as err:
        # The API refused the request, for example an unknown id.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
