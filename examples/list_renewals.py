import sys

from allisall import Allisall, APIError

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # Every client with a renewal date, page by page.
        for renewal in client.dashboard.list_renewals():
            roi = "undefined" if renewal.roi is None else renewal.roi
            print(f"{renewal.name}: renews {renewal.renewal_date}, ROI {roi}")
    except APIError as err:
        # The API refused the request, for example a key without the read scope.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
