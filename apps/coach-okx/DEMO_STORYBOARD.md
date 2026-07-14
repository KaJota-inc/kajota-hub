# OKX.AI Genesis Hackathon — ≤90-second demo storyboard

Target duration: **88 seconds** (2s safety margin under the 90s cap).
Rule of thumb: 4 beats × 22s each. Every beat pays off a specific criterion
OKX judges cite: (1) real-world use case, (2) discoverable ASP, (3)
on-chain settlement with proof, (4) agent-native UX (no human sign-off).

Real-voice VO recommended (Zama-style ban risk unclear here, but authentic
voice always wins on human-judged criteria — see [[feedback-realvoice-demo-video]]).

Companion X post uses the same 4 clips as a 4-tweet thread: intro → use
case → demo GIF → CTA.

---

## Beat 1 — "Where the ASP lives" (0:00 → 0:22)

**On screen:** OKX.AI marketplace search. Type "shopping" or "insight" —
Kajota Coach card appears in the results. Hover shows: name, "A2MCP",
per-call fee ($0.01 USDC), one-line description. Click through to the
Coach ASP profile page. ERC-8004 agent id + XLayer registration link
visible in the corner.

*Fallback if OKX.AI marketplace isn't publicly browsable during the
demo:* screen-cap the OKLink ERC-8004 identity contract read call
(`getAgent(agentId)` on XLayer), showing the same fields — proves the
identity is on-chain even without a UI.

**VO line (~5s, ~15 words):**
> "This is Kajota Coach, live on the OKX.AI marketplace as an A2MCP
> Agent Service Provider."

**On-screen text overlay:** "Registered ASP on XLayer (chain 195/196)"

---

## Beat 2 — "The real-world use case" (0:22 → 0:44)

**On screen:** Split-screen. Left: a buyer agent's terminal issuing a
plain-English request — "Give me a premium insight on my recent
purchases and wishlist opportunities." Right: the Coach `/coach/premium`
route responds with **HTTP 402** — the price tag (JSON body + PAYMENT-
REQUIRED header) is visible: amount, asset, network `eip155:195`,
facilitator URL.

**VO line (~6s, ~18 words):**
> "The buyer agent asks a shopping question. Coach answers with a
> forty-oh-two — an on-chain price tag, one cent USDC."

**On-screen text overlay:** "402 Payment Required — self-documenting
price tag"

---

## Beat 3 — "Settled on XLayer, no human sign-off" (0:44 → 1:10)

**On screen:** Buyer agent's CLI (`onchainos payment pay --payload ...`
or a hand-rolled equivalent) signs an EIP-3009 `transferWithAuthorization`
over $0.01 KJUSD and retries the POST. Coach hits `/verify` then
`/settle` on the facilitator (log line visible), receives the tx hash,
and returns **HTTP 200** with the premium insight body + settlement
object (`network`, `transaction`, `payer`, `settled: true`). Cut to
OKLink block explorer: the on-chain USDC transfer confirmed on XLayer
testnet, buyer → payTo address.

**VO line (~10s, ~28 words):**
> "The agent signs a one-shot authorization. The facilitator settles on
> XLayer in seconds. No wallet popup, no human sign-off — this is the
> agent-native payment rail OKX.AI is here to standardize."

**On-screen text overlays:** "Settlement: XLayer testnet" + tx hash in
monospace.

---

## Beat 4 — "The insight the buyer paid for" (1:10 → 1:28)

**On screen:** Zoom into the Coach response body. Show the actual
agentic output: 3-4 sentences citing real product names + prices from
the MongoDB tool calls (already in a demo dataset), then the [CARDS]
block rendered — one card for the recommendation, one for each buy-now
wishlist hit. Cut to the mobile app view (existing Coach client) showing
the same insight in-app for context, or skip and stay on the raw
response.

**VO line (~6s, ~17 words):**
> "And the buyer gets what they paid for — grounded, personalized
> insight from an agent that pays its own rent."

**On-screen text overlay:** "Kajota Coach on OKX.AI — kajota.io"

---

## Production checklist

- [ ] Reuse the `ffmpeg trim → PIL captions → adelay+amix VO` pipeline
      from [[feedback-demo-video-production]]. Single `filter_complex`,
      LOOP image inputs for overlays.
- [ ] Record VO first via macOS `say` for the timing pass, then re-record
      with real voice if hackathon rules allow (see the memory note on
      Zama's ban).
- [ ] Test on 1080p and 720p — OKX judges may re-encode.
- [ ] Terminal recordings via `charmbracelet/vhs` (see [[feedback-terminal-recording-vhs]]).
      Set `Sleep > runtime` in the .tape to avoid truncation.
- [ ] Grab the OKLink XLayer testnet block-explorer screencap AFTER the
      settlement fires so the tx has time to confirm.
- [ ] Keep total video runtime ≤ 88s — verify with `ffprobe -v error -show_entries format=duration -of csv=p=0 out.mp4`.

## X thread mirror

Tweet 1 (Intro, 260 chars):
> Kajota Coach is live on the OKX.AI marketplace — an A2MCP Agent Service
> Provider that gives you paid, deep-dive purchase insights. Every
> question settles a $0.01 USDC micropayment on XLayer. No wallet popup,
> no human sign-off. #OKXAI

Tweet 2 (Use case, 260 chars):
> Real problem: agentic shopping assistants need to buy tools from other
> agents — but nobody wants a wallet popup every 3 seconds. Coach
> answers HTTP 402 with an on-chain price tag; buyer agents sign one
> authorization and get their answer. Instant.

Tweet 3 (Demo GIF, 90-second clip attached):
> Watch it settle. Coach on OKX.AI → 402 → EIP-3009 sign → XLayer tx →
> insight delivered. All in under 6 seconds end-to-end. #OKXAI

Tweet 4 (CTA):
> Try it: [Coach ASP link on OKX.AI marketplace]. Source: [GitHub link].
> Judges — every on-chain claim above is verifiable on OKLink XLayer
> testnet at [contract addresses]. #OKXAI @OKX
