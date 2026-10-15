#!/usr/bin/env bash
# Rebuilds the Mandate Beacon inspector in the kajota-zama repo and vendors
# the dist/ output into apps/beacon/ for the Docker build context.
#
# Re-run after:
#   - any change to kajota-zama/beacon/src/**
#   - any change to the chain-side manifest (deployments/beacon-sepolia.json);
#     the beacon's own `prebuild` hook re-syncs the manifest into
#     public/beacon-sepolia.json, so this script just picks up the fresh build.

set -euo pipefail

HUB="$(cd "$(dirname "$0")/.." && pwd)"
DOCS="${KAJOTA_DOCS:-$HOME/Documents}"
SRC="$DOCS/kajota-zama/beacon"
DEST="$HUB/apps/beacon"

[[ -d $SRC ]] || { echo "!! missing beacon source: $SRC" >&2; exit 1; }

echo ">> building beacon inspector in $SRC"
(cd "$SRC" && npm run preflight)

echo ">> vendoring dist/ → apps/beacon/"
rm -rf "$DEST"
mkdir -p "$DEST"
cp -R "$SRC/dist/"* "$DEST/"

count=$(find "$DEST" -type f | wc -l | tr -d ' ')
echo "OK — apps/beacon/ now contains $count files"
if command -v jq >/dev/null 2>&1; then
  jq -r '"   anchors=\(.anchors | length) · MandateAnchor=\(.MandateAnchor.address) · SakkMandate=\(.SakkMandate.address) · EsusuMandate=\(.EsusuMandate.address)"' "$DEST/beacon-sepolia.json"
else
  echo "   (jq not installed; raw manifest at apps/beacon/beacon-sepolia.json)"
fi
