# IELTS × System Design × PhD — 12-Week Domain Curriculum

> *"The technical world you already know becomes the English classroom."*

**Owner:** Oluwabori · **Issued:** 2026-10-06 · **Target band:** IELTS Academic **8.0 overall, no component below 7.5**
**Window:** 2026-10-06 → 2027-01-26 (12 weeks) · aligned to UCL cycle 1 (12 Feb 2027)

---

## 0 · Why this exists

Generic IELTS prep teaches you to speak and write about tourism, pollution, and hobbies. That is useful for the test and *entirely wasted* for the next five years of your life. The programme that follows is designed to serve three goals at once:

1. **IELTS 8.0** — fluent, precise academic English across all four skills.
2. **PhD interview readiness** — the ability to defend a research proposal, discuss methodology, and answer hostile technical questions in English for 20–30 minutes without visible strain.
3. **Senior system-design communication** — the register in which Staff+ engineers explain architecture clearly, as distinct from merely correctly.

The programme replaces every generic IELTS topic with a topic from your actual PhD domain. The same substance is then rotated through four surfaces each week:

| Surface | What it drills |
|---|---|
| **System Design study block** | Structural knowledge — the thing itself |
| **IELTS Speaking (Part 2 + Part 3)** | Spoken fluency under time pressure |
| **IELTS Writing (Task 2 + Design-Doc)** | Written coherence, lexical precision, argument structure |
| **PhD interview question** | Methodological framing — what you would *do* about it |

This "same substance, four surfaces" method is the hinge of the programme. One week of domain reading pays off four times.

---

## 1 · Target band and the gap it closes

**Formal minimums:**

| Programme | Overall | Each component |
|---|---|---|
| UCL CS (Level 1) | 6.5 | 6.0 |
| Imperial Computing (Standard) | 6.5 | 6.0 |
| Imperial Computing (Higher) | 7.0 | 6.5 |
| York EECS graduate | 7.0 | (programme page does not specify) |

**Target band — deliberately well above every minimum:**

| Component | Target |
|---|---|
| Listening | **8.5** |
| Reading | **8.5** |
| Writing | **7.5** |
| Speaking | **7.5** |
| **Overall** | **8.0** |

Rationale: the examiner's definition of 7.5+ Speaking is *"flexible use of a wide range of language, extended discourse on abstract topics, errors rare and non-impeding"*. That is **precisely** the discourse profile a PhD interview expects. Train for the interview; the band falls out of it.

---

## 2 · The weekly rhythm (unchanged shape, new content)

| Day | Minutes | What |
|---|---|---|
| Mon | 120 | **Domain reading** + System Design study block (new concept, model paragraph, vocab bank) |
| Tue | 90 | **IELTS Speaking Part 2** cue card on the week's domain (recorded) + 30 min writing drill |
| Wed | 120 | **IELTS Speaking Part 3** discussion + Reading practice (one full test) |
| Thu | 90 | **IELTS Writing Task 2** on the week's domain (timed, 40 min) + 30 min Listening |
| Fri | 90 | **Design-Doc drill** (60 min, in the app) + 30 min Speaking recap |
| Sat | 120 | **PhD interview mock** on the week's domain (recorded) + 60 min Reading / Listening test |
| Sun | 60 | Weekly retro + glance at next week's domain preview |

**Non-negotiables:** Speaking daily, Writing Task 2 at least twice weekly, Friday Design-Doc, Sunday retro.

---

## 3 · The 12-domain map

| Wk | Domain | Hinge concept | Four-way anchor topic |
|----|---|---|---|
| 1 | **Distributed Systems** | Partial failure, CAP, consensus | Fault tolerance in financial infrastructure |
| 2 | **Microservices Architecture** | Service boundaries, saga, idempotency | Order of operations across services |
| 3 | **Event-Driven Architecture (Kafka)** | At-least-once + idempotent consumer | Kafka in high-volume payments |
| 4 | **Financial System Architecture** | Authorisation → settlement → reconciliation | Payment platform under provider outage |
| 5 | **Database Architecture** | ACID, isolation levels, replication | SQL vs NoSQL for a ledger |
| 6 | **Caching & Performance** | TTL, invalidation, stampede | High-throughput financial read path |
| 7 | **Reliability Engineering** | SLO, error budget, chaos | Availability vs consistency, when it matters |
| 8 | **AI Infrastructure** | Inference economics, model routing | Why not always use the largest model |
| 9 | **AI Agents** | Bounded autonomy, HITL, tool permissions | Autonomous financial agents under mandate |
| 10 | **AI Safety & Verification** | Formal + runtime verification, invariants | Deterministic rails under a probabilistic brain |
| 11 | **Cybersecurity** | Zero trust, prompt injection, audit logs | Security risk of AI agents touching bank APIs |
| 12 | **Web2 × Web3 Financial Architecture** | Finality, bridges, oracles | Risks of financial flow spanning both worlds |

The thesis-shaped sentence that *stitches all twelve together*:

> *"Engineering reliable AI-native distributed systems for autonomous financial transaction processing."*

Each week brings one piece of that sentence into sharp focus.

---

## 4 · WEEK 1 — Distributed Systems (worked example, in full)

This week is the template. Later weeks follow the same structure.

### 4.1 Domain reading — the hinge concepts

A **distributed system** is a collection of independent machines that cooperate over a network to present the illusion of a single service. The *abiding challenge* is that none of the convenient properties of a single process — shared memory, instantaneous communication, synchronous failure — survives the network boundary. Messages are lost or reordered, clocks drift, nodes fail without warning, and *partial failure* becomes the default state against which every design must be measured.

Two theorems anchor the field. **CAP** states that, during a network partition, a system must choose between consistency and availability — it cannot keep both. **FLP impossibility** states that no deterministic consensus algorithm can guarantee progress in an asynchronous network with even one faulty node. The intellectual tradition that has grown around these constraints — Lamport clocks, Paxos, Raft, quorum reads, consistent hashing, vector timestamps — is not academic trivia but a *set of hard-won techniques* for reasoning in the presence of uncertainty.

**Fault tolerance** is best thought of as a *design posture*, not a feature: redundancy, isolation, retry with backoff, bulkheads, and circuit breakers all contribute. No amount of patching reproduces what careful design confers. The practical skill is the discipline to enumerate failure modes *before* writing the happy path.

**Consistency** is a *per-operation contract*, not a system-wide property. Linearisability is strongest and most expensive; eventual consistency is cheapest and often enough. The best designers aspire to the *weakest guarantee that correctness permits*.

**Idempotency** is the single property that makes retries safe. In a world of at-least-once delivery, exactly-once is a myth; what one actually ships is at-least-once delivery with idempotent handlers.

### 4.2 Vocabulary bank (30 items — add to Vocab app)

| Word | POS | Meaning | Example |
|---|---|---|---|
| partition | n. | a split in the network isolating subsets of nodes | *Under partition, we must choose between availability and consistency.* |
| quorum | n. | minimum nodes required to proceed | *A write commits once a quorum of replicas acknowledges it.* |
| replica | n. | a copy of data held on a different node | *Three replicas across three availability zones is a common configuration.* |
| topology | n. | the arrangement of nodes and connections | *Mesh and ring topologies tolerate failure differently.* |
| asynchronous | adj. | not waiting for a response | *Asynchronous messaging decouples producers from consumers.* |
| crash-fault | n. | a failure in which a node simply stops | *Most consensus algorithms address crash faults; Byzantine faults are harder.* |
| byzantine | adj. | (of a fault) actively malicious or arbitrary | *Byzantine fault tolerance is only worth the overhead in adversarial settings.* |
| consensus | n. | agreement among nodes on a shared value | *Raft and Paxos solve consensus under crash-fault assumptions.* |
| linearisable | adj. | behaving as if operations happen at a single instant | *Linearisable reads are expensive — ask for them only when necessary.* |
| converge | v. | arrive at the same state eventually | *Replicas converge once writes stop and messages are delivered.* |
| stale | adj. | (of a read) returning an older value | *Stale reads are acceptable for analytics, catastrophic for payments.* |
| monotonic | adj. | never going backward | *A monotonic clock is essential for correct timeouts.* |
| idempotent | adj. | repeatable without further effect | *Idempotent endpoints make retry logic safe.* |
| redundant | adj. | duplicated for safety | *Redundant links keep the service alive during a cable cut.* |
| bulkhead | n. | isolation boundary limiting blast radius | *Bulkheads prevent one slow dependency from exhausting all threads.* |
| graceful | adj. | (of degradation) controlled and still usable | *Graceful degradation returns a reduced service rather than no service.* |
| backoff | n. | strategy of waiting longer between retries | *Exponential backoff with jitter avoids retry storms.* |
| saturate | v. | fill to capacity | *Without a bulkhead, a slow caller can saturate the thread pool.* |
| scalability | n. | the ability to grow with load | *Horizontal scalability is cheaper than vertical scalability past a point.* |
| resilience | n. | the ability to recover from failure | *Resilience is a design property, not a configuration flag.* |
| availability | n. | the proportion of time the system is reachable | *Four nines of availability allows roughly fifty minutes of downtime a year.* |
| throughput | n. | work completed per unit time | *Throughput and latency are often at odds.* |
| latency | n. | time between request and response | *Tail latency matters more than mean latency in user-facing systems.* |
| bottleneck | n. | the slowest component that caps the whole system | *The ledger write is almost always the bottleneck in a payment path.* |
| contention | n. | competition for a shared resource | *Row-level contention on a hot account kills throughput.* |
| failover | n. | automatic switch to a backup | *Failover testing is only meaningful in production-shaped environments.* |
| hinted-handoff | n. | technique of storing a write for an unavailable replica | *Hinted handoff preserves durability while a replica is down.* |
| split-brain | n. | two sides of a partition both believing they are primary | *Fencing tokens are the standard defence against split-brain.* |
| degradation | n. | reduction in service quality | *Degradation beats outage, every time.* |
| failure domain | n. | the scope within which a single fault can cause damage | *A good design keeps failure domains small and well-labelled.* |

### 4.3 Four-way remix — one topic, four surfaces

**Hinge topic:** *Fault tolerance in a payment system when a downstream bank becomes unavailable.*

#### Surface A — System Design study block (Monday, 90 min)

Design a payment service that remains operational when its downstream bank integration starts failing. Cover: timeout and retry policy with exponential backoff and jitter; circuit breaker tripping at a failure-rate threshold; graceful degradation to a "pending" state for transactions that cannot be confirmed; idempotency key handling so client retries do not duplicate charges; dead-letter queue for exhausted retries; observability (success rate per provider, latency distribution, breaker state); and the eventual reconciliation step that resolves pending transactions once the bank recovers.

Write the design doc end-to-end in the Writing app's **Design-Doc mode**. Target length ≥1000 words. Target rubric score ≥28/40 on this one — it is a Week 1 baseline.

#### Surface B — IELTS Speaking Part 2 cue card (Tuesday, 90 min)

> **Describe a complex technical system you have worked on that had to remain available even when parts of it were failing.**
>
> You should say:
> - what the system did and who used it
> - which parts could fail
> - how the system coped with those failures
> - and explain how you felt about the way it was designed.

Record a 2-minute take. Transcribe it (Otter). Listen back once. Ask: did I describe the system in *plain* English with precise technical nouns in the right places, or did I retreat into jargon? High-band speaking of a technical topic uses *few* technical words placed accurately — not many.

#### Surface C — IELTS Speaking Part 3 / PhD interview questions (Wednesday, 60 min)

Record 2–3 minute answers to each.

1. *"When computer systems become more complex, they tend to fail in more interesting ways. Why does this happen, and what can be done about it?"*
2. *"Some engineers argue that absolute reliability in financial systems is impossible, and the honest goal is managed failure. Do you agree?"*
3. **(PhD-shaped)** *"In your proposed research on autonomous financial systems, how would you characterise the trade-off between availability and consistency, and would your framework take a different position on that trade-off than existing systems?"*
4. **(PhD-shaped)** *"How does the presence of a machine-learned component change the fault-tolerance analysis of a payment system?"*

For (3) and (4), the right register is the model paragraph in §9 below.

#### Surface D — IELTS Writing Task 2 prompt (Thursday, 40 min)

> *"Modern digital services depend on networks of computers that may fail at any time. Some argue that the pursuit of reliability has become so expensive that it now holds back innovation. To what extent do you agree?"*

Write ≥260 words. Opinion-led — commit in the introduction and defend. The temptation to list ("firstly … secondly … finally") is strong and will cap you at band 6.5; use the discourse moves (hedge, extend, pivot) from the phrase bank in [research-ielts-prep.md](research-ielts-prep.md). Grade yourself against the four descriptors; name your two weakest paragraphs.

#### Surface E — Design-Doc drill (Friday, 60 min)

Pick one from the Writing app's design-doc list — the Chat system (Week 2 preview) or the Payment ledger — and run the 60-minute timer. The point here is less to invent and more to *write at speed with full structure*. Target: all eight sections populated, ≥900 words, rubric ≥24/40.

### 4.4 Reading-passage practice (Saturday morning, 60 min)

Use the hinge-concept paragraphs in §4.1 as your IELTS Reading passage. Set a 20-minute timer. Produce five questions in each of these formats, then answer them from the passage:

- 2× True / False / Not Given
- 1× Matching Headings (invent 4 heading options for the 4 paragraphs; pick the right pairing)
- 1× Multiple choice (4 options, 1 correct)
- 1× Summary completion (a 3-sentence summary with 3 blanks drawn from the passage)

If generating your own questions feels circular, swap this slot for a Cambridge IELTS 18 passage. The important thing is not the specific passage but the drill rhythm.

### 4.5 PhD-interview mock (Saturday afternoon, 60 min)

Record a continuous 15–20 minute monologue + Q&A on this scenario:

> *"Walk me through how you would introduce an autonomous AI agent into a Nigerian payment switch — Remita, say — without compromising settlement correctness. I want you to be concrete: what the agent decides, what it does not decide, how its decisions are bounded, what the audit story looks like, and where the model would most plausibly go wrong."*

This is the Week 1 version of the question you will likely be asked at UCL / York. Grade yourself on three axes:

1. **Technical content** — did you commit to specific choices, or did you hedge throughout?
2. **English register** — band 7.5+ discourse markers, varied sentence structure, errors infrequent and non-impeding?
3. **PhD framing** — did you connect the engineering choices back to a research question, or did you merely describe a product?

### 4.6 Sunday retro (30 min)

Three sentences:

- *What improved this week — evidence not vibes.*
- *What is stuck — name the specific pattern or leak.*
- *Next week's one focus.*

Add new vocab from the week to the app's Vocab bank. Preview Week 2 (Microservices).

---

## 5 · WEEKS 2 – 12 — scaffolded in the four-way format

Each week below gives the hinge topic + one prompt per surface. Expand to the full Week 1 format on the day: domain reading, vocab bank, four-way remix.

### Week 2 — Microservices Architecture

**Hinge:** Order-of-operations across services; sagas; distributed transactions

- **System Design** — Design an order-fulfilment system across three microservices (orders, inventory, payments). Explain where you place the saga and how you compensate.
- **Speaking Part 2** — *Describe a project where you had to split a single system into separate parts. You should say what the parts were, why you split them, how they communicated, and whether you would do it the same way again.*
- **Speaking Part 3** — *"Breaking a system into smaller pieces sounds attractive but introduces costs that are easy to overlook. What are they?"*
- **Writing Task 2** — *"Some engineers believe that organisations overuse the microservice pattern and would be better served by simpler, more cohesive systems. Discuss both views and give your opinion."*
- **PhD interview** — *"How would an autonomous AI agent change the trade-off between orchestration and choreography in a payment saga?"*

### Week 3 — Event-Driven Architecture (Kafka)

**Hinge:** At-least-once delivery + idempotent consumer

- **System Design** — Design the event spine for a payment processor. Partitions, consumer groups, offset commit strategy, DLQ, replay, schema evolution.
- **Speaking Part 2** — *Describe a time you had to redesign a system so it could handle a much larger volume of work.*
- **Speaking Part 3** — *"Why is it so difficult to guarantee that each message is processed exactly once?"*
- **Writing Task 2** — *"Event-driven systems are praised for their flexibility but criticised for their complexity. Discuss both views and give your opinion."*
- **PhD interview** — *"If your autonomous agent subscribes to the same event stream humans do, what new failure modes does that introduce, and how would your research address them?"*

### Week 4 — Financial System Architecture

**Hinge:** Authorisation → settlement → reconciliation

- **System Design** — Design a payment gateway from API edge to downstream processor, including the risk engine, the ledger, and the reconciliation worker.
- **Speaking Part 2** — *Describe a time you used a digital payment service that went wrong. Explain what happened, how you reacted, and what you learned about how such systems work.*
- **Speaking Part 3** — *"When something goes wrong in a digital payment, who should bear the responsibility — the user, the bank, or the technology provider?"*
- **Writing Task 2** — *"Financial institutions should increasingly automate payment decisions using artificial intelligence. To what extent do you agree?"*
- **PhD interview** — *"How would you introduce autonomous AI into a payment infrastructure without compromising settlement correctness?"*

### Week 5 — Database Architecture

**Hinge:** ACID, isolation, replication, sharding

- **System Design** — Choose a storage topology for a double-entry ledger that must sustain 10 k writes/s and support strict audit queries.
- **Speaking Part 2** — *Describe a technology you use every day that you believe most people do not fully understand.*
- **Speaking Part 3** — *"Does the way information is stored really matter, as long as the service feels fast to the user?"*
- **Writing Task 2** — *"The amount of personal and financial data stored by companies has grown enormously in the last decade. Some argue this is a necessary foundation of modern services, others that it is a looming risk. Discuss both views and give your opinion."*
- **PhD interview** — *"When would you prefer PostgreSQL to MongoDB for a financial-settlement system, and what properties specifically drive that preference?"*

### Week 6 — Caching & Performance

**Hinge:** TTL, invalidation, cache stampede, thundering herd

- **System Design** — Design a caching layer for a high-throughput account-balance read path serving 50 k QPS.
- **Speaking Part 2** — *Describe a time waiting for something made a strong impression on you.*
- **Speaking Part 3** — *"People today expect digital services to respond almost instantly. Is this expectation reasonable?"*
- **Writing Task 2** — *"Modern businesses are judged as much on the speed of their services as on their correctness. To what extent is this a healthy development?"*
- **PhD interview** — *"How would risk-adaptive inference affect your caching strategy for AI-driven decisions in a payment flow?"*

### Week 7 — Reliability Engineering

**Hinge:** SLO, error budget, incident response, chaos engineering

- **System Design** — Define SLIs, SLOs, and the alerting policy for an autonomous payment router. Specify the burn rates that trigger paging vs ticketing.
- **Speaking Part 2** — *Describe a time something you depended on failed unexpectedly.*
- **Speaking Part 3** — *"Is it reasonable to accept that complex systems will fail some of the time, and plan for failure instead of trying to prevent it?"*
- **Writing Task 2** — *"Increasing automation in critical services such as healthcare and finance brings efficiency but also makes failures more severe when they occur. Discuss both views and give your opinion."*
- **PhD interview** — *"In your research, where does the responsibility for the system's error budget sit when an autonomous AI agent is one of the decision-makers in the loop?"*

### Week 8 — AI Infrastructure

**Hinge:** Inference economics, model routing, latency vs quality

- **System Design** — Design a model-serving layer that routes requests between a small, cheap model and a larger, slower one based on risk and uncertainty.
- **Speaking Part 2** — *Describe a technology that is becoming more capable each year, and the effect it is having on the people who use it.*
- **Speaking Part 3** — *"Why do people sometimes resist using more powerful tools even when they are available?"*
- **Writing Task 2** — *"Artificial intelligence is becoming cheaper and more capable every year. Some argue that it should be used in every possible context; others caution against overuse. Discuss both views and give your opinion."*
- **PhD interview** — *"Explain your notion of an 'intelligence budget' and how it would be enforced at inference time."*

### Week 9 — AI Agents

**Hinge:** Bounded autonomy, tool permissions, human-in-the-loop

- **System Design** — Design an autonomous customer-dispute agent for a payment platform. Specify the mandate schema, the escalation ladder, and the audit event stream.
- **Speaking Part 2** — *Describe a situation in which you had to trust someone else to make a decision on your behalf.*
- **Speaking Part 3** — *"How much authority should software be given to act on a person's behalf without their explicit approval?"*
- **Writing Task 2** — *"Some researchers argue that autonomous AI agents should be allowed to make financial decisions without human intervention. Others believe that human oversight is essential. Discuss both views and give your opinion."*
- **PhD interview** — *"Should an AI agent be allowed to execute financial transactions autonomously, and under what constraints?"*

### Week 10 — AI Safety & Verification

**Hinge:** Deterministic rails under a probabilistic brain; invariants, policy engines

- **System Design** — Design the verification layer that sits between an LLM-based planner and a financial ledger. Enumerate the invariants it enforces and the actions it blocks.
- **Speaking Part 2** — *Describe a rule or principle that you believe should never be broken.*
- **Speaking Part 3** — *"How might society decide which decisions machines should be allowed to take, and which must remain human?"*
- **Writing Task 2** — *"As AI systems take on more autonomous roles, their decisions can be difficult to explain and verify. To what extent should explainability be a legal requirement in high-stakes applications?"*
- **PhD interview** — *"Why might deterministic verification be necessary when AI is used in financial systems, and what verification techniques are you planning to study?"*

### Week 11 — Cybersecurity

**Hinge:** Zero trust, prompt injection, agent identity, audit logs

- **System Design** — Design the authentication, authorisation, and audit layer for a fleet of AI agents calling external bank APIs on behalf of tenants.
- **Speaking Part 2** — *Describe a time your personal information or security was at risk.*
- **Speaking Part 3** — *"Who should bear the greater responsibility for digital security — the companies that build the systems or the people who use them?"*
- **Writing Task 2** — *"The rise of AI agents has introduced new categories of security risk that older defences were not designed for. Discuss the main risks and the measures that might address them."*
- **PhD interview** — *"What are the specific security risks of allowing AI agents to access financial APIs, and how might your research framework constrain them?"*

### Week 12 — Web2 × Web3 Financial Architecture

**Hinge:** Finality, bridges, oracles, cross-chain settlement

- **System Design** — Design a settlement system that moves value between a Nigerian bank account and a stablecoin wallet, including the oracle, the custody model, and the reconciliation story.
- **Speaking Part 2** — *Describe a change in the way people pay for things that you have noticed in the last few years.*
- **Speaking Part 3** — *"What are the arguments for and against replacing cash with purely digital forms of money?"*
- **Writing Task 2** — *"Some economists argue that blockchain-based financial infrastructure is a genuine advance; others see it as an unnecessary complication of problems that traditional systems already solve. Discuss both views and give your opinion."*
- **PhD interview** — *"What additional risks arise when autonomous AI agents operate across traditional banking rails and public blockchain networks simultaneously, and how would your framework address them?"*

---

## 6 · The engineer-English translation drill (built in to every week)

Your single biggest IELTS risk is not vocabulary — it is **over-complexity**. You know ten layers of detail where IELTS rewards clear two-layer explanations. Every week, pick one sentence from your System Design study block and run it through this translation:

**Engineer form:**
> *"The consumer commits offsets after the database transaction to prevent inconsistent state."*

**Academic / IELTS form:**
> *"The system should record the transaction only after the database operation has successfully completed. This reduces the risk of acknowledging an event that has not actually been processed."*

Rules:

- Replace every acronym with its idea.
- Replace every verb-nominalisation with a verb (*"commits offsets"* → *"records the position"*).
- Add one clarifying clause explaining *why*, not just *what*.
- Keep sentences short — 15–22 words is the sweet spot.

Do five of these a week. Keep them in a running file. By Week 4 you will have reshaped your reflex.

---

## 7 · Progress tracking

Use the app's **Sessions log** for drills and the **Vocab bank + Trivia** for lexis. For band tracking, do one full IELTS mock (all four skills) at the end of **Week 4, Week 8, and Week 12** and record component bands against the targets in §1.

**Milestones:**

| By end of | Writing / Speaking | Reading / Listening |
|---|---|---|
| Week 4 | 6.5+ consistently; comfortable with discourse moves | 7.5+ (hit the easy ceiling early) |
| Week 8 | 7.0+ consistently; opinion-led essays natural | 8.0+ |
| Week 12 | **7.5+** consistently; one Writing or Speaking at 8.0 | **8.5+** |

If Week 8 writing is still 6.5, book a paid examiner mock (E2Language or interviewing.io / a verified IELTS tutor on italki) — a single external data point is worth a fortnight of self-grading.

---

## 8 · Rolling into the PhD application

| Month | PhD-side move | IELTS-side state |
|---|---|---|
| **Oct 2026** (now) | Supervisor outreach (UCL, Imperial, York); draft research proposal v1; **CSC FSB application ~14 Oct** | Week 1–4 of this plan — foundation; take diagnostic now |
| **Nov 2026** | Supervisor confirmations; proposal v2 | Week 5–8 — building to 7.0; first paid mock |
| **Dec 2026** | Funding paperwork; proposal v3 | Week 9–12 — building to 7.5+; second paid mock |
| **Jan 2027** | Final materials; **book IELTS test** for mid-Jan | Full official mock Week 12; test taken end of January |
| **Feb 2027** | **UCL cycle 1 (12 Feb) submission** | Score received; attach to applications |
| **Mar – Apr 2027** | UCL cycle 2, Imperial, York; **interviews** | Interview practice using Week 9–12 PhD mocks |
| **Oct 2027** | **PhD start** (if funded) | — |

The two tracks are deliberately parallel, not sequential. Nothing in the IELTS plan blocks a proposal draft; nothing in the PhD plan blocks a Writing session.

---

## 9 · The target-English model paragraph (study this one closely)

This is the register we are training toward. Read it aloud three times; find the moves.

> *"I would not allow the model to directly mutate the financial ledger. Instead, I would separate probabilistic decision-making from deterministic execution. The AI agent could propose an action, but a policy and verification layer would evaluate the proposed action against authorisation constraints and financial invariants before execution. The amount of verification would then be proportional to the risk and financial consequence of the decision."*

**What makes it band 8:**

- **Commits in the first sentence** — *"I would not allow"*, not *"I think it might be better if the system did not …"*
- **Pivots cleanly with "Instead"** — a discourse marker doing real work.
- **Precise distinctions** — *"probabilistic decision-making"* vs *"deterministic execution"* is one idea in six words.
- **Technical nouns placed accurately, not stacked** — four domain nouns in a paragraph of fifty-six words.
- **Final sentence states a principle** — *"proportional to the risk and financial consequence of the decision"* elevates the whole paragraph from description to position.
- **Zero wasted words.** Nothing could be cut without losing meaning.

Your own answers should sit here. Not with more jargon. With *more precise* jargon placed *less frequently* and surrounded by clear scaffolding.

---

## 10 · Where to find things

- **Weekly plan structure:** this file.
- **Concept dictionary (20 topics, 5 clusters):** [research-ielts-prep.md](research-ielts-prep.md) — the cross-reference for any topic listed above.
- **Live drill app:** `~/Documents/ielts-sda-prep/app` — `npm run dev` → http://localhost:5173/
- **80-topic SD syllabus:** keep as Appendix A below; dip into it when a weekly domain overlaps with a tier.
- **Original MAANG-oriented plan:** [PLAN.md](../PLAN.md) — preserved for reference below the updated header.

---

## Appendix A — 80-topic System-Design syllabus (reference)

Not a schedule — a **recall list**. By the end of Week 12 you should be able to give a 2-minute spoken definition for each.

**Tier 1 — Foundations:** scalability · availability · consistency · CAP · ACID · database indexing · caching · load balancing · REST APIs · messaging

**Tier 2 — Distributed systems:** Kafka · event-driven architecture · event sourcing · CQRS · saga · transactional outbox · idempotency · distributed transactions · service discovery · circuit breakers

**Tier 3 — Production architecture:** observability · distributed tracing · rate limiting · backpressure · disaster recovery · multi-region systems · zero-downtime deployment · chaos engineering · Kubernetes · cloud architecture

**Tier 4 — Financial architecture:** payment gateway · payment switch · digital wallet · double-entry ledger · settlement system · reconciliation system · fraud detection system · banking API · cross-border payments · RTGS

**Tier 5 — AI infrastructure:** LLM inference · model serving · model routing · adaptive inference · GPU scheduling · KV-cache management · agent orchestration · agent memory · tool calling · RAG

**Tier 6 — AI safety:** AI authorisation · agent identity · bounded autonomy · runtime verification · formal verification · AI guardrails · policy engines · human-in-the-loop · AI observability · agent auditing

**Tier 7 — Web3:** blockchain architecture · smart contracts · wallet architecture · oracle systems · cross-chain messaging · bridges · DeFi · MEV · on-chain identity · Web2/Web3 security convergence

**Tier 8 — Your thesis:** risk-adaptive inference · intelligence budgets · risk-aware model routing · consequence-aware autonomy · verification allocation · financial invariants · safe autonomy · AI decision auditability · risk-adjusted inference efficiency · autonomous financial systems

---

## Appendix B — Discourse-move phrase bank (quick reference)

Lifted from [research-ielts-prep.md §Phrase bank](research-ielts-prep.md); kept here for daily use.

**Hedge:** *arguably · on balance · it is fair to say · there is a case to be made that · with suitable qualification*
**Extend:** *not only … but also · which is why · the deeper point is that · what is more striking is · this generalises to*
**Pivot:** *that said · it does not follow that · a related but distinct question is · granted — but …*
**Signal depth:** *lends shape to the trade-off · bears a family resemblance to · admits of degree · stands at the intersection of*
**Signal commitment:** *the right stance here is · on this I would want to insist · the honest view is*
**Signal evidence:** *the empirical record suggests · the engineering experience is that · in practice*

---

## Appendix C — Rapid-start checklist (do this today)

- [ ] Open the Writing app, pick *"Design the TikTok For-You feed"* (or the Chat system); run the 60-min Design-Doc drill as the **Week 1 Monday system-design study block proxy**.
- [ ] Record a 5-minute monologue on *"a complex technical system you have worked on"* — raw Week 1 Speaking baseline.
- [ ] Transcribe it (Otter); count fillers; grade yourself against the four Speaking criteria.
- [ ] Add the 30 Week-1 vocabulary items from §4.2 into the app's Vocab bank.
- [ ] Run one 10-item Trivia round from the Vocab bank.
- [ ] Preview Week 2 (Microservices) for 15 minutes.
- [ ] Draft the first paragraph of your CSC FSB research-interest statement using the §9 model paragraph as a prose template.

Total time ≈ 3 hours. That is Week 1 Day 1. On we go.
