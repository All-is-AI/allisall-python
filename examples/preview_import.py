import sys

from allisall import Allisall, APIError, ImportMapping

# The mapping names the CSV column that holds each event member.
mapping: ImportMapping = {
    "columns": {
        "timestamp": "Time",
        "agent_key": "Agent",
        "client_key": "Client",
        "category": "Category",
        "event_type": "Type",
        "cost": "Cost",
        "currency": "Currency",
    },
    "timezone": "Asia/Tokyo",
    "delimiter": ",",
}
file = (
    "Time,Agent,Client,Category,Type,Cost,Currency\n"
    "2026-08-14 12:12:40,support-bot,acme,model,completion,0.3683,JPY\n"
)

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # Nothing is stored: the preview reports what an import would do.
        preview = client.imports.preview({"mapping": mapping, "file": file})
        print(f"{preview.valid} of {preview.total_rows} rows valid, {preview.rejected} rejected")
        for error in preview.errors:
            print(f"row {error.row}: {error.code}: {error.detail}")
    except APIError as err:
        # The API refused the request, for example a key without the ingest scope.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
