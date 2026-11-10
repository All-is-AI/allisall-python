import sys

from allisall import Allisall, APIError

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # Every published calculation in the workspace, page by page.
        for item in client.calculations.list(state="published"):
            period = f"{item.period.from_} to {item.period.to}"
            print(f"{item.client_name} {period}: {item.coverage_findings} coverage findings")
    except APIError as err:
        # The API refused the request, for example a key without the read scope.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
