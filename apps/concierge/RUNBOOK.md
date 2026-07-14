# RUNBOOK — land a real Casper settlement (clear the mandatory bar)

The buildathon **requires** "a working prototype on Casper Testnet with a
**transaction-producing on-chain component**." This runbook produces exactly
that: one real `transfer_with_authorization` settled on Casper, with a deploy
hash you can show. Follow **Path B** — it also deploys our own contract (a
second judging criterion) and, because minting hands the supply to the
deployer, the payer already has a balance (no WCSPR wrapping).

> ⏱️ Deadline: **Jul 7, 2026 23:59 UTC**. This is ~30–45 min of work once you
> have a funded key. Steps that touch a private key are **yours to run** — I
> never handle keys.

---

## 0. One-time prerequisites

1. **Casper Wallet account (secp256k1).** Create one, then export its secret
   key as PEM → save as `agent/scripts/payer.pem`.
   - Its public key → account hash is your **payer**. Derive the 00-prefixed
     account hash (Casper Wallet shows the account hash; prefix `00`).
2. **Fund it** at the faucet: <https://testnet.cspr.live/tools/faucet>
   (5,000 test CSPR — enough for the ~800 CSPR deploy + gas).
3. **Sponsored CSPR.cloud key** — the one you have (⚠️ **rotate the leaked one
   first** in the CSPR.cloud console).
4. Install deps once:
   ```sh
   pip install -e ./agent            # agent
   (cd agent/scripts && npm install) # signer + deploy tooling
   ```

---

## Path B — deploy our token, then settle on it (recommended)

### 1. Deploy Cep18X402 (our own CEP-18 with `transfer_with_authorization`)
```sh
cd agent/scripts
export CLIENT_PRIVATE_KEY_PATH=./payer.pem
export CLIENT_KEY_ALGO=secp256k1

node deploy_cep18x402.mjs            # DRY RUN — check the args + tx hash, no spend
node deploy_cep18x402.mjs --submit   # deploys (~800 CSPR); prints the package hash
```
On success it prints:
```
X402_ASSET=<package hash>
X402_ASSET_NAME="KaJota USD"
```
The deployer account is now minted the full supply, so it can pay.

### 2. Configure the paywall
Put these in `agent/.env.casper` (copy from `.env.casper.example`):
```
X402_FACILITATOR_API_KEY=<your rotated CSPR.cloud key>
X402_NETWORK=casper:casper-test
X402_ASSET=<package hash from step 1>
X402_ASSET_NAME=KaJota USD
X402_ASSET_DECIMALS=9
X402_MAX_AMOUNT=1000000                      # 0.001 KJUSD
X402_PAY_TO=00<merchant account-hash>        # a recipient; can be a 2nd account you own
X402_FEE_PAYER=81d557c9dcaadea97c34d79bf7b6af07aa9d760e5dd1aabf78a45fb39e072c3a
```
> `X402_ASSET_NAME` MUST equal the token `name` you deployed — the facilitator
> rebuilds the EIP-712 domain from it. `X402_PAY_TO` is the merchant; using a
> second account you control keeps the transfer clean (payer ≠ recipient).

### 3. Bring up the stack + settle
```sh
# terminal 1 — agent + bridge + Metro
export CLIENT_PRIVATE_KEY_PATH=./agent/scripts/payer.pem
npm run demo

# terminal 2 — drive one paid call end-to-end (probe 402 → sign → settle)
cd agent/scripts && node x402_client.mjs
```
`x402_client.mjs` prints the **on-chain deploy hash** of the settlement:
```
💰 On-chain settlement:  network=casper:casper-test  deploy hash=<HASH>
```
Verify it: `https://testnet.cspr.live/deploy/<HASH>` — **that hash is the
mandatory on-chain component.** Screenshot it for the demo.

### 4. (Optional) do it from the app
With the stack up, run `npm run ios`, tap **Premium Insight**, then **Pay &
settle** — the bridge signs, the facilitator settles, and the screen shows the
same deploy hash (tappable to cspr.live).

---

## Path A — quick alternative (shared WCSPR, no deploy)

Skip the contract deploy and pay in the shared testnet Wrapped CSPR. The catch:
your payer must **hold WCSPR**, so you first wrap CSPR → WCSPR (call the WCSPR
contract's `deposit` entrypoint, e.g. via CSPR.trade or `casper-client`). Then:
```
X402_ASSET=3d80df21ba4ee4d66a2a1f60c32570dd5685e4b279f6538162a5fd1314847c1e
X402_ASSET_NAME=Wrapped CSPR
```
…and run steps 3–4 above. This clears the mandatory transaction bar but does
**not** give us a deployed contract, so Path B scores better.

---

## What each step proves (map to the criteria)

| Step | Buildathon requirement it satisfies |
|---|---|
| Deploy Cep18X402 (Path B step 1) | **Working Smart Contracts** — functional deployed contract on testnet |
| The settlement deploy hash (step 3) | **Mandatory**: transaction-producing on-chain component |
| Agent + MCP + premium flow (already built) | Use of AI / Agentic Systems; Real-World Applicability |
| The mobile screen (step 4) | User Experience & Design |
| Repo + README (done) | **Mandatory**: open-source repo with docs |
| Demo video (record after step 3) | **Mandatory**: public walkthrough |

After step 3 you are **eligible**; after step 1 + the video you are
**competitive**. Then submit the BUIDL (`SUBMISSION.md`) on DoraHacks and push
for CSPR.fans votes (top-3 auto-advance to the Final Round).
