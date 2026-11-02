import sys

from allisall import Allisall, APIError

# Replace CALCULATION_ID with the id of one of your calculations.
calculation_id = "CALCULATION_ID"

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # The SDK sends one Idempotency-Key on every attempt, so a retry cannot
        # create a second report.
        report = client.reports.create_for_calculation(calculation_id)
        print(f"created report {report.id} for {report.client_name}")
    except APIError as err:
        # The API refused the request, for example an unknown id.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
