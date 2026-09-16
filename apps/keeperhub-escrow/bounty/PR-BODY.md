# PR body — ready to open, needs your go-ahead

Title: `fix: #2431 warn when a web3 write node sets integrationId`
Base: `KeeperHub/keeperhub` ← `KaJota-inc/keeperhub-1:issue-2431` (`6ddb999`)
Gate: **cleared** — #2431 carries `accepted` (also `confirmed`, `enhancement`).

⚠️ Opening it is a public PR on their repo under @KaJota-inc. Say go.

---

## Issue

Closes #2431

## What this changes

Adds a `validate_workflow` warning when a web3 write node carries
`integrationId`, and names `web3Connection` on the MCP surface.

Built to the plan in the triage comment, which replaced the one I filed. Two
things changed as a result, and both are load-bearing:

**The rule keys on `integrationId` being present, not on `web3Connection`
being absent.** `parseWeb3Connection` maps missing, empty and `"default"` to
one branch (`lib/safe/signer-resolver.ts:361`), so those three states resolve
to the same signer. A rule keyed on absence could be silenced by writing
`"default"` — a value that changes nothing. `integrationId` is read by no web3
step (zero references under `plugins/web3/`) and the editor never writes it on
a web3-credential action, so it is inert by construction there and only
reachable from the API or MCP surface.

**The message never calls routing "unset" and never names `"eoa"`.** Absence
routes to the org-policy resolver (`write-contract-core.ts:88-90`), and
`/api/execute/node` strips the field from caller config on purpose so a write
honours the org Safe and its active role. `"eoa"` is the branch that bypasses
that, so telling an agent its routing is unset would point it at the bypass.
Both properties are asserted, not just intended.

**Also names the field on the MCP surface**, per the last paragraph of that
comment: `web3Connection` appeared in no doc under `docs/agent/`, which is
what sends an agent to `integrationId` in the first place.
`docs/agent/mcp-server.md` now documents the field, its three signer branches,
that absence is org policy, and that `integrationId` is not read by any web3
step — next to the existing line saying there is no per-action `walletId`.

Not included: the `protocol-write` config-drop identified in triage
(`protocol-write.ts:366-381` not copying the field through, while
`action-config.tsx:1123` renders the selector for those actions). That is a
separate defect with a separate fix and it gets its own issue.

## Scope

One change. The rule and the doc are interdependent rather than separable:
the warning tells an author to use `web3Connection`, and until this PR nothing
on the surface an agent reads names that field — shipping the warning alone
would point at a field the docs never mention.

Scoped to `isWriteActionType` (write-contract, its batch variant,
protocol-write) rather than every mutating action. Widening it would warn on
shipped templates: 12 of the seed workflows carry a `web3/approve-token` node,
and `validate-workflow-seed-workflows.test.ts` holds a warning against a seed
workflow to be a validator false positive. No seed workflow sets
`integrationId`, so this rule starts at zero warnings across the seeds.

## How it was verified

`tests/unit/validate-workflow-signer-routing.test.ts`, 20 cases. The ones that
would catch a regression in the reasoning above:

- **warns for every `web3Connection` state** — absent, `""`, `"default"`,
  `"eoa"`, `"safe:<id>"`. This is the loophole test: it fails if the rule is
  ever re-keyed on absence.
- **the message never matches `/unset|unrouted|no sender routing/i` and never
  contains `"eoa"`** — fails if someone "helpfully" enumerates the accepted
  values in the warning.
- silent for: neither key set, a read node carrying `integrationId`,
  empty-string and non-string `integrationId`.
- warns once per offending node, and covers all three write action types.
- does not throw on malformed input: nodes not an array, a null node, a node
  with no `data`, a node with null `config`.

Commands run:

```
pnpm vitest run tests/unit/validate-workflow-signer-routing.test.ts \
  tests/unit/validate-workflow-structural.test.ts \
  tests/unit/validate-workflow-allowance.test.ts \
  tests/unit/validate-workflow-deep.test.ts \
  tests/unit/validate-workflow-seed-workflows.test.ts
  -> 5 files, 159 tests passed

pnpm check        -> 2251 files, 0 errors
pnpm type-check   -> 0 errors (after `pnpm discover-plugins`; without the
                     codegen, staging and this branch both report the same 10
                     errors from the ungenerated lib/step-registry and
                     lib/credential-map)
```

I also ran the full `tests/unit` suite on clean `staging` and on this branch:
37 files / 27 tests fail identically on both, so those are pre-existing and
environment-dependent rather than anything here.

## Screenshots

Nothing renders.

---

- [x] Targets `staging`
- [x] Title carries the issue number
- [x] `pnpm check` and `pnpm type-check` pass
- [x] No secrets, `.env` files, or credentials committed
