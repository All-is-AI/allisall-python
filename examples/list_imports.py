import sys

from allisall import Allisall, APIError

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # Every import in the workspace, newest first, page by page.
        for item in client.imports.list():
            counts = f"{item.accepted} accepted, {item.duplicates} duplicates"
            print(f"{item.filename}: {counts}, {item.rejected} rejected")
    except APIError as err:
        # The API refused the request, for example a key without the read scope.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
