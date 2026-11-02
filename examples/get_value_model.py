import sys

from allisall import Allisall, APIError

# Replace VALUE_MODEL_ID with the id of one of your value models.
value_model_id = "VALUE_MODEL_ID"

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        model = client.value_models.get(value_model_id)
        print(f"{model.name}, version {model.version} ({model.status})")
        for item in model.line_items:
            print(f"{item.outcome_type}: {item.unit_value} {model.currency} each, {item.label}")
    except APIError as err:
        # The API refused the request, for example an unknown id.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
