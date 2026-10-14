# IELTS × PhD Prep — Reliable, Autonomous AI-Native Distributed Systems

A paired study document covering twenty concepts you will need to discuss fluently in both IELTS Speaking Part 3 and PhD interviews. Everything is written in band 7.5+ register so that reading it is itself a drill: you absorb the collocations, grammar patterns, and discourse markers as you go.

## How to use this

- **One cluster per day** over five days. Read the definitions aloud. Shadow the model sentences until the stress and chunking feel natural.
- **The italicised phrases are the "chunks"** — the two- to four-word collocations that distinguish band 7 from band 8 writing. Recycle them verbatim; a well-placed collocation outperforms a rare word every time.
- **The vocabulary entries** sit under each topic because context cements retention. Add any that are new to you to the app's Vocab bank for trivia-based review.
- **Each cluster closes with Part 3 questions** that double as PhD-interview prompts. Record yourself answering; grade for fluency, lexis, and whether you commit to a view (hedging is fine, fence-sitting is not).
- **The cross-cutting Writing prompts** at the end stretch the same content into 40-minute Task 2 essays and 60-minute design-doc drills.

Register note: PhD-interview English is more compressed than IELTS Speaking but less performative than Task 2. The pieces below sit between the two deliberately.

---

## Cluster A — AI-native systems and the agents that drive them

### 1. What makes a system *AI-native*

An AI-native system is one in which machine-learned models sit at the heart of the control flow rather than at its periphery. In such architectures, inference is a *first-class dependency*: it drives routing, prioritisation, and even recovery, in the same way a database or a message broker would in a conventional stack. The hallmark of an AI-native design is therefore not the mere presence of a model but the *tight coupling* between predictions and the system's behaviour. Three features *tend to co-occur*: a continuous feedback loop that returns outcomes to the training pipeline, an evaluation layer that *runs alongside* the serving layer, and a guardrail layer that bounds what the model is permitted to decide. Where any of these is missing, the system is better described as AI-assisted — a weaker claim.

**Key collocations** — *first-class dependency · tight coupling · feedback loop · at the heart of · bounded autonomy · continuous evaluation*

**Vocabulary**

- **inference** · noun · the step in which a trained model produces an output for a new input · *Low-latency inference is the main cost driver in a feed-ranking service.*
- **underpin** · verb · to form the basis of something · *Three design principles underpin any AI-native architecture.*
- **periphery** · noun · the outer edge or margins of something · *In legacy systems, the model lives on the periphery; in AI-native ones, it sits at the core.*
- **retrofit** · verb · to add a new feature to an existing structure · *Observability is far cheaper to design in than to retrofit.*
- **permissive** · adjective · allowing a lot of freedom · *A permissive guardrail layer invites the very failures the system was meant to avoid.*
- **harness** · verb · to use the power of something productively · *The challenge is to harness non-determinism without inheriting its brittleness.*

**Model sentences**

- *What distinguishes an AI-native system from an AI-assisted one is less the sophistication of the model and more the degree to which predictions are permitted to drive consequential decisions.*
- *Only when inference, evaluation, and guardrails move in lockstep can a system genuinely claim to be AI-native rather than merely AI-adjacent.*

**Part 3 / interview prompts**

1. In what sense is calling a system "AI-native" more than a marketing label?
2. What architectural changes would a payments platform have to make before it could reasonably describe itself as AI-native?

### 2. AI agents and *agentic* systems

An agent, in the current literature, is a program that *perceives, decides, and acts* in a loop toward a goal. What *sets agentic systems apart* from classical automation is that the decision step is itself model-driven: the program chooses, at runtime, which tool to invoke, what argument to pass, and when to stop. This loop grants a degree of autonomy that pays off in open-ended tasks — triage, routing, code repair — where the search space is too large for a hand-coded policy. The same autonomy, however, *comes with a cost*: non-determinism, long tails of unexpected behaviour, and *runaway* loops when termination conditions are poorly specified. The engineering challenge, therefore, is less to make agents *more* capable than to make their capability *predictable under constraint*.

**Key collocations** — *perceive, decide, act · set apart from · comes with a cost · bounded by a policy · tool-use loop · runaway behaviour*

**Vocabulary**

- **triage** · verb/noun · to sort by urgency; the act of sorting · *An LLM-based agent can triage incoming tickets before a human sees them.*
- **invoke** · verb · to call or activate (a tool, a function) · *The planner invokes a search tool whenever its confidence falls below a threshold.*
- **non-determinism** · noun · the property that identical inputs may yield different outputs · *Non-determinism is the single most awkward property to engineer around.*
- **long tail** · noun phrase · the small-probability edge cases that collectively dominate · *The long tail of agent misbehaviour is where most of the engineering goes.*
- **brittle** · adjective · liable to break under conditions outside the design envelope · *A prompt-stitched agent can be surprisingly brittle under schema drift.*
- **envelope** · noun · the set of conditions within which a system is designed to operate · *Formal methods help us keep the agent inside its operational envelope.*

**Model sentences**

- *The defining feature of an agent is not that it uses an LLM but that it closes a loop between perception and action without a human in the critical path.*
- *What makes agentic systems difficult to engineer is precisely what makes them useful: they take decisions we did not anticipate having to specify.*

**Part 3 / interview prompts**

1. Where does the boundary between "automation" and "an agent" actually lie?
2. In which domains is the autonomy of agents a net benefit, and in which is it a liability?

### 3. LLM-based software agents

LLM-based agents are a particular subclass in which a large language model acts as the planner, the reasoner, and *as often as not* the controller for a loop of tool calls. Their appeal is that the capacity to compose plans in natural language dramatically compresses the engineering distance between a vague user request and a concrete execution. Their drawback is equally characteristic: the planner is a stochastic function with no formal contract, and the *failure modes* that follow — hallucinated tool arguments, silent repetition, misinterpretation of state — do not resemble those of deterministic software. Engineering such agents responsibly involves narrowing the agent's choice set through *structured outputs*, grounding its state through retrieval, and enforcing *typed interfaces* at every tool boundary.

**Key collocations** — *as often as not · failure modes · structured outputs · typed interfaces · ground the state · stochastic by design*

**Vocabulary**

- **stochastic** · adjective · containing an element of randomness · *An LLM is a stochastic function, however powerful.*
- **compose** · verb · to assemble smaller parts into a larger whole · *The LLM composes a multi-step plan from the tool list it is handed.*
- **hallucinate** · verb · (of a model) to produce confident but false output · *The model hallucinated a field name that does not exist in the schema.*
- **ground** · verb · to anchor model output in verifiable context · *Retrieval-augmented generation grounds the model's answers in a known corpus.*
- **ergonomic** · adjective · designed to be comfortable to use · *A typed tool interface is as much about ergonomics as it is about safety.*
- **constrain** · verb · to limit the possibilities · *Constraining the output to a JSON schema removes a whole class of parsing bugs.*

**Model sentences**

- *The virtue of an LLM-based planner — that it can respond to a request it has never explicitly been trained on — is also the source of its worst failures.*
- *Rather than attempting to make the model deterministic, we build cages around it: typed schemas, retrieval anchors, and bounded tool permissions.*

**Part 3 / interview prompts**

1. What makes a language model a good planner, and what makes it a dangerous one?
2. How might you measure whether an LLM-based agent has improved from one release to the next?

### 4. Autonomous decision-making

Autonomous decision-making describes the delegation of a specific choice — "which route to use", "which account to freeze", "whether to retry" — from a human to a program that acts without case-by-case review. Autonomy, in this sense, *admits of degree*: a system might choose freely within a narrow bound and still require human sign-off beyond it. The engineering question is therefore not whether a system should be autonomous but *how far* and *under which conditions*. In financial contexts, this involves pre-committing to a mandate — a declarative contract that caps the amount, scope, counterparty, or time window over which the agent may act — and backing that mandate with on-chain or cryptographic verification. The pattern bears a close resemblance to classical process control: *control within tolerances, escalate otherwise*.

**Key collocations** — *admits of degree · case-by-case review · pre-committed mandate · within tolerances · escalate otherwise · cryptographic verification*

**Vocabulary**

- **mandate** · noun · an authorisation granted to act within specific bounds · *The agent operates under a mandate that caps daily spending at ten thousand naira.*
- **tolerance** · noun · an allowed range of variation · *The controller stays silent while the error remains within tolerance.*
- **delegate** · verb · to hand over authority for a task · *We delegate retry logic to the agent but keep final-settlement sign-off human.*
- **escalate** · verb · to pass up to a higher authority · *If confidence falls below sixty per cent, the agent escalates to a reviewer.*
- **pre-commit** · verb · to decide in advance and bind oneself to that decision · *A pre-committed spending limit is enforceable without further negotiation.*
- **declarative** · adjective · stating what, not how · *Mandates are deliberately declarative so that they can be checked against execution.*

**Model sentences**

- *Autonomy is not a binary; it is a dial with a range of safe settings for a given task, and the engineer's job is to pick the setting and defend the choice.*
- *A trustworthy autonomous system is one whose mandate is strict enough to constrain its mistakes and generous enough to permit its usefulness.*

**Part 3 / interview prompts**

1. Which decisions should never be delegated to an autonomous system?
2. How might a bank balance the efficiency of autonomous transaction handling with the public's demand for accountability?

---

## Cluster B — AI × Software Engineering, in both directions

### 5. AI4SE — AI *for* Software Engineering

AI4SE denotes the application of AI, and increasingly of LLMs, to the problems software engineers face: bug localisation, code review, test generation, repair, refactoring, documentation, and migration. The subfield has moved rapidly from research prototypes to production tooling in the last two years, with Copilot-style assistants now embedded in most mainstream IDEs. The research questions, however, remain *far from settled*: how to evaluate suggestions beyond pass-rate on crafted benchmarks, how to measure productivity without conflating it with throughput, and how to prevent the quiet accumulation of *technical debt* when the easy path is "accept the suggestion". Zhen Ming (Jack) Jiang's group at York, among others, treats AI4SE as a problem of *empirical software engineering*: measurement first, intervention second.

**Key collocations** — *far from settled · pass-rate on benchmarks · technical debt · bug localisation · empirical measurement · a quiet accumulation*

**Vocabulary**

- **benchmark** · noun · a reference dataset or task used to evaluate systems · *The benchmark has saturated, so improvements no longer discriminate between models.*
- **assistant** · noun · a system that augments but does not replace a human · *A coding assistant should raise the floor rather than the ceiling of its users.*
- **conflate** · verb · to merge two distinct things wrongly · *We should not conflate activity with productivity.*
- **saturate** · verb · to reach a level beyond which no improvement is visible · *Once a benchmark saturates, researchers move to harder evaluations.*
- **crafted** · adjective · deliberately constructed · *Hand-crafted test cases flatter the models that were trained on their style.*
- **intervention** · noun · a deliberate change made to study its effect · *Measurement precedes intervention in rigorous empirical work.*

**Model sentences**

- *The honest claim about AI4SE is that it changes the shape of the engineer's day far more than it changes the output of the engineering process.*
- *Until we have evaluation methods that survive outside the lab, every productivity figure quoted for AI coding assistants should be read with scepticism.*

**Part 3 / interview prompts**

1. How might we measure whether an AI coding assistant actually makes engineers better rather than merely faster?
2. In what ways could over-reliance on AI assistants reshape the skills we expect of junior developers?

### 6. SE4AI — Software Engineering *for* AI systems

SE4AI is the complementary discipline: applying the methods of software engineering — testing, version control, configuration management, observability, release engineering — to systems that happen to include learned components. The difficulty is that *conventional practices break* when the artefact under management has a probability distribution rather than a specification. Datasets drift, model weights are enormous, evaluation is dataset-dependent, and reproducibility rests on seeds, hardware, and library versions that a Git commit does not capture. SE4AI consequently reaches for new abstractions — model cards, data cards, lineage graphs, shadow evaluation — not because software engineering is unfit for AI but because the unit of work has changed. Jiang's lab explicitly bridges this gap: the same rigour that was once reserved for distributed systems is being extended to the pipelines that train and serve them.

**Key collocations** — *conventional practices break · dataset drift · shadow evaluation · lineage graph · model card · release engineering*

**Vocabulary**

- **drift** · noun · gradual change in data distribution over time · *Feature drift is the quiet killer of production models.*
- **lineage** · noun · the recorded history of how a thing came to be · *Data lineage lets us reproduce an experiment months later.*
- **reproducible** · adjective · able to be re-run with the same outcome · *A truly reproducible training run pins every random seed and every dependency.*
- **artefact** · noun · a produced object; here, model weights or datasets · *The artefact under version control is now a four-gigabyte file, not a text file.*
- **shadow** · adjective · running in parallel for comparison, not serving traffic · *Shadow deployment lets us measure the new model without exposing users to it.*
- **lifecycle** · noun · the full sequence from creation to retirement · *A model lifecycle has stages that software lifecycles do not.*

**Model sentences**

- *What SE4AI acknowledges is that a model is a kind of software whose contract is statistical rather than axiomatic.*
- *Practices that served us well for text files — diff, review, roll back — degrade when the thing we are managing weighs several gigabytes and depends on the data it was trained on.*

**Part 3 / interview prompts**

1. Which parts of traditional software engineering transfer cleanly to ML systems, and which do not?
2. If you were asked to establish SE4AI practices at a bank, where would you start?

---

## Cluster C — Distributed systems foundations

### 7. Distributed systems

A distributed system is a collection of independent machines that cooperate over a network to present, from the outside, the illusion of a single service. The *abiding challenge* of such systems is that none of the convenient properties of a single process — shared memory, instantaneous communication, synchronous failure — survives the network boundary. Messages are lost or reordered, clocks drift, nodes fail without warning, and partial failure becomes the default state against which every design must be measured. The intellectual tradition that has grown around these constraints — Lamport clocks, Paxos, Raft, vector timestamps, consistent hashing — is not a collection of trivia but a set of hard-won techniques for reasoning in the presence of uncertainty.

**Key collocations** — *the abiding challenge · partial failure · network boundary · hard-won techniques · reason in the presence of uncertainty · default state*

**Vocabulary**

- **partition** · noun · a split in the network that isolates subsets of nodes · *Under partition, we must choose between availability and consistency.*
- **quorum** · noun · the minimum number of nodes required to proceed · *A write succeeds once a quorum of replicas acknowledges it.*
- **replica** · noun · a copy of data held on a different node · *Three replicas across three availability zones is a common configuration.*
- **topology** · noun · the arrangement of nodes and connections · *Mesh and ring topologies tolerate failure differently.*
- **asynchronous** · adjective · not waiting for a response · *Asynchronous messaging decouples producers from consumers.*
- **crash-fault** · noun · a failure in which a node simply stops · *Most consensus algorithms address crash faults; Byzantine faults are harder.*

**Model sentences**

- *The temptation when teaching distributed systems is to present the algorithms; the harder lesson is why we need them at all.*
- *Every subtle bug I have fixed in production turned out, on reflection, to be a failure to take partial failure seriously.*

**Part 3 / interview prompts**

1. Why is reasoning about distributed systems considered harder than reasoning about single-process programs?
2. Where in a modern bank's architecture would you expect the distributed-systems trade-offs to be most sharply felt?

### 8. Fault tolerance

Fault tolerance is the capacity of a system to continue operating correctly in the presence of faults — hardware failures, dropped packets, misbehaving dependencies — without losing data or returning wrong answers. It is best thought of as a *design posture* rather than a feature: redundancy, isolation, retry with backoff, bulkheads, and circuit breakers all contribute, but no amount of post-hoc patching reproduces what careful design confers. The practical skill is the discipline to enumerate failure modes before writing the happy path: which component fails, how is it detected, what is the fallback, how is the user told, and how does recovery proceed. In regulated systems — payments especially — a *failure-mode catalogue* is as much a deliverable as the code itself.

**Key collocations** — *design posture · retry with backoff · circuit breaker · failure-mode catalogue · the happy path · graceful degradation*

**Vocabulary**

- **redundant** · adjective · duplicated for safety · *Redundant links are what keep the service alive during a cable cut.*
- **bulkhead** · noun · an isolation boundary that limits the blast radius of a failure · *Bulkheads prevent a slow dependency from exhausting all threads.*
- **graceful** · adjective · (of degradation) occurring in a controlled, usable way · *Graceful degradation returns a reduced service rather than no service at all.*
- **backoff** · noun · a strategy of waiting longer between retries · *Exponential backoff with jitter avoids retry storms.*
- **detect** · verb · to notice that something has failed · *Fast detection is as important as fast recovery.*
- **saturate** · verb · to fill to capacity · *Without a bulkhead, a single slow caller can saturate the thread pool.*

**Model sentences**

- *Fault tolerance is not an add-on; it is the choice to treat failure as the normal case and success as the pleasant exception.*
- *The architectures that survive are not the ones that avoid faults but the ones that confine them.*

**Part 3 / interview prompts**

1. Can a system ever be made genuinely fault-tolerant, or is this always a question of degree?
2. How does the cost of achieving fault tolerance change the economics of running a service?

### 9. Consistency

In distributed systems, consistency describes the guarantees a system makes about what any reader will see after a write. The strongest model, linearisability, insists that every operation appears to take place at some single instant between its invocation and its return, as if there were one copy of the data. Weaker models — sequential consistency, causal consistency, eventual consistency — relax that guarantee in exchange for availability, latency, or throughput. The famous CAP theorem *lends shape to the trade-off*: during a partition, a system must sacrifice either consistency or availability; it cannot keep both. In practice, the choice is rarely binary and never permanent: modern systems tune consistency *per operation*, offering strong reads where correctness demands it and relaxed reads where it does not.

**Key collocations** — *lends shape to the trade-off · per-operation tuning · linearisable reads · sacrifice availability · eventual convergence · correctness-critical path*

**Vocabulary**

- **linearisable** · adjective · behaving as if operations happen at a single instant · *Linearisable reads are expensive and worth asking for only when necessary.*
- **causal** · adjective · (of consistency) preserving cause-and-effect ordering · *Causal consistency is often enough for user-facing timelines.*
- **converge** · verb · to arrive at the same state eventually · *Replicas converge once writes stop and messages are delivered.*
- **stale** · adjective · (of a read) returning an older value · *Stale reads are acceptable for analytics, catastrophic for payments.*
- **monotonic** · adjective · never going backward · *A monotonic clock is essential for correct timeouts.*
- **relaxed** · adjective · (of consistency) weaker, in exchange for other properties · *Relaxed reads deliver sub-millisecond latency at the cost of occasional staleness.*

**Model sentences**

- *Consistency, in the distributed-systems sense, is not a binary property of the system but a per-operation contract that the designer picks and the client depends on.*
- *The best designers do not aspire to the strongest guarantee available; they aspire to the weakest guarantee that correctness permits.*

**Part 3 / interview prompts**

1. In what sense is consistency a design decision rather than a feature of the technology?
2. How might a bank reason about which operations deserve strong consistency and which do not?

### 10. Idempotency

An operation is idempotent when performing it twice has the same effect as performing it once. In a world of lost acknowledgements and client retries, idempotency *is less a nicety than a necessity*: without it, the honest answer to "did the transfer go through?" is "I don't know, and asking again might make it worse". The usual mechanism is a client-generated idempotency key stored server-side with a deduplication window long enough to survive worst-case retries. The subtleties are in the margins: what counts as "the same" request, how to handle in-flight duplicates, when to expire the key, and how to make the dedup store itself survive failure. Payments, in particular, treat the idempotency key *as a load-bearing identifier*, often more important than any other field in the request.

**Key collocations** — *less a nicety than a necessity · load-bearing identifier · dedup window · in-flight duplicate · at-least-once delivery · the retry storm*

**Vocabulary**

- **idempotency key** · noun · a client-supplied token used to deduplicate requests · *A good idempotency key is both unique and reconstructible by the client.*
- **deduplicate** · verb · to remove duplicates · *The server deduplicates incoming webhooks by their event id.*
- **retry storm** · noun · a cascading flood of retries that overwhelms the dependency · *Retry storms are the predictable consequence of unbounded client retries.*
- **side effect** · noun · a lasting change caused by an operation · *Idempotency bites only for operations with side effects.*
- **replay** · verb · to deliver a stored message again · *A replay attack re-sends a captured request to force a duplicate action.*
- **window** · noun · a bounded time range · *The dedup window should be at least twice the client's maximum retry interval.*

**Model sentences**

- *The hardest-won lesson of a payments career is that at-least-once delivery is cheap and exactly-once delivery is a myth; what one actually ships is at-least-once delivery with idempotent handlers.*
- *A system without idempotency is a system in which every network blip is a potential duplicate transaction.*

**Part 3 / interview prompts**

1. Why is "exactly once" delivery considered impossible in distributed systems, and what do engineers do instead?
2. How does the design of an idempotency scheme reflect assumptions about the clients that will use it?

---

## Cluster D — Reliability, verification, and the apparatus of trust

### 11. Observability

Observability is the property of a system that permits an engineer to answer questions about its internal state from the outside, without redeploying. The field has largely converged on three pillars — metrics, logs, and distributed traces — complemented by the discipline of defining service-level indicators (what you measure), service-level objectives (what you promise), and error budgets (how much you may burn before you stop shipping features). A system is observable *not when it emits data* but when the data suffices to answer unanticipated questions. The *acid test*, drawn from Charity Majors, is whether an on-call engineer can diagnose a novel failure using only existing telemetry; if the honest answer is no, the system is at best monitored, not observed.

**Key collocations** — *the acid test · three pillars · error budget · on-call engineer · unanticipated questions · existing telemetry*

**Vocabulary**

- **telemetry** · noun · the data a system emits about itself · *The telemetry budget is often as fiercely contested as the compute budget.*
- **trace** · noun · a record of a request's path through many services · *A distributed trace shows exactly which hop added the latency.*
- **cardinality** · noun · the number of distinct values of a metric label · *High-cardinality labels explode storage costs if left unchecked.*
- **SLO** · noun · a service-level objective — a numerical reliability target · *An SLO without an error budget is a wish, not a policy.*
- **page** · verb · to alert an on-call engineer · *Only an SLO burn warrants paging someone at four in the morning.*
- **symptom** · noun · an externally visible manifestation of an internal fault · *Alert on symptoms, not causes.*

**Model sentences**

- *Observability is not a tool one buys but a property one earns by designing it in from the first commit.*
- *The test of a well-instrumented system is not whether it can explain the failures you anticipated but whether it can help you reason about the ones you did not.*

**Part 3 / interview prompts**

1. What distinguishes observability from the older practice of monitoring?
2. In what ways do agentic systems demand observability tools that classical software does not?

### 12. Verification and validation

Verification asks whether we built the system right — whether it meets its specification; validation asks whether we built the right system — whether it meets the user's needs. The distinction *has stood the test of time* because it keeps two different conversations separate: with the engineer, about correctness; with the stakeholder, about fitness for purpose. For AI systems, both halves are harder. Verification is awkward because learned components lack a crisp specification; validation is awkward because the user's definition of "right" shifts as the system reshapes their workflow. Formal verification, model checking, property-based testing, red-teaming, and *A/B evaluation under live load* each address a slice of the problem. The responsible practitioner uses several at once, because no single method covers an AI system's failure surface.

**Key collocations** — *has stood the test of time · fitness for purpose · failure surface · a crisp specification · A/B evaluation · property-based testing*

**Vocabulary**

- **specification** · noun · a precise description of what a system should do · *Writing the specification is often harder than implementing it.*
- **conform** · verb · to meet a specification · *The verification harness checks that the model conforms to the stated invariants.*
- **invariant** · noun · a property that must hold at all times · *A ledger's invariant is that debits and credits balance.*
- **red-team** · verb · to attempt to break a system from an adversary's position · *The agent survived a red-team exercise with only one successful jailbreak.*
- **surrogate** · noun · a proxy used in place of the real thing · *An offline benchmark is a surrogate for live performance.*
- **adversarial** · adjective · deliberately designed to cause failure · *Adversarial examples probe the model's weak spots.*

**Model sentences**

- *Verification asks whether the system meets its contract; validation asks whether that contract was ever worth meeting.*
- *For AI systems, the specification itself is a research artefact, and every evaluation method is partial.*

**Part 3 / interview prompts**

1. Why is it harder to verify a machine-learned component than a hand-coded one?
2. What role, if any, should formal methods play in AI engineering?

### 13. Safety and reliability

Safety and reliability are related but *not interchangeable*. A reliable system does what it was designed to do, with high probability, under expected conditions; a safe system behaves acceptably even under unexpected ones. The distinction *matters most* when a system is given scope to act on the world: a reliable autopilot that flies into terrain in rare weather is unsafe; a safe autopilot that stalls out at the first anomaly is unreliable. For autonomous AI systems, the challenge is to engineer *both* at once — low mean failure rate and bounded worst-case behaviour. Techniques include defence in depth, bounded authority, kill switches, canary deployments, and the discipline of running the system in a shadow mode before trusting its decisions. None is sufficient alone; the layered combination is the point.

**Key collocations** — *not interchangeable · matters most · defence in depth · bounded authority · kill switch · shadow mode*

**Vocabulary**

- **anomaly** · noun · an observation that departs from the expected · *Anomaly detectors feed the alerting pipeline but should rarely page.*
- **envelope** · noun · the operating range for which a system is designed · *Outside its envelope, the model's confidence should drop sharply.*
- **canary** · noun · a small deployment used to detect problems before full rollout · *The canary caught a regression that offline tests had missed.*
- **jailbreak** · noun · a prompt or input that bypasses the model's guardrails · *The jailbreak corpus is the dataset of attacks we have survived.*
- **containment** · noun · the limitation of a failure's reach · *Containment lets us ship imperfect models with acceptable blast radius.*
- **permissioned** · adjective · requiring explicit authorisation · *Every tool the agent can call is permissioned at the mandate level.*

**Model sentences**

- *A system can be reliable without being safe and safe without being reliable; the engineering job is to deliver both.*
- *The right question to ask of an autonomous system is not "how well does it work?" but "what does it do when it is wrong?".*

**Part 3 / interview prompts**

1. How should we trade off safety against reliability when the two pull in different directions?
2. In which domains is the safety of autonomous systems a societal rather than an engineering question?

### 14. Explainability

Explainability is the extent to which a system can justify its outputs in terms that a human — a user, an auditor, a regulator — can act on. The research literature *draws a useful distinction* between inherently interpretable models (linear models, shallow decision trees), which explain themselves by construction, and post-hoc explanations (saliency maps, SHAP values, chain-of-thought traces), which attempt to describe why a complex model behaved as it did. For LLM-based agents, the natural-language rationale that accompanies a decision is itself a kind of explanation — but *a notoriously unreliable one*, since the model may generate a plausible rationale after reaching its decision by other means. The honest practitioner treats such rationales as hypotheses, not evidence.

**Key collocations** — *draws a useful distinction · a notoriously unreliable one · post-hoc explanation · act on the output · auditable rationale · chain-of-thought trace*

**Vocabulary**

- **interpretable** · adjective · capable of being understood directly by a human · *Interpretable models trade some accuracy for a great deal of trust.*
- **rationale** · noun · a stated reason for a decision · *A written rationale accompanies every blocked transaction.*
- **saliency** · noun · a measure of how much an input contributed to an output · *Saliency maps are a weak but widely used form of explanation.*
- **auditable** · adjective · capable of being examined after the fact · *Decisions are logged in an auditable form that survives model updates.*
- **confabulate** · verb · to produce a plausible but unfounded explanation · *LLMs confabulate rationales as fluently as they produce correct answers.*
- **justify** · verb · to show the grounds for a claim · *The model justifies its routing choice with a cost-latency trade-off.*

**Model sentences**

- *Explainability is not a property of the model alone; it is a relationship between the model's output and the person who needs to act on it.*
- *The rationale a language model offers for its decision is a hypothesis about its own behaviour, no more and no less.*

**Part 3 / interview prompts**

1. Why is explainability sometimes at odds with model accuracy?
2. How should regulators decide what counts as a sufficient explanation for an AI-driven decision?

### 15. Auditability

Auditability is the capacity of a system to produce, after the fact, an *immutable and complete* account of what happened: which inputs arrived, which decisions were taken, which actions followed, and on whose authority. It is the discipline that converts "the system did this" from a claim into something a regulator or litigant can verify. For autonomous AI systems, auditability is harder than logging. The record must capture the model version, the retrieval context, the tool arguments, the mandate under which the agent acted, and ideally a cryptographic commitment that *the record itself has not been tampered with*. In regulated finance, auditability is not a nice-to-have; it is the legal basis on which an autonomous system is allowed to act at all.

**Key collocations** — *immutable and complete · tamper-evident · cryptographic commitment · legal basis · authorised chain of custody · nice-to-have*

**Vocabulary**

- **immutable** · adjective · unchangeable once written · *Audit logs should be immutable or at least tamper-evident.*
- **provenance** · noun · the documented origin and history of a thing · *The provenance of the training data is part of the model's audit trail.*
- **tamper-evident** · adjective · leaving visible traces if altered · *A hash chain makes an append-only log tamper-evident.*
- **chain of custody** · noun phrase · the documented sequence of hands something has passed through · *A compromised chain of custody weakens any evidence drawn from the log.*
- **attestation** · noun · a signed statement that a condition was met · *The agent produces a signed attestation that the mandate was respected.*
- **forensic** · adjective · suitable for use as legal evidence · *Forensic-grade logging adds overhead but earns its place in regulated systems.*

**Model sentences**

- *An auditable system is one in which, in the aftermath of an incident, we can reconstruct not just what the system did but why it was permitted to do so.*
- *In finance, the audit trail is not the system's documentation; it is the system's defence.*

**Part 3 / interview prompts**

1. What are the practical limits of auditability when a decision depends on a very large model?
2. How might blockchain-based audit trails change the standard of evidence in financial disputes?

---

## Cluster E — Humans, evaluation, and oversight

### 16. Human-in-the-loop systems

A human-in-the-loop (HITL) design keeps a person in the critical path for decisions that are either high-stakes, poorly specified, or outside the system's envelope of competence. The design question is seldom whether to involve humans but *where to place* the handoff: at the input (triage), the decision (approval), the output (review), or the feedback (correction). Each placement trades throughput for assurance differently. In financial systems, HITL is often *statutorily required* for actions above a monetary threshold, which gives the engineer a hard constraint to work around rather than a design choice to deliberate over. The craft lies in *making the handoff cheap* — presenting the human with enough context to decide quickly, and routing them to the next item in milliseconds, not minutes.

**Key collocations** — *in the critical path · statutorily required · place the handoff · make the handoff cheap · throughput for assurance · envelope of competence*

**Vocabulary**

- **handoff** · noun · the transfer of a task from one actor to another · *A well-designed handoff carries forward all the context the human needs.*
- **throughput** · noun · the rate at which work is completed · *HITL review caps the throughput of the pipeline at human speed.*
- **threshold** · noun · a value above which different rules apply · *Above the ten-million-naira threshold, two sign-offs are required.*
- **oversight** · noun · supervisory responsibility · *Legal oversight of AI decisions is often more effective than technical constraint alone.*
- **intervene** · verb · to step in and alter the course of events · *The reviewer intervenes in roughly five per cent of the agent's decisions.*
- **cognitive load** · noun phrase · the mental effort a task imposes · *A good review UI minimises the reviewer's cognitive load.*

**Model sentences**

- *Keeping a human in the loop is not a confession that the system is weak; it is an acknowledgement that some decisions should always carry a human signature.*
- *The engineering question is not whether to involve people but how to involve them without wasting their time.*

**Part 3 / interview prompts**

1. In which contexts does human oversight genuinely improve outcomes, and in which does it merely slow them down?
2. How can one design a review interface that respects both speed and accuracy?

### 17. AI evaluation

Evaluation is the discipline of asking, with statistical honesty, "how well does this system actually work?". For classical models, we have reliable playbooks — held-out test sets, confusion matrices, calibration curves. For LLM-based systems, the ground has shifted: tasks are open-ended, references are costly or contested, and the models themselves are now routinely drafted as judges. The field has responded with a *patchwork of methods*: head-to-head comparisons, LLM-as-judge pipelines, task-specific benchmarks, and the ultimate arbiter — live A/B tests with real users. The practitioner's instinct, hard-won, is that *every metric eventually lies*: it either saturates, is gamed, or ceases to track the behaviour the user cared about. Evaluation is therefore an iterative dialogue between what we measure and what we value.

**Key collocations** — *every metric eventually lies · a patchwork of methods · head-to-head comparison · live A/B tests · hard-won instinct · the ultimate arbiter*

**Vocabulary**

- **held-out** · adjective · set aside, not used in training · *A held-out test set is the single most important thing to guard.*
- **arbiter** · noun · a final judge · *Live user behaviour is the arbiter of whether a change was an improvement.*
- **calibration** · noun · the alignment between predicted and observed probabilities · *Poor calibration undermines any downstream decision that treats confidence as truth.*
- **leaderboard** · noun · a ranked table of system scores · *Leaderboard progress is not a substitute for user-facing improvement.*
- **gameable** · adjective · susceptible to being exploited rather than solved · *A gameable benchmark produces impressive numbers and no better product.*
- **ablation** · noun · an experiment that removes one component to isolate its contribution · *A disciplined ablation forces honesty about what each piece earned.*

**Model sentences**

- *The purpose of evaluation is not to produce a number for the slide deck; it is to catch oneself before shipping a regression no one noticed.*
- *A benchmark is a map; the territory is production, and the two diverge the moment one looks away.*

**Part 3 / interview prompts**

1. How can one tell whether an improvement on a benchmark will translate into an improvement for users?
2. What should the role of human judgment be in evaluating AI systems that aspire to superhuman performance on narrow tasks?

### 18. AI-generated code and its risks

AI-generated code *presents a paradox*: it accelerates the easy cases and distorts the hard ones. The suggestions it offers are plausible, idiomatic, and locally correct — but they encode the biases of the training corpus, inherit its security defects, and often look sufficiently professional to escape review. The documented risks fall into three families: *insecure patterns* reproduced at scale (SQL injection, hard-coded secrets, path traversal), *stale APIs* confidently cited after they have been deprecated or removed, and *subtle semantic drift* in which the suggested code solves a nearby problem rather than the one at hand. Mitigations are now well understood — human review, in-IDE scanning, policy-aware prompting, provenance tracking — but *the ultimate safeguard* is the engineer who refuses to accept a diff they do not understand.

**Key collocations** — *presents a paradox · insecure patterns · stale APIs · semantic drift · the ultimate safeguard · in-IDE scanning*

**Vocabulary**

- **deprecated** · adjective · marked for removal; discouraged · *The model happily cites deprecated APIs that have not been in the SDK for a year.*
- **plausible** · adjective · appearing reasonable at first glance · *A plausible wrong answer is harder to catch than an obvious one.*
- **boilerplate** · noun · standard, repeated code · *AI assistants shine at boilerplate and struggle at non-obvious logic.*
- **sanitise** · verb · to remove dangerous content from input · *Sanitising the LLM output before executing it is non-negotiable.*
- **inheritance** · noun · receiving properties from a source · *Code generated from a repository inherits that repository's bugs.*
- **supply chain** · noun phrase · the sequence of dependencies and processes that produce software · *AI-generated code expands the supply-chain surface considerably.*

**Model sentences**

- *The most dangerous property of AI-generated code is not that it is wrong but that it is wrong in a way that reads correct.*
- *A reviewer who waves through an AI-generated patch has, in practice, signed their name under its bugs.*

**Part 3 / interview prompts**

1. What forms of oversight will developers need to retain over AI-generated code in the coming decade?
2. Is it reasonable to hold the user of an AI coding assistant responsible for defects the model introduced?

### 19. Testing AI systems

Testing AI systems *bears a family resemblance* to testing software — assertions, fixtures, continuous integration — but the properties being tested are different. We ask not only "does this function return the right value?" but also "does the model's accuracy stay within tolerance across a representative distribution of inputs?", "does the agent recover gracefully from a malformed tool response?", and "does the pipeline still train on the data we have today?". The practical answer is a *layered testing strategy*: unit tests for deterministic components, scenario tests for agent behaviours, metamorphic tests for invariants that should hold under input transformations, and continuous evaluation against a frozen regression suite. The point is not to prove the system correct but to catch regressions quickly and loudly enough that someone can act.

**Key collocations** — *bears a family resemblance · layered testing strategy · metamorphic test · regression suite · frozen reference · catch regressions quickly*

**Vocabulary**

- **regression** · noun · an unintended worsening after a change · *A regression suite exists so that improvements elsewhere do not quietly break the basics.*
- **fixture** · noun · a known state prepared for a test · *A good fixture is small, representative, and committed to version control.*
- **metamorphic** · adjective · (of a test) checking a relation under input transformation · *A metamorphic test asks whether renaming a variable leaves the output unchanged.*
- **flaky** · adjective · intermittently failing, usually for infrastructure reasons · *A flaky test erodes trust in the whole suite.*
- **replay** · noun · the re-execution of recorded production traffic in test · *Replay testing is cheap once the recording infrastructure exists.*
- **coverage** · noun · the proportion of behaviour exercised by tests · *Behaviour coverage, unlike line coverage, is what matters for agents.*

**Model sentences**

- *Testing an AI system well means admitting from the outset that no finite test suite can prove it correct and still insisting on tests that catch the regressions that matter.*
- *The goal of a testing strategy is not perfect assurance; it is the fastest honest feedback loop one can afford.*

**Part 3 / interview prompts**

1. How does testing a learned component differ from testing a hand-coded one?
2. Is it sensible to let AI assistants write the very tests used to evaluate them?

### 20. Monitoring autonomous agents

Monitoring an autonomous agent in production is observability with a specific set of questions: is the agent acting within its mandate, is its decision quality holding up, is its tool-use pattern drifting, and is anyone trying to break it? Classical dashboards — error rate, latency, throughput — remain necessary but no longer sufficient. The *second-order metrics* that matter are agent-specific: *decision rate*, *escalation rate*, *reversal rate*, *jailbreak attempt rate*, *mandate-breach rate*, and the distribution of tools the agent chose to invoke. A healthy agent-monitoring pipeline couples these metrics to automated interventions: throttle on burn, freeze on breach, roll back on reversal spike. The pattern is familiar from classical control engineering; what is new is that the system under control is a probabilistic artefact.

**Key collocations** — *second-order metrics · mandate-breach rate · reversal spike · throttle on burn · freeze on breach · a probabilistic artefact*

**Vocabulary**

- **throttle** · verb · to deliberately slow or limit · *The platform throttles the agent as soon as its reversal rate spikes.*
- **drift** · noun · a slow change in behaviour or input distribution · *Drift detection sits upstream of every alert that matters.*
- **reversal** · noun · an action undone, often by a human after the fact · *A rising reversal rate is the loudest signal an agent is going wrong.*
- **burn** · noun · the rate at which an error budget is consumed · *A fast burn triggers paging; a slow burn triggers a ticket.*
- **synthetic** · adjective · (of monitoring traffic) artificially generated · *Synthetic probes catch dependency failures before real users do.*
- **envelope** · noun · the operating range considered safe · *Monitoring exists to prove the agent is still inside its envelope.*

**Model sentences**

- *Monitoring an autonomous agent is less about watching for failures than about noticing, quickly, that the agent has started making the wrong kind of decisions.*
- *The best monitoring pipeline is the one that does not merely alert a human but takes the first safe corrective action on its own.*

**Part 3 / interview prompts**

1. What new metrics does the rise of autonomous agents force us to invent?
2. How much corrective authority should an automated monitoring system have over the agent it watches?

---

## Cross-cutting IELTS Writing Task 2 prompts

Use these for 40-minute timed essays. They are deliberately phrased in general-reader register — the challenge is to deploy the lexis above without lapsing into jargon.

1. *"Autonomous systems are increasingly making decisions that affect ordinary people's finances. Some believe this will lead to fairer outcomes; others believe it will erode accountability. Discuss both views and give your opinion."*

2. *"Software created with the help of artificial intelligence tools has become common in both industry and education. To what extent do you agree that developers should remain fully accountable for the behaviour of AI-generated code?"*

3. *"As AI systems take on more autonomous roles, the ability to explain their decisions has become a public concern. Discuss the extent to which explainability should be a legal requirement in high-stakes applications."*

4. *"Modern digital services depend on networks of computers that may fail at any time. Some argue that the pursuit of reliability has become so expensive that it is now harmful to innovation. To what extent do you agree?"*

5. *"The deployment of AI assistants in regulated industries such as banking requires strong oversight. Discuss who should bear primary responsibility for the behaviour of such systems — the engineers who build them, the companies that deploy them, or the regulators who permit their use."*

## Cross-cutting Design-Doc prompts (60 minutes each)

For the Writing page's Design-Doc mode. These stretch exactly the same vocabulary into MAANG-register technical prose.

1. *Design an AI-native payment routing service that selects a route per transaction from among several providers, bounded by a declarative mandate and auditable after the fact.*

2. *Design a human-in-the-loop review platform for an LLM-based agent that handles customer disputes. Define the hand-off placements, the review-SLA, and the escalation ladder.*

3. *Design the monitoring and alerting layer for a fleet of autonomous agents operating under per-tenant mandates. Include the second-order metrics and the automated interventions.*

4. *Design the audit trail for an autonomous financial agent such that any decision can be reconstructed six months later with the model version, retrieval context, and mandate it operated under.*

---

## Phrase bank — the discourse moves of band 7.5+

Hedge (soften a claim without weakening it):

- *arguably · on balance · it is fair to say · there is a case to be made that · with suitable qualification · to a first approximation*

Extend (add weight to a claim already made):

- *not only … but also · which is why · the deeper point is that · what is more striking is · this generalises to · the same logic applies to*

Pivot (change direction without jarring the reader):

- *that said · it does not follow that · a related but distinct question is · there is a bigger question underneath this · granted — but …*

Signal depth (mark that you are about to do a careful comparison):

- *lends shape to the trade-off · bears a family resemblance to · admits of degree · stands at the intersection of · has stood the test of time · the honest answer is*

Signal commitment (mark that you are about to take a position):

- *the right stance here is · on this I would want to insist · the honest view is · this is where I part company with the consensus*

Signal evidence (mark that you are about to appeal to a source):

- *the empirical record suggests · the engineering experience is that · in practice · as the recent literature has shown · a well-documented example is*

---

## A note on register

The vocabulary above is not uniformly "band 8". It is deliberately mixed: everyday words (*envelope*, *window*, *harness*) used with precision alongside less common ones (*confabulate*, *metamorphic*, *forensic*). This is what high-band English actually looks like — not a parade of long words but an accurate word chosen for each slot. The IELTS examiners who award band 8 and above describe it as "a wide range of vocabulary used with flexibility and precision"; they emphatically do not describe it as "many rare words". When you draft your own answers, prefer the ordinary word in its precise sense over the rare word in its approximate one. That instinct, more than any list, is what will move your Speaking and Writing bands past 7.5.
