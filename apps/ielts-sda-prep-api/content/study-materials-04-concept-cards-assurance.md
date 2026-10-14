# Concept Cards D — Assurance: V&V, Safety, Explainability, Auditability

*The assurance vocabulary is what separates an engineer from a *researcher* in an AI-native
interview — and it's the heart of SE4AI. These four are also exactly where a financial-systems
background like yours is a differentiator, because regulated money forces assurance to be real.*

---

### 17. Verification and validation

**Definition.** Two distinct questions. *Verification:* are we building the system right — does it
meet its specification? *Validation:* are we building the right system — does it meet the user's
actual need? For AI, both are hard because the spec itself is often probabilistic.

**Lexis:** *verification vs validation*, *to meet the specification*, *fitness for purpose*, *a
probabilistic spec*, *formal methods*, *empirical validation*, *the oracle problem*.

**Model answer.** "I'd keep verification and validation firmly apart, because they answer different
questions. Verification asks whether we built the thing *right* — does it conform to its
specification. Validation asks whether we built the *right* thing — does it actually serve the
need. Classical software lets you verify against a crisp spec, sometimes even formally. AI breaks
that, because the specification is itself fuzzy — 'give a helpful, faithful answer' isn't something
you can prove. So verification shifts toward the parts you *can* pin down — the deterministic
guardrails, the invariants — while validation becomes heavily empirical: gold-sets, human
evaluation, online metrics. There's a deep challenge lurking here, the oracle problem: for many AI
outputs, you don't have a cheap way to know the right answer, which is precisely what makes testing
them a research question."

**Grounded in your work.** "I verify the *invariants* formally even when I can't verify the model —
in Mesh, I can't prove the agent reasons correctly, but I can prove, with tests, that funds can
never be locked forever and the operator can't rotate itself."

**Be ready for:** *"Can you ever formally verify an LLM system?"* → You verify the deterministic
envelope around it, not the model; the model you validate empirically. Hybrid assurance.

---

### 18. Safety and reliability

**Definition.** *Reliability:* the system does what it should, consistently, over time.
*Safety:* the system doesn't do what it must never do, even when it fails. Safety is about bounding
the worst case; reliability about raising the average.

**Lexis:** *the worst case vs the average case*, *to bound the downside*, *a safety invariant*,
*fail-safe vs fail-operational*, *defence in depth*, *a kill-switch*, *graceful degradation*.

**Model answer.** "I draw a sharp line between reliability and safety. Reliability is about the
average case — the system doing its job consistently. Safety is about the *worst* case — guaranteeing
the system never does the catastrophic thing, even while failing. The two need different tools.
Reliability you buy with redundancy, retries, good testing. Safety you buy with hard constraints
that hold *regardless* of the model's behaviour — a spending cap, a kill-switch, an invariant the
code enforces no matter what the LLM proposes. I lean heavily on defence in depth: multiple
independent layers, so that no single failure — a hallucinated action, a compromised key — reaches
the catastrophic outcome. In a financial context especially, I'd rather the system fail *safe* and
stop than fail *operational* and keep moving money."

**Grounded in your work.** "This is literally what I built in Kajota Shield — a per-agent spend
mandate, a kill-switch, and a fraud check in a single deterministic `checkAndSpend`, so the agent's
autonomy is bounded by constraints it cannot talk its way past."

**Be ready for:** *"Fail-safe or fail-operational for a payments agent?"* → Fail-safe by default;
the cost of an unsafe action in money movement dominates the cost of a halt.

---

### 19. Explainability

**Definition.** The degree to which a human can understand *why* an AI system produced a particular
output — through transparent reasoning traces, cited sources, feature attribution, or inherently
interpretable designs.

**Lexis:** *to surface the reasoning*, *feature attribution*, *a rationale / decision trail*, *post-
hoc vs intrinsic interpretability*, *source attribution*, *a glass-box vs black-box model*, *to
justify a decision*.

**Model answer.** "Explainability is the bridge between a model's decision and a human's trust in
it — and in regulated domains it's not optional, it's a requirement. There's a useful distinction
between *intrinsic* interpretability, where the model is transparent by construction, and *post-hoc*
explanation, where you reconstruct a rationale after the fact — feature attribution, say, or in the
LLM world, citing the retrieved sources a decision rested on. I'm somewhat sceptical of post-hoc
explanations that are really just plausible stories, so where stakes are high I prefer to *ground*
the decision in traceable evidence rather than ask the model to narrate its own reasoning, which it
may confabulate. The question I keep asking is: if this decision were challenged, could we show,
concretely, what it was based on?"

**Grounded in your work.** "In Witness, the verdict carries its evidence CIDs and all three jurors'
arguments — so the explanation isn't the model's self-narration, it's the actual traceable material
the decision rested on."

**Be ready for:** *"Isn't a model's explanation of itself enough?"* → No — LLMs can confabulate a
convincing rationale unrelated to the true cause; ground explanations in evidence, not narration.

---

### 20. Auditability

**Definition.** The ability to reconstruct, after the fact, exactly what a system did and why —
a tamper-evident record of inputs, decisions, actions, and actors, sufficient for compliance,
forensics, and accountability.

**Lexis:** *a tamper-evident record*, *an immutable audit trail*, *to reconstruct after the fact*,
*provenance*, *non-repudiation*, *a system of record*, *who did what, when, and why*.

**Model answer.** "Auditability is explainability's stricter, colder cousin — it's not about
understanding a decision in the moment, but about being able to *prove*, later and to a third party,
exactly what happened. For that you need an immutable, tamper-evident record: the inputs, the
decision, the action taken, and the actor responsible, all captured such that nobody can quietly
rewrite history. In regulated finance this is foundational — non-repudiation and provenance aren't
nice-to-haves, they're what let you answer a regulator or settle a dispute. With autonomous agents
it becomes *more* important, not less, because when a system acts on its own, the audit trail is the
only way to assign accountability for what it did."

**Grounded in your work.** "Witness is essentially an auditability machine — the verdict's root hash
is anchored on-chain, byte-identical to the stored record, so anyone can verify after the fact that
the evidence hasn't been altered, *without trusting my server*. That's tamper-evidence by
construction."

**Be ready for:** *"Explainability vs auditability — same thing?"* → No. Explainability is for
understanding now; auditability is for proving later. One helps the user, the other the regulator.
