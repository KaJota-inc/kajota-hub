#!/usr/bin/env bash
# concierge-slack (agent) — config namespaced SLK_* (note: its own real var
# SLACK_BOT_TOKEN is set as SLK_SLACK_BOT_TOKEN so the prefix strip yields it).
set -euo pipefail
PREFIX="SLK_"
while IFS='=' read -r k v; do
  [[ $k == ${PREFIX}* ]] && export "${k#$PREFIX}=$v"
done < <(env)
export PORT=8104
cd /srv/apps/slack
exec /srv/venvs/slack/bin/python -m kajota_concierge.server
