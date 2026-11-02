import sys

from allisall import Allisall, APIError

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        table = client.cost.get_price_table()
        for rate in table.models:
            print(
                f"{rate.model}: {rate.input_per_1k} in, {rate.output_per_1k} out,"
                f" per 1,000 tokens in {table.currency}"
            )
    except APIError as err:
        # The API refused the request, for example a key without the read scope.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
