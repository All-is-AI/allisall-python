import sys

from allisall import Allisall, APIError

# Reads the API key from AIA_API_KEY. The health check itself sends no
# credential.
with Allisall() as client:
    try:
        health = client.health.get()
        print(f"{health.status}, version {health.version}")
    except APIError as err:
        # The API refused the request, for example while the service is unavailable.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
