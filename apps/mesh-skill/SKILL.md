# KaJota Mesh Escrow — SKILL.md

> On-chain USDC escrow for AI agents. Lock funds against a listing, release on
> proof of delivery, or refund — all on Ethereum Sepolia, no wallet keys
> required on the calling agent's side.

This file is what a calling agent reads to use the service end-to-end. No
other documentation, no human walkthrough. If the agent can follow this
SKILL.md and complete an escrow lifecycle, the service has done its job.

---

## What this service does

- **`/escrow/quote`** — convert a USD amount into USDC base units (informational).
- **`/escrow/deposit/{id}`** — read on-chain state for an existing escrow.
- **`/escrow/release`** — release escrowed USDC to the seller.
- **`/escrow/refund`** — refund escrowed USDC to the buyer.
- **`/healthz`** — service + chain liveness probe.

## What this service does NOT do

- It does not custody arbitrary wallets. The service holds a single
  *release-authority* key for the deployed escrow; the lock side requires
  the buyer to deposit directly on-chain (see "Locking funds" below).
- It does not advise on whether to release or refund. It executes; the
  decision lives in the calling agent.

## Authentication

The skill is currently **open** for the hackathon. Future versions will
gate `release` and `refund` behind a HMAC-signed request header.

## Stack

| Layer | Value |
|---|---|
| Chain | Ethereum Sepolia (chainId `11155111`) |
| USDC | `0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238` (6 decimals) |
| `CosellRegistry` | `0xfce6bd68d8d6f858d447f537d206c1e354b44315` |
| `CosellEscrow` | `0x599869cef2e4c52e2c9074caaf8f9fb0cb191776` |
| Explorer | https://sepolia.etherscan.io |

---

## Endpoints

### `GET /healthz`

Probe service + chain. No body.

```bash
curl -s https://<host>/healthz | jq
```

```json
{
  "ok": true,
  "mode": "live",
  "service_address": "0xe10cff27c99074cd44c64bed1b000226442524a4",
  "chain_id": 11155111,
  "extra": { "block_number": 9123456, "escrow": "0x5998...91776", "registry": "0xfce6...44315" }
}
```

`mode` is `"live"` when the service holds a funded key, `"dry_run"` when it
returns synthetic tx hashes (useful for local development).

---

### `POST /escrow/quote`

Convert human-readable USD to USDC base units. Pure compute — no chain call.

Request:
```json
{ "amount_usd": 42.50 }
```

Response:
```json
{
  "gross_amount_units": 42500000,
  "fee_amount_units": 0,
  "net_amount_units": 42500000,
  "currency": "USDC"
}
```

---

### Locking funds

Locking deposits USDC from the **buyer's** wallet directly into the
`CosellEscrow` contract on-chain. This SKILL.md service does not custody
buyer wallets; the buyer-side agent must:

1. Have a wallet with Sepolia USDC and ETH (for gas).
2. Approve `CosellEscrow` to spend USDC: `USDC.approve(escrow, grossAmountUnits)`.
3. Call `CosellEscrow.deposit(listingId, grossAmountUnits)` from that wallet.

The `Deposited` event emits a `depositId` the agent should retain — pass
it back to this SKILL via `/escrow/release` or `/escrow/refund`.

A reference implementation in TypeScript+viem lives at
[`apps/mobile` in this repo](../src/services/escrow); a Python+web3.py
helper is in [`mesh.py`](./kajota_mesh_skill/mesh.py).

---

### `GET /escrow/deposit/{deposit_id}`

Read on-chain state for a deposit.

```bash
curl -s https://<host>/escrow/deposit/0xabcd...1234 | jq
```

```json
{
  "deposit_id": "0xabcd...1234",
  "listing_id": "0x1111...2222",
  "buyer": "0xb000...",
  "seller": "0xa000...",
  "gross_amount_units": 42500000,
  "fee_amount_units": 0,
  "net_amount_units": 42500000,
  "status": "pending"
}
```

`status` is `"pending"`, `"released"`, or `"refunded"`.

---

### `POST /escrow/release`

Release escrowed USDC to the seller. Authorised by the service wallet
(matches `releaseAuth` on the deployed escrow). Agents call this once
they have verified delivery off-chain.

Request:
```json
{ "deposit_id": "0xabcd...1234" }
```

Response:
```json
{
  "deposit_id": "0xabcd...1234",
  "action": "release",
  "tx_hash": "0x9999...",
  "explorer_url": "https://sepolia.etherscan.io/tx/0x9999..."
}
```

---

### `POST /escrow/refund`

Refund escrowed USDC to the buyer. Authorised by the service wallet.
Use when delivery did not occur or both parties agree to cancel.

Same request / response shape as `/escrow/release`.

---

## End-to-end agent recipe

Pseudo-code an agent can follow using *only* this SKILL.md:

```python
# 1. Buyer side: deposit on-chain (signed by buyer's own wallet).
#    Resulting depositId comes from the Deposited event.
deposit_id = call_contract(
    CosellEscrow, "deposit", listing_id, gross_amount_units
)  # buyer's wallet signs

# 2. Off-chain: seller delivers; buyer-agent verifies.

# 3. Buyer agent (or release authority) hits the SKILL service:
resp = requests.post(f"{SKILL_URL}/escrow/release", json={"deposit_id": deposit_id})
print(resp.json()["explorer_url"])

# 4. Check final state:
state = requests.get(f"{SKILL_URL}/escrow/deposit/{deposit_id}").json()
assert state["status"] == "released"
```

---

## NANDA Index registration

This service is discoverable via the MIT NANDA Index. Its AgentFacts
record lives alongside this file at [`agentfacts.json`](./agentfacts.json).

---

## Source

GitHub: https://github.com/KaJota-inc/kajota-coach (branch
`hackathon/nanda-mesh-skill`, dir `skill/`).
