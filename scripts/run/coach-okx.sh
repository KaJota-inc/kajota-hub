#!/usr/bin/env bash
# coach-okx (agent) — shares generic var names with concierge/slack, so its
# config is namespaced COKX_* in Render and de-namespaced here.
set -euo pipefail
PREFIX="COKX_"
while IFS='=' read -r k v; do
  [[ $k == ${PREFIX}* ]] && export "${k#$PREFIX}=$v"
done < <(env)
export PORT=8101
cd /srv/apps/coach-okx
exec /srv/venvs/coach-okx/bin/python -m kajota_concierge.server
