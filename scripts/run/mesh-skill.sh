#!/usr/bin/env bash
# mesh-skill (skill, rapid-agent branch) — namespaced MSKL_*.
set -euo pipefail
PREFIX="MSKL_"
while IFS='=' read -r k v; do
  [[ $k == ${PREFIX}* ]] && export "${k#$PREFIX}=$v"
done < <(env)
export PORT=8105
cd /srv/apps/mesh-skill
exec /srv/venvs/mesh-skill/bin/python -m kajota_mesh_skill.main
