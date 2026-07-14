#!/usr/bin/env bash
# concierge (agent, rapid-agent branch) — config namespaced CONC_*.
set -euo pipefail
PREFIX="CONC_"
while IFS='=' read -r k v; do
  [[ $k == ${PREFIX}* ]] && export "${k#$PREFIX}=$v"
done < <(env)
export PORT=8103
cd /srv/apps/concierge
exec /srv/venvs/concierge/bin/python -m kajota_concierge.server
