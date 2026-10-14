#!/usr/bin/env bash
# dsa-native — static SPA + MongoDB-backed sync for the DSA + AI-native
# interview prep daily driver. Reverse-proxied by Caddy at /dsa-native/*.
#
# Env namespace is DSAN_* so it cannot collide with the other hub apps.
# The wrapper strips the prefix before launching the server.
set -euo pipefail

export PORT=8112
# Mongo URI — reuse the shared kajota Atlas cluster via a DSAN-prefixed
# Render env var (sync: false). The server reads MONGODB_URI; we rename.
export MONGODB_URI="${DSAN_MONGODB_URI:-}"
export MONGODB_DB="${DSAN_MONGODB_DB:-dsa_native}"

cd /srv/apps/dsa-native
exec node server.js
