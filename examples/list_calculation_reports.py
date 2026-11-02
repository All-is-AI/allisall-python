import sys

from allisall import Allisall, APIError

# Replace CALCULATION_ID with the id of one of your calculations.
calculation_id = "CALCULATION_ID"

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # Every report of the calculation, page by page.
        for report in client.reports.list_for_calculation(calculation_id):
            shared = "never" if report.shared_at is None else report.shared_at
            print(f"{report.id} for {report.client_name}: shared {shared}")
    except APIError as err:
        # The API refused the request, for example an unknown id.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
