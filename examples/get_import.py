import sys

from allisall import Allisall, APIError, to_import_mapping

# Replace IMPORT_ID with the id of one of your imports.
import_id = "IMPORT_ID"

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        item = client.imports.get(import_id)
        print(f"{item.filename}: {item.total_rows} rows")
        # The mapping it ran with, ready to send as the next import's mapping.
        mapping = to_import_mapping(item.mapping)
        print(mapping)
    except APIError as err:
        # The API refused the request, for example an unknown id.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
