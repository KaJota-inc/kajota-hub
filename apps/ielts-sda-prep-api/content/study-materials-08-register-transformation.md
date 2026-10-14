# Register Transformation — Engineer-Speak → Academic English

*Your single highest-leverage IELTS skill. As a strong engineer, your risk in the exam and the
viva is not thin vocabulary — it is **over-complexity**: dumping jargon in dense, clause-stacked
sentences that an examiner (or a non-specialist professor) can't follow. Band 8 and a good viva
reward the opposite: ideas made clear. This file trains the conversion.*

---

## The method — four moves

1. **Name the mechanism, not the jargon.** Say *what happens and why*, then attach the term once.
   "The system records the event only after the write succeeds" — *then* "this is idempotent
   processing," not the reverse.
2. **One idea per sentence.** Break clause-stacks apart. A band-8 speaker uses complex grammar for
   *nuance*, not for cramming three concepts into one breath.
3. **Lead with the why.** State the purpose before the implementation. Purpose is what a listener
   can hold onto; implementation is what they get lost in.
4. **For opinion prompts, use the hedge-and-trade-off frame.** *"It depends on…"* → name the two
   forces → resolve with a proportionality principle. This is exactly how high-band speaking and a
   good research answer both sound.

> **Litmus test:** could a smart person outside your field follow it on first hearing? If not,
> you've optimised for sounding clever over being understood — which costs you marks and credibility.

---

## Worked transformations

Each pair: ❌ engineer-dense → ✅ academic-clear. Read the ✅ versions aloud; they're the target register.

**1. Delivery semantics**
❌ "The consumer commits offsets after the DB txn to avoid inconsistent state."
✅ "The system should record the transaction only after the database operation has completed
successfully. This *reduces the risk* of acknowledging an event that was never actually processed."

**2. Idempotency**
❌ "We dedupe on an idempotency key with a sparse unique index so replays are no-ops."
✅ "Each operation carries a unique identifier, so that if the same request arrives twice — which
is normal in distributed systems — the second attempt has *no further effect*. The guarantee lives
in the database itself, not in application code, because that is the only place it cannot be raced."

**3. CAP / consistency**
❌ "Under partition you pick C or A; we went AP with eventual consistency on the cache."
✅ "When the network splits, a system must choose between *always answering* and *always answering
correctly* — it cannot do both. For data that can tolerate a brief delay, I favour availability and
let the copies *converge over time*; for a balance or a ledger entry, I would not."

**4. Fault tolerance**
❌ "We catch the embedding failure and fall back to full-text so it degrades instead of 500ing."
✅ "Rather than let the feature fail outright when one dependency is unavailable, the system falls
back to a simpler method that still returns a useful result. *A worse answer is preferable to no
answer* — that is graceful degradation."

**5. Agent reliability**
❌ "0.95^20 is ~0.36 so you need verification, bounded retries and a step cap."
✅ "Reliability *compounds*: if each step of a long task is ninety-five per cent reliable, a
twenty-step task succeeds barely a third of the time. So the engineering problem is not making the
agent clever — it is making a *long chain of steps dependable*, through verification at each step
and strict limits on how long it may run."

**6. Bounded autonomy**
❌ "Gate consequential actions behind a confidence/$ threshold, else route to a human."
✅ "The agent may act on its own for routine, low-stakes decisions, but anything above a certain
level of risk or value is *referred to a person*. The cost of a wrong automatic decision far
outweighs the cost of a short delay."

**7. The deterministic envelope (your thesis sentence)**
❌ "The LLM proposes, a policy+verification layer checks invariants, then execution; verification
scales with risk."
✅ "I would not allow the model to change the financial ledger directly. Instead, I would *separate
probabilistic decision-making from deterministic execution*: the agent proposes an action, and a
policy-and-verification layer checks it against authorisation rules and financial invariants before
anything happens. The amount of checking is then *proportional to the risk and consequence* of the
decision."

**8. Observability**
❌ "We emit per-stage spans so we can reconstruct the trace when it misbehaves."
✅ "The system records each step of its own reasoning and every action it takes, so that when
something goes wrong we can *reconstruct exactly why* — rather than simply observing that it did."

**9. Verification vs validation**
❌ "You can't formally verify the model so you verify the envelope and validate the core
empirically."
✅ "You cannot *prove* a language model correct, so I verify the parts that can be pinned down — the
deterministic safeguards and invariants — and I *validate the model empirically*, by measuring its
behaviour against carefully chosen test cases."

**10. Auditability**
❌ "The on-chain verdictRoot is byte-identical to the stored CID so it's tamper-evident without
trusting the server."
✅ "A fingerprint of each decision is stored publicly and matches the full record exactly, so that
anyone can later confirm the record *has not been altered* — without having to trust the system that
produced it."

**11. Evaluation**
❌ "LLM-as-judge for faithfulness but validate the judge against human labels or it's the same
failure dist."
✅ "You can use one model to grade another's answers, but only if you have first checked that its
judgements *agree with human experts*. Otherwise you are simply asking the system to mark its own
work."

**12. Security (prompt injection)**
❌ "Treat tool outputs as untrusted; a retrieved doc can carry an injection."
✅ "Anything the system reads from the outside world — even a document it retrieved itself — must be
treated as *untrusted input*, because it may contain instructions designed to hijack the model's
behaviour."

---

## The gold standard (memorise the shape, not the words)

> "I would not allow the model to directly mutate the financial ledger. Instead, I would separate
> probabilistic decision-making from deterministic execution. The AI agent could *propose* an
> action, but a policy and verification layer would evaluate that proposed action against
> authorisation constraints and financial invariants before execution. The amount of verification
> would then be *proportional to the risk and financial consequence* of the decision."

Notice: sophisticated ideas, plain words, one thought per sentence, and a principle at the end.
That is band-8 speaking, senior system-design communication, and a PhD-interview answer — all at once.

---

## Daily drill

Pick one engineer-sentence from your own work (a commit message, a design note), and run the four
moves on it. Say the ✅ version aloud twice. Over twelve weeks this converts your default register
from *dense* to *clear* — the difference between a 7.0 and an 8.0, and between a nervous viva and a
convincing one.
