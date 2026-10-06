#!/usr/bin/env bash
# payflow-freshdesk — NIP payment-ops triage webhook receiver for Freshdesk.
# Its config is namespaced PFFD_* in Render and de-namespaced here so the
# app sees FRESHDESK_*/ANTHROPIC_API_KEY/etc at their native names.
set -euo pipefail
PREFIX="PFFD_"
while IFS='=' read -r k v; do
  [[ $k == ${PREFIX}* ]] && export "${k#$PREFIX}=$v"
done < <(env)
export PORT=8109
cd /srv/apps/payflow
exec /srv/venvs/payflow/bin/uvicorn \
  payflow.integrations.freshdesk.asgi:app \
  --host 127.0.0.1 --port "$PORT" \
  --proxy-headers --forwarded-allow-ips '*'
