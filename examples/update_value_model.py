import sys

from allisall import Allisall, APIError

# Replace CLIENT_ID with the id of one of your clients.
client_id = "CLIENT_ID"

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # A key left out keeps its value.
        model = client.value_models.update_for_client(client_id, {"status": "archived"})
        print(f"{model.name} is now {model.status}")
    except APIError as err:
        # The API refused the request, for example an unknown id.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
