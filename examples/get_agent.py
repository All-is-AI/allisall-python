import sys

from allisall import Allisall, APIError

# Replace AGENT_ID with the id of one of your agents.
agent_id = "AGENT_ID"

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        agent = client.agents.get(agent_id)
        print(f"{agent.agent_key} {agent.name} ({agent.status})")
        print(
            f"{agent.stats.events} events, costing {agent.stats.cost_total} {agent.stats.currency}"
        )
    except APIError as err:
        # The API refused the request, for example an unknown id.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
