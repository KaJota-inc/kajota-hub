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
SECRET="/etc/secrets/a2a-state.tar.gz"

mkdir -p "$STATE_DIR"

# First-boot: extract the tarball into $STATE_DIR (idempotent — tar will
# overwrite existing files, which is what we want if the operator uploads
# a refreshed identity).
if [ -f "$SECRET" ]; then
  # Marker so we only extract once per boot, not on supervisord restarts.
  if [ ! -f "$STATE_DIR/.provisioned-from-secret" ]; then
    echo "[okx-a2a] extracting identity from $SECRET into $STATE_DIR"
    tar -xzf "$SECRET" -C "$STATE_DIR"
    date -u +"provisioned=%Y-%m-%dT%H:%M:%SZ from=$SECRET" > "$STATE_DIR/.provisioned-from-secret"
  fi
else
  echo "[okx-a2a] WARNING — $SECRET not mounted. Daemon will run with a"
  echo "[okx-a2a] fresh XMTP identity, which is NOT the one OKX bound to"
  echo "[okx-a2a] ASP 5855. Upload the tarball as a Render secret file."
fi

# The daemon writes state relative to $HOME; make sure that resolves to
# the state dir's parent so ~/.okx-agent-task = $STATE_DIR.
export HOME="$(dirname "$STATE_DIR")"

# `run` = foreground mode (needed for supervisord). `daemon start` would
# double-fork and confuse supervisord's process supervision.
exec okx-a2a run
