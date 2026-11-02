import sys

from allisall import Allisall, APIError

# Replace COST_LINE_ITEM_ID with the id of one of your cost line items.
cost_line_item_id = "COST_LINE_ITEM_ID"

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # A key left out keeps its value; None clears it.
        item = client.cost.update_line_item(cost_line_item_id, {"end_date": "2026-12-31"})
        print(f"{item.label} now ends on {item.end_date}")
    except APIError as err:
        # The API refused the request, for example an unknown id.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
