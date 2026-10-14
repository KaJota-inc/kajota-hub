#!/usr/bin/env bash
# ielts-sda-prep-api — single-user sync backend for the PhD prep React app.
#
# No shared config to inherit. All vars are namespaced KH_IELTS_* so they
# cannot collide with any other hub app. If KH_IELTS_API_TOKEN is unset,
# the server refuses to serve (fail-closed, see server.py:require_bearer).
set -euo pipefail

export PORT=8111
# Database file. Set KH_IELTS_DB_PATH in Render to a path on the Render
# persistent disk, e.g. /srv/data/ielts-sda-prep-api.sqlite3.
export KH_IELTS_DB_PATH="${KH_IELTS_DB_PATH:-/srv/data/ielts-sda-prep-api.sqlite3}"
# Comma-separated list, e.g.:
#   https://ielts-sda-prep.vercel.app,http://localhost:5173
export KH_IELTS_ALLOWED_ORIGINS="${KH_IELTS_ALLOWED_ORIGINS:-}"
# Per-upload audio cap in bytes (default 25 MiB).
export KH_IELTS_MAX_AUDIO_BYTES="${KH_IELTS_MAX_AUDIO_BYTES:-26214400}"
# Bundled public content (campaign + study markdown). Ships inside the image
# under the app dir; override only if you relocate it.
export KH_IELTS_CONTENT_DIR="${KH_IELTS_CONTENT_DIR:-/srv/apps/ielts-sda-prep-api/content}"

cd /srv/apps/ielts-sda-prep-api
exec /srv/venvs/ielts-sda-prep-api/bin/uvicorn \
  ielts_sda_prep_api.server:app \
  --host 127.0.0.1 \
  --port "$PORT" \
  --log-level info
