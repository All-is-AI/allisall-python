import sys

from allisall import Allisall, APIError

# Replace COST_LINE_ITEM_ID with the id of one of your cost line items.
cost_line_item_id = "COST_LINE_ITEM_ID"

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        client.cost.delete_line_item(cost_line_item_id)
        print(f"deleted cost line item {cost_line_item_id}")
    except APIError as err:
        # The API refused the request, for example an unknown id.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
