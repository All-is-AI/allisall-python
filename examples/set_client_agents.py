import sys

from allisall import Allisall, APIError

# Replace CLIENT_ID with the id of one of your clients.
client_id = "CLIENT_ID"
# Replace AGENT_ID with the id of one of your agents.
agent_id = "AGENT_ID"

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # The list replaces the client's assigned agents.
        assigned = client.clients.set_agents(client_id, {"agent_ids": [agent_id]})
        for agent in assigned.agents:
            print(f"assigned agent {agent.agent_key}: {agent.name}")
    except APIError as err:
        # The API refused the request, for example an unknown id.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
