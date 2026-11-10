import sys

from allisall import Allisall, APIError

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # The API key names the workspace, so the call takes no id.
        workspace = client.workspace.get()
        print(f"{workspace.name}: figures in {workspace.currency}, created {workspace.created_at}")
    except APIError as err:
        # The API refused the request, for example a key without the read scope.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
