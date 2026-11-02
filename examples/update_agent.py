import sys

from allisall import Allisall, APIError

# Replace AGENT_ID with the id of one of your agents.
agent_id = "AGENT_ID"

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # A key left out keeps its value; None clears it.
        agent = client.agents.update(agent_id, {"status": "retired"})
        print(f"{agent.agent_key} is now {agent.status}")
    except APIError as err:
        # The API refused the request, for example an unknown id.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
