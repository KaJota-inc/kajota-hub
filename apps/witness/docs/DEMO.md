# Kajota Witness — 3-minute demo script

For recording a screencast you can paste into the 0G Arena submission form. Target: **3 minutes flat.** Each numbered beat below = ~20-30 seconds of screen time.

---

## Before you hit record

- [ ] **Pre-warm the embedding model:** `cd ~/Documents/kajota-witness && npx tsx src/test-memory.ts` — first run downloads ~80MB of `@xenova/transformers` weights into `.cache/`. Skip this and your first live dispute will hang ~30s on the model pull.
- [ ] `cd ~/Documents/kajota-witness && npm run start` — wait for `kajota-witness listening on http://localhost:4022`
- [ ] Open `http://localhost:4022/ui` in a fresh browser tab
- [ ] Open `http://localhost:4022/verify` in a second tab (you'll switch to it at 02:25)
- [ ] Open `https://chainscan-galileo.0g.ai/address/0x2f1D3a881cfbeA01Cf55f3cAd125aA32Bf8cEC94` in a third tab (the WitnessAnchor contract page)
- [ ] Browser at ~125% zoom; window 1280×800
- [ ] Mute Slack/Discord/notifications
- [ ] Use Loom, OBS, or QuickTime (anything that captures system audio + mic)
- [ ] **DON'T have `.env` open in any visible editor window** — leaks the wallet PK

---

## Script

### **00:00 – 00:25 — The problem (25s)**

**Show:** Witness UI header.

**Say:**
> "In African micro-commerce, sellers chat with buyers across WhatsApp, Instagram, and direct DMs. When something goes wrong — wrong size shipped, partial order, pricing dispute — there's no record either side can prove. The platform owns the data. And when escrow fires, there's no neutral way to decide who's right."

### **00:25 – 00:50 — The Memory layer (25s)**

**Show:** Memory panel (left). Point at the cards.

**Say:**
> "Kajota Witness gives sellers cross-session memory they actually own. Every conversation is encrypted client-side and uploaded as a content-addressed blob to 0G Storage. Each card is one chat. Each CID is real."

**Action:** Click any chat's CID → opens 0G storagescan in a new tab. Pause for ~2s, return to demo tab.

**Say:**
> "Permanent on Galileo. Verifiable by anyone — even if Kajota disappears."

### **00:50 – 01:15 — Seed a new chat live, with one click (25s)**

**Show:** Click `+ Seed a new conversation` to expand the form. Click the **`sandals haggling`** preset button.

**Say:**
> "I'll create a brand new chat live. Click the preset, fill the form, hit Save to 0G."

**Action:** Click `Save to 0G →`. The stage progress shows it encrypting + uploading. ~20s. New card appears at top.

**Say:**
> "Encrypted client-side, uploaded, indexed for retrieval — twenty seconds. Now there's new evidence in the corpus."

### **01:15 – 01:55 — File a dispute, convene the jury (40s)**

**Show:** The Court panel on the right.

**Pre-prepared dispute claim to paste into the claim textarea:**
```
The seller said ₦6,000 for the sandals and refused to give me any discount.
```

**Action:** Paste claim, click "Convene jury".

**Say:**
> "The buyer's now claiming the seller wouldn't negotiate. We file the dispute. Witness pulls the most relevant chats from 0G — including the one we just seeded — runs three LLM jurors on Groq in parallel, and a judge synthesizes. Watch the progress."

**Action:** Stage progress visibly walks through: evidence → jury → storage → anchor. Each dot turns from amber-pulse to green-check.

### **01:55 – 02:25 — The verdict + on-chain anchor (30s)**

**Show:** Verdict card. Ruling badge, jury cards, evidence list, both 0G badges (emerald + indigo).

**Say:**
> "Release to seller, ninety percent confident. The prosecutor, defender, and neutral analyst each cite the exact chat where the seller dropped from six-k to five-point-five. The judge synthesizes."

**Action:** Scroll to the indigo "Verdict anchored on 0G Chain" badge.

**Say:**
> "And the verdict isn't just stored — it's anchored on 0G Chain. The on-chain root is byte-identical to the storage CID. Our WitnessAnchor contract records dispute ID, root hash, ruling, and confidence."

### **02:25 – 03:00 — Verify trustlessly (35s) ← the punchline**

**Action:** Copy the verdict CID from the green box. Switch to tab 2 (`/verify`). Paste into the field. Click **Verify ↓**.

**Say:**
> "And here's the part judges should care about. This page runs four independent cross-checks: it pulls the blob from 0G Storage, matches our local index, calls the on-chain anchor contract, and decrypts the content. **matchesStorageCid: true.** The chain root and the storage blob are byte-identical. No server trust required."

**Action:** Highlight the green ✓ on the `matchesStorageCid: true` line.

**Say:**
> "Three real 0G surfaces — Storage, Chain, deployed contract — each doing work the app can't run without. And the companion patch in kajota-coach is already live on a branch — every Coach turn fires into this same memory layer in production. Built end-to-end during the tournament window."

---

## Things NOT to do on camera

- Don't open `.env` — even glancing at it on screen leaks the wallet PK
- Don't refresh the UI mid-demo (loses the verdict card state)
- Don't run the seed → dispute back-to-back too fast — the upload takes ~20s and the dispute takes ~40s; the stage progress is the proof it's doing real work
- Don't apologize for latency — name it ("each upload is a real Galileo storage tx; this is what real settlement looks like")
- Don't paste the verdict CID into `/verify` until AFTER the dispute returns — the verify route reads the local index which only has the entry once the dispute write completes

## If something breaks during recording

- **Server crashes:** stop, restart `npm run start`, redo from the seed step (don't try to mid-stream recover)
- **Groq rate-limit:** wait 30s, retry the dispute (you'll see a 429 in the dispute card)
- **0G upload times out:** rare; redo the seed
- **No anchor badge:** check `.env` has `WITNESS_ANCHOR_ADDRESS=0x2f1D3a88…cEC94`

## Backup demo dispute prompts (if your first one verdicts weirdly)

> The seller agreed to 6 pairs but only sent 4.

> I paid ₦11k for trainers and they never arrived.

> The seller charged ₦14k but we agreed on ₦12k.

All three resolve cleanly against the seeded chats.

## Reference artifacts to mention on-camera

- WitnessAnchor contract: `0x2f1D3a881cfbeA01Cf55f3cAd125aA32Bf8cEC94`
- 0G Galileo (chainId 16602)
- Free testnet faucet: https://faucet.0g.ai
- Companion Coach integration branch: https://github.com/KaJota-inc/kajota-coach/tree/feat/witness-memory-integration (commit `1d7c570`)

## What to caption / pin in the video description

```
Kajota Witness — encrypted seller memory + AI jury on 0G Galileo.
Built in 36 hours for 0G Zero Cup Round 1.

Repo: https://github.com/KaJota-inc/kajota-witness
Contract: https://chainscan-galileo.0g.ai/address/0x2f1D3a881cfbeA01Cf55f3cAd125aA32Bf8cEC94

Stack: Node + TypeScript + Fastify + 0G Storage SDK + Groq llama-3.3-70b-versatile
Three 0G surfaces, each load-bearing: Storage (blobs) + Chain txs + on-chain commitment.
```
