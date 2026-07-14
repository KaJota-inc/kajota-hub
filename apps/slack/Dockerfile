# KaJota Concierge agent image — used by Render for the deployed service.
#
# Uses python:3.11-slim as the base and installs Node 22 alongside it,
# because the MongoDB MCP server is a Node package that the agent
# launches via `npx`. Both runtimes live in the same container so the
# agent's subprocess-spawn of the MCP server works without network
# access at startup.

FROM python:3.11-slim

# ---- Node 22 (for the MongoDB MCP server) -------------------------
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
 && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && rm -rf /var/lib/apt/lists/*

# Pre-pull the MongoDB MCP server so the first `chat` request doesn't
# pay the ~30 MB download tax. Render's free plan cold-start is slow
# enough already.
RUN npx -y mongodb-mcp-server@latest --help > /dev/null 2>&1 || true

# ---- Python deps --------------------------------------------------
WORKDIR /app
COPY pyproject.toml /app/
COPY kajota_concierge /app/kajota_concierge

RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir -e .

# Build-time sanity check that both MCP partner runtimes are reachable
# from inside the image. We do these as actual subprocess calls so the
# build fails loudly if either binary isn't on PATH — rather than
# discovering it at first user request.
RUN python -c "import mcp_server_fetch" \
 && node --version > /dev/null \
 && npx --version > /dev/null

# ---- Render expects $PORT, defaults to 8080 -----------------------
ENV PORT=8080
EXPOSE 8080

# Healthcheck — Render polls this. Matches the FastAPI route.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD curl -fsS http://localhost:${PORT}/healthz || exit 1

# Entrypoint: launches FastAPI via uvicorn on $PORT.
CMD ["python", "-m", "kajota_concierge.server"]
