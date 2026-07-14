#!/usr/bin/env bash
# mesh-okx (skill) — shares MESH_* names with mesh-skill; namespaced MOKX_*.
set -euo pipefail
PREFIX="MOKX_"
while IFS='=' read -r k v; do
  [[ $k == ${PREFIX}* ]] && export "${k#$PREFIX}=$v"
done < <(env)
export PORT=8102
cd /srv/apps/mesh-okx
exec /srv/venvs/mesh-okx/bin/python -m kajota_mesh_skill.main
