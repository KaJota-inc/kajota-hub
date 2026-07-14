# KaJota Concierge Agent

**Google Cloud Rapid Agent Hackathon 2026 submission** (Jun 11, 2026).

A shopping assistant agent built on **Gemini 3 Pro** via Google's
**Agent Development Kit (ADK)**, with **MongoDB Atlas** as the data
layer reached through the official **MongoDB MCP server**.

Hits all four track-mandated stack pieces:

| Requirement | How |
|---|---|
| Gemini 3 | `gemini-3-pro` via ADK (`google.adk.agents.Agent(model=...)`)  |
| Google Cloud ADK | `google-adk` Python package |
| Model Context Protocol | `McpToolset` connects via stdio to the MCP server |
| Partner integration via MCP | **MongoDB** (`mongodb-mcp-server@latest` via `npx`) |

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│  Mobile (KaJota app)                                       │
│     POST /chat { message, userId, sessionId? }            │
└───────────────────────────┬────────────────────────────────┘
                            │ HTTPS
┌───────────────────────────▼────────────────────────────────┐
│  Render Web Service (FastAPI: kajota_concierge.server)    │
│     ADK Runner ──▶ root_agent (Gemini 3 Pro)               │
│                       │                                    │
│                       └─tools─▶ MCP Toolset                │
└───────────────────────────────────┬────────────────────────┘
                                    │ stdio (MCP)
                          ┌─────────▼─────────┐
                          │ mongodb-mcp-server │
                          │   (via npx, subproc)│
                          └─────────┬─────────┘
                                    │ TLS
                          ┌─────────▼─────────┐
                          │  MongoDB Atlas    │
                          │  db: kajota       │
                          │  cols: users,     │
                          │  products,        │
                          │  purchases,       │
                          │  wishlist         │
                          └───────────────────┘
```

## Local dev

### 1. Install

```sh
cd agent
pip install -e .
# Node 22+ needed for the MongoDB MCP server (npx fetches it on first run)
```

### 2. Configure

Copy the env template at `/Users/oluwaboriola/Documents/kajota-coach/.env.rapid-agent.example`
to `agent/.env.rapid-agent` and fill in:

```
# GCP — needed for Gemini 3 calls via Vertex AI
GCP_PROJECT_ID=<your-project>
GCP_REGION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=../secrets/rapid-agent/gcp-service-account.json
GEMINI_MODEL=gemini-3-pro

# MongoDB — Atlas connection string (free M0 cluster works)
MONGODB_URI=mongodb+srv://<user>:<pwd>@<cluster>.mongodb.net/

# Partner pick (this build uses MongoDB)
PARTNER=mongodb
```

### 3. Seed the demo data

```sh
kajota-agent-seed
# or: python -m kajota_concierge.seed
```

Seeds the `kajota` database with:
- 1 demo user (`demo-user-1`, "Bori")
- 20 products across sneakers / hoodies / accessories / tech
- 8 past orders with mixed statuses (delivered, shipped in-flight, processing)
- 3 wishlist items

### 4. Run

**Interactive (ADK web UI):**
```sh
adk web kajota_concierge
# Open the printed http://localhost:8000 URL
```

**HTTP server (the Render deployment shape):**
```sh
kajota-agent
# or: python -m kajota_concierge.server
# Listens on $PORT (default 8080)
```

## Demo prompts

The demo flow that produces the cleanest video — each one exercises a
different MCP tool:

| Prompt | MCP tool fired |
|---|---|
| "Where's my order?" | `find` on `purchases` filtered by `status: shipped` |
| "What did I last buy?" | `find` on `purchases` sorted by `orderedAt` |
| "What should I buy next?" | `aggregate` over `purchases` for top category + price range, then `find` on `products` |
| "Add the Supreme hoodie to my wishlist at 30000 NGNT" | `insert-one` on `wishlist` |
| "What's on my wishlist?" | `find` on `wishlist` |
| "Are there sneakers under 25000?" | `find` on `products` with category + priceQuote filter |

For the recording, the order I'd hit:

1. `"What did I last buy?"` → AirPods Pro 2nd Gen / Keychron K2 / Yankees cap
2. `"Where's my Keychron order?"` → status: shipped, expected delivery in 2 days
3. `"What should I get next?"` → agent aggregates the purchase history, recommends a sneaker or tech item based on most-bought category + average price
4. `"Add the Supreme Box Logo hoodie to my wishlist at 30000 NGNT"` → MCP write, then "what's on my wishlist?" shows it landed

That's a 90-second cycle showing 4 distinct MCP tool calls + reasoning.

## Deploy to Render

The repo's `agent/Dockerfile` is what Render builds. Wire it up via the
parent repo's HACKS.md `kajota-coach-rapid-agent` env group + the
Secret Files mount for `gcp-service-account.json`.

```sh
# In the repo root (not agent/)
git push origin hackathon/rapid-agent
# Render auto-deploys
```

## Hackathon submission deliverables

| Item | Path |
|---|---|
| Functional agent | this repo |
| Public open-source repo | https://github.com/KaJota-inc/kajota-coach/tree/hackathon/rapid-agent |
| Demo video | _(record after Render deploy is live)_ |
| Devpost form | _(fill at submission time)_ |

Deadline: **Jun 11, 2026 2:00 PM PT** (judging Jun 22–Jul 6).
