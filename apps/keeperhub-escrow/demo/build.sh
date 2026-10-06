#!/usr/bin/env bash
# Demo v6 — final assembly.
#
# Frames are 3200x2000 (1600x1000 CSS @2x). Each shot gets its own framing
# rather than one global crop: the verdict/report panels are roughly square,
# so they are matted onto the page's own background (#050507) instead of
# being sliced to 16:9. Full-width shots crop straight to 16:9.
set -euo pipefail
cd "$(dirname "$0")"

F=frames; W=work2; mkdir -p $W; rm -f $W/*.mp4 $W/list.txt

# A near-square panel centred on the page background, sized to leave the
# lower ~140px clear for captions.
CARD () { echo "crop=$1,scale=-1:900:flags=lanczos,pad=1920:1080:(ow-iw)/2:26:color=0x050507"; }

# clip <name> <frame> <dur> <filter> [zoom]
clip () {
  local name=$1 img=$2 dur=$3 filt=$4 zoom=${5:-1} fps=30
  local frames; frames=$(python3 -c "print(int($dur*30))")
  local z="zoompan=z=1:d=$frames:s=1920x1080:fps=$fps"
  [ "$zoom" = "1" ] && z="zoompan=z='min(zoom+0.00030,1.035)':d=$frames:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1920x1080:fps=$fps"
  ffmpeg -y -v error -loop 1 -i "$F/$img.png" -t "$dur" \
    -vf "${filt},${z},format=yuv420p" -r $fps -c:v libx264 -preset slow -crf 17 "$W/$name.mp4"
  echo "file '$PWD/$W/$name.mp4'" >> $W/list.txt
  printf '  ✓ %-5s %6ss  ← %s\n' "$name" "$dur" "$img"
}

PANEL=$(CARD "1240:1330:1600:130")     # CFO verdict card (+ its tabs)
RUNS=$(CARD  "1240:1330:1600:100")     # replay panel + runs table
AUDIT=$(CARD "1180:1330:330:120")      # auditor report card

echo "rendering…"
# §1 HOOK — open on the refusal
clip s1  s1-hold       11.28 "$PANEL" 1
# §2 WHAT IT IS
clip s2  s2-hero       17.32 "crop=2500:1406:180:260,scale=1920:1080:flags=lanczos" 1
# §3 THE REFUSAL — hold → release → the real on-chain runs
clip s3a s1-hold        7.60 "$PANEL" 0
clip s3b s3-release     7.50 "$PANEL" 0
clip s3c s3-runs        7.50 "$RUNS"  1
# §4 WHERE THE MODEL IS — deterministic rules, three verdicts, then the traps
clip s4a s3-release    11.35 "$PANEL" 1
clip s4b s4-reject     11.35 "$PANEL" 0
clip s4c s5-traps      11.34 "crop=3000:1688:100:120,scale=1920:1080:flags=lanczos" 1
# §5 PR + AUDITOR — 2450 wide keeps "#1857" in the title. 2150 cut it, and
# 3200 leaves a dead black band where GitHub's layout ends.
clip s5a s5-pr         10.15 "crop=2450:1378:0:110,scale=1920:1080:flags=lanczos" 1
clip s5b s5-audit      10.17 "$AUDIT" 1
# §6 DOES THIS ALONE — the watcher, then third-party proof it actually fired.
#
# The panel's "released by coach" counter is in-memory and reads 0 after any
# redeploy, which undercuts the line it plays under. A block explorer does
# not have that problem, and is not our own page asserting our own success:
# it carries the 85/15 split executing on-chain and "confirmed within 12.364
# secs" against the ~15s claim. Cut to it just before "it released that one
# on its own" lands at ~116.5s.
clip s6a s6-autonomous  8.94 "crop=2400:1350:400:70,scale=1920:1080:flags=lanczos" 1
# Cropped to the facts only — heading and tabs dropped — then matted so the
# 0.085/0.015 split sits above the caption band instead of under it.
clip s6b s6-explorer    6.58 "crop=2120:1193:180:800,scale=-1:900:flags=lanczos,pad=1920:1080:(ow-iw)/2:16:color=0xFFFFFF" 1
# §7 CLOSE
clip s7  s2-hero        9.72 "crop=2500:1406:180:260,scale=1920:1080:flags=lanczos" 0

echo "concatenating…"
ffmpeg -y -v error -f concat -safe 0 -i $W/list.txt -c copy $W/silent.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 $W/silent.mp4
