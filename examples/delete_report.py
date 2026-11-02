import sys

from allisall import Allisall, APIError

# Replace REPORT_ID with the id of one of your reports.
report_id = "REPORT_ID"

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        client.reports.delete(report_id)
        print(f"deleted report {report_id}")
    except APIError as err:
        # The API refused the request, for example an unknown id.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
