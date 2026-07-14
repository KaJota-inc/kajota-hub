#!/usr/bin/env bash
# Copies each app's source from its sibling repo into apps/ so the hub is a
# self-contained Docker build context. Re-run after you update any source repo.
#
# It copies the CURRENTLY CHECKED-OUT branch of each repo. The branches that
# match what's live on Render today are:
#   kajota-coach-okx   -> hackathon/okx-asp   (coach-okx + mesh-okx)
#   kajota-coach       -> hackathon/rapid-agent (concierge + mesh-skill)
#   kajota-coach-slack -> hackathon/slack      (slack)
#   kajota-witness     -> main                 (witness)
set -euo pipefail

HUB="$(cd "$(dirname "$0")/.." && pwd)"
DOCS="${KAJOTA_DOCS:-$HOME/Documents}"

copy() { # <repo> <subdir|""> <dest-name>
  local src="$DOCS/$1" sub="${2:-}" dest="$HUB/apps/$3"
  [[ -d $src ]] || { echo "!! missing repo: $src" >&2; exit 1; }
  echo ">> apps/$3  <=  $1${sub:+/$sub}  ($(git -C "$src" branch --show-current 2>/dev/null || echo '?'))"
  rm -rf "$dest"; mkdir -p "$dest"
  rsync -a \
    --exclude '.git' --exclude 'node_modules' --exclude '.venv' \
    --exclude '__pycache__' --exclude '*.pyc' --exclude '*.egg-info' \
    --exclude 'dist' --exclude 'build' \
    "$src/${sub:+$sub/}" "$dest/"
}

copy kajota-coach-okx   agent  coach-okx
copy kajota-coach-okx   skill  mesh-okx
copy kajota-coach       agent  concierge
copy kajota-coach       skill  mesh-skill
copy kajota-coach-slack agent  slack
copy kajota-witness     ""     witness

echo "OK — vendored 6 apps into $HUB/apps"
