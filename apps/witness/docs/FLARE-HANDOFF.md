# Flare Summer Signal — user-action handoff

Everything that can be built without your wallet is on `hackathon/flare-summer-signal`.
The steps below are the ones only you can run (fund wallets, get API keys, run deploys).
Once you've done them and pasted the tx hashes back, I'll record the demo and submit
the BUIDL on DoraHacks.

**Submission deadline: Aug 14 2026 20:59 UTC. Target: submit by Aug 12 (48h buffer).**

## 0 — Rotate the deployer key (from `[[feedback-credentials-in-chat]]`)

The `WITNESS_DEPLOYER_PK` in `.env` was pasted in chat in Jun and is considered
compromised. **Generate a fresh key** and use it as the deployer for all Flare +
Sepolia txs below. Keep the old address around for read-only tests only.

Suggested (in a private shell, do NOT paste output back into chat):

```bash
node -e "const w=require('ethers').Wallet.createRandom(); console.log('addr:', w.address); console.log('pk:  ', w.privateKey)"
```

## 1 — Fund two wallets

- **Sepolia ETH** to the deployer address — need ~0.02 ETH.
  Faucet options: [sepoliafaucet.com](https://sepoliafaucet.com/) · [google cloud faucet](https://cloud.google.com/application/web3/faucet/ethereum/sepolia) · [pk910 pow faucet](https://sepolia-faucet.pk910.de/).
- **Coston2 C2FLR** to the same address — need ~5 C2FLR.
  Faucet: <https://faucet.flare.network/coston2> (drips 100 C2FLR).

## 2 — Get an FDC verifier API key

Sign up at [Flare Developer Portal](https://flare.network/developers) and grab a
testnet verifier API key. Paste into `.env` as `VERIFIER_API_KEY_TESTNET=…`.
(The FDC verifier can 401 without one; the DA layer does not need one.)

## 3 — Fill `.env`

```bash
cd ~/Documents/kajota-witness
git checkout hackathon/flare-summer-signal
cp .env.example .env   # or merge new keys into your existing .env
```

Set these six variables:

```
WITNESS_DEPLOYER_PK=0x… (the fresh key from step 0)
SEPOLIA_RPC_URL=https://ethereum-sepolia-rpc.publicnode.com
COSTON2_RPC_URL=https://coston2-api.flare.network/ext/C/rpc
VERIFIER_API_KEY_TESTNET=…
# already defaulted in .env.example, but you can override:
VERIFIER_URL_TESTNET=https://fdc-verifiers-testnet.flare.network
COSTON2_DA_LAYER_URL=https://ctn2-data-availability.flare.network
```

## 4 — Local smoke test (no chain calls)

```bash
npm install
npm run flare:smoke
```

Expected: `OK FlareWitnessConsumer (FlareWitnessConsumer.sol): 4993 bytes, 9 ABI entries`
followed by the escrow line. If this fails, `npm i` again and rerun — solc + viaIR
occasionally memory-spikes on first run.

## 5 — Deploy to Sepolia + Coston2

```bash
npm run flare:deploy:sepolia   # deploys WitnessAnchor to Sepolia; writes WITNESS_ANCHOR_SEPOLIA to .env
npm run flare:deploy:coston2   # deploys FlareWitnessConsumer + FlareCosellEscrow; writes both addresses to .env
```

Paste the four `address:` lines back and I'll fill the "Verified contracts" table
in `docs/FLARE.md` + the memory memo.

## 6 — Produce a demo verdict and attest it

```bash
# 6a. Anchor a fake verdict on Sepolia (returns a tx hash)
npm run flare:anchor -- \
  --dispute 0x$(openssl rand -hex 32) \
  --root    0x$(openssl rand -hex 32) \
  --ruling  release_to_seller \
  --conf    8700

# 6b. Feed the Sepolia tx hash to the FDC attester
npm run flare:attest -- <sepolia-tx-hash-from-6a>
```

The attester runs a ~180-second FDC voting round, then submits the proof to the
consumer on Coston2. When it finishes, paste back:
- the Sepolia anchor tx hash
- the Coston2 `FdcHub.requestAttestation` tx hash
- the Coston2 `submitVerdict` tx hash

I'll thread those into the demo video and the BUIDL submission.

## 7 — When steps 5+6 are done, ping me

I'll:
- Record the ≤3-min demo (playbook Rule: hook in 10s, no live-demo, no AI voice — check Flare rules first)
- Fill `docs/FLARE.md` verified-tx table
- Draft the BUIDL text
- Coordinate the DoraHacks submission with you (final "Submit" click is yours)

## Failure modes to expect

| Symptom | Likely cause | Fix |
|---|---|---|
| `prepareRequest failed (401)` | Missing/invalid `VERIFIER_API_KEY_TESTNET` | Sign up on Flare dev portal; paste key |
| `DA not ready (404)` after 10 retries | Round hasn't finalized yet, or DA layer lagging | Rerun `flare:attest` with same tx hash — the request is already submitted, only DA fetch needs to complete |
| `zero balance` on Coston2 | Faucet hasn't dripped, or wrong wallet | Wait 2 min, or use a different faucet page |
| `FDC: invalid proof` on submitVerdict | Wrong sourceId or emitter address mismatch | Confirm `WITNESS_ANCHOR_SEPOLIA` in `.env` matches the address `flare:anchor` printed |
| `Stack too deep` on any Solidity compile | `viaIR` disabled somewhere | Should not happen — check `scripts/flare/compile.ts` still sets `viaIR: true` |
