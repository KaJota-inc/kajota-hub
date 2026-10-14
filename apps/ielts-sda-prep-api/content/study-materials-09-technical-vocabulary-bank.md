# Technical Vocabulary Bank — Usage, Not Lists

*A word list is near-worthless; the band comes from **usage**. Each term below carries a one-line
gloss and a model collocation in a sentence you could actually say. Bank three per day into
sentences of your own. Italicised phrases are the collocations worth stealing wholesale.*

---

## Architecture

- **architecture** — the high-level structure of a system. *"The architecture cleanly separates
  decision-making from execution."*
- **component** — a distinct part with a defined role. *"Each component fails independently, so the
  design must contain the blast radius."*
- **subsystem** — a self-contained part of a larger system. *"The settlement subsystem is isolated
  from the user-facing path."*
- **interface** — the contract through which parts interact. *"A stable interface lets us change
  the implementation without breaking callers."*
- **dependency** — something a component relies on. *"The model is an expensive, unpredictable
  dependency, so we design around it."*
- **abstraction** — hiding detail behind a simpler surface. *"A good abstraction lets you reason
  about the system without holding every detail in mind."*
- **boundary** — where responsibility shifts from one part to another. *"I keep determinism at the
  boundary and trust the model only within it."*
- **integration** — making separate systems work together. *"The hard part of integration is
  reconciling two systems that fail in different ways."*

## Performance

- **latency** — the delay before a response. *"We trade a little latency for a far more reliable
  result."*
- **throughput** — volume handled per unit time. *"The design must sustain peak throughput without
  degrading."*
- **scalability** — capacity to grow with load. *"Horizontal scalability lets us add machines
  rather than rewrite the system."*
- **utilisation** — how fully a resource is used. *"High GPU utilisation keeps inference cost
  down."*
- **bottleneck** — the limiting stage. *"Instrumentation revealed the bottleneck was storage, not
  the model."*
- **overhead** — the cost a mechanism adds. *"Verification adds overhead, so we apply it in
  proportion to the risk."*
- **efficiency** — output relative to resource spent. *"Risk-adjusted efficiency — spending
  compute where consequence is highest — is the thesis in a phrase."*

## Reliability

- **resilience** — recovering gracefully from failure. *"Resilience is designing for partial
  failure, not pretending it won't happen."*
- **availability** — the share of time a system is usable. *"We chose availability over strict
  consistency for non-critical data."*
- **consistency** — all parts agreeing on the data. *"Strong consistency is costly; I reserve it
  for the ledger."*
- **redundancy** — spare capacity that absorbs failure. *"Redundancy turns a component failure into
  a non-event."*
- **recovery** — returning to normal after a fault. *"A low recovery time matters more than a rare
  failure."*
- **degradation** — a controlled drop in service. *"Graceful degradation means the feature gets
  worse, not unavailable."*
- **failure domain** — the scope one failure can affect. *"Isolating failure domains keeps one
  outage from cascading."*

## Security

- **authentication** — proving who you are. *"Authentication establishes identity; authorisation
  decides what that identity may do."*
- **authorisation** — what an identity is permitted to do. *"The agent's authorisation is bounded
  by an explicit spend mandate."*
- **confidentiality / integrity** — secrecy / non-alteration of data. *"Finance needs both
  confidentiality of balances and integrity of the ledger."*
- **privilege** — the level of access granted. *"Least privilege limits the damage a compromised
  key can do."*
- **vulnerability / threat / attack surface** — a weakness / an adversary / the exposed area.
  *"Giving an agent API access widens the attack surface considerably."*
- **prompt injection** — hostile instructions hidden in input. *"We treat retrieved text as
  untrusted precisely because of prompt injection."*

## AI

- **inference** — running a trained model to get an output. *"Inference cost scales with every
  request, so we tier the models."*
- **reasoning** — the model's step-by-step working toward an answer. *"The model handles reasoning;
  the orchestrator handles control."*
- **uncertainty / calibration** — how unsure the model is / whether that matches reality. *"A
  well-calibrated model knows when it doesn't know — which is when we escalate."*
- **autonomy** — acting without per-decision sign-off. *"Autonomy should be bounded by the
  consequence of being wrong."*
- **verification** — checking an output against rules. *"Verification is deterministic even when the
  decision is probabilistic."*
- **interpretability** — how understandable the model's behaviour is. *"I prefer grounding a
  decision in evidence over trusting the model's own narration."*
- **evaluation** — systematic measurement of quality. *"Evaluation lives inside the workflow, not
  as a pre-launch checkbox."*

## Finance

- **settlement** — the final, irreversible transfer of value. *"AI may decide, but settlement must
  never violate a deterministic invariant."*
- **transaction** — a single unit of financial work. *"Each transaction has a lifecycle:
  authorisation, processing, settlement, reconciliation."*
- **ledger** — the authoritative record of balances. *"I would never let a model mutate the ledger
  directly."*
- **reconciliation** — confirming two records agree. *"Reconciliation catches the discrepancies
  that eventual consistency allows."*
- **exposure** — the amount at risk. *"Verification effort should track financial exposure."*
- **systemic risk** — risk that one failure endangers the whole system. *"Concentrating autonomy
  without limits introduces systemic risk."*

## Research

- **hypothesis** — a testable claim. *"My hypothesis is that risk-adaptive routing beats a static
  rules engine on cost without breaching safety."*
- **methodology** — how the study is conducted. *"The methodology compares a learned policy against
  a trivial baseline first."*
- **empirical** — grounded in observation. *"Model behaviour is validated empirically, since it
  cannot be proven."*
- **baseline / ablation** — the trivial comparator / removing a part to test its effect. *"Always
  run the null hypothesis before tuning inside the system."*
- **contribution** — what the work adds that didn't exist. *"My contribution is a hybrid-assurance
  framework: verify the envelope, validate the core."*
- **limitation / generalisability** — where it falls short / how far it transfers. *"I'd be candid
  about the limitation: the results may not generalise beyond payment routing."*

---

## How to deploy these in the exam

- **Speaking:** aim for one precise term per idea, *explained in plain words* — never a string of
  jargon. One well-used term beats five name-dropped.
- **Writing Task 2:** the Reliability, AI, and Research sets give you the lexical range examiners
  reward; the Finance set gives you *topic-specific precision* most candidates lack.
- **Viva:** the Research set is your register for discussing contribution and limitation — the two
  things a panel probes hardest.
