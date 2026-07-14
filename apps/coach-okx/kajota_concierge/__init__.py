"""KaJota Concierge — a Gemini 3 shopping agent on the Google ADK.

Entry points:
    - ``kajota_concierge.agent`` exposes the ``root_agent`` ADK discovers
      by name when you run ``adk web`` / ``adk run kajota_concierge``.
    - ``kajota_concierge.server`` exposes a FastAPI wrapper for the
      deployed Render service.
    - ``kajota_concierge.seed`` seeds the demo MongoDB collections so
      the agent has a realistic dataset to reason over.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - type-checkers only
    from kajota_concierge.agent import root_agent

__all__ = ["root_agent"]


def __getattr__(name: str):
    """Lazily expose ``root_agent`` without eager-importing the agent.

    ADK still discovers ``kajota_concierge.root_agent`` (PEP 562 makes this
    indistinguishable from a module-level binding), but plain
    ``import kajota_concierge`` — or importing a sibling like
    ``x402_casper`` / ``seed`` — no longer drags in google-adk and a live
    MONGODB_URI just to load the package. Keeps the x402 paywall and its
    tests importable in a minimal environment.
    """
    if name == "root_agent":
        from kajota_concierge.agent import root_agent

        return root_agent
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
