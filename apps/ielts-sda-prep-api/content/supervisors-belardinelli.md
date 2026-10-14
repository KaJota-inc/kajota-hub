# Francesco Belardinelli — Imperial — Priority 8 (Backup)

*Treat fit as a hypothesis until the professor confirms it.*

## Official profile (verified source)

- **URL**: https://qrt-labs.imperial.ac.uk/projects (QRT 2027-FB-1)
- **Verified on**: 2026-10-14 per workbook Verified Sources sheet
- **Contact**: use the QRT project page contact convention.
- **Project reference**: QRT 2027-FB-1 — Runtime Monitoring and Shielding
  to Synthesize Safe and Trustworthy RL Controllers.
- **Research themes**: runtime verification, shielding, safe reinforcement
  learning.

## Thesis-fit hypothesis

FB-1's runtime-shielding framework maps onto the *bounded autonomy* primitive
in principle — the shield decides whether an action proposed by the
controller is safe to execute. Payflow's adversarial verifier downgrading
unsafe retry strategies to `status_query` is the same primitive expressed
without the RL framing.

**However**, FB-1 is RL-centric, and the thesis is LLM-triager-centric.
The Risk Register names this as "potential scope mismatch: RL controller
focus may not map directly to inference routing." Honest reading: FB-1 is
a backup, not a primary. Approach only if SD-2 and HF-1 both close.

## Primitive(s) hit

- [ ] Cost-aware inference
- [x] Bounded autonomy *(central primitive — shield IS bounded autonomy —
      but the RL framing is a scope mismatch)*
- [x] Verification *(central primitive — runtime verification is Belardinelli's
      home ground)*

## Open questions for the professor (prioritised)

1. For QRT 2027-FB-1, is the shielding primitive portable away from an RL
   controller to an LLM-driven inference router, or is the project scope
   strictly tied to RL action-selection?
2. Would you consider supervision of a thesis that uses your runtime-
   shielding formalism as the theoretical layer under an LLM-triager
   implementation (Payflow is the working prototype), or does that read as
   project-scope creep?
3. On the Risk Register point — if the answer is "scope-tied to RL", would
   you consider co-supervising with Demetriou (SD-2) where the shielding
   theory is the formal contribution and the application is non-RL?

## Status timeline (Sanguine momentum signal)

| Date | Stage | Action | Evidence file |
|---|---|---|---|
| 2026-10-14 | Shortlisted (Backup) | Card created; marked Priority 8 | this file |
| 2026-10-27 | Decision gate (planned) | Decide approach OR archive | append here |

## Risk notes (Melancholic honesty)

- **Scope mismatch is the dominant risk**. The Risk Register names it
  explicitly. Do not pitch FB-1 as primary thesis fit; it is the backup if
  SD-2 and HF-1 both close.
- **Primary vs secondary framing**: if approached at all, approach as "the
  shielding formalism is the theoretical contribution; the application is
  Payflow's non-RL triager" — not as "I am applying to FB-1 as a
  straightforward project candidate."
- **Approach only if actively needed**: this card does not require Day-1
  through Day-20 action. Revisit on 2026-10-27 (Day 14) only if SD-2
  supervision capacity has not materialised.

## Next action (dated)

- **2026-10-27 (Day 14)**: review FB-1 full description + 1 recent
  Belardinelli paper; decide pursue-as-backup OR archive. Append the
  decision to this card.
- **Trigger to approach**: SD-2 supervision capacity confirmed-closed by
  Demetriou AND HF-1 scope confirmed too narrow.
- **If approached**: `outreach-drafts/belardinelli.md` drafted with the
  explicit "non-RL application of your shielding formalism" framing to
  pre-empt the scope-mismatch concern.
