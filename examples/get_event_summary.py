import sys

from allisall import Allisall, APIError

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # August 2026 in Tokyo: each day runs from local midnight.
        summary = client.events.get_summary(
            from_="2026-08-01T00:00:00+09:00", to="2026-09-01T00:00:00+09:00"
        )
        print(f"{summary.total} events")
        for day in summary.days:
            print(f"{day.start}: {day.count}")
        for category in summary.categories:
            print(f"{category.category}: {category.count}")
    except APIError as err:
        # The API refused the request, for example a key without the read scope.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
