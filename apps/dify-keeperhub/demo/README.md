# Demo video pipeline

Rebuilds `kajota-dify-keeperhub-demo.mp4` (1920x1080, 78s, silent) from a
live Dify instance. Nothing is mocked: every screen is captured from a real
run, and the one typeset card carries recorded tool output verbatim.

```bash
python3 cards.py                    # title / guard / close cards + caption plates
bash build-dify.sh                  # clips -> concat -> mp4
```

`frames-dify/` and `cards/` are **committed**, so those two commands rebuild
the cut bit-for-bit (verified: same sha256, 78.000s, 1920x1080, 2340 frames)
with no Dify instance and no network. Re-capturing is a separate matter:

```bash
node shoot-explorer.mjs ./frames-dify   # e1-explorer — needs only the chain
node shoot-dify.mjs ./frames-dify       # d1/d2/d3/d4/d5 — needs a live Dify
```

## Why it is built this way

**Silent and caption-driven.** There is no voice track, so every claim has to
be legible on screen. Captions are burned as PIL plates because this ffmpeg
has no libass — `subtitles=` does not exist and fails as a filter *parse*
error mentioning `force_style`, which reads like a quoting bug and isn't.
Check `ffmpeg -filters | grep subtitles` before trying to escape anything.

**`Input.dispatchMouseEvent`, not `element.click()`.** Dify's "Test Run"
control does not respond to a synthetic `.click()` — React's handler never
fires. An earlier pass reported a successful click and produced four
byte-identical frames. The frames are the only honest signal here: if
consecutive captures have the same byte size, nothing happened.

**Poll the DOM, not the clock.** The run panel reports its outcome without
ever using the word "succeeded", so a predicate looking for it reads false on
a perfectly good run. Assert on the output JSON instead.

**ASCII in the cards.** The chosen face has no U+2192, so `→` renders as tofu.
`cards.py` includes a glyph check; keep card text inside the face's coverage.

## Frame provenance

Not every frame comes from `shoot-dify.mjs`, and a dry run of this pipeline
on 2026-09-17 is what surfaced that. Two of the five it consumes do not:

| frame | produced by | reproducible today |
|---|---|---|
| `d1-canvas` | `shoot-dify.mjs` | needs a live Dify instance |
| `d4-tracing` | `shoot-dify.mjs` | needs a live Dify instance |
| `d5-detail` | `shoot-dify.mjs` | needs a live Dify instance |
| `d3-detail` | hand-capture during the session; `shoot-dify.mjs` writes `d3-result`, which is a **different image** | no — not scripted |
| `e1-explorer` | `shoot-explorer.mjs` | **yes** — the tx is permanent on chain |

`build-dify.sh` now asserts all inputs exist before rendering. Previously a
missing frame surfaced as an ffmpeg complaint about a nonexistent file,
which reads like a path bug rather than a gap in the capture scripts.

`shoot-explorer.mjs` regenerates *an* explorer frame, not a byte-identical
one — confirmation count and relative timestamp move. It asserts the page
reports success before writing, so it cannot quietly capture a frame that
claims a successful release from a page showing a revert.

## Never install the instance under /private/tmp

The Dify instance that produced the `d*` frames was installed into a session
scratchpad under `/private/tmp`. macOS's periodic cleaner deletes files there
by access time, and on 2026-09-17 it destroyed the instance:

- `nginx/` and `ssrf_proxy/` config templates and entrypoints were deleted.
  Docker then **recreated each missing bind-mount source as an empty
  directory**, so nginx tried to exec a directory and exited **127** — which
  looks like a broken image, not a deleted file. Two different files both
  reporting exactly 64 bytes is the tell: that is an empty dir's inode size.
- Postgres lost every directory that is empty at rest — `pg_notify`,
  `pg_stat_tmp`, `pg_logical/snapshots` — each recreatable with `mkdir`, and
  each failing one at a time so recovery looks tantalisingly close.
- Then `global/pg_filenode.map`, with most of `global/`. That maps catalog
  OIDs to physical filenodes and is written at initdb. It cannot be
  reconstructed. `base/` still held 12M of intact table data and the WAL said
  `redo is not required`, and none of that mattered.

`docker-compose.yaml` and `.env` went too, so the stack cannot even be
brought back up in place. Put the instance somewhere durable.

## What the cut shows

| shot | source | claim |
|---|---|---|
| title | card | the gap this fills |
| canvas | real capture | one KeeperHub node, "Cannot sign or broadcast" |
| tracing | real capture | the tool invoked, 1.592s |
| result | real capture | `signed: false`, `broadcast: false` |
| detail | real capture | `SUCCESS · 1.777s · 3 steps` |
| guard | card, recorded output | refuses without the acknowledgement |
| explorer | real capture | tx `0x4c316e38…`, block 11690913 |
| close | card | the chain end to end |

The guard card is the only typeset frame. It reproduces the actual recorded
output of two `execute_call` invocations with identical arguments, and is
labelled on screen as a transcript rather than presented as a screenshot.
