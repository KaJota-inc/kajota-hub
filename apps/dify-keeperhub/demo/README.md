# Demo video pipeline

Rebuilds `kajota-dify-keeperhub-demo.mp4` (1920x1080, 78s, silent) from a
live Dify instance. Nothing is mocked: every screen is captured from a real
run, and the one typeset card carries recorded tool output verbatim.

```bash
node shoot-dify.mjs ./frames-dify   # log in, capture the canvas + a Test Run
python3 cards.py                    # title / guard / close cards + caption plates
bash build-dify.sh                  # clips -> concat -> mp4
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
