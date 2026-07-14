"""KaJota Concierge agent definition.

Gemini 3 Pro on Google's Agent Development Kit (ADK), with MongoDB
Atlas reached through the official MongoDB MCP server (which
launches as a subprocess via ``npx`` and speaks the Model Context
Protocol over stdio).

The agent's tools come from the MongoDB MCP server's auto-exposed
toolset (find / aggregate / insert-one / update-one / etc.). The
ADK ``McpToolset`` discovers them at startup.

The instruction below pins behaviour: the agent must query MongoDB
for the data it needs before answering. No fabrication, no guessing.

ADK discovers ``root_agent`` by name. Don't rename without updating
the ``agents.yaml`` (if one exists) or the ``adk run`` invocation.
"""

from __future__ import annotations

import os
from typing import Final

from dotenv import load_dotenv

# Load .env.rapid-agent if present; falls back to the process env.
# Render injects its env group directly; this is for local dev.
# Must happen BEFORE any google.* import — those probe the env at
# module-load to pick between Vertex AI and the public Gemini API.
load_dotenv(".env.rapid-agent")
load_dotenv(".env")

# Force google-genai (and therefore ADK) to use Vertex AI rather than
# the public Gemini API. Without these three the ADK looks for a
# GEMINI_API_KEY and raises ValueError when it doesn't find one.
# We map our shorter GCP_PROJECT_ID / GCP_REGION names onto the
# canonical Google ones so callers only need to set the short ones.
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
if "GOOGLE_CLOUD_PROJECT" not in os.environ:
    project = os.environ.get("GCP_PROJECT_ID", "")
    if project:
        os.environ["GOOGLE_CLOUD_PROJECT"] = project
if "GOOGLE_CLOUD_LOCATION" not in os.environ:
    # Default to `global` — Gemini 3 preview models (gemini-3.1-pro-preview
    # in particular) ONLY publish to the global endpoint, not regional ones
    # like us-central1. GA models like gemini-2.5-pro also accept global,
    # so this is forward-compatible. Override via GCP_REGION if a specific
    # region is needed for a future model.
    os.environ["GOOGLE_CLOUD_LOCATION"] = os.environ.get("GCP_REGION", "global")

# Env-var fallback for the GCP credentials. The clean path is to mount
# the service-account JSON as a file (Render Secret File at
# /etc/secrets/gcp-service-account.json, or local file pointed at by
# GOOGLE_APPLICATION_CREDENTIALS). If that's wedged on the deploy
# platform, set GCP_SERVICE_ACCOUNT_JSON to the raw JSON contents and
# we'll persist it to /tmp at startup and re-point ADC at it. Either
# path works; env var takes priority because it's the explicit override.
_sa_json_inline = os.environ.get("GCP_SERVICE_ACCOUNT_JSON", "").strip()
if _sa_json_inline:
    import tempfile

    _sa_path = os.path.join(tempfile.gettempdir(), "kajota-gcp-sa.json")
    with open(_sa_path, "w", encoding="utf-8") as _f:
        _f.write(_sa_json_inline)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = _sa_path

from google.adk.agents import Agent  # noqa: E402  imported after env set
from google.adk.tools.mcp_tool import McpToolset, StdioConnectionParams  # noqa: E402
from mcp import StdioServerParameters  # noqa: E402

# ---- Model selection ----------------------------------------------

# The Rapid Agent track prompt requests Gemini 3 Pro. We hit two
# blockers on that in this hack run:
#   - gemini-3-pro (preview) was discontinued on Mar 26, 2026 → 404
#   - gemini-3.1-pro-preview requires Model Garden allowlist access
#     that our hackathon GCP project hadn't been granted yet → 404
# Pivoting to gemini-2.5-pro (GA, broadly available) for the submission
# so the demo actually runs. Override at runtime via GEMINI_MODEL env
# var when the Gemini 3 access lands.
GEMINI_MODEL: Final[str] = os.environ.get("GEMINI_MODEL", "gemini-2.5-pro")

# ---- MongoDB MCP toolset ------------------------------------------

_MONGODB_URI = os.environ.get("MONGODB_URI", "")
if not _MONGODB_URI:
    # Fail loud rather than silently boot an agent with no data layer.
    # The Rapid Agent track requires a partner MCP integration; if Mongo
    # isn't configured, the submission isn't valid.
    raise RuntimeError(
        "MONGODB_URI is not set. Configure it in .env.rapid-agent (local "
        "dev) or the Render env group (deployed). See agent/README.md."
    )

mongodb_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            # Launches the official MongoDB MCP server as a subprocess.
            # `-y` accepts the `npx` package install prompt on first run.
            command="npx",
            args=[
                "-y",
                "mongodb-mcp-server@latest",
                "--connectionString",
                _MONGODB_URI,
            ],
            # The server reads its config from the connection string;
            # keep the env passthrough minimal so it can't pick up
            # unrelated host secrets.
            env={
                "PATH": os.environ.get("PATH", ""),
            },
        ),
        # Generous startup timeout: the first `npx` invocation downloads
        # ~30 MB of the MongoDB driver. Subsequent runs are cached and
        # start in <2s.
        timeout=60,
    ),
)

# ---- Fetch MCP toolset (second partner) --------------------------
#
# Anthropic's reference Fetch MCP server, launched as a Python module.
# Exposes a single `fetch` tool that retrieves a URL and returns the
# converted Markdown body (or raw, on request). No auth, no API key.
#
# The agent uses this when a shopping question can't be answered from
# the merchant's own database — competitor prices, public product spec
# pages, review summaries. Composing it with the MongoDB MCP under the
# same ADK runner is the Rapid Agent submission's "MCP as architecture,
# not checkbox" claim.
#
# Install: `pip install mcp-server-fetch` (pinned in pyproject.toml).
fetch_mcp = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="python",
            args=[
                "-m",
                "mcp_server_fetch",
                # Identify ourselves so target servers don't see a bare
                # `python-httpx` UA. Public web hosts are friendlier to
                # named bots.
                "--user-agent",
                "KaJotaConciergeAgent/1.0 (hackathon; +https://github.com/KaJota-inc/kajota-coach)",
                # Honour robots.txt — the agent shouldn't crawl past
                # what humans can hit. Reasonable default; flip off for
                # specific demos via env if needed.
            ],
            env={
                "PATH": os.environ.get("PATH", ""),
            },
        ),
        # Fetch is usually fast (<2s for small pages) but a real
        # product / Wikipedia page through Render free-tier outbound
        # can spend 20-40s on the HTTP roundtrip + markdown conversion.
        # The MCP-roundtrip timeout has to cover the worst case, so
        # 60s. Heavier than ideal for short pages but never the
        # bottleneck — Gemini's own reasoning latency dwarfs this.
        timeout=60,
    ),
)

# ---- Agent definition --------------------------------------------

root_agent = Agent(
    name="kajota_concierge",
    model=GEMINI_MODEL,
    description=(
        "KaJota Concierge — a shopping assistant for the KaJota commerce "
        "platform. Has direct read+write access to the user's purchase "
        "history, wishlist, and the product catalogue via MongoDB Atlas "
        "(reached through the official MongoDB MCP server). Reasons over "
        "concrete database state, never fabricates data."
    ),
    instruction=(
        "You are KaJota Concierge, a shopping assistant for KaJota — a "
        "commerce platform where users shop with stablecoins. Your job "
        "is to help the user find what they're looking for, track their "
        "orders, manage their wishlist, and suggest items they'd plausibly "
        "want based on their purchase history.\n"
        "\n"
        "DATABASE: `kajota` on MongoDB Atlas. Schemas — only these fields "
        "exist. DO NOT query or project for fields not listed here:\n"
        "  - `users`:     {_id, userId, name, email}\n"
        "  - `products`:  {_id, name, category, priceQuote, quoteSymbol, "
        "    stock, addedAt}\n"
        "  - `purchases`: {_id, orderId, userId, itemId, itemName, "
        "    category, pricePaidQuote, quoteSymbol, status, orderedAt, "
        "    shippedAt, deliveredAt, expectedDelivery}\n"
        "  - `wishlist`:  {userId, itemId, itemName, currentPriceQuote, "
        "    targetPriceQuote, quoteSymbol, addedAt, notes}\n"
        "\n"
        "RULES:\n"
        "1. You have direct MongoDB access via the MCP tools (find, "
        "   aggregate, insert-one, update-one). USE THEM. Query the "
        "   database for any user-specific question before answering.\n"
        "2. Never fabricate item names, prices, dates, or order ids. If "
        "   the data isn't in MongoDB, say so explicitly.\n"
        "3. NEVER pass a `projection` argument that asks for fields not "
        "   in the schema above (e.g. there is no `items` field on "
        "   `purchases`). Stick to the exact field names listed.\n"
        "4. 'What did I last buy?': `find` on `purchases` filtered by "
        "   `userId`, sorted by `orderedAt: -1`, limit 1. Cite "
        "   `itemName` + `pricePaidQuote` + `quoteSymbol`.\n"
        "5. 'What should I get next?': `aggregate` on `purchases` to "
        "   identify the user's most-bought category, then `find` on "
        "   `products` filtered by that category, excluding items they "
        "   already own. Cite `name` + `priceQuote` + `quoteSymbol`.\n"
        "6. 'Where is my <X> order?': `find` on `purchases` by `itemName` "
        "   (regex match) + `userId`. Report `status`, `shippedAt`, "
        "   `expectedDelivery` verbatim.\n"
        "7. \"What's on my wishlist?\": `find` on `wishlist` filtered by "
        "   `userId`. Cite `itemName` + `currentPriceQuote` + "
        "   `targetPriceQuote`.\n"
        "8. 'Add X to my wishlist': first `find` on `products` to get "
        "   the `_id` (which IS the `itemId`) + `priceQuote`, then "
        "   `insert-one` into `wishlist` with userId, itemId, itemName, "
        "   currentPriceQuote (= product priceQuote), targetPriceQuote "
        "   (~70% of current, rounded), quoteSymbol.\n"
        "9. Default user id is `demo-user-1`. If the caller passes a "
        "   different `userId`, use that.\n"
        "\n"
        "PUBLIC WEB (via the second MCP partner — `fetch`):\n"
        "- You also have a `fetch` tool from the official Anthropic Fetch "
        "  MCP server. It retrieves a URL and returns its Markdown body.\n"
        "- Use it ONLY when the question needs public-web context that "
        "  isn't in MongoDB: competitor prices on retailer sites, official "
        "  product spec pages, public review summaries. Do NOT use it for "
        "  data the user has stored with KaJota (use MongoDB).\n"
        "- Cite the URL you fetched in your reply so the user can verify.\n"
        "- If a fetch fails (timeout, 4xx, 5xx), explain that briefly and "
        "  fall back to whatever you can answer from MongoDB.\n"
        "\n"
        "OUTPUT FORMAT (strictly enforced):\n"
        "- Use PLAIN TEXT only. No markdown. No `**bold**`, no `*` or "
        "  `-` bullets, no `#` headers, no backticks. Just sentences.\n"
        "- Be concierge-tight: 1-3 sentences of natural narrative, "
        "  citing exact item names and prices verbatim from the DB.\n"
        "- When your answer references one or more concrete products, "
        "  orders, or wishlist items, APPEND a single structured block "
        "  at the very end of your reply, in this exact form (nothing "
        "  after [/CARDS]):\n"
        "    [CARDS]\n"
        "    [\n"
        "      {\"title\":\"<item name>\","
        "\"subtitle\":\"<category, status, or short tag>\","
        "\"price\":\"<current price + currency>\","
        "\"footer\":\"<target price / ETA / extra info, or empty>\"}\n"
        "    ]\n"
        "    [/CARDS]\n"
        "  Strict valid JSON inside the block (double-quoted keys and "
        "  values). One card per item. Omit the block entirely on "
        "  non-product turns (greetings, clarifying questions, errors).\n"
    ),
    tools=[mongodb_mcp, fetch_mcp],
)
