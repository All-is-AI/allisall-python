import sys

from allisall import Allisall, APIError

# Replace CALCULATION_ID with the id of one of your calculations.
calculation_id = "CALCULATION_ID"

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        calculation = client.calculations.get(calculation_id)
        roi = "undefined" if calculation.ratios.roi is None else calculation.ratios.roi
        print(f"{calculation.state}, ROI {roi}")
        value = "none" if calculation.value_total is None else calculation.value_total
        print(f"value {value}, cost {calculation.cost_total} {calculation.currency}")
    except APIError as err:
        # The API refused the request, for example an unknown id.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
