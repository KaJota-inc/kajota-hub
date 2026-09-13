# Draft comment for issue #2431 — plan correction

⚠️ **Not posted yet.** Needs your go-ahead: it's a public comment under
@KaJota-inc on KeeperHub's repo. Time-sensitive, because their policy says
"`accepted` accepts a specific plan" — if triage lands before this, they'd be
accepting the wrong one.

---

Correcting my own plan before triage reaches it — the reason and scope stand,
but the rule I proposed would not have been shippable.

I wrote that the rule should flag "a signer-routed node that has no
`web3Connection`". Implementing it against `staging` `f8c8f18` shows that
fires on almost every legitimate workflow, because omitting `web3Connection`
**is** the documented default: the field's own docs row gives `"default"` as
org policy, so a node that says nothing is asking for org policy, which is
correct and extremely common.

Two concrete pieces of evidence:

- `tests/unit/validate-workflow-structural.test.ts` asserts
  `warnings: []` with `toEqual` on its happy path, and **no fixture in that
  suite sets `web3Connection`**. The broad rule breaks your own test — not
  because the test is wrong, but because the rule was.
- Same for the seeded workflow data: nothing there sets it either.

So the signal isn't "routing is unset". It's narrower and, I think, more
useful: **the author tried to name a signer and used a key that doesn't route
one.**

Revised plan — warn only when `integrationId` is present **and**
`web3Connection` is absent:

- code `SIGNER_ROUTING_KEY_IGNORED: "signer-routing-key-ignored"` (additive)
- a pure `runSignerRoutingCheck(workflow, warnings)` called from
  `validateWorkflow` after `runAllowancePreflightCheck`
- `readNodeActionConfig` extended with the two fields, so there's still one
  config reader rather than a second that can drift from it
- covers `isWriteActionType` plus `BATCH_WRITE_CONTRACT_ACTION_TYPE`, so the
  sibling surfaces go together
- still a warning: `valid` stays `true`, only `warnings` grows

Silent for: neither key set; both set; `web3Connection` set to any of
`default` / `eoa` / `safe:<id>`; read nodes; empty-string or non-string
`integrationId`.

On the sibling question from my original scope — I've covered the three types
reachable through `isWriteActionType` and the batch constant. I still haven't
verified whether `resolveSigner` is invoked for the
`NON_CALLDATA_MUTATING_ACTION_TYPES` set (`approve-token`, `transfer-funds`,
`transfer-token`, the Tempo writes). If it is, the same warning should cover
them and I'll extend it — that's the one thing I'd still like you to confirm
rather than guess at.

Rule and tests are written and green against `f8c8f18` (my earlier message
said they already were; they weren't at the time — they are now):

https://github.com/KeeperHub/keeperhub/compare/staging...KaJota-inc:keeperhub-1:issue-2431

+338/-1 across three files, 20 tests, `biome check` clean. I ran the full unit
suite on clean `staging` and again with the change: identical failure counts
(37 files / 27 tests, pre-existing and environment-dependent), +20 passing,
which is exactly this file's test count.

Happy to open the PR on `accepted`, or to drop it if you'd rather solve this at
the node schema instead.
