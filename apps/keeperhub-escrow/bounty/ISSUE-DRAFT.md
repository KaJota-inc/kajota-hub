# Issue draft — KeeperHub/keeperhub

⚠️ **Not filed yet.** Their [ISSUES.md](https://github.com/KeeperHub/keeperhub/blob/staging/ISSUES.md)
requires an issue with the `accepted` label before a behaviour-changing PR, and
"validation" is explicitly on the Required list. They triage within two working
days. Filing this is the gate for the $500 bounty PR.

---

**Title:** `validate_workflow passes a write-contract node whose signer routing is unset`

## Reason

`validate_workflow` reports a workflow as valid when its write-contract node
carries `integrationId` and no `web3Connection`, so the node has no sender
routing at all. Nothing in either validation tier looks at the field that
actually routes the signer.

**What happened.** Workflow `1pyjp0c15z2h558jld8pn` (org-scoped key, hosted
`app.keeperhub.com/mcp`), a single `web3/write-contract` node whose config is:

```json
{
  "actionType": "web3/write-contract",
  "abiFunction": "release",
  "network": "11155111",
  "contractAddress": "0x599869cef2e4c52e2c9074caaf8f9fb0cb191776",
  "integrationId": "xv7x4qalziyodoir6wyu4",
  "functionArgs": "[\"{{@trigger-1:HTTP.depositId}}\"]",
  "abi": "[{\"type\":\"function\",\"name\":\"release\", ...}]"
}
```

Both tiers pass it:

```
validate_workflow { workflowId }                  -> { "valid": true, "nodeCount": 2 }
validate_workflow { workflowId, deepCheck: true } -> { "valid": true, "nodeCount": 2 }
```

**What I expected.** At least a warning that sender routing is unset.

**What told me to expect it.** Two things in this repo, at `staging` `f8c8f18`:

1. `docs/plugins/web3.md:492` and `docs/api/workflows.md:194` both document the
   routing field by name — *"Web3 Connection | `web3Connection` | Sender
   routing: `default` (org policy), `eoa` (force the Turnkey EOA), or
   `safe:<safeWalletId>`"* — and `docs/api/workflows.md:173` shows
   `"web3Connection": "default"` in the canonical write-contract example.
2. `lib/safe/signer-resolver.ts:340` describes it as the *"Per-node Web3
   Connection field, as persisted on `WorkflowNode.config.web3Connection`"*,
   and `resolveSigner` reads only that field.

So `web3Connection` is the documented and implemented routing key. A node
setting `integrationId` instead has no routing, and `integrationId` is a real
key elsewhere — `lib/mcp/workflow-schema-constants.ts:74` documents it as
*"ID of the database integration"* — so it is plausible to reach for and
produces no complaint from any surface I could find.

**Confirmed in source, not just observed.** Neither tier references either
field. At `f8c8f18`:

```
grep -c web3Connection lib/mcp/validate-workflow.ts       -> 0
grep -c integrationId  lib/mcp/validate-workflow.ts       -> 0
grep -c web3Connection lib/mcp/validate-workflow-deep.ts  -> 0
grep -c integrationId  lib/mcp/validate-workflow-deep.ts  -> 0
```

**What it costs.** An agent-authored workflow validates clean and its signer
is decided by fallback rather than by anything in the workflow. My org has one
web3 integration, so the fallback happens to be the wallet I intended and the
misconfiguration is invisible. I cannot demonstrate a wrong-wallet broadcast,
because I have no second wallet to mis-route to — which is the point: the
failure is latent until an org adds one, and then it is a signing question
discovered at execute time rather than at validate time.

## Scope

**Covered.** A validation rule for nodes whose sender is resolved through
`web3Connection`.

**Checked and found consistent.** The docs (both tables agree), the MCP tool
descriptions, and `signer-resolver.ts`. The behaviour is only missing from the
validator — I am not proposing any change to routing, defaults, or
`signer-resolver.ts`.

**Siblings.** Deliberately raised as one question rather than one node type,
because the same config is signer-routed across more than write-contract:
`isWriteActionType` covers `web3/write-contract`, `web3/batch-write-contract`
and `*protocol-write*`, and `NON_CALLDATA_MUTATING_ACTION_TYPES` in
`lib/mcp/action-type.ts` lists `web3/approve-token`, `web3/transfer-funds`,
`web3/transfer-token` and the Tempo writes, with the comment that they *"do
genuinely broadcast a signed transaction from the org wallet."* I have not
verified which of those the resolver is invoked for — if the answer is "all
mutating nodes", the rule should cover that set, and I would rather you name it
than guess. **That list is my main open question.**

**Explicitly not covered.** Whether `integrationId` should be rejected by the
node schema outright. That is a separate, more breaking change and it can ship
independently of a validator warning, so by your one-issue test it is a
separate issue. Happy to file it if you want it.

**Not covered.** Anything about `execute_contract_call`'s simulate path, which
behaves correctly — a would-revert dry run reports `wouldRevert: true` and
decodes custom errors whenever the caller's ABI carries their definitions.

## Plan

Additive, in the existing idiom of `lib/mcp/validate-workflow.ts`:

1. New code in `lib/mcp/validate-workflow-codes.ts`:
   `MISSING_SIGNER_ROUTING: "missing-signer-routing"` — additive, per the
   file's note that adding a code is safe and renaming is not.
2. A pure `runSignerRoutingCheck(workflow, warnings)` called from
   `validateWorkflow` in spec order, flagging a signer-routed node that has no
   `web3Connection`, with `parameterPath` pointing at the node's config. Where
   `integrationId` is present it is worth naming in the message, since that is
   the specific confusion — but the rule is "routing is unset", not
   "`integrationId` is banned".
3. Tests alongside the existing validator tests.

**On severity:** I have drafted this as a **warning**, not an error, on the
grounds that an existing workflow relying on the fallback still runs correctly
today and should not start failing validation. If you would rather it be an
error, or gated behind `deepCheck`, say so and I will build that — per
ISSUES.md, I will treat a triage comment as the plan.

I can have the PR up the day this is accepted; the rule and its tests are
already written against `f8c8f18`.

---

## Notes for us (not part of the issue)

- Filed under @bori7. Prior merged contribution to this repo: PR #1857.
- **Timing risk:** two-working-day triage against a **Sep 18 12:00 CEST**
  deadline. File immediately. If it has not moved in two days, ISSUES.md says
  commenting is "the correct response, not nagging".
- If `accepted` does not land in time, the main-track Dify BUIDL is unaffected
  — this is a separate BUIDL for a separate bounty.
- Do **not** claim the docs describe `integrationId` as silently ignored. They
  do not. They document `web3Connection` as the routing field, which is the
  accurate and sufficient citation.
