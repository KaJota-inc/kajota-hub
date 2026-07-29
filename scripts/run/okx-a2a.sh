#!/usr/bin/env bash
# OKX A2A daemon — hosts the XMTP identity that owns ASP 5855.
# See rejection notice from Jul 17: OKX platform online-check needs the
# daemon reachable 24/7. On a laptop it goes down when the machine sleeps
# or shuts, so we run it here in the always-on hub.
#
# The daemon's identity + inbox live in ~/.okx-agent-task/{xmtp,sqlite}.
# Those files are provisioned via a Render secret file mounted at
# /etc/secrets/a2a-state.tar.gz and extracted on first boot. If the secret
# file isn't present (e.g. Render preview envs, local docker run), the
# daemon still starts — but it'll register a fresh XMTP identity, which
# WON'T be the identity OKX has bound to ASP 5855. That's a red flag; log
# it loudly.

set -euo pipefail

STATE_DIR="${OKX_A2A_STATE_DIR:-/root/.okx-agent-task}"
# Render secret files are text-only, so the identity tarball is stored as
# base64 (.b64). Prefer the base64 form; fall back to a raw tarball if an
# operator drops one in via a persistent disk mount.
SECRET_B64="/etc/secrets/a2a-state.tar.gz.b64"
SECRET_BIN="/etc/secrets/a2a-state.tar.gz"

mkdir -p "$STATE_DIR"

extract_if_new() { # <source-path> <decoder-cmd...>
  local src="$1"; shift
  [ -f "$src" ] || return 1
  # Marker keyed on source path so re-uploading a different file triggers
  # re-provision, but supervisord restarts of the same file don't.
  local marker="$STATE_DIR/.provisioned-from-$(basename "$src")"
  if [ -f "$marker" ]; then
    echo "[okx-a2a] state already provisioned from $src"
    return 0
  fi
  echo "[okx-a2a] extracting identity from $src into $STATE_DIR"
  "$@" < "$src" | tar -xz -C "$STATE_DIR"
  date -u +"provisioned=%Y-%m-%dT%H:%M:%SZ from=$src" > "$marker"
}

if ! extract_if_new "$SECRET_B64" base64 -d \
  && ! extract_if_new "$SECRET_BIN" cat; then
  echo "[okx-a2a] WARNING — no identity secret found at:"
  echo "[okx-a2a]   $SECRET_B64"
  echo "[okx-a2a]   $SECRET_BIN"
  echo "[okx-a2a] Daemon will start with a FRESH XMTP identity, which is"
  echo "[okx-a2a] NOT the one OKX bound to ASP 5855. Upload the base64"
  echo "[okx-a2a] tarball as a Render secret file to fix."
fi

# The daemon writes state relative to $HOME; make sure that resolves to
# the state dir's parent so ~/.okx-agent-task = $STATE_DIR.
export HOME="$(dirname "$STATE_DIR")"

# `run` = foreground mode (needed for supervisord). `daemon start` would
# double-fork and confuse supervisord's process supervision.
exec okx-a2a run
