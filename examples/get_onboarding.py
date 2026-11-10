import sys

from allisall import Allisall, APIError

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        progress = client.onboarding.get()
        for step in progress.steps:
            if step.completed:
                state = "completed"
            elif step.skipped_at is not None:
                state = f"skipped at {step.skipped_at}"
            else:
                state = "to do"
            print(f"{step.step}: {state}")
        print(f"resume at: {progress.current_step or 'every step is done'}")
    except APIError as err:
        # The API refused the request, for example a key without the read scope.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
