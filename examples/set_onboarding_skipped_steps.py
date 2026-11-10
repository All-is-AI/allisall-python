import sys

from allisall import Allisall, APIError

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # The steps replace the whole set of skipped steps; [] clears every skip.
        progress = client.onboarding.set_skipped_steps({"steps": ["add_agent"]})
        print(f"resume at: {progress.current_step or 'every step is done'}")
    except APIError as err:
        # The API refused the request, for example a key without the write scope.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
