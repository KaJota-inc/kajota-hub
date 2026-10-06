#!/usr/bin/env bash
# payflow-zendesk — NIP payment-ops triage webhook receiver for Zendesk.
# Its config is namespaced PFZD_* in Render and de-namespaced here so the
# app sees ZENDESK_*/ANTHROPIC_API_KEY/etc at their native names.
set -euo pipefail
PREFIX="PFZD_"
while IFS='=' read -r k v; do
  [[ $k == ${PREFIX}* ]] && export "${k#$PREFIX}=$v"
done < <(env)
export PORT=8110
cd /srv/apps/payflow
exec /srv/venvs/payflow/bin/uvicorn \
  payflow.integrations.zendesk.asgi:app \
  --host 127.0.0.1 --port "$PORT" \
  --proxy-headers --forwarded-allow-ips '*'
