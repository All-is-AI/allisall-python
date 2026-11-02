import sys
from decimal import Decimal

from allisall import Allisall, APIError

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # The models replace the whole price table.
        table = client.cost.set_price_table(
            {
                "models": [
                    {
                        "model": "claude-sonnet",
                        "input_per_1k": Decimal("0.45"),
                        "output_per_1k": Decimal("2.25"),
                    },
                    {
                        "model": "gpt-4o",
                        "input_per_1k": Decimal("0.375"),
                        "output_per_1k": Decimal("1.5"),
                    },
                ]
            }
        )
        print(f"the price table holds {len(table.models)} models")
    except APIError as err:
        # The API refused the request, for example a key without the write scope.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
