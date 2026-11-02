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
        # The SDK sends one Idempotency-Key on every attempt, so a retry cannot
        # import the file twice.
        result = client.imports.commit({"mapping": mapping, "file": file})
        print(f"import batch {result.import_batch_id}")
        print(
            f"accepted {result.accepted}, duplicates {result.duplicates},"
            f" rejected {result.rejected}"
        )
        for error in result.errors:
            print(f"row {error.row}: {error.code}: {error.detail}")
    except APIError as err:
        # The API refused the request, for example a key without the ingest scope.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
