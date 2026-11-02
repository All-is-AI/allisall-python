import sys

from allisall import Allisall, APIError

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # Every value model in the workspace, page by page.
        for model in client.value_models.list():
            print(f"{model.client_name}: {model.name}, version {model.version} ({model.status})")
    except APIError as err:
        # The API refused the request, for example a key without the read scope.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
