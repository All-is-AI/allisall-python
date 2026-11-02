import sys

from allisall import Allisall, APIError

# Reads the API key from AIA_API_KEY.
with Allisall() as client:
    try:
        # The SDK sends one Idempotency-Key on every attempt, so a retry cannot
        # create a second agent.
        agent = client.agents.create(
            {
                "agent_key": "support-bot",
                "name": "Support bot",
                "framework": "LangGraph",
                "version": "1.4.0",
                "status": "active",
            }
        )
        print(f"created agent {agent.id} ({agent.agent_key})")
    except APIError as err:
        # The API refused the request, for example a key without the write scope.
        sys.exit(f"the API refused the request: {err.status} {err.code} (request {err.request_id})")
