import sys
from decimal import Decimal

from allisall import Allisall, APIError

# Replace CLIENT_ID with the id of one of your clients.
client_id = "CLIENT_ID"

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # The line items replace the model's whole set, and version must be the
        # model's current version, so read it first.
        current = client.value_models.get_for_client(client_id)
        model = client.value_models.set_line_items_for_client(
            client_id,
            {
                "version": current.version,
                "line_items": [
                    {
                        "outcome_type": "ticket_resolved",
                        "label": "Support ticket resolved autonomously",
                        "unit_value": Decimal("1200"),
                        "provenance_note": (
                            "Agreed with Acme ops lead, 2026-07-20:"
                            " fully loaded cost of a tier-1 ticket."
                        ),
                    },
                    {
                        "outcome_type": "escalation_avoided",
                        "label": "Escalation to a human agent avoided",
                        "unit_value": Decimal("450.5"),
                    },
                ],
            },
        )
        print(f"version {model.version} holds {len(model.line_items)} line items")
    except APIError as err:
        # The API refused the request, for example an unknown id.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
