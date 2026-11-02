import sys

from allisall import Allisall, APIError

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # Every agent in the workspace, page by page.
        for agent in client.agents.list():
            print(f"{agent.agent_key} {agent.name}: assigned to {agent.client_count} clients")
    except APIError as err:
        # The API refused the request, for example a key without the read scope.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
