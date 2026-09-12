# KeeperHub for Dify

**Move value onchain from a Dify workflow — and see what a transaction would
do before anything is signed.**

Dify users build agents and workflows. Those agents can read anything and
decide anything, but they cannot reliably move value onchain: nonces get
stuck, gas spikes, transactions fail silently, and nothing keeps a record.
[KeeperHub](https://keeperhub.com) is the execution layer for exactly that.
This plugin puts it inside Dify.

Built on **`keeperhub-mcp`**, KeeperHub's own published MCP kernel, rather
than a hand-rolled HTTP client. Their SDK strategy is explicit — a shared
framework-agnostic kernel with per-framework adapters importing it — so this
composes with that instead of duplicating it.

## The three tools

| tool | moves value? | what it does |
|---|---|---|
| `simulate_call` | **never** | Evaluates a contract call through KeeperHub without signing or broadcasting. Safe for a model to call unsupervised. |
| `execute_call` | yes, gated | Executes a call. Requires `acknowledge_moves_value: true`; without it, **simulates and refuses**. |
| `run_workflow` | yes | Triggers a KeeperHub workflow a human already authored and reviewed. Prefer this — the agent picks from a menu rather than writing the recipe. |

### The guarantee, and why it is structural

`simulate_call` sets `simulate: true` unconditionally — not as a default a
caller can override. `execute_call` refuses without an explicit
acknowledgement, and when it refuses it *simulates instead*, so the caller
sees the outcome it was about to sign for.

The point is the default: an agent that reaches for the wrong tool, or omits
a flag, gets a simulation. Nothing irreversible happens by omission. Chain ID
defaults to **Ethereum Sepolia (11155111)**, because a tool an LLM can reach
should not have mainnet as its path of least resistance.

This is tested rather than asserted — `tests/test_guardrail.py` proves
`simulate` cannot be forced false, and that every falsey spelling of the
acknowledgement (`false`, `"no"`, `""`, `None`, `0`) still refuses.

## Constraints we hit, and how they were solved

| constraint | resolution |
|---|---|
| **A successful simulation of a failing transaction arrives as HTTP 400.** KeeperHub reports a would-revert dry run with a 400 whose body describes the revert, and the MCP kernel turns any non-200 into an exception. Left alone, the single most useful result — *"this would have failed, here is why"* — reaches the author as "the tool is broken". | Recovered as data, keyed on `status: "simulated"` in the body rather than on the status code. A `broadcast` failure still raises, and that boundary is pinned by a test. |
| **KeeperHub appends human guidance after the JSON** (`Next step: …`). | The first parser anchored the JSON match to end-of-string and therefore never fired — the recovery silently did nothing. Now matched unanchored, with a regression test carrying the real trailing prose. |
| **Custom errors decode only if the caller's ABI carries the error definitions.** With the function fragment alone, KeeperHub returns `unknown custom error` and raw bytes; an agent composing a call from a prompt sends exactly that. | The plugin surfaces the 4-byte selector and states precisely what to add to the ABI. It does **not** pretend to decode: the missing input is the definition, not the computation. |
| **Dify passes every tool parameter as a string**, but `abi` and `function_args` must be real JSON. | Parsed at the boundary, with failures named after the field the author actually typed — `` `function_args` is not valid JSON `` beats a stack trace. |
| **A `wfb_` workflow-builder key is a valid KeeperHub key that cannot authenticate against MCP.** | The kernel can tell key kinds apart, so this is rejected with the reason rather than a bare 401 — and the key is masked in the message. |
| **A retried Dify node fires a workflow twice.** | `run_workflow` accepts an idempotency key and passes it through. |

### One thing we built and deleted

A pure-Python keccak-256 and an ABI-driven custom-error decoder — ~80 lines,
correct, tested against real selectors. Then the live check showed KeeperHub
already decodes custom errors whenever the ABI carries their definitions, and
when it doesn't there is nothing local to compute from either. The code could
never fire, so it was removed rather than shipped as depth. Recorded here
because the deletion is the honest result.

## Verified against the live service

Simulated `CosellEscrow.release(bytes32)` on Ethereum Sepolia
(`0x599869cef2e4c52e2c9074caaf8f9fb0cb191776`) against an already-settled
deposit:

```
function-only ABI  -> wouldRevert: true, revertSelector: 0x9cd29bc9, hint returned
ABI with errors    -> revertReason: DepositNotPending(0xe713d5a3…8f0f2d13)
both               -> status: simulated — nothing signed, nothing broadcast
```

The transaction would have reverted. No gas was spent finding that out, which
is the entire argument for simulating first.

## Development

```bash
uv sync
uv run pytest -q          # 30 tests, no network required
```

Tests stub the KeeperHub call and assert on what *would* have been sent —
the only way to prove "simulate cannot broadcast" without broadcasting.

## Verified inside a real Dify instance

Installed into Dify (self-hosted, full docker stack) over the plugin daemon's
remote-install path, and confirmed through Dify's own APIs rather than by
assertion:

| check | evidence |
|---|---|
| Plugin loads | `Installed tool: keeperhub` from the plugin runtime |
| Dify recognises the provider | `/tool-providers` lists `kajota/keeperhub/keeperhub`; `/plugin/list` shows `kajota/keeperhub:0.1.0@d0ec0ee…`, `runtime_type: remote` |
| Credential validation runs **through this code** | a `wfb_` key is rejected with a traceback through `provider/keeperhub.py:18`; a bogus `kh_` key is rejected from `tools/_kh.py:69` after reaching KeeperHub |
| A real key is accepted | `{"result":"success"}` — which means `_validate_credentials` made a live `list_integrations` call to KeeperHub and it passed |
| The reason reaches the user | *"This key starts with `wfb_`… MCP requires an organization key (`kh_`) from Settings → API Keys"*, surfaced as `ToolProviderCredentialValidationError` |
| Keys are not leaked | the same error masks it as `wfb_…beef` |

The negative tests are the load-bearing ones: an accepted real key proves
nothing on its own unless a bad key is refused, and both are.

## The transaction

Executed through this plugin's `execute_call` tool, on Ethereum Sepolia:

**[`0x4c316e389ad51ca7e8bf88e1d0f656215164b8ec1a11f8d21c00239ae7eb0335`](https://sepolia.etherscan.io/tx/0x4c316e389ad51ca7e8bf88e1d0f656215164b8ec1a11f8d21c00239ae7eb0335)**

Verified against a public RPC rather than taken from KeeperHub's own response:
`status: SUCCESS`, block **11690913**, gas used **57,804**, one `Approval` log
emitted by the USDC contract — so state genuinely changed. Gas was paid by
KeeperHub's relayer (`0xa17cb6ad…`) through the EIP-7702 account, not by the
caller.

The call was `approve(escrow, 0)` on Sepolia test USDC, chosen deliberately:
`approve` is permissionless and needs no balance, so it can succeed from the
keeper wallet, and an amount of `0` moves nothing. The point was to produce a
real state-changing transaction, not to move funds.

**Both halves of the guard ran in the same invocation:**

```
1. tool called WITHOUT acknowledge_moves_value
   -> executed: False, simulated_instead: True
   -> "Refused to execute: this call moves value onchain..."

2. tool called WITH acknowledge_moves_value
   -> executed: True
   -> tx 0x4c316e38…eb0335
```

And the paired simulations, on the same contract shape:

| call | simulate result |
|---|---|
| `approve(escrow, 0)` — valid | `wouldRevert: false`, `success: true`, with a gas estimate |
| `release(settledDeposit)` — invalid | `wouldRevert: true`, `DepositNotPending(0xe713d5a3…)` |

No gas was spent discovering the second one.

## Status

Testnet-first and honest about it: Sepolia by default, mainnet reachable by
setting `chain_id`. Not yet published to the Dify marketplace.

**Not yet done:** a Dify workflow that calls the tool end to end (tool
invocation goes through a workflow Tool node, not a console endpoint), and one
*executed* transaction to sit alongside the simulations.

Licence: Apache-2.0
