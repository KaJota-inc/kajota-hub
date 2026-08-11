# Demo v6 build pipeline

Rebuilds the submission video from the live site. Nothing here is hand-edited
footage — every frame is captured from `kajota-hub.onrender.com/keeperhub/` at
build time, so the video cannot drift from what the site actually does.

```bash
node shoot.mjs ./frames                 # capture the console, 9 frames @ 3200x2000
node shoot1.mjs <url> frames/x.png      # capture one arbitrary page (used for the PR)
python3 captions.py                     # SRT -> transparent caption plates
bash build.sh                           # frames -> timed clips -> work2/silent.mp4
python3 mux.py                          # overlay captions + VO -> the final mp4
```

Inputs: `../DEMO-V6-SCRIPT.md` for the section marks, `v6-fixed.srt` for
captions, `~/Downloads/vo-v2-tight.m4a` for the voice track.
Output: `~/Downloads/kajota-coach-demo-v6.mp4` — 1920x1080, 30fps, 2:10.80.

## Why it's built this way

**Capture over CDP, not the browser-automation screenshot API.** The MCP
screenshot path returns 1372x873 JPEG — fine to look at, too soft to put in
front of judges. `shoot.mjs` drives headless Chrome at 1600x1000 with
`deviceScaleFactor: 2` and writes PNGs, so frames are 3200x2000. Node 22+
ships a WebSocket, so the CDP client needs no dependencies.

**Captions are PIL plates, not `subtitles=`.** This machine's ffmpeg is built
without libass, so the `subtitles` filter does not exist. It fails as a filter
*parse* error mentioning `force_style`, which reads like a quoting bug and
isn't — check `ffmpeg -filters | grep subtitles` before trying to escape
anything. `captions.py` renders each cue to a transparent PNG and `mux.py`
composites them as 45 timed overlays.

**Panels are matted, not cropped, to 16:9.** The verdict and audit cards are
roughly square. Slicing them to 16:9 either shrinks them or cuts the rules
off, so they are scaled and centred on the page's own background (`#050507`)
with the lower ~140px kept clear for captions. Full-width shots crop directly.

## The one thing to check before rebuilding

Section 6 claims "it released that one on its own." The autonomous panel's
counters are **in-memory** — any push to `main` redeploys Render, restarts the
watcher, and resets `releasedByCoach` to 0. The claim stays true (the on-chain
tx is permanent, and the runs table in section 3 shows it), but the panel on
screen will read 0 and undercut the line.

Run `../preflight.sh` first. It warns on exactly this, and fails outright if
`KH_WATCHER_LIVE` is unset — which would make the section 6 line false.
