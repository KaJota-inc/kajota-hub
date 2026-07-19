#!/usr/bin/env bash
# judge — live x402 click-to-settle demo (Node, plain http server on :8107).
#
# Reuses the concierge's paywall config (the CONC_X402_* vars already set in
# Render) so we don't duplicate them. The ONLY judge-specific secret is the
# payer signing key, namespaced JUDGE_ so it never leaks into the concierge's
# env. The PEM is multi-line, so it is exported directly (NOT via the env
# line-parse loop, which only handles single-line CONC_X402_* values).
set -euo pipefail

# Shared single-line paywall config from the concierge (strip CONC_ prefix).
while IFS='=' read -r k v; do
  [[ $k == CONC_X402_* ]] && export "${k#CONC_}=$v"
done < <(env)

# Judge-only: the payer key (multi-line) + algo, handled directly.
export CLIENT_PRIVATE_KEY_PEM="${JUDGE_CLIENT_PRIVATE_KEY_PEM:-}"
export CLIENT_KEY_ALGO="${JUDGE_CLIENT_KEY_ALGO:-secp256k1}"
# The demo's resource is behind the hub's /concierge mount.
export X402_RESOURCE="${X402_RESOURCE:-https://kajota-hub.onrender.com/concierge/coach/premium}"

export PORT=8107
cd /srv/apps/judge
exec node server.mjs
