import sys
from datetime import UTC, date, datetime

from allisall import Allisall, APIError

# A renewal date one calendar year after today's UTC date. A date before yesterday in UTC is
# refused.
today = datetime.now(UTC).date()
try:
    renewal_date = today.replace(year=today.year + 1).isoformat()
except ValueError:  # 29 February, in a year without one: 1 March, as TypeScript and Go give.
    renewal_date = date(today.year + 1, 3, 1).isoformat()

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
                "renewal_date": renewal_date,
            }
        )
        print(f"created client {created.id} ({created.name})")
    except APIError as err:
        # The API refused the request, for example a key without the write scope.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
