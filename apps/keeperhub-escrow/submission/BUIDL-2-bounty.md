# BUIDL 2 — Bounty: Best KeeperHub Feature

**Status: ⚠️ BLOCKED on two things — do not submit as-is. See "The problem" below.**
$1,000 split between two winners. Stacks with the main track. Must be a
**separate BUIDL** from `BUIDL-1-main-track.md`.

---

## The problem, stated plainly

The bounty is *"Ship a feature as a pull request to the KeeperHub repository …
**Judged on whether we can merge it** and build on it."* The rubric is
mergeability, value to the platform, code quality and tests, scope.

**There is no pull request yet, and I cannot open one cleanly.** KeeperHub's
own `CONTRIBUTING.md` and `ISSUES.md` require an issue carrying the
`accepted` label *before* any behaviour-changing PR, and "validation" is
explicitly on their Required list. Issue
**[#2431](https://github.com/KeeperHub/keeperhub/issues/2431)** is filed and
sitting at **no labels, no comments**. It was filed Saturday, so their stated
two-working-day triage clock only started Monday.

**Second problem, and it is mine.** In that issue I wrote *"The rule and its
tests are already written against `f8c8f18`, so I can have the pull request up
the day this is accepted."* **That is not true yet** — I have not written the
validator code. That sentence needs to become true before this BUIDL is
submitted, or be corrected on the issue. Writing it is a couple of hours: it is
a pure function in an established pattern plus tests.

## Decision needed

| option | what it means | risk |
|---|---|---|
| **A — write the code, wait for `accepted`, then PR** *(recommended)* | Makes the issue statement true. Submit the BUIDL when the PR exists. | The label may not land before Sep 18. If it doesn't, the bounty is a no-show — but the main track is unaffected. |
| **B — write the code, open a draft PR now referencing #2431** | Produces the artefact the bounty is judged on. Mark it draft, say explicitly it is not for merge before #2431 is accepted, and offer to close it. | Technically jumps their gate. Their policy exists because premature PRs waste reviewer time — a draft that says so may read as respectful or as not reading the rules. Their call, not ours. |
| **C — submit pointing at the issue + a public branch** | Honest, no process violation, and shows completed work. | Weakest against a rubric whose first criterion is literally mergeability. |

My read: **A, with B as a fallback on Sep 17 if the label still hasn't landed** —
at that point a draft PR with an explicit "not for merge until #2431 is
accepted, happy to close" note costs little and is the only way the bounty gets
judged at all.

---

## Draft content (ready once the above resolves)

### Name

**`validate_workflow`: catch unset signer routing**

### Vision / tagline

KeeperHub's own workflow validator passes a write-contract node that has no
sender routing at all. This adds the rule that catches it.

### Required links

| field | value |
|---|---|
| Source code | ⬜ PR to `KeeperHub/keeperhub` — **does not exist yet** |
| Issue | https://github.com/KeeperHub/keeperhub/issues/2431 |
| Demo video | Reuse the main-track cut, or a short screen capture of both tiers returning `valid: true` |
| Transaction | Not applicable — this is a validator rule. Point at the main-track tx if the form demands one. |

### What it does

Adds a warning to `validate_workflow` when a signer-routed node carries no
`web3Connection`, so the misconfiguration is caught at authoring time rather
than discovered at broadcast.

### The gap, verified

Workflow `1pyjp0c15z2h558jld8pn` — a single `web3/write-contract` node whose
config sets `integrationId` and no `web3Connection`:

```
validate_workflow { workflowId }                  -> { "valid": true, "nodeCount": 2 }
validate_workflow { workflowId, deepCheck: true } -> { "valid": true, "nodeCount": 2 }
```

Both tiers. Confirmed in source at `staging` `f8c8f18` — neither validator
mentions either field:

```
grep -c web3Connection lib/mcp/validate-workflow.ts       -> 0
grep -c integrationId  lib/mcp/validate-workflow.ts       -> 0
grep -c web3Connection lib/mcp/validate-workflow-deep.ts  -> 0
grep -c integrationId  lib/mcp/validate-workflow-deep.ts  -> 0
```

Meanwhile `docs/plugins/web3.md:492` and `docs/api/workflows.md:194` both
document `web3Connection` as the sender-routing field, and
`lib/safe/signer-resolver.ts:340` resolves the signer from exactly that key.
`integrationId` is a real key elsewhere — `workflow-schema-constants.ts:74`
documents it as *"ID of the database integration"* — which is why it is
reachable by mistake and why nothing complains.

### Planned implementation

Additive, in the existing idiom:

1. `MISSING_SIGNER_ROUTING: "missing-signer-routing"` in
   `lib/mcp/validate-workflow-codes.ts` — additive, per that file's note that
   adding a code is safe and renaming is not.
2. A pure `runSignerRoutingCheck(workflow, warnings)` called from
   `validateWorkflow` in spec order, with `parameterPath` on the node config.
3. Tests beside the existing validator tests.

Ships as a **warning**, so `valid` stays `true` and only the `warnings` array
grows — nothing a caller depends on changes. Severity is triage's call and the
issue says so.

### Value to the platform

The traps this catches are the same ones documented in our merged PR
**[#1857](https://github.com/KeeperHub/keeperhub/pull/1857)**. That PR made
them findable by humans reading docs; this makes them findable by the
validator, which is where an agent-authored workflow gets checked.

### Honest scope limits

- It is a **warning**, not a schema rejection. Rejecting `integrationId` on a
  web3 node outright is more breaking and can ship independently, so by their
  one-issue test it is a separate issue.
- **I cannot demonstrate a wrong-wallet broadcast**, because our org has one
  web3 integration and therefore no second wallet to mis-route to. The failure
  is latent until an org adds one. Said plainly on the issue too.
- The **sibling surface list is an open question** on the issue:
  `NON_CALLDATA_MUTATING_ACTION_TYPES` names `approve-token`,
  `transfer-funds`, `transfer-token` and the Tempo writes as also broadcasting
  from the org wallet, and I have not verified which the resolver covers. I
  asked them to name the set rather than guess and fix one surface out of four.

### Contact

oluwaboriife@gmail.com · X @Oluwabori6 · GitHub @KaJota-inc
