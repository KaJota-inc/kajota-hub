# kajota-hub — one container, six apps behind a Caddy reverse proxy.
#
# Layout inside the image:
#   /srv/apps/<name>      vendored source for each app (see scripts/vendor.sh)
#   /srv/venvs/<name>     an ISOLATED Python venv per FastAPI app so their
#                         dependency sets (fastapi/web3/pydantic pins) never
#                         collide with each other
#   Caddy                 listens on $PORT, routes by path prefix
#   supervisord           runs Caddy + all six app processes
#
# Only spirit-of-glory-api (JVM) is intentionally NOT here — it stays on its
# own instance (see README).
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONUNBUFFERED=1 \
    NODE_MAJOR=22 \
    # Ride out transient PyPI/CDN hiccups (files.pythonhosted.org 502s) instead of
    # failing the whole hub build — applies to every pip install below, including the
    # isolated build-dependency fetches (setuptools) that broke the slack venv.
    PIP_RETRIES=8 \
    PIP_DEFAULT_TIMEOUT=120

# ---- System deps in small layers (keeps peak build memory low) ------
# Base tools + supervisor
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates gnupg supervisor \
 && rm -rf /var/lib/apt/lists/*

# Node 22 (agents spawn the MongoDB MCP server; witness runs via tsx)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
 && apt-get install -y --no-install-recommends nodejs \
 && rm -rf /var/lib/apt/lists/*

# Caddy (reverse proxy) from its official apt repo
RUN curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
      | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg \
 && curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
      > /etc/apt/sources.list.d/caddy-stable.list \
 && apt-get update \
 && apt-get install -y --no-install-recommends caddy \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /srv
COPY apps /srv/apps

# ---- Isolated Python venvs (one layer each: low peak memory + caching) --
# Agent family (installable packages: `pip install -e .`). The `google-adk`
# 2.x line moved `McpToolset` behind the `[mcp]` extra; the vendored source
# imports it directly (`from google.adk.tools.mcp_tool import McpToolset`),
# so all three ADK-based apps need the extra installed explicitly — the
# apps' pyproject.toml only pins bare `google-adk>=1.2.0`.
RUN python -m venv /srv/venvs/coach-okx && /srv/venvs/coach-okx/bin/pip install -q --upgrade pip \
 && /srv/venvs/coach-okx/bin/pip install -q -e /srv/apps/coach-okx \
 && /srv/venvs/coach-okx/bin/pip install -q "google-adk[mcp]"
RUN python -m venv /srv/venvs/concierge && /srv/venvs/concierge/bin/pip install -q --upgrade pip \
 && /srv/venvs/concierge/bin/pip install -q -e /srv/apps/concierge \
 && /srv/venvs/concierge/bin/pip install -q "google-adk[mcp]"
RUN python -m venv /srv/venvs/slack && /srv/venvs/slack/bin/pip install -q --upgrade pip \
 && /srv/venvs/slack/bin/pip install -q -e /srv/apps/slack \
 && /srv/venvs/slack/bin/pip install -q "google-adk[mcp]"

# Mesh family — upstream Dockerfiles run from source (no `-e .`), so install
# the explicit runtime deps and let supervisord launch from the app cwd.
RUN python -m venv /srv/venvs/mesh-okx && /srv/venvs/mesh-okx/bin/pip install -q --upgrade pip \
 && /srv/venvs/mesh-okx/bin/pip install -q \
      "fastapi>=0.118.0" "uvicorn[standard]>=0.30.0" "web3>=7.4.0" "pydantic>=2.9.0" "pydantic-settings>=2.4.0"
RUN python -m venv /srv/venvs/mesh-skill && /srv/venvs/mesh-skill/bin/pip install -q --upgrade pip \
 && /srv/venvs/mesh-skill/bin/pip install -q \
      "fastapi>=0.118.0" "uvicorn[standard]>=0.30.0" "web3>=7.4.0" "pydantic>=2.9.0" "pydantic-settings>=2.4.0"

# Pre-pull the MongoDB MCP server (Node) the agents spawn on first chat.
RUN npx -y mongodb-mcp-server@latest --help > /dev/null 2>&1 || true

# ---- Witness (Node/Fastify, run via tsx) ---------------------------
# `ws` pulls native optional deps (bufferutil/utf-8-validate) that node-gyp
# compiles, so a C toolchain is needed for the install. We add it in its own
# layer, build, then purge it to keep the runtime image lean.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && cd /srv/apps/witness && npm install --include=dev \
 && apt-get purge -y build-essential && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

# ---- Judge demo (Node, plain http server) --------------------------
# Live x402 click-to-settle demo. casper-js-sdk + casper-x402; install with a
# toolchain present in case a transitive dep needs a native build, then purge
# it to keep the runtime image lean.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && cd /srv/apps/judge && npm install --omit=dev \
 && apt-get purge -y build-essential && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

# ---- OKX A2A daemon (XMTP) — hosts the identity that owns ASP 5855 --
# Pinned rather than @latest so we don't get surprised by a bad release
# mid-review; bump manually when doctor flags a new version.
# Includes build-essential because @xmtp/node-bindings has an optional
# arm64-linux native binary via node-gyp on some platforms.
RUN apt-get update \
 && apt-get install -y --no-install-recommends build-essential \
 && npm install -g @okxweb3/a2a-node@0.1.10 \
 && apt-get purge -y build-essential && apt-get autoremove -y \
 && rm -rf /var/lib/apt/lists/*

# ---- Proxy + process manager + landing page ------------------------
COPY Caddyfile /etc/caddy/Caddyfile
COPY supervisord.conf /etc/supervisor/conf.d/kajota-hub.conf
COPY index.html /srv/index.html
COPY scripts/run /srv/run
RUN chmod +x /srv/run/*.sh

# Render injects $PORT; Caddy binds it. 10000 is the local default.
ENV PORT=10000
EXPOSE 10000

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/kajota-hub.conf"]
