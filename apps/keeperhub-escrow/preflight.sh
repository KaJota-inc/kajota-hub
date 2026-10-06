#!/usr/bin/env bash
#
# Demo preflight — run this immediately before recording, and again if you
# touch anything between the dry run and the take.
#
#   bash apps/keeperhub-escrow/preflight.sh
#
# Every check maps to a line in DEMO-V6-SCRIPT.md. A FAIL means the video
# would claim something that isn't currently true, which is the one class of
# mistake there's no editing around.
#
# Exit 0 = safe to record. Exit 1 = a script claim is currently false.
# WARNs don't block recording but change what will be on screen.

set -uo pipefail

HUB="${HUB:-https://kajota-hub.onrender.com}"
DEPOSIT="0xe713d5a3eb6c0c3c247e3c86ad23696e006c6097de47d5fad9a303838f0f2d13"

pass=0; fail=0; warn=0
ok()   { printf '  \033[32m✓\033[0m %-34s %s\n' "$1" "${2:-}"; pass=$((pass+1)); }
no()   { printf '  \033[31m✗\033[0m %-34s %s\n' "$1" "${2:-}"; fail=$((fail+1)); }
wrn()  { printf '  \033[33m!\033[0m %-34s %s\n' "$1" "${2:-}"; warn=$((warn+1)); }
head_() { printf '\n\033[1m%s\033[0m\n' "$1"; }

jq_() { python3 -c "import json,sys;d=json.load(sys.stdin);print($1)" 2>/dev/null; }

# ---------------------------------------------------------------- service up
head_ "Service"

code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 20 "$HUB/keeperhub/healthz")
[ "$code" = "200" ] && ok "console reachable" "$code" \
                    || no "console reachable" "got $code — Render may be redeploying"

CFG=$(curl -s --max-time 20 "$HUB/keeperhub/config")
wf=$(echo "$CFG" | jq_ 'd["workflowId"]')
kh=$(echo "$CFG" | jq_ 'd["khKeyConfigured"]')
[ -n "$wf" ] && ok "workflow id" "$wf" || no "workflow id" "missing"
[ "$kh" = "True" ] && ok "KeeperHub API key" "configured" \
                   || no "KeeperHub API key" "NOT configured — release will fail"

# ------------------------------------------------- section 6: autonomy claim
# "It released that one on its own." Only true while KH_WATCHER_LIVE=1.
head_ "Section 6 — autonomy"

AUT=$(curl -s --max-time 20 "$HUB/keeperhub/autonomous")
mode=$(echo "$AUT"  | jq_ 'd["mode"]')
run=$(echo "$AUT"   | jq_ 'd["running"]')
rel=$(echo "$AUT"   | jq_ 'd["counts"]["releasedByCoach"]')
up=$(echo "$AUT"    | jq_ 'round((d["lastTickAt"]-d["log"][0]["at"])/60000,1)')

[ "$mode" = "live" ] && ok "watcher mode" "live" \
  || no "watcher mode" "$mode — section 6 line is FALSE, set KH_WATCHER_LIVE=1"
[ "$run" = "True" ] && ok "watcher running" "uptime ${up}m" \
  || no "watcher running" "$run"

if [ "$rel" = "0" ]; then
  wrn "autonomous panel" "empty (0 releases) — deploy reset it; needs a fresh deposit for footage"
else
  ok "autonomous panel" "$rel release(s) on screen"
fi

# --------------------------------------- sections 1+3: the refusal, then flip
# The hook is a refusal. If this stops returning hold, the video has no opening.
head_ "Sections 1+3 — refusal, then release"

SR() {
  curl -s --max-time 25 -X POST "$HUB/concierge/coach/should-release" \
    -H 'content-type: application/json' \
    -d "{\"depositId\":\"$DEPOSIT\",\"buyerConfirmed\":$1,\"sellerShipped\":true,\"activeDispute\":false,\"daysSinceDeposit\":0.01,\"grossAmountUsdc\":0.10}"
}

H=$(SR false)
hd=$(echo "$H" | jq_ 'd["decision"]')
hf=$(echo "$H" | jq_ '",".join(r["name"] for r in d["rules"] if not r["passed"])')
hn=$(echo "$H" | jq_ 'len(d["rules"])')
[ "$hd" = "hold" ] && ok "unconfirmed buyer → HOLD" "fails: $hf" \
                   || no "unconfirmed buyer → HOLD" "got '$hd' — the hook is broken"
[ "$hn" = "6" ] && ok "rule count" "6 on screen" || wrn "rule count" "$hn, script says six"

R=$(SR true)
rd=$(echo "$R" | jq_ 'd["decision"]')
[ "$rd" = "release" ] && ok "confirmed buyer → RELEASE" "one signal different" \
                      || no "confirmed buyer → RELEASE" "got '$rd'"

# --------------------------------------------------- section 4: the LLM part
# "No keyword list reads English." Only true if the LLM classifier answered —
# a keyword fallback would still return isDispute, so check the classifier.
head_ "Section 4 — model on screen"

T=$(curl -s --max-time 30 -X POST "$HUB/concierge/coach/triage" \
     -H 'content-type: application/json' \
     -d '{"message":"the parcel arrived but one of the two speakers is missing"}')
td=$(echo "$T" | jq_ 'd["isDispute"]')
tc=$(echo "$T" | jq_ 'd["classifier"]')
tk=$(echo "$T" | jq_ 'd["category"]')

[ "$td" = "True" ] && ok "triage flags partial delivery" "category=$tk" \
                   || no "triage flags partial delivery" "isDispute=$td"
[ "$tc" = "llm" ] && ok "classifier" "llm (not fallback)" \
                  || wrn "classifier" "$tc — keyword fallback; section 4's claim is weaker on screen"

# ------------------------------------------------------ section 5: the audit
head_ "Section 5 — auditor"

A=$(curl -s --max-time 25 -X POST "$HUB/concierge/coach/audit-workflow" \
  -H 'content-type: application/json' \
  -d '{"workflow":{"name":"probe","nodes":[{"id":"s","type":"action","data":{"config":{"actionType":"web3/write-contract","function":"release","integrationId":"int_x","functionArgs":["{{@trigger.body.depositId}}"]}}}],"edges":[]}}')
ap=$(echo "$A" | jq_ 'd["passed"]')
ai=$(echo "$A" | jq_ 'len(d["issues"])')
[ "$ap" = "False" ] && ok "trap workflow rejected" "$ai issues found" \
                    || no "trap workflow rejected" "passed=$ap — auditor is not catching traps"

# ----------------------------------------------------------------- verdict
head_ "Verdict"
printf '  %d passed · %d warnings · %d failed\n\n' "$pass" "$warn" "$fail"

if [ "$fail" -gt 0 ]; then
  printf '  \033[31mDo not record.\033[0m A line in the script is currently false.\n\n'
  exit 1
fi
printf '  \033[32mSafe to record.\033[0m\n'
printf '  Do NOT push to main until the take is done — a deploy restarts the\n'
printf '  watcher and blanks the autonomous panel mid-recording.\n\n'
exit 0
