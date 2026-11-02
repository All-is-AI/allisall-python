import sys

from allisall import Allisall, APIError

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # Every outcome type the workspace's events carry, page by page.
        for usage in client.outcome_types.list():
            print(f"{usage.outcome_type}: {usage.events} events, quantity {usage.quantity}")
    except APIError as err:
        # The API refused the request, for example a key without the read scope.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
