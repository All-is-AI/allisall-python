import sys

from allisall import Allisall, APIError

# Replace REPORT_ID with the id of one of your reports.
report_id = "REPORT_ID"

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        report = client.reports.get(report_id)
        shared = "never" if report.shared_at is None else report.shared_at
        print(f"report for {report.client_name}: shared {shared}")
        for disclosure in report.disclosures:
            print(f"{disclosure.kind}: {'included' if disclosure.included else 'left out'}")
    except APIError as err:
        # The API refused the request, for example an unknown id.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
