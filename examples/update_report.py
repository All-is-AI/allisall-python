import sys

from allisall import Allisall, APIError

# Replace REPORT_ID with the id of one of your reports.
report_id = "REPORT_ID"

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # A key left out keeps its value; None clears it.
        report = client.reports.update(
            report_id,
            {
                "note": "August was the first full month on the new routing rules.",
                "disclosures": [
                    {"kind": "unpriced", "included": True, "text": None},
                    {
                        "kind": "token_valued",
                        "included": True,
                        "text": (
                            "Model costs for 220 events were valued"
                            " from token counts at list prices."
                        ),
                    },
                ],
            },
        )
        print(f"report {report.id}: {report.note}")
    except APIError as err:
        # The API refused the request, for example an unknown id.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
