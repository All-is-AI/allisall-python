import sys

from allisall import Allisall, APIError

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # Every report in the workspace, newest first, page by page.
        for report in client.reports.list():
            period = f"{report.period.from_} to {report.period.to}"
            print(f"{report.id} for {report.client_name}, {period}: {report.state}")
    except APIError as err:
        # The API refused the request, for example a key without the read scope.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
