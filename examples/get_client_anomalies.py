import sys

from allisall import Allisall, APIError

# Replace CLIENT_ID with the id of one of your clients.
client_id = "CLIENT_ID"

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # What looks unusual in the client's events for August 2026.
        anomalies = client.analytics.get_anomalies_for_client(
            client_id, from_="2026-08-01T00:00:00Z", to="2026-09-01T00:00:00Z"
        )
        print(f"days without outcomes: {len(anomalies.zero_outcome_days)}")
        print(f"cost spikes: {len(anomalies.cost_spikes)}")
        # The list holds at most 100 outcome types; the omitted count is the rest.
        unmapped = len(anomalies.unmapped_outcome_types) + anomalies.unmapped_outcome_types_omitted
        print(f"unmapped outcome types: {unmapped}")
    except APIError as err:
        # The API refused the request, for example an unknown id.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
