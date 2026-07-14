"""KaJota Concierge — a Gemini 3 shopping agent on the Google ADK.

Entry points:
    - ``kajota_concierge.agent`` exposes the ``root_agent`` ADK discovers
      by name when you run ``adk web`` / ``adk run kajota_concierge``.
    - ``kajota_concierge.server`` exposes a FastAPI wrapper for the
      deployed Render service.
    - ``kajota_concierge.seed`` seeds the demo MongoDB collections so
      the agent has a realistic dataset to reason over.
"""

from kajota_concierge.agent import root_agent

__all__ = ["root_agent"]
