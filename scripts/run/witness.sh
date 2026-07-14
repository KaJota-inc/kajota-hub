#!/usr/bin/env bash
# kajota-witness (Node/Fastify via tsx). Its env vars (ZG_*, GROQ_API_KEY,
# WITNESS_*, INDEX_PATH) don't collide with any other app, so they're set
# directly in Render — no namespacing needed. We only pin PORT.
set -euo pipefail
export PORT=8106
cd /srv/apps/witness
exec ./node_modules/.bin/tsx src/server.ts
