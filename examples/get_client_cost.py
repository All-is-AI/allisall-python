import sys

from allisall import Allisall, APIError

# Replace CLIENT_ID with the id of one of your clients.
client_id = "CLIENT_ID"

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # The cost of serving the client in August 2026.
        cost = client.analytics.get_cost_for_client(
            client_id, from_="2026-08-01T00:00:00Z", to="2026-09-01T00:00:00Z"
        )
        print(f"cost: {cost.total} {cost.currency}")
        print(
            f"pass-through {cost.pass_through}, token-valued {cost.token_valued},"
            f" manual {cost.manual}"
        )
    except APIError as err:
        # The API refused the request, for example an unknown id.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
