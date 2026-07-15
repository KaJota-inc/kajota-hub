# OKX.AI Genesis Hackathon — build & submit runbook

Deadline: **Thu Jul 17, 2026 22:59 UTC**. Ship for OKX internal review by
**Sun Jul 13** to leave 4 days of buffer for approval + resubmit.

The critical gating rule from HackQuest: *"If the ASP listing is not
approved or cannot go live, your hackathon submission will be deemed
invalid."* So the ASP going live on OKX.AI **is** the deliverable — the
Google Form + video are wrappers around it.

---

## User-side actions that block the build

Order them like this — each unblocks a downstream step.

- [ ] **Click "Start Register"** on https://www.hackquest.io/hackathons/OKXAI-Genesis-Hackathon
- [ ] **Apply for OKX Developer Portal API keys** — https://web3.okx.com/onchain-os/dev-portal
- [ ] **Fund a fresh EOA** with XLayer testnet OKB from https://web3.okx.com/xlayer/faucet.
      Export the private key as `DEPLOYER_PRIVATE_KEY` in `~/Documents/kajota-mesh-okx/.env`.
- [ ] **Verify** whether the OKX.AI marketplace lives on XLayer **mainnet only** (chain 196)
      vs. also accepting testnet (195) registrations. If mainnet-only, get real OKB (~5 OKB
      for identity deploys + fees) and small amount of real USDT for `--service fee`.
- [ ] After the ASP is live: **post the required X thread** with `#OKXAI`, ASP intro,
      use case, and demo/walkthrough. Save the URL — it goes in the Google Form.
- [ ] **Fill the submission Google Form** — https://forms.gle/mddEUagmDbyV37ws8

---

## Build steps (mostly automated in the two worktrees)

### 1. Deploy mesh escrow to XLayer testnet

Worktree: `~/Documents/kajota-mesh-okx` (branch `hackathon/okx-genesis`).

```bash
cd ~/Documents/kajota-mesh-okx
pnpm install
echo "DEPLOYER_PRIVATE_KEY=0x…" >> .env      # from faucet-funded EOA
pnpm --filter @kajota-mesh/contracts deploy:xlayer-testnet-with-mock
```

Outputs `packages/contracts/deployments/195.json` with `usdc`, `registry`,
`escrow`, and `releaseAuth` addresses. Deploys a fresh `MockUSDC` (called
"KaJota USD" on-chain) as the 6-decimal stablecoin so we don't depend on
XLayer's testnet USDT liquidity.

### 2. Deploy Coach ASP + Mesh SKILL to Render

Worktree: `~/Documents/kajota-coach-okx` (branch `hackathon/okx-asp`).

```bash
cd ~/Documents/kajota-coach-okx
git push -u origin hackathon/okx-asp
```

In the Render dashboard, create a new Blueprint from `render.yaml`. Set the
`sync: false` env vars in the dashboard:

**kajota-concierge-agent:**
- `GCP_PROJECT_ID` — your Vertex AI project
- `MONGODB_URI` — Atlas SRV URI (reuse from prior deploys)
- `X402_FACILITATOR_URL` — Coinbase CDP URL or self-hosted `coinbase/x402`
- `X402_PAY_TO` — `0x…` EOA on XLayer (the ASP's revenue address)
- `X402_ASSET` — the KJUSD address from `deployments/195.json` (`usdc` field)
- `X402_FACILITATOR_API_KEY` — if the facilitator requires a bearer token

Also mount `/etc/secrets/gcp-service-account.json` as a Secret File.

**kajota-mesh-skill:**
- `MESH_RELEASE_AUTH_KEY` — the deployer's private key (same one used for
   `pnpm deploy:xlayer-testnet-with-mock`; that account is `releaseAuth`)
- `MESH_ESCROW_ADDR`, `MESH_REGISTRY_ADDR`, `MESH_USDC_ADDR` — from
  `deployments/195.json`

After both boot, verify:
```bash
curl -s https://kajota-hub.onrender.com/coach-okx/ | jq
curl -s https://kajota-hub.onrender.com/coach-okx/coach/premium | jq
curl -s https://kajota-hub.onrender.com/mesh-okx/healthz | jq
```

Coach's `GET /coach/premium` should return a 402 with the XLayer payment
requirements — that's the "endpoint is live and self-documenting" proof
we cite in the submission.

### 3. Register the ASP on OKX.AI (via `onchainos` CLI)

Install the CLI (see `okx/onchainos-skills` README):

```bash
curl -sSL https://raw.githubusercontent.com/okx/onchainos-skills/main/install.sh | sh
```

Set OKX API keys in `.env` (from the Developer Portal application above):

```bash
export OKX_API_KEY="…"
export OKX_SECRET_KEY="…"
export OKX_PASSPHRASE="…"
```

Then:

```bash
# 1. Pre-flight: verify wallet has no existing ASP identity, capture consent.
onchainos agent pre-check --role asp

# 2. Upload the avatar (real file, no URL).
onchainos agent upload --file agent/assets/kajota-avatar.png

# 3. Register — the JSON body is in agent/asp-manifest.json.
onchainos agent create --role asp \
  --name "Kajota Coach" \
  --description "AI shopping concierge — paid deep-dive insights over your shopping history, settled per-call on XLayer via x402." \
  --picture <cdn-url-from-previous-step> \
  --service "$(jq -c '.services' agent/asp-manifest.json)"

# 4. Activate.
onchainos agent activate --preferred-language en-US
```

Then submit for OKX internal review through whatever surface the CLI or
Developer Portal exposes (verify at registration time).

### 4. Demo video (≤ 90 seconds)

Follow the [[feedback-demo-video-production]] pattern in memory:
- Clip 1: OKX.AI marketplace, Coach ASP visible in the search (or a mockup)
- Clip 2: Buyer agent hits `POST /coach/premium` — 402 shown
- Clip 3: Buyer agent retries with signed X-PAYMENT — 200 response with
  agentic insight visible, plus the XLayer tx hash overlaid
- Clip 4: OKLink block explorer showing the tx confirmed on XLayer

Real-voice VO ideally (see [[feedback-realvoice-demo-video]]) since OKX
judges likely score for authenticity.

### 5. X post + Google Form

Post on X — `#OKXAI` hashtag, 1-tweet intro + 1-tweet use case + 1-tweet
demo GIF. Save URL. Paste into https://forms.gle/mddEUagmDbyV37ws8.

---

## Category strategy

Aim for these prize categories in order of fit:
1. **Revenue Rocket** ($20K/10K/6K/4K) — SME merchant enablement pitch
2. **Finance Copilot** ($7.5K, 3×$2.5K USDT) — escrow-based trade finance angle
3. **Best Product** ($20K/10K/6K/4K) — general polish + real-world use case
4. **Social Buzz** ($10K, 10×$1K USDT) — depends on X post traction

Reuse Ignyte writeup framing (real-world SME use case + on-chain proofs)
for the narrative — that criterion maps directly.

---

## Guardrails

- **Do NOT touch** active work in `~/Documents/kajota-coach` (Ignyte),
  `~/Documents/kajota-nanda`, `~/Documents/kajota-coach-casper`, or
  `~/Documents/kajota-zama`.
- The x402 code path retargeted from Casper to XLayer lives in
  `x402_xlayer.py`; the Casper module + its tests still exist on this
  branch but are unimported by `server.py` — do not delete them (breaks
  the ability to cherry-pick the OKX branch back into Casper follow-ups).
- Mesh deployment truth (Jul 8 memory correction): only Sepolia +
  Arbitrum Sepolia have `deployments/*.json` on-disk. Do NOT cite Mantle
  Sepolia or Polygon Amoy addresses in the writeup unless we redeploy.
