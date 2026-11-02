import sys

from allisall import Allisall, APIError

# Replace COST_LINE_ITEM_ID with the id of one of your cost line items.
cost_line_item_id = "COST_LINE_ITEM_ID"

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        item = client.cost.get_line_item(cost_line_item_id)
        print(f"{item.label}: {item.monthly_amount} {item.currency} a month")
        end = "no end date" if item.end_date is None else item.end_date
        print(f"from {item.start_date} to {end}")
    except APIError as err:
        # The API refused the request, for example an unknown id.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
