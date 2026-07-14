# KaJota Coach × Casper — demo script (~100s, real on-chain)

Goal: show an AI agent paying for its own work on Casper — with a **real,
live settlement** and its transaction on the explorer. No slideware, no mocks.

Everything here is already deployed and working; you're just recording it.

## Real assets to have on screen
- **Contract (KaJota USD, our own CEP-18):**
  https://testnet.cspr.live/contract-package/354ca0ad7ef8c97a02b195a1f39e96908fd3bf20d6ec4255850d05f1784fb404
- **Deploy tx:**
  https://testnet.cspr.live/transaction/df0847848800502b1b6919c1ad9a2dc0845c309006382b21ef8ad759d7c4171a
- **Settlement tx** (the agent micropayment):
  https://testnet.cspr.live/transaction/88c4153e211011915b7b7bc2af718ada2b506266512701a7488a80f77a58b4a3

## Pre-record setup
1. **Rotate** the CSPR.cloud key first; put the new one in `agent/.env.casper`.
2. Open 3 browser tabs: the contract page, the deploy tx, the settlement tx (above).
3. Terminal ready in `agent/scripts`, env loaded:
   ```sh
   cd agent/scripts && set -a; . ../.env.casper; set +a
   export CLIENT_PRIVATE_KEY_PATH=./payer.pem CLIENT_KEY_ALGO=secp256k1
   ```
4. (Optional, for the app beat) iOS sim running the Premium screen, and
   `npm run demo` up if you want the mobile pay shown.

---

### Scene 1 — Hook (0:00–0:12)
**On screen:** title card → "KaJota Coach · an AI agent that pays on Casper."
**VO:** "AI agents can reason — but they can't pay. KaJota Coach can. It settles
its own micropayments on Casper with x402: no card, no account, no human."

### Scene 2 — The live settlement — MONEY SHOT (0:12–0:45)
**On screen:** run it, let the output stream:
```sh
node settle_once.mjs
```
**VO:** "Here's the agent paying, live. It signs a transfer-with-authorization,
the CSPR.cloud facilitator verifies it — `isValid: true` — then settles it
on-chain — `success: true` — and hands back a real Casper transaction hash."
**Highlight (freeze/zoom):**
`/verify → isValid:true` … `/settle → success:true, transaction:88c4153e…`

### Scene 3 — Proof on-chain (0:45–1:05)
**On screen:** switch to the **settlement tx** browser tab (88c4153e…).
**VO:** "That's it on the Casper explorer — processed, in a block. It's a real
CEP-18 transfer, and the gas was paid by Casper's sponsored feePayer. The agent
moved value without ever holding native gas. That's the x402 promise, working."
**Highlight:** Status = processed · block 8394190 · the transfer entry.

### Scene 4 — Our own contract (1:05–1:22)
**On screen:** switch to the **contract page** (KaJota USD) + the deploy tx tab.
**VO:** "And we didn't borrow a token — we deployed our own CEP-18 with
transfer-with-authorization, KaJota USD, right here on testnet. Contract and
mint, on-chain."

### Scene 5 — The agentic layer (1:22–1:38)
**On screen:** quick cuts — `agent.py` (Casper MCP toolset) + `x402_casper.py`,
then the **mobile Premium screen** (the 402 price tag → Pay).
**VO:** "The Coach reaches Casper over MCP and gates premium insights behind
this x402 paywall — in the app, one tap settles on Casper. It's the whole
Casper AI Toolkit in one product: x402, MCP, and our own Odra contract."

### Scene 6 — Close (1:38–1:48)
**On screen:** title card → "Agentic AI + Payments on Casper · open-source."
**VO:** "An agent that earns, pays, and reads on-chain — and it's MIT-licensed,
a reference the next Casper builders can copy. That's KaJota Coach on Casper."

---

**Notes**
- Scene 2 is 100% live and reproducible — it settles a fresh tx every run (each
  gets its own hash). Record it once clean; if you want, use the freshly printed
  hash for Scene 3 instead of the pre-opened one.
- If a run ever prints a non-success (e.g. facilitator hiccup), just re-run —
  the payer holds 1M KJUSD, so it settles.
- Keep it tight; the settlement + explorer beats (Scenes 2–3) are what win. Lead
  with them if you need to cut for time.
