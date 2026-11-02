import sys

from allisall import Allisall, APIError

# Replace CLIENT_ID with the id of one of your clients.
client_id = "CLIENT_ID"

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # The SDK sends one Idempotency-Key on every attempt, so a retry cannot
        # create a second calculation.
        calculation = client.calculations.create_for_client(
            client_id,
            {"period": {"from": "2026-08-01T00:00:00Z", "to": "2026-09-01T00:00:00Z"}},
        )
        print(f"calculation {calculation.id} ({calculation.state})")
        value = "none" if calculation.value_total is None else calculation.value_total
        print(f"value {value}, cost {calculation.cost_total} {calculation.currency}")
    except APIError as err:
        # The API refused the request, for example an unknown id.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
