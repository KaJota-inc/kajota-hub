# VO cue sheet — read this over the screen (≈100s)

Word-for-word narration, timed to the scenes in `DEMO_SCRIPT.md`. Speak at a
calm, confident pace (~150 wpm). Pauses marked with «beat». Screen action in
[brackets].

---

**[0:00 — title card: "KaJota Coach · an AI agent that pays on Casper"]**

> "AI agents can reason — but they can't pay. Every paid action hits a human
> wall: sign up, get an API key, add a card. «beat» KaJota Coach doesn't. It
> settles its own payments — on Casper."

**[0:12 — terminal, run `node settle_once.mjs`]**

> "Here's the agent paying, live. It signs a transfer-with-authorization…
> «beat» the CSPR-dot-cloud facilitator verifies it — isValid, true… «beat as
> /settle runs» …and settles it on-chain — success, true. That's a real Casper
> transaction hash, right there."

**[0:38 — switch to the settlement tx on cspr.live]**

> "And here it is on the Casper explorer — processed, in a block. It's a real
> CEP-18 transfer, and the gas was paid by Casper's sponsored fee-payer. «beat»
> The agent moved value without ever holding native gas. That's the x402
> promise — working."

**[0:58 — switch to the KaJota USD contract page + deploy tx]**

> "And we didn't borrow a token. We deployed our own CEP-18 with
> transfer-with-authorization — KaJota USD — right here on testnet. Our
> contract, our mint, on-chain."

**[1:12 — quick cuts: `agent.py` (Casper MCP) + the mobile Premium screen]**

> "The Coach reaches Casper over MCP, and gates premium insights behind this
> x402 paywall. In the app, one tap settles on Casper. «beat» It's the whole
> Casper AI Toolkit in one product — x402, MCP, and our own Odra contract."

**[1:32 — title card: "Agentic AI + Payments on Casper · open-source"]**

> "An agent that earns, pays, and reads on-chain — and it's open-source, a
> reference the next Casper builders can copy. «beat» That's KaJota Coach, on
> Casper."

**[~1:45 — end]**

---

## Delivery notes
- The **/settle pause (~5–15s)** is your friend — let it breathe; say the
  "verify… settle…" line slowly so the hash lands right as you finish.
- Say the numbers as words: "isValid true", "success true" — don't spell hex.
- If you fluff a line, keep rolling; you can trim in edit. The only thing that
  must be clean is the terminal output and the explorer pages.
- Total runs ~1:45. If you need ≤90s, cut Scene 5 (the app beat) — Scenes 2–3
  (settle + explorer) are the ones that win.
- Optional cold open (before 0:00): 3s of the settlement hash on cspr.live with
  "This is an AI agent that just paid for itself on Casper. Here's how." — hooks
  hard, then rewind to the terminal.
