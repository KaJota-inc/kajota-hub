# BUIDL 1 — Main track: Best Integration into a Live Project

**Status: ready to submit once the demo video is uploaded.**
Deadline **Sep 18, 12:00 CEST**. A BUIDL enters one track only — the bounty is
a separate BUIDL (see `BUIDL-2-bounty.md`).

---

## Name

**KeeperHub for Dify**

## Vision / tagline

Dify agents can decide anything. They cannot move value onchain reliably.
This plugin lets them — and shows what a transaction would do before anything
is signed.

## Category

Crypto / Web3 · AI Agents · Infra / API

---

## Required links

| field | value | verified |
|---|---|---|
| Source code | https://github.com/KaJota-inc/kajota-hub/tree/main/apps/dify-keeperhub | 200, public |
| Demo video | https://youtu.be/kq3OB3RNJiE | 200, public, 78s, 1080p |
| Transaction | https://eth-sepolia.blockscout.com/tx/0x4c316e389ad51ca7e8bf88e1d0f656215164b8ec1a11f8d21c00239ae7eb0335 | 200 |

---

## Form answer — which project did you integrate with, and what does it do?

**[Dify](https://github.com/langgenius/dify)** — 155k stars, self-hosted and
cloud, with a plugin marketplace and real deployed business users.

The integration is a Dify **tool plugin** that gives any Dify agent or
workflow three tools backed by KeeperHub:

| tool | moves value? | what it does |
|---|---|---|
| `simulate_call` | **never** | Evaluates a contract call through KeeperHub without signing or broadcasting. Safe for a model to call unsupervised. |
| `execute_call` | yes, gated | Executes a call. Requires `acknowledge_moves_value: true`; without it, **simulates and refuses**. |
| `run_workflow` | yes | Triggers a KeeperHub workflow a human already authored and reviewed. |

Dify users build agents and workflows that can read and decide anything, but
have no reliable path to moving value onchain. KeeperHub is that path. The
plugin's own contribution is the *shape* of the gate: the safe tool is the one
a model reaches for by default, and the dangerous one refuses and simulates
unless a human has explicitly acknowledged the specific call. The default
outcome of an ambiguous agent decision is a dry run, not a transaction.

It is built on **`keeperhub-mcp`**, KeeperHub's own published MCP kernel,
rather than a hand-rolled HTTP client — which is the strategy that repo states
explicitly: a shared framework-agnostic kernel with per-framework adapters
importing it.

## Form answer — which KeeperHub surfaces did you use?

- **MCP server** — the whole integration runs over it, via `keeperhub-mcp` (PyPI 0.1.0)
- **`execute_contract_call`** with `simulate: true` / `false` — the simulate-first primitive this plugin is built around
- **`execute_workflow`** — for `run_workflow`, with idempotency-key passthrough
- **`list_integrations`** — used for credential validation, deliberately: it needs a real session and org scope but touches no chain, so validating a key can never move value
- **Audit trail** — every run is attributable in KeeperHub's own execution record
- **Turnkey / EIP-7702 signing + gas sponsorship** — the executed transaction was signed by KeeperHub's keeper and its gas paid by KeeperHub's relayer, not the caller

Not used: CLI, x402, MPP.

## Form answer — testnet or mainnet?

**Testnet.** Ethereum Sepolia by default (chain `11155111`), and that default
is deliberate rather than incidental: a tool an LLM can reach should not have
mainnet as its path of least resistance. Mainnet is reachable by setting
`chain_id`, and there is nothing testnet-specific in the code.

## Form answer — what still breaks or is unfinished?

Candidly, and in order of how much it would bother me as a reviewer:

1. **Not packaged as a `.difypkg`, so it is installed in remote/debug mode.**
   The consequence is concrete: Dify refuses to export a workflow DSL while a
   plugin is remote — *"You used a remote plugin … please remove it first"* —
   so the example workflow ships as a raw graph JSON rather than a DSL you can
   import in one click. The official CLI is downloaded but runs silently on
   `--help` and `version`, and I did not get to the bottom of it.
2. **Not published to the Dify marketplace.**
3. **`run_workflow` confirms the trigger, not the outcome.** KeeperHub's
   `execute_workflow` returns once the trigger is accepted; the run continues
   server-side. The tool says so in its own output rather than implying
   completion, but a caller wanting the final transaction hash has to poll the
   audit trail themselves. A polling variant is the obvious next tool.
4. **The guard is per-call, not per-session.** `acknowledge_moves_value` gates
   one invocation. There is no spend cap, no rate limit, and no "this agent may
   execute at most N times per hour". Those belong in a policy layer.
5. **One tool parameter is awkward.** `abi` must be a JSON string because Dify
   passes every tool parameter as a string, so an agent composing a call has to
   embed escaped JSON. It works and the errors name the field, but it is not
   pleasant.
6. **Custom errors decode only when the caller's ABI carries the error
   definitions.** That is KeeperHub's behaviour, not a bug in the plugin, and
   an agent sending only the function fragment lands on the raw selector. The
   plugin surfaces the selector and says exactly what to add. I built an
   ABI-driven decoder for this and then deleted it once I confirmed it could
   never fire — when the ABI has the errors KeeperHub already decodes them, and
   when it doesn't there is nothing local to compute from.

## Form answer — contact

- Email: oluwaboriife@gmail.com
- X: @Oluwabori6
- GitHub: @KaJota-inc

---

## Description (the long field)

### What it is

A Dify tool plugin that makes KeeperHub the execution layer inside Dify.
Three tools, built on KeeperHub's own `keeperhub-mcp` kernel.

### The idea worth stealing

`simulate_call` passes `simulate: true` **unconditionally** — not as a default
a caller can override. `execute_call` refuses without an explicit
acknowledgement, and when it refuses it *simulates instead*, so the caller
sees the outcome it was about to sign for. An agent that reaches for the wrong
tool, or omits a flag, gets a simulation.

This is tested rather than asserted. `tests/test_guardrail.py` proves
`simulate` cannot be forced false and that every falsey spelling of the
acknowledgement — `false`, `"no"`, `""`, `None`, `0` — still refuses.

### Execution through KeeperHub

**[`0x4c316e38…eb0335`](https://sepolia.etherscan.io/tx/0x4c316e389ad51ca7e8bf88e1d0f656215164b8ec1a11f8d21c00239ae7eb0335)**
— `approve(escrow, 0)` on Sepolia test USDC, executed through the plugin's
`execute_call`.

Verified against a public RPC rather than taken from KeeperHub's response:
`status: SUCCESS`, block **11690913**, gas used **57,804**, one `Approval` log
emitted by the USDC contract — so state genuinely changed. Gas was paid by
KeeperHub's relayer (`0xa17cb6ad…`) via the EIP-7702 account.

The call was chosen deliberately: `approve` is permissionless and needs no
balance, so it can succeed from the keeper wallet, and an amount of `0` moves
nothing. The goal was a real state-changing transaction, not a transfer. No
private key was involved at any point — KeeperHub signs.

**Both halves of the guard ran in that same invocation:**

```
1. execute_call WITHOUT acknowledge_moves_value
   -> executed: false, simulated_instead: true
2. execute_call WITH acknowledge_moves_value
   -> executed: true, tx 0x4c316e38…eb0335
```

And both simulate outcomes, on the same contract shape:

| call | simulate result |
|---|---|
| `approve(escrow, 0)` — valid | `wouldRevert: false`, `success: true`, gas estimate `35862` |
| `release(settledDeposit)` — invalid | `wouldRevert: true`, `DepositNotPending(0xe713d5a3…)` |

No gas was spent discovering the second one. That is the whole argument.

### Reliability and observability

The engineering that mattered was one bug the live service surfaced.

**A successful simulation of a failing transaction arrives as HTTP 400.**
KeeperHub reports a would-revert dry run with a 400 whose body describes the
revert, and the MCP kernel turns any non-200 into an exception. Left alone,
the single most useful result — *"this would have failed, here is why"* —
reaches the workflow author as "the tool is broken". It is now recovered as
data, keyed on `status: "simulated"` in the body rather than on the status
code, so a **broadcast** failure still raises. That boundary is pinned by a
test.

The first version of that recovery also never fired, because it anchored its
JSON match to end-of-string and KeeperHub appends human guidance after the
body. There is a regression test carrying the real trailing prose.

Other non-happy paths handled: a `wfb_` workflow-builder key is rejected with
the reason rather than a bare 401, and masked in the message; `abi` and
`function_args` are parsed at the boundary with failures named after the field
the author typed; `run_workflow` takes an idempotency key so a retried Dify
node does not fire twice.

### Verified inside a real Dify instance

Not asserted — confirmed through Dify's own APIs:

| check | evidence |
|---|---|
| Plugin loads | `Installed tool: keeperhub` |
| Dify recognises it | `/tool-providers` lists `kajota/keeperhub/keeperhub`; `/plugin/list` shows `kajota/keeperhub:0.1.0@d0ec0ee…` |
| Validation runs **through this code** | a `wfb_` key rejects with a traceback through `provider/keeperhub.py:18`; a bogus `kh_` key rejects from `tools/_kh.py:69` after reaching KeeperHub |
| A real key is accepted | `{"result":"success"}` — meaning `_validate_credentials` made a live `list_integrations` call and it passed |
| A workflow runs it | `Start → Simulate through KeeperHub → End`, all nodes succeeded, `SUCCESS · 1.777s · 3 steps` |

The negative tests are the load-bearing ones: an accepted key proves nothing
on its own unless a bad key is refused.

### Developer experience

**38 tests, no network required** — they stub the KeeperHub call and assert on
what *would* have been sent, which is the only way to prove "simulate cannot
broadcast" without broadcasting. Includes `tests/test_plugin_spec.py`, which
validates the manifest and all three tool specs through **Dify's own pydantic
models** — the ones Dify runs on install — catching the failure a unit test
cannot: correct logic behind a manifest Dify refuses.

The demo video is rebuilt by a committed pipeline (`demo/`) that captures a
live Dify instance, so the video cannot drift from what the plugin does.

### Prior contribution to KeeperHub

Merged docs PR **[KeeperHub/keeperhub#1857](https://github.com/KeeperHub/keeperhub/pull/1857)**
(+80 −12, 3 files, reviewed by @joelorzet, merged by @suisuss) documenting the
web3 write-contract field-name traps.
