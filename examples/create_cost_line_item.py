import sys
from decimal import Decimal

from allisall import Allisall, APIError

# Replace CLIENT_ID with the id of one of your clients.
client_id = "CLIENT_ID"

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # The SDK sends one Idempotency-Key on every attempt, so a retry cannot
        # create a second line item.
        item = client.cost.create_line_item(
            {
                "label": "Hosting",
                "target": {"kind": "client", "id": client_id},
                "monthly_amount": Decimal("30000"),
                "start_date": "2026-07-01",
            }
        )
        print(f"created cost line item {item.id}: {item.monthly_amount} {item.currency} a month")
    except APIError as err:
        # The API refused the request, for example an unknown id.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
