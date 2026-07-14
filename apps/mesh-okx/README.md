# KaJota Mesh Skill — operator README

On-chain escrow as a NANDA-discoverable skill. Agents read `SKILL.md`,
discover endpoints, lock / release / refund USDC on Ethereum Sepolia.

The agent-facing contract lives in [`SKILL.md`](./SKILL.md). The NANDA
Index record lives in [`agentfacts.json`](./agentfacts.json). This file
is for the human running the deploy.

## Local smoke test (no keys, no chain)

```bash
cd skill
python -m venv .venv && source .venv/bin/activate
pip install fastapi 'uvicorn[standard]' web3 pydantic pydantic-settings
MESH_DRY_RUN=true python -m kajota_mesh_skill.main &
curl -s localhost:8081/healthz | jq
curl -s localhost:8081/escrow/quote -H content-type:application/json -d '{"amount_usd": 42.5}' | jq
curl -s localhost:8081/escrow/release -H content-type:application/json -d '{"deposit_id": "0xabcd1234"}' | jq
```

In dry-run mode `release` / `refund` return synthetic tx hashes — useful
for offline demos.

## Live deploy (Render)

This repo's `render.yaml` adds a `kajota-mesh-skill` service alongside
the existing Coach + Concierge services. Env vars to set in the Render
dashboard (`sync: false` in the YAML):

| Key | What |
|---|---|
| `MESH_RPC_URL` | Sepolia HTTPS RPC (Alchemy / Infura / Ankr) |
| `MESH_RELEASE_AUTH_KEY` | Private key for the wallet authorised to call `release` and `refund` — must match `releaseAuth` on the deployed escrow (`0xe10cff...524a4`) |

Defaults baked into [`settings.py`](./kajota_mesh_skill/settings.py):

| Key | Default |
|---|---|
| `MESH_REGISTRY_ADDRESS` | `0xfce6bd68d8d6f858d447f537d206c1e354b44315` |
| `MESH_ESCROW_ADDRESS` | `0x599869cef2e4c52e2c9074caaf8f9fb0cb191776` |
| `MESH_USDC_ADDRESS` | `0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238` |
| `MESH_CHAIN_ID` | `11155111` |

## NANDA Index registration

Once deployed, register the service in the MIT NANDA Index using the
NANDA adapter SDK:

```bash
pip install nanda-adapter
# Provide the agentfacts.json URL once the service is up:
nanda register --agentfacts https://kajota-mesh-skill.onrender.com/agentfacts.json
```

(The `/agentfacts.json` route serves the file from the repo statically —
see TODO in `main.py` to wire it once the deploy URL is known.)

## NandaHack submission

Submit at https://nandahack.media.mit.edu/ on the *Skills* page with:

- **Hosted endpoint**: the Render URL
- **GitHub link**: this branch
- **SKILL.md**: this file's sibling
