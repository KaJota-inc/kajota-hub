#!/usr/bin/env bash
# keeperhub-escrow — Kajota × KeeperHub live console (Node, plain http on :8108).
#
# Reads the KH_* namespaced env vars set in Render:
#   KH_API_KEY (required, kh_...), KH_WORKFLOW_ID (default: hackathon workflow),
#   KH_CONTRACT_ADDRESS, KH_KEEPER_ADDRESS, KH_CHAIN_ID, KH_DEMO_DEPOSIT_ID,
#   KH_API_BASE (default: https://app.keeperhub.com).
set -euo pipefail
export PORT=8108
cd /srv/apps/keeperhub-escrow
exec node server.mjs
