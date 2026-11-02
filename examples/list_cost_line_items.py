import sys

from allisall import Allisall, APIError

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # Every cost line item in the workspace, page by page.
        for item in client.cost.list_line_items():
            print(
                f"{item.label}: {item.monthly_amount} {item.currency} a month"
                f" from {item.start_date}"
            )
    except APIError as err:
        # The API refused the request, for example a key without the read scope.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
