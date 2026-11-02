import sys

from allisall import Allisall, APIError

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # The SDK sends one Idempotency-Key on every attempt, so a retry cannot
        # create a second client.
        created = client.clients.create(
            {
                "name": "Acme Logistics",
                "status": "active",
                "client_key": "acme",
                "renewal_date": "2026-12-31",
            }
        )
        print(f"created client {created.id} ({created.name})")
    except APIError as err:
        # The API refused the request, for example a key without the write scope.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
