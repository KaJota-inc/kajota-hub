# BUIDL 2 — Bounty: Best KeeperHub Feature

**Status: UNBLOCKED — ready to submit.** The PR exists and the issue was
accepted. $1,000 split between two winners, stacks with the main track, and
must be a **separate BUIDL** from `BUIDL-1-main-track.md`.

---

## Name

**`validate_workflow`: catch the signer-routing key that does nothing**

## Vision / tagline

An agent composing a KeeperHub workflow reaches for `integrationId` to pick a
wallet. No web3 step reads it. This makes the validator say so — and names the
field that does work, which the MCP surface never mentioned.

## Required links

| field | value |
|---|---|
| Source code / PR | **https://github.com/KeeperHub/keeperhub/pull/2538** |
| Issue | https://github.com/KeeperHub/keeperhub/issues/2431 (`accepted`, `confirmed`) |
| Demo video | Reuse the main-track cut, or skip — this is a validator rule, nothing renders |
| Transaction | Not applicable. If the form insists, point at the main-track tx `0x4c316e38…eb0335` |

## What it does

Adds a `validate_workflow` warning when a web3 write node carries
`integrationId`, and documents `web3Connection` on the MCP surface for the
first time.

## Mergeability — the bounty's first criterion

- **Issue-first, per their own policy.** #2431 filed, triaged, and carries
  `accepted` + `confirmed`. Their `ISSUES.md` says `accepted` is the signal to
  start; nothing was written against the repo before it landed.
- **Built to triage's plan, not mine.** @suisuss replaced my plan in a comment,
  and their policy says that comment is the plan. The PR is built to it.
- **Their checklist, honestly ticked.** Targets `staging`; title carries the
  issue number; `pnpm check` clean over 2,251 files; `pnpm type-check` 0 errors
  after `pnpm discover-plugins`; no secrets.
- **Additive and reversible.** A new warning code, one pure function, one
  extended config reader, one doc section. `valid` is unchanged — only the
  `warnings` array grows, which the codes file notes agents tolerate.

## Value to the platform

Two layers, and the second is the one triage asked for:

1. **The warning.** `integrationId` is inert on a `web3/*` node — zero
   references under `plugins/web3/` — and the editor never writes it there, so
   it is only reachable from the API or MCP surface. Exactly the path an agent
   is on.
2. **The root cause.** `web3Connection` appeared in **no doc under
   `docs/agent/`**, so nothing an agent reads named the field that actually
   routes the signer. That is what sends it to `integrationId`.
   `docs/agent/mcp-server.md` now documents the field and its three branches.

It also continues the merged docs PR
[#1857](https://github.com/KeeperHub/keeperhub/pull/1857): that made these
traps findable by humans reading docs, this makes one findable by the validator
and names the missing field on the agent surface.

## Code quality and tests

`+351/-1` across four files. **20 test cases**, and two of them exist to stop
the reasoning regressing:

- **warns for every `web3Connection` state** — absent, `""`, `"default"`,
  `"eoa"`, `"safe:<id>"`. This fails if the rule is ever re-keyed on absence,
  which was the loophole in my first draft: `parseWeb3Connection` maps
  missing, empty and `"default"` to one branch, so a rule keyed on absence
  could be silenced by writing a value that changes nothing.
- **the message never matches `/unset|unrouted|no sender routing/i` and never
  contains `"eoa"`** — because absence routes to org policy and `"eoa"` is the
  branch that bypasses it, so calling routing "unset" would point an agent at
  the bypass.

Plus: silent for a read node carrying the key, empty-string and non-string
values; one warning per offending node; all three write action types; and no
throw on malformed nodes.

Verification, baselined rather than asserted: 159 tests green across the five
validator suites, and the full `tests/unit` suite fails identically on clean
`staging` and on this branch (37 files / 27 tests, pre-existing and
environment-dependent).

## Scope and completeness

One change, deliberately. The warning and the doc are interdependent: the
warning tells an author to use `web3Connection`, and until this PR nothing on
the agent surface named that field.

Scoped to `isWriteActionType` rather than every mutating action, because
widening it warns on shipped templates — 12 seed workflows carry a
`web3/approve-token` node, and `validate-workflow-seed-workflows.test.ts`
holds a seed warning to be a false positive. No seed sets `integrationId`, so
this starts at zero.

**Left out on purpose:** the `protocol-write` config-drop triage identified
(`protocol-write.ts` not copying the field through while the editor renders
the selector for those actions). Real, and separable, so it gets its own issue
rather than riding along here.

## Contact

oluwaboriife@gmail.com · X @Oluwabori6 · GitHub @KaJota-inc
