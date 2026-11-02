import sys

from allisall import Allisall, APIError

# Replace CLIENT_ID with the id of one of your clients.
client_id = "CLIENT_ID"

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # The client's return on investment for August 2026.
        result = client.analytics.get_roi_for_client(
            client_id, from_="2026-08-01T00:00:00Z", to="2026-09-01T00:00:00Z"
        )
        ratios = result.ratios
        if ratios.roi is None:
            print(f"ROI undefined: {ratios.undefined_reason}")
        else:
            print(f"ROI: {ratios.roi}")
        value = "none" if result.value.total is None else result.value.total
        print(f"value {value}, cost {result.cost.total} {result.currency}")
    except APIError as err:
        # The API refused the request, for example an unknown id.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
