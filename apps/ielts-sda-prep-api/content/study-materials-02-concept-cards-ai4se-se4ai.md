# Concept Cards B — AI4SE & SE4AI

*The two directions of the field you're positioning into. Jiang's York group names exactly this
split; it's also live at TUM's SEAI group and elsewhere. Know both, and know which way your own
research points (both — see the research-direction file).*

---

### 7. AI4SE — AI for Software Engineering

**Definition.** Using AI, chiefly LLMs, to *do* software engineering: code generation, automated
testing and bug reproduction, program repair, code review, and mining software repositories.

**Lexis:** *to augment the developer*, *automated program repair*, *code synthesis*, *bug
localisation*, *repository mining*, *a productivity multiplier*, *developer-in-the-loop*.

**Model answer.** "AI4SE is about turning the tooling of software engineering over to AI — code
synthesis, automated testing, bug reproduction, program repair, even mining repositories for
patterns. The promise is a genuine productivity multiplier, and in narrow tasks it's already real.
But I'd temper the enthusiasm: the model augments the developer, it doesn't replace the judgment,
because generated code *inherits* whatever the model misunderstood. My instinct is to treat an LLM
coding assistant as a very fast, slightly unreliable junior — enormously useful, provided there's a
developer-in-the-loop and a test suite that the human, not the model, is accountable for."

**Grounded in your work.** "I use AI4SE tooling daily across the Kajota repos — but a lesson I've
internalised is that a faithful port of code inherits the source's *bugs*, so I validate generated
or ported code on live data for the exact item reported and a sibling that must keep working."

**Be ready for:** *"Where does AI4SE break down today?"* → On tasks needing whole-system context
or long-horizon correctness; it shines locally and struggles globally.

---

### 8. SE4AI — Software Engineering for AI systems

**Definition.** Applying software-engineering discipline *to* AI systems: architecture, testing,
reliability, security, deployment, and monitoring of systems whose core is a learned model.

**Lexis:** *to engineer around a learned component*, *the AI lifecycle*, *reproducibility*, *data
and model versioning*, *drift*, *testability of non-determinism*, *production-grade AI*.

**Model answer.** "SE4AI flips the arrow: instead of AI doing software engineering, it's software
engineering done *properly* for AI systems. And it matters enormously, because the thing that makes
an AI prototype thrilling — a probabilistic, data-dependent core — is exactly what makes it hard to
test, version, deploy, and keep reliable. So SE4AI concerns itself with the unglamorous scaffolding:
how you version data and models together for reproducibility, how you test a non-deterministic
component, how you detect drift, and how you deploy without a silent regression. I'd argue this is
where most real-world AI value is won or lost — the model is the easy part; the engineering around
an expensive, unpredictable dependency is the hard part."

**Grounded in your work.** "Most of my AI systems are really SE4AI stories — the Redis-optional
dedup, the bounded retry in Pulse, the latency instrumentation in Witness. None of that is the
model; it's the engineering that makes the model safe to depend on."

**Be ready for:** *"How do you test something non-deterministic?"* → Gold-sets with tolerance
bands, property-based assertions on invariants, and LLM-as-judge validated against human labels —
not exact-match.

---

### 9. AI-generated code and its risks

**Definition.** Code produced by an LLM, carrying distinctive risks: plausible-but-wrong logic,
inherited vulnerabilities, licence contamination, and over-trust because it *reads* fluently.

**Lexis:** *plausible but incorrect*, *to read fluently yet fail subtly*, *inherited
vulnerabilities*, *over-reliance / automation bias*, *licence contamination*, *a false sense of
correctness*.

**Model answer.** "The danger with AI-generated code is precisely that it reads *fluently* — it
looks like something a competent engineer wrote, which lulls you into trusting logic that is subtly
wrong. Beyond correctness, there are quieter risks: the model may reproduce an insecure pattern it
saw a thousand times in training, or introduce a dependency with an incompatible licence. The
through-line is automation bias — the human stops reviewing because the output *looks* right. So my
rule is that generated code earns no more trust than a pull request from a stranger: it must pass
the same review and the same tests. Fluency is not correctness, and the gap between them is where
the bugs live."

**Grounded in your work.** "I've seen this concretely — a reverted auth fix in my backend left a
JWT signature *unverified* while the code still looked like it was checking things. It parsed the
token, checked the algorithm and audience, and then quietly didn't verify the signature. Fluent,
and wrong."

**Be ready for:** *"How do you mitigate it at team scale?"* → Mandatory review of AI output, SAST
in CI, dependency/licence scanning, and never letting generated code bypass the normal gate.

---

### 10. Testing AI systems

**Definition.** Validating systems with a non-deterministic core: behavioural and metamorphic
tests, gold-set evaluation, adversarial/red-team inputs, and invariants that must hold regardless
of the model's output.

**Lexis:** *behavioural testing*, *metamorphic relations*, *a gold / regression set*, *adversarial
inputs*, *red-teaming*, *tolerance bands*, *invariants over exact outputs*.

**Model answer.** "Testing AI systems forces you to let go of exact-match assertions, because the
output legitimately varies. Instead you test at a higher level of abstraction. Gold-sets give you a
regression baseline — a curated set of inputs with acceptable outputs, re-run on every change.
Metamorphic testing is elegant here: you don't assert the exact answer, you assert a *relation* —
paraphrasing the question shouldn't change the verdict, say. Then you red-team adversarially, and
crucially you test the *invariants* the model must never violate regardless of what it generates.
That last category is where I'm strictest, because an invariant breach — say, moving money the
system shouldn't — is categorically worse than a merely mediocre answer."

**Grounded in your work.** "My Mesh contracts have 87 adversarial tests — not happy-path checks but
things like 'the operator can NOT rotate itself' and 'pause blocks deposits but the buyer can still
confirm receipt'. I'm testing that my own safety mechanism can't trap a user's funds."

**Be ready for:** *"How do you test for hallucination?"* → Faithfulness scoring against retrieved
context, plus gold-sets where the correct answer is 'I don't know'.

---

### 11. AI evaluation

**Definition.** Systematically measuring an AI system's quality across offline (pre-deploy,
gold-sets) and online (live-traffic sampling) settings, separating component metrics from
end-to-end outcomes.

**Lexis:** *offline vs online evaluation*, *faithfulness and answer relevance*, *LLM-as-judge*,
*to validate the judge against human labels*, *architecture-informed metrics*, *quality drift*,
*evaluation-driven design*.

**Model answer.** "Evaluation is the discipline that separates a demo from a product, and the key
realisation is that it can't be a one-off gate — it has to run continuously, offline *and* online.
Offline, you curate gold-sets and run them on every change. Online, you sample live traffic to
catch drift before users do. I'm careful to measure components separately: for retrieval I'd look
at recall and precision against known-relevant documents; for generation, at faithfulness and
answer relevance, often via an LLM-as-judge — but a judge is worthless unless you've *validated it
against human labels*, otherwise it's just the same failure distribution grading its own homework.
The most sophisticated framing I've seen ties each metric to an architectural component — the
planner to task completion, memory to coherence, the router to tool-selection accuracy."

**Grounded in your work.** "My clearest eval win is a number I earned: in Pulse, adding a bounded
retry moved the share of real-Gemini answers from roughly sixty per cent to over ninety. The
fallback rate *was* the evaluation metric."

**Be ready for:** *"Your LLM-judge disagrees with users — what now?"* → Re-validate the judge
against fresh human labels; trust the humans, recalibrate the judge, never the reverse.
