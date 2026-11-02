import sys

from allisall import Allisall, APIError

# Replace CALCULATION_ID with the id of one of your calculations.
calculation_id = "CALCULATION_ID"

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        client.calculations.delete(calculation_id)
        print(f"deleted calculation {calculation_id}")
    except APIError as err:
        # The API refused the request, for example an unknown id.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
