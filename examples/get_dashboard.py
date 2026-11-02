import sys

from allisall import Allisall, APIError

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # The portfolio for August 2026.
        dashboard = client.dashboard.get(month="2026-08")
        print(f"value {dashboard.value_total}, cost {dashboard.cost_total} {dashboard.currency}")
        roi = "undefined" if dashboard.ratios.roi is None else dashboard.ratios.roi
        print(f"ROI {roi}")
        for item in dashboard.clients:
            item_roi = "undefined" if item.roi is None else item.roi
            print(f"{item.name}: ROI {item_roi}")
        # The list holds at most 1,000 clients; the omitted count is the rest.
        print(f"clients not listed: {dashboard.clients_omitted}")
        # The five counted clients with the highest value, whatever the sort.
        for item in dashboard.top_clients:
            print(f"top: {item.name}, value {item.value_total}")
    except APIError as err:
        # The API refused the request, for example a key without the read scope.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
