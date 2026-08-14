# Template Readiness Contract

> **Status:** Normative template-level readiness contract  
> **Applies to:** `production-ai-runtime-template`  
> **Owns:** the definition of when the reusable template may be called **READY**  
> **Does not own:** current milestone/next action (`.ai/handoff.md`), detailed architecture semantics (`architecture.md` / `architecture-rules.md`), or project-specific requirements (`.ai/projects/<project>/`)  
> **Target:** assignment-ready reusable production AI / agent runtime baseline  
> **Agent rule:** understand the intent, inspect actual evidence, improve the design when justified, and never silently rewrite normative architecture.

---

## 1. Why this document exists

This repository already has:

- an approved target architecture;
- architecture invariants;
- prompt, agent-behaviour, and controlled-tool contracts;
- security, testing, evaluation, observability, and error-handling policies;
- a deferred-capability register;
- milestone and documentation governance.

Those documents explain **how the template should be engineered**.

They do not, by themselves, answer one critical question:

> **When is the template itself finished enough to be called READY?**

This document answers that question.

It is the template-level **finish line**.

It prevents two opposite failure modes:

1. **Stopping too early**  
   The repository has useful code and documentation, but still requires architectural surgery before a real AI assignment can be implemented safely.

2. **Never stopping / overengineering**  
   The repository keeps adding RAG backends, databases, brokers, Kubernetes, multiple model providers, generic tool systems, and other infrastructure that no real project has requested.

The template is READY when the mandatory baseline in this document is satisfied.

It is **not** required to implement every capability in
[`deferred-capabilities.md`](deferred-capabilities.md).

---

# 2. What we are trying to build

We are building a reusable **production-oriented AI / agent runtime template** that can be used as the starting point for different enterprise AI assignments without first undoing framework, vendor, or seed-domain coupling.

The intended template should let a new project begin approximately from:

```text
Project requirement
        ↓
project architecture decision
        ↓
Delivery Adapter
        ↓
optional Orchestration Adapter
        ↓
Application Core
        ↓
Application-owned Ports / Contracts
        ↓
Outbound / Driven Adapters
```

The current seeded Customer Support workflow is useful reference code.

It is **not** the product architecture.

The reusable template must make it possible to replace or omit:

- Customer Support domain behaviour;
- LangGraph;
- OpenAI;
- LangSmith;
- a retrieval backend;
- a persistence backend;
- deployment infrastructure;

without rewriting the application semantics that do not belong to those technologies.

---

# 3. What problem this template solves

The template exists to solve a recurring production-AI engineering problem:

> A prototype can call an LLM quickly, but production delivery becomes expensive when business semantics, prompts, framework state, provider SDKs, observability, retrieval, tools, and infrastructure are mixed together.

The template therefore aims to solve the following problems before a project starts.

## 3.1 Vendor coupling

Application behaviour must not depend directly on OpenAI SDK types or another provider SDK.

We want:

```text
Application Operation
        ↓
LLMPort
        ↓
OpenAI Adapter
```

not:

```text
Application / LangGraph Node
        ↓
OpenAI SDK
```

---

## 3.2 Framework coupling

LangGraph may orchestrate application operations, but it must not become the owner of reusable application semantics.

We want:

```text
LangGraph Node
        ↓
Application Operation
```

not:

```text
LangGraph Node
        =
Application Core
```

A future FastAPI path must be able to call the same Application Core without requiring LangGraph.

---

## 3.3 Prompt reproducibility

A production execution must be able to answer:

```text
Which exact prompt produced this result?
```

The answer must not be:

```text
whatever prompt was "production" at that moment
```

Prompt identity, revision, and content hash must be application-owned and traceable.

---

## 3.4 Untraceable AI execution

A production run must be correlatable across application execution, model invocation, logs, failures, and optional orchestration.

The application therefore owns an execution/correlation identity rather than depending on a vendor tracing object.

---

## 3.5 Unsafe model authority

Model output is probabilistic and untrusted.

The model must not:

- grant authorization;
- redefine policy;
- invent successful side effects;
- bypass deterministic rules;
- convert unverified content into application authority.

---

## 3.6 Uncontrolled side effects

Ordinary LLM inference and business/external actions are different paths.

```text
LLM inference
→ LLMPort
→ provider adapter
```

is not:

```text
ToolRequest
→ validation
→ authorization
→ controlled execution
→ ToolResult
```

The template must preserve that distinction.

---

## 3.7 Prototype-only testing

Production AI requires both:

```text
software correctness
+
AI behaviour evidence
```

`pytest` cannot prove semantic AI quality.

An LLM evaluation cannot prove deterministic software correctness.

The template must support both disciplines without conflating them.

---

## 3.8 Observability lock-in and unsafe logging

Tracing must not require application contracts to become LangSmith/OpenTelemetry contracts.

Observability also must not become automatic storage of:

- prompts;
- user messages;
- PII;
- secrets;
- retrieved documents;
- tool payloads;
- raw model output;
- hidden chain-of-thought.

---

## 3.9 Assignment rework

When a new assignment arrives, the first engineering task should be:

```text
understand requirements
→ activate justified capabilities
→ implement the project
```

not:

```text
remove CustomerSupport assumptions
→ untangle LangGraph
→ untangle OpenAI
→ invent prompt versioning
→ repair tests
→ then finally start the assignment
```

A READY template has already removed that structural tax.

---

# 4. Definition of READY

The template may be called:

```text
TEMPLATE BASELINE — READY
```

only when **all Mandatory Readiness Gates** in this document are satisfied.

READY means:

> The repository is a coherent, tested, documented, production-oriented baseline from which a real AI/agent project can begin without mandatory architectural rework.

READY does **not** mean:

- every possible enterprise capability exists;
- every future assignment needs no new architecture decision;
- RAG is implemented;
- a database is implemented;
- Kubernetes exists;
- multiple LLM providers exist;
- generic HITL/checkpointing exists;
- MCP exists;
- cloud infrastructure is complete for every deployment;
- all projects use LangGraph;
- all projects use agents.

Those are activated only when a real project requires them.

---

# 5. Readiness authority

This document owns:

- the mandatory baseline capability set;
- the definition of template READY;
- readiness acceptance gates;
- the distinction between READY requirements and deferred/project-specific capability.

It deliberately does **not** own:

- current deadlines;
- current milestone identifiers;
- current file/line defects;
- temporary migration decisions;
- today's repository debt list.

Those belong in handoff, milestone, project-status, or Git-backed evidence.

It does **not** duplicate the detailed semantics owned by other documents.

Use the appropriate authority for detail:

| Concern | Detailed authority |
| --- | --- |
| Architecture | `architecture.md` |
| Architecture invariants | `architecture-rules.md` |
| Deferred / optional capability | `deferred-capabilities.md` |
| Prompt semantics | `../contracts/prompt-lifecycle-contract.md` |
| Agent behaviour | `../contracts/agent-behavior-contract.md` |
| Controlled tools | `../contracts/tool-execution-contract.md` |
| Testing | `../engineering/testing-strategy.md` |
| AI evaluation | `../engineering/evaluation-strategy.md` |
| Security | `../engineering/security-principles.md` |
| Observability | `../operations/observability-strategy.md` |
| Error handling | `../operations/error-handling-strategy.md` |
| Current continuation / next action | `../handoff.md` |
| Git state / commit boundaries | Git |

If a readiness statement conflicts with a domain authority, surface the discrepancy.

Do not silently redefine the domain contract here.

---


# 6. How a future agent should use this document

This document is not intended to turn a future engineer or AI agent into a passive compliance checker.

Its purpose is to give the agent enough **problem context, architectural intent, decision rationale, and finish-line criteria** to make good decisions even when the current repository contains something we did not anticipate.

A capable future agent should be able to do two things at the same time:

```text
respect approved architecture
+
challenge an implementation or rule when evidence shows that it is wrong
```

The agent should optimize for the **problem we are trying to solve**, not for literal preservation of today's file structure.

## 6.1 Start from evidence, not documentation alone

Before proposing a material architecture/runtime change, inspect the actual repository.

Distinguish explicitly:

```text
FACT
= directly supported by repository / tests / configuration / approved requirement

INFERENCE
= conclusion derived from facts

ASSUMPTION
= unverified condition temporarily used for planning

DECISION
= chosen architecture/policy after alternatives and trade-offs were considered
```

Do not present an inference or assumption as a repository fact.

Git remains factual authority for repository/commit state.

The appropriate `.ai/` authority remains normative for approved architecture and policy.

When implementation and documentation disagree, surface the discrepancy rather than choosing whichever source is more convenient.

---

## 6.2 Positive intervention is expected

A future agent SHOULD intervene when repository evidence shows that:

- current runtime contradicts the architectural intent;
- a supposedly reusable boundary still leaks framework/provider/domain concerns;
- a readiness requirement is incomplete or internally inconsistent;
- a simpler architecture provides the same or stronger guarantees;
- an abstraction exists without a real caller or requirement;
- a repeated real project requirement exposes a genuine missing baseline capability;
- a previous decision creates unnecessary coupling, duplicated ownership, or unavoidable rework;
- tests validate implementation mechanics but fail to protect the intended behaviour;
- documentation has accidentally frozen a current implementation detail as a permanent architectural invariant.

The desired process is:

```text
inspect actual evidence
        ↓
identify discrepancy / opportunity
        ↓
classify FACT vs INFERENCE
        ↓
state the problem being caused
        ↓
identify affected readiness gate / contract
        ↓
compare realistic alternatives
        ↓
recommend KEEP / ADAPT / REPLACE / DEFER
        ↓
define impact and rollback
        ↓
architecture review
        ↓
implementation only after authorization
```

Do not silently "fix" architecture while implementing another milestone.

---

## 6.3 The agent should preserve intent, not accidental structure

Examples:

If the repository currently uses four OpenAI wrapper instances, the question is not:

> How do I preserve four wrappers forever?

The question is:

> What current behaviour/configuration must remain correct, and what is the simplest architecture that preserves it?

If retrieval currently lives inside a LangGraph execution path, the question is not:

> Does retrieval permanently belong to LangGraph?

The question is:

> Is that placement a deliberate reusable ownership decision, or simply current seeded placement that this milestone is not changing?

If a class exists in the adapter today, its existence alone does not prove that it belongs in an application port.

Current implementation surface:

```text
≠
required reusable contract surface
```

---

## 6.4 Prefer no change when no real problem exists

Positive intervention does not mean continuous redesign.

Do not invent changes simply because another pattern is fashionable or theoretically cleaner.

If the current design:

- respects ownership;
- satisfies the readiness contract;
- is testable;
- is safe;
- is understandable;
- does not create meaningful future rework;

then:

```text
KEEP
```

is a valid and often preferable architecture decision.

The goal is not maximum abstraction.

The goal is **minimum justified structure with correct production ownership**.

---

## 6.5 Required format when challenging an approved direction

When a future agent believes an approved direction should change, report at least:

```text
FACTS
What repository/project evidence triggered the concern?

CURRENT DECISION
What approved rule/design is being challenged?

PROBLEM
What concrete correctness, safety, coupling, reuse, or delivery problem does it cause?

AFFECTED READINESS GATES
Which part of this contract is affected?

OPTIONS
What realistic alternatives exist?

RECOMMENDATION
KEEP / ADAPT / REPLACE / DEFER

TRADE-OFFS
What do we gain and lose?

SCOPE
What files/contracts/milestones would be affected?

MIGRATION / ROLLBACK
Can the change be introduced or reverted safely?

STATUS
Architecture review required before implementation.
```

This prevents both blind obedience and uncontrolled redesign.

---

# 7. Decision priority hierarchy

When two or more technically valid designs compete, use this priority order unless a real project requirement justifies a different trade-off.

```text
1. Correct ownership and dependency direction
2. Safety, correctness, and explicit failure semantics
3. Reusability across genuinely plausible projects
4. Testability and operational visibility
5. Simplicity / smallest justified abstraction
6. Maintainability and explicit composition
7. Performance and cost when materially relevant
8. Extensibility for demonstrated future needs
```

These priorities are not independent checkboxes.

They are a trade-off hierarchy.

## 7.1 What this means in practice

Do not sacrifice:

```text
ownership
safety
testability
simplicity
```

for speculative extensibility.

Examples:

Prefer:

```text
one provider
behind a correct LLMPort
```

over:

```text
three providers
behind a premature routing framework
```

Prefer:

```text
explicit Python composition
```

over:

```text
DI container
```

when the container solves no real current complexity.

Prefer:

```text
project-specific RAG adapter when RAG is required
```

over:

```text
pre-installed universal vector stack
```

before a corpus/query/latency requirement exists.

Prefer:

```text
stable application-visible failure semantics
```

over:

```text
catch-all fallback that hides failures
```

even when the latter appears more "resilient".

---

## 7.2 Performance and cost are real, but evidence-driven

Latency, throughput, model cost, token cost, connection reuse, and infrastructure cost are production concerns.

They should influence architecture when they are material.

Do not prematurely optimize them without evidence.

A performance optimization that breaks ownership or makes behaviour harder to test requires strong justification.

---

## 7.3 Readiness is not architectural maximalism

A design is not more production-grade merely because it contains:

- more interfaces;
- more services;
- more agents;
- more queues;
- more databases;
- more cloud components.

Production-grade means the required system properties are intentional, measurable, testable, and owned by the correct layer.

---

# 8. Architectural tripwires and stop conditions

The following patterns are strong warning signals.

They do not automatically prove the design is wrong, but they require explicit inspection before implementation continues.

## 8.1 Ownership tripwires

```text
LangGraph node starts owning reusable application policy.
Application Core imports a provider/framework SDK.
Delivery code starts choosing models/providers.
GraphState becomes the required input contract of reusable application operations.
A provider adapter decides application authorization or business policy.
```

---

## 8.2 Abstraction tripwires

```text
A port mirrors every method of its current adapter.
A generic service exists only because "we may need it later".
A new base class has one implementation and no demonstrated boundary benefit.
A provider registry/model router appears before routing is a requirement.
A generic ToolExecutor appears before a controlled tool use case exists.
A RetrievalPort appears solely to make the architecture diagram look complete.
```

---

## 8.3 AI safety/correctness tripwires

```text
Model output is treated as authorization.
Model output is treated as proof that an external action succeeded.
Model output is treated as retrieval provenance without validation.
A deterministic policy check is moved into an LLM prompt.
An LLM failure is converted into apparent success.
A human-review requirement can be silently erased downstream.
```

---

## 8.4 Observability tripwires

```text
LangSmith/OpenTelemetry types enter Application Core contracts.
Raw prompts/messages/results are logged automatically.
Secrets or PII become normal telemetry fields.
Hidden chain-of-thought is requested as an operational artifact.
Tracing IDs become the application's only execution identity.
```

---

## 8.5 Project/template leakage tripwires

```text
One assignment's domain model becomes a global template contract.
Customer Support-specific behaviour becomes a reusable application abstraction.
A project-specific infrastructure choice becomes mandatory baseline infrastructure.
A deferred capability is activated because it is common/popular rather than required.
```

---

## 8.6 Delivery/process tripwires

```text
A milestone mixes architecture alignment with unrelated cleanup.
Implementation starts before ownership/contracts are decided.
Cursor/implementation agent is forced to choose architecture from an underspecified prompt.
Documentation is changed to describe desired behaviour before runtime implements it.
A milestone's next step repairs architecture introduced by the previous milestone.
```

When a tripwire appears:

```text
STOP scope expansion
        ↓
inspect evidence
        ↓
surface discrepancy
        ↓
decide architecture
        ↓
resume only with explicit scope
```

Do not work around a tripwire invisibly.

---

# 9. How to challenge this document itself

This document is normative.

It is **not infallible**.

It captures the best reusable-template understanding currently approved.

A future agent SHOULD challenge a readiness rule when strong repository evidence or repeated real-project evidence shows that the rule:

- solves the wrong problem;
- duplicates another boundary without adding protection;
- introduces more coupling than it removes;
- requires speculative infrastructure;
- prevents a simpler architecture with equal or stronger guarantees;
- conflicts with the approved template objective;
- has become obsolete because the runtime architecture materially evolved;
- repeatedly forces project-specific exceptions that reveal the baseline is wrong.

## 9.1 What is not a valid reason to challenge the contract

Do not weaken a rule merely because:

- implementation is inconvenient;
- a test currently fails;
- a vendor SDK encourages tighter coupling;
- a framework's example code uses a different pattern;
- a deadline makes architecture review feel expensive;
- another repository uses more infrastructure;
- a capability is currently popular.

Difficulty is not evidence that a readiness rule is wrong.

---

## 9.2 What to do when the contract itself appears wrong

Do not silently edit the contract and continue implementation.

Use:

```text
evidence
        ↓
identify affected rule
        ↓
explain why the current rule harms the template objective
        ↓
show alternatives
        ↓
show consequences for existing architecture/contracts
        ↓
recommend contract change
        ↓
explicit architecture review
        ↓
update normative docs
        ↓
then implementation
```

A future agent is allowed to say:

```text
"The current normative rule should change."
```

But must also explain **why** and what evidence supports the change.

---

## 9.3 North-star test for any proposed improvement

Before recommending a material change, ask:

```text
Does this reduce unavoidable rework for the next real project?

Does it improve ownership, safety, testability, or operational clarity?

Does it preserve or improve the ability to replace frameworks/providers?

Does it solve a demonstrated problem rather than a hypothetical one?

Can it be implemented and reviewed in a coherent bounded milestone?

Will the next milestone build on it rather than undo it?
```

If most answers are **NO**, the proposed improvement probably does not belong in the reusable baseline.

---

# 10. Target baseline architecture

The READY baseline must support this dependency direction:

```text
Client / Caller
        ↓
Delivery Adapter
        ↓
optional Orchestration Adapter
        ↓
Application Core
        ↓
Application-owned Ports / Contracts
        ↓
Outbound / Driven Adapters
```

For an LLM path:

```text
FastAPI / caller
        ↓
optional LangGraph
        ↓
Application Operation
        ↓
LLMPort
        ↓
Provider Adapter
        ↓
Provider SDK
```

The same application operation must be independently callable without:

- LangGraph execution;
- OpenAI SDK;
- a provider network call when a fake port is used.

This is a core readiness property, not only a testing convenience.

---

# 11. Mandatory Readiness Gate A — Real Application Core

## Required

The repository must have a real application-owned execution layer for reusable behaviour.

Application Core must own, where applicable:

- application/use-case semantics;
- deterministic business/runtime policy;
- application contracts;
- prompt invocation ownership;
- provider-neutral outbound-port usage;
- controlled side-effect policy.

LangGraph nodes may orchestrate and map state, but must not be the only home of reusable application semantics.

## Acceptance evidence

At least one active production path — and ultimately all baseline active LLM paths intended to remain in the template — must follow:

```text
Orchestration / Delivery
        ↓
Application Operation
        ↓
Port
        ↓
Adapter
```

Application operations must be testable without LangGraph.

Application Core must not import:

- `langgraph`;
- OpenAI SDK;
- LangSmith SDK;
- graph-specific state types.

## Why this decision was made

Without this boundary, changing orchestration framework or calling the same use case directly from FastAPI requires rewriting business/runtime behaviour.

The Application Core is the reusable asset.

Frameworks are replaceable mechanisms.

---

# 12. Mandatory Readiness Gate B — Explicit Composition Root

## Required

Concrete runtime construction must occur at an explicit composition boundary.

Composition owns:

- reading approved configuration;
- constructing provider adapters;
- constructing application operations;
- wiring application operations into delivery/orchestration adapters.

Do not use:

- hidden global mutable service registries;
- service locators;
- dependency-injection frameworks without a demonstrated need;
- provider construction inside application operations;
- provider construction inside LangGraph nodes.

`graph.py` must not become the permanent owner of provider composition merely because LangGraph is currently used.

## Why this decision was made

Dependency inversion is incomplete if the correct interfaces exist but production construction still happens inside the wrong layer.

Plain explicit Python composition is easier to inspect, test, review, and adapt than introducing a DI framework before one is necessary.

---

# 13. Mandatory Readiness Gate C — Provider-neutral LLM boundary

## Required

The application must call LLMs through a minimal provider-neutral `LLMPort`.

The port must expose only capabilities required by active application operations.

Provider SDK objects must not cross the port.

Prefer adapting a viable existing provider component over creating a parallel replacement when it can satisfy the approved port cleanly.

## Required properties

- provider-neutral request semantics;
- typed structured output where downstream code depends on structure;
- no OpenAI SDK types in application contracts;
- no LangSmith types in application contracts;
- provider-specific credentials stay outside Application Core;
- provider-specific exceptions are translated to stable application-visible failure categories;
- retries/timeouts that are provider transport concerns remain adapter responsibilities.

## Model configuration

The baseline does not require a generic model router.

If different application operations use different provider/model configurations, explicit configured adapter instances are acceptable.

Do not invent provider-neutral model-profile infrastructure before runtime evidence requires it.

## Why this decision was made

The goal is **replaceability**, not multiple providers for appearance.

One concrete provider behind a clean port is more reusable than multiple providers coupled directly to application behaviour.

---

# 14. Mandatory Readiness Gate D — Prompt identity and immutable resolution

This is a mandatory baseline capability.

## Required conceptual identity

Every production-relevant prompt execution must be attributable to:

```text
prompt_id
revision
content_hash
```

A prompt reference identifies an immutable revision.

The application must not depend on:

```text
"current production prompt"
```

without resolving it to a concrete revision before execution.

## Required runtime direction

Conceptually:

```text
Application Operation
        ↓
PromptRef
        ↓
PromptRepository
        ↓
ResolvedPrompt
        ↓
LLMPort
```

A local/code-backed prompt repository is sufficient for the baseline if it satisfies the contract.

A remote prompt-management platform is not required.

## Required traceability

Where AI behaviour is executed or evaluated, evidence must be able to identify:

- prompt id;
- prompt revision;
- content hash;
- model/provider execution identity where appropriate;
- model configuration required to reproduce the behaviour.

## Why this decision was made

Prompt versioning is required for:

- reproducibility;
- regression analysis;
- evaluation attribution;
- production incident analysis;
- rollback;
- governance;
- controlled promotion.

Prompt identity must therefore belong to the application, not to LangSmith or another vendor prompt host.

---

# 15. Mandatory Readiness Gate E — ExecutionContext

The application must own a minimal execution/correlation context.

## Baseline fields

```text
request_id
run_id
optional thread_id
```

Additional fields such as:

- user;
- tenant;
- actor;
- policy context;

remain requirement-driven.

## Required properties

`ExecutionContext` must:

- be application-owned;
- be transport/framework/provider neutral;
- not become an arbitrary metadata dumping ground;
- not contain secrets;
- be propagatable through application operations;
- support correlation across delivery, orchestration, provider invocation, failures, and telemetry.

Graph state may carry a copy of relevant identifiers.

Graph state is not the architectural owner of execution identity.

## Why this decision was made

Correlation cannot be owned by LangSmith, OpenTelemetry, FastAPI request objects, or LangGraph checkpoint state if the Application Core is intended to be portable.

---

# 16. Mandatory Readiness Gate F — Thin application-owned telemetry boundary

The baseline must have a thin application-owned telemetry/event boundary.

Conceptually:

```text
ExecutionContext
+
Application Execution Events
        ↓
TelemetryPort
        ↓
Exporter(s)
```

## Baseline event visibility

Where useful and safe, the system should be able to represent:

- operation name;
- request/run correlation;
- provider/model identity;
- prompt revision;
- latency;
- attempts/retries;
- routing/policy outcome;
- error category;
- final outcome.

Token usage/cost are requirement-driven fields.

## Not required

The baseline does not require:

- OpenTelemetry exporter;
- custom telemetry platform;
- metrics backend;
- tracing vendor replacement.

Current LangSmith/stdlib logging may remain as exporters/adapters while the application boundary is made explicit.

## Security rule

Raw content is not automatically telemetry.

Never make hidden chain-of-thought an observability requirement.

## Why this decision was made

Production support needs traceability, but vendor telemetry objects must not become application contracts.

The telemetry boundary preserves portability while avoiding creation of an in-house observability platform.

---

# 17. Mandatory Readiness Gate G — Explicit error boundary

The runtime must have stable, layer-appropriate failure semantics.

For relevant failures, the system must be able to answer:

```text
What failed?
Who owns the failure?
Is it retryable?
Should execution fail, fallback, continue, or escalate?
What state remains valid?
What is safe to expose externally?
What telemetry is required?
```

## Required boundaries

Provider-specific exceptions must not leak into Application Core.

Application failures must not be silently converted into success.

Unexpected internal defects must remain distinguishable from expected business/model failures.

Model parsing/validation failures must have explicit behaviour.

Retries must occur only where safe and useful.

Human review must remain explicit when policy, uncertainty, or execution failure requires it.

## Why this decision was made

Production reliability is not “catch Exception and continue.”

Failure ownership and state semantics must remain understandable across provider, application, orchestration, and delivery layers.

---

# 18. Mandatory Readiness Gate H — Deterministic vs probabilistic responsibility

The template must preserve the rule:

```text
Known deterministic rule
        → deterministic code

Probabilistic interpretation / generation
        → LLM
```

Examples that should remain deterministic when known:

- schema validation;
- length/threshold checks;
- allow/deny rules;
- authorization;
- idempotency;
- provenance checks;
- explicit policy.

LLMs may perform:

- interpretation;
- drafting;
- classification;
- planning/judgement where deterministic rules are insufficient.

## Why this decision was made

Using an LLM for known policy increases cost, latency, non-determinism, and evaluation burden without adding value.

---

# 19. Mandatory Readiness Gate I — Untrusted AI output

Model output must be treated as untrusted data.

## Required

When downstream code depends on structure:

- use an application-owned typed schema;
- validate the result;
- reject/fallback/escalate on invalid output according to policy.

Model output must not:

- authorize itself;
- declare an external action completed;
- invent retrieved provenance;
- redefine application policy;
- bypass deterministic checks.

## Why this decision was made

A model is a probabilistic component, not an authority boundary.

---

# 20. Mandatory Readiness Gate J — Controlled side-effect semantics

The template must preserve application-owned controlled-side-effect semantics.

Conceptually:

```text
ToolRequest
        ↓
request/schema validation
        ↓
policy/authorization
        ↓
idempotency when required
        ↓
execution via adapter
        ↓
result validation
        ↓
ToolResult
```

## Baseline requirement

The **contract and policy semantics** must be explicit and reusable.

The baseline does not need a generic `ControlledToolExecutor`.

The baseline does not need MCP, REST, or DB tool adapters.

No currently implemented side-effect path may bypass the approved controlled-execution principle.

## Critical distinction

```text
LLMPort/provider inference
≠
ToolRequest/tool execution
```

## Why this decision was made

Validation is not authorization.

Model intent is not permission.

A registered tool is not automatically an authorized tool.

The template must prevent future agent features from turning provider output into unconstrained production actions.

---

# 21. Mandatory Readiness Gate K — Human escalation semantics

The template must have a stable behavioural principle for human escalation.

Human review is required when justified by:

- policy;
- material risk;
- meaningful uncertainty;
- high-impact or irreversible actions;
- failed execution paths that cannot safely complete.

The baseline must not silently erase an upstream `needs_human_review` decision.

## Not required

READY does not require:

- LangGraph `interrupt()` / resume;
- durable HITL persistence;
- review UI;
- checkpointed approval workflow.

Those remain project-driven.

## Why this decision was made

The behavioural requirement and the implementation mechanism are different concerns.

We need safe escalation semantics without prematurely building a generic HITL platform.

---

# 22. Mandatory Readiness Gate L — Security baseline

The baseline must respect:

- explicit trust boundaries;
- least privilege;
- secure defaults;
- secrets outside source/prompts/contracts/logs;
- authentication distinct from authorization;
- application-owned authorization policy;
- PII/sensitive-data minimization;
- untrusted external/retrieved/tool/model content;
- deliberate external egress.

## Required readiness evidence

There must be no known baseline path where:

- model output grants authorization;
- secrets are embedded in prompts or application contracts;
- provider credentials leak into Application Core;
- raw sensitive payloads are automatically logged;
- retrieved/tool content can redefine system authority.

## Not required by default

Project-specific:

- IAM architecture;
- regulatory mapping;
- full OWASP threat model;
- data-residency implementation;
- tenant authorization design;

are activated when requirements justify them.

## Why this decision was made

A reusable template must establish safe boundaries without pretending one generic security architecture fits every project.

---

# 23. Mandatory Readiness Gate M — Software testing

The baseline must have meaningful deterministic tests for its reusable boundaries.

Required categories where applicable:

- Application Operation tests using fake outbound ports;
- orchestration/delivery adapter tests using fake application dependencies;
- provider adapter tests using fake provider clients;
- composition/wiring tests without live external calls;
- failure-path tests;
- validation/provenance/policy tests;
- regression tests for important corrected behaviours.

Tests must prove contracts and boundaries, not implementation trivia.

## READY quality gate

```text
poetry run pytest
```

must pass.

No known intentionally failing test is acceptable in the READY baseline.

---

# 24. Mandatory Readiness Gate N — Static quality

A reusable READY template must not ship known baseline static-analysis failure as normal state.

Required:

```text
poetry run pyright
→ 0 errors
```

Required:

```text
poetry run ruff check .
→ clean
```

or an explicitly approved equivalent zero-violation baseline.

Existing seeded Ruff/Pyright debt may be tolerated during intermediate milestones.

It is **not** acceptable at final template READY.

## Why this decision was made

Known static debt copied into every future project becomes recurring delivery tax.

The template should export good defaults, not known cleanup work.

---

# 25. Mandatory Readiness Gate O — AI evaluation discipline

The baseline must support reproducible AI evaluation when a project changes probabilistic behaviour.

The template does not need a custom evaluation platform.

## Required discipline

An evaluation-relevant execution should be attributable to:

```text
prompt revision
+
model
+
model configuration
+
evaluation dataset/version
+
evaluation result
```

The template must clearly separate:

```text
pytest
→ deterministic correctness

AI evaluation
→ probabilistic behaviour / regression
```

## Baseline evidence

At minimum, the template must contain a usable evaluation strategy and a project must be able to define:

- representative/golden cases;
- success metrics;
- baseline vs candidate comparison;
- promotion criteria.

A generic permanent evaluation dataset is not required because evaluation cases are domain-specific.

## Why this decision was made

Production AI cannot be promoted safely using software tests alone.

At the same time, building a custom eval platform before a project needs one is unnecessary infrastructure.

---

# 26. Mandatory Readiness Gate P — Delivery/configuration hygiene

The repository must be safe to copy as a new project baseline.

Required:

- Python 3.11 / Poetry configuration is internally consistent;
- `.env.example` documents currently required baseline configuration without secrets;
- Dockerfile reflects the actual runtime;
- Docker Compose does not advertise stale starter/template identity;
- health/readiness behaviour is factual and documented;
- helper scripts that are documented as usable are actually usable;
- root README setup/run/test instructions are factually correct;
- no seed-specific infrastructure name is presented as the reusable template identity.

## Why this decision was made

Architecture quality is undermined if every new project begins by repairing stale environment/configuration scaffolding.

---

# 27. Mandatory Readiness Gate Q — FastAPI delivery baseline

FastAPI remains the baseline HTTP delivery adapter.

READY requires:

- working application startup;
- factual health/version endpoints;
- clean delivery/application ownership;
- no provider selection or business policy in FastAPI delivery code.

READY does **not** require a speculative generic AI endpoint.

The actual business/use-case API is project-specific.

## Why this decision was made

The template should provide a production-capable delivery foundation without inventing an API contract for unknown future assignments.

---

# 28. Mandatory Readiness Gate R — LangGraph remains optional

The repository may retain a LangGraph example/orchestration path.

However, READY requires:

- Application Core does not depend on LangGraph;
- LangGraph-specific state/routing remains orchestration-owned;
- no generic universal agent graph is introduced;
- application operations can run without graph execution.

## Why this decision was made

LangGraph is useful for workflows that need graph orchestration.

It is not required for every AI application.

Making it optional prevents framework lock-in and keeps simple use cases simple.

---

# 29. Mandatory Readiness Gate S — Retrieval/RAG activation readiness

The baseline must preserve a clean path for a future retrieval/RAG requirement.

Current reusable concepts may include:

- retrieval-shaped orchestration;
- query construction;
- `RetrievedDocument`;
- retrieved-document state/contracts;
- grounded drafting capability;
- provenance validation.

## READY does not require

- repository corpus;
- embeddings;
- vector database;
- chunking;
- reranking;
- retrieval service vendor;
- `RetrievalPort` solely for completeness.

If a real project requires RAG, it should be possible to activate a clean retrieval boundary without undoing the core LLM/application architecture.

## Critical rule

No Customer Support-specific knowledge corpus belongs in the reusable baseline.

## Why this decision was made

RAG is common enough that we should preserve useful seams.

It is not universal enough to justify choosing a backend before requirements exist.

---

# 30. Mandatory Readiness Gate T — Automated verification baseline

The reusable template must verify its core quality gates automatically.

Manual local validation remains useful, but final readiness must not depend on a human remembering to run every command.

## Required

The repository must have an automated CI verification path that runs, at minimum:

```text
pytest
pyright
ruff
Docker build
```

It should also perform a minimal startup/health smoke validation when practical without requiring live external provider credentials.

The CI path must:

- run on the repository's normal change workflow;
- fail when a required quality gate fails;
- avoid live LLM/provider calls;
- avoid requiring production secrets;
- use the same authoritative project configuration used by local development.

## Not required

READY does not require:

- continuous deployment;
- AWS deployment automation;
- Terraform/CloudFormation;
- Kubernetes;
- multi-environment promotion pipelines;
- a custom CI platform.

Those are project/deployment requirements.

## Why this decision was made

A reusable production-oriented template should export enforceable quality defaults.

If correctness depends only on developers remembering local commands, every future project inherits avoidable process risk.

Automating the baseline gates gives every derived project an immediate regression barrier without forcing a deployment architecture.

---

# 31. Mandatory Readiness Gate U — Documentation and continuity

The template is not READY if the runtime and documentation disagree materially.

Required:

- `.ai/README.md` remains a valid fresh-session entry point;
- architecture docs describe actual approved architecture;
- `file-map.md` describes actual current ownership;
- contracts distinguish target semantics from implementation;
- deferred capabilities remain explicitly deferred;
- README accurately describes current runtime;
- affected `docs/**` match current runtime responsibilities;
- `.ai/handoff.md` reflects the latest approved continuation state;
- no competing ChatGPT/Cursor handoff systems exist.

A fresh engineer or AI session should be able to understand:

```text
What is this template?
What problem does it solve?
What architecture is approved?
What is actually implemented?
What is intentionally deferred?
What is allowed next?
How do I add a new project?
```

without needing private conversation history.

## Why this decision was made

A reusable template is also an engineering knowledge product.

Architecture that exists only in chat history is not reusable.

---

# 32. Critical design decisions and why we made them

This section records the most important **why**, so future sessions do not reopen decisions merely because another implementation looks convenient.

| Decision | Why |
| --- | --- |
| **Seeded Customer Support runtime is reference code, not target architecture** | Prevent one domain from defining reusable template contracts. |
| **Application Core owns reusable semantics** | Business/runtime behaviour must survive framework/provider changes. |
| **LangGraph is an optional orchestration adapter** | Avoid graph-framework lock-in and allow direct FastAPI/use-case execution. |
| **LLMPort is application-owned and provider-neutral** | Provider replacement should not require rewriting application operations. |
| **Adapt viable existing components before creating parallel replacements** | Preserve proven behaviour/tests and avoid duplicate abstractions when the existing component can satisfy the approved boundary cleanly. |
| **Do not add multiple providers by default** | Portability comes from boundaries, not from speculative integrations. |
| **Explicit composition, no DI framework by default** | Plain wiring is easier to reason about and sufficient for current complexity. |
| **Application owns prompt identity** | Reproducibility, evaluation, rollback, and governance cannot depend on vendor aliases. |
| **Prompt revisions are immutable before execution** | “Current production prompt” is not reproducible evidence. |
| **Application owns ExecutionContext** | Correlation must not be owned by FastAPI, LangGraph, LangSmith, or OpenTelemetry. |
| **Thin TelemetryPort, exporter-neutral** | Preserve observability portability without building a custom tracing platform. |
| **Deterministic rules stay deterministic** | Reduce cost, latency, non-determinism, and unnecessary evaluation burden. |
| **Structured LLM output is validated** | Downstream software requires explicit contracts, not provider prose. |
| **Model output is untrusted** | LLM text is not authorization, provenance, policy, or proof of action. |
| **LLM inference is not ToolRequest execution** | Provider inference and controlled business side effects have different security semantics. |
| **Validation ≠ authorization** | Well-formed tool input does not imply permission to execute it. |
| **ToolRequest/ToolResult semantics are baseline; generic executor is deferred** | Preserve safe agent design without inventing a universal tool platform. |
| **Human escalation is a behavioural principle; durable HITL is deferred** | Preserve safety without forcing checkpoint/UI infrastructure into every project. |
| **Testing and AI evaluation are separate** | Deterministic correctness and probabilistic quality require different evidence. |
| **No automatic raw-content/CoT telemetry** | Protect privacy/security and avoid treating hidden reasoning as an operational artifact. |
| **RAG backend is deferred but retrieval seams are preserved** | Be ready for common retrieval assignments without choosing a backend prematurely. |
| **Optional infrastructure stays deferred** | Production-grade means justified architecture, not maximum infrastructure count. |
| **Static quality must be clean at final READY** | The reusable template must not export known technical debt into every project. |
| **One `.ai/` continuity system** | Avoid competing sources of truth between humans, ChatGPT, Cursor, and future tools. |

---

# 33. Recommended baseline implementation order

This document defines **what must eventually be true**, not a calendar deadline.

The following sequence is a recommended implementation order for satisfying the highest-leverage readiness gaps in the current template architecture.

It is not a fixed roadmap and it is not tied to any date.

## P0.1 Application LLM Execution Boundary

Establish:

```text
Delivery / optional Orchestration Adapter
        ↓
Application Operation
        ↓
LLMPort
        ↓
Provider Adapter
```

The resulting baseline should have:

- a real Application Core;
- explicit composition;
- provider-neutral typed structured LLM results;
- no provider construction inside application/orchestration nodes;
- no GraphState dependency inside Application Core;
- current behaviour/configuration preserved where it is part of approved runtime semantics;
- layered tests across application, orchestration, adapter, and composition boundaries.

---

## P0.2 Prompt Identity / Immutable Prompt Resolution

Establish:

```text
PromptRef
ResolvedPrompt
PromptRepository
prompt_id
revision
content_hash
```

with at least one simple replaceable baseline implementation.

The goal is reproducibility and prompt-management portability, not a prompt platform.

---

## P0.3 Execution correlation + telemetry boundary

Establish the minimal:

```text
ExecutionContext
→ application execution events
→ TelemetryPort
→ current exporter(s)
```

without introducing a custom observability platform or vendor migration unless required.

---

## P0.4 Baseline quality and repository hygiene closure

Before declaring the template READY:

```text
pytest
→ PASS

pyright
→ 0 errors

ruff
→ clean

Docker build
→ PASS

minimal startup / health smoke validation
→ PASS

git diff --check
→ PASS
```

Also close reusable-template hygiene debt that would otherwise be copied into every new project, such as:

- incomplete required configuration examples;
- stale starter/template identity;
- documented helper scripts that are not actually usable;
- materially stale README/runtime documentation.

Current concrete defects belong in `.ai/handoff.md`, project status, or milestone planning — not in this timeless readiness contract.

---

## P0.5 Final readiness review

Perform a template-wide audit against this document.

Mandatory gates are classified as:

```text
PASS
BLOCKED
```

A mandatory gate cannot be marked `NOT APPLICABLE`.

Conditional sub-requirements inside a mandatory gate may be classified as:

```text
PASS
NOT APPLICABLE — justified
BLOCKED
```

The template cannot be declared READY while any mandatory gate is BLOCKED.

---

# 34. Baseline capabilities that must be architecturally true but need no speculative runtime

The following must be **correctly defined and protected**, but do not require a generic runtime implementation merely for template completeness:

## Controlled tools

Required:

- `ToolRequest` / `ToolResult` contract semantics;
- validation vs authorization separation;
- controlled execution rule.

Not required:

- generic executor;
- MCP;
- DB tool;
- REST tool.

---

## Human-in-the-loop

Required:

- human escalation semantics.

Not required:

- checkpointing;
- durable approval store;
- interrupt/resume;
- review UI.

---

## Retrieval

Required:

- no domain-specific corpus in baseline;
- clean activation path;
- provenance remains untrusted/validated where retrieval is used.

Not required:

- retrieval backend;
- vector DB;
- embeddings;
- reranker.

---

## Persistence

Required:

- architectural distinction between domain persistence and DB-as-tool.

Not required:

- PostgreSQL;
- MongoDB;
- generic persistence port without a real persistence requirement.

---

# 35. Explicitly NOT required for TEMPLATE READY

The following are not baseline completion requirements unless a real project activates them:

- additional LLM providers;
- provider registry;
- model router;
- Azure/OpenAI/Gemini/Claude adapters;
- LangSmith prompt-management adapter;
- OpenTelemetry exporter;
- custom evaluation platform;
- generic `ControlledToolExecutor`;
- MCP;
- REST tool adapter;
- DB tool adapter;
- PostgreSQL;
- MongoDB;
- Redis as required application dependency;
- long-term memory;
- vector database;
- embeddings;
- chunking;
- reranking;
- generic RetrievalPort merely for completeness;
- Kafka;
- RabbitMQ;
- Kubernetes;
- generic streaming;
- history/thread APIs;
- LangGraph checkpointing;
- generic durable HITL;
- generic review UI;
- speculative multi-tenancy;
- speculative IAM model;
- generic cloud deployment/IaC for every provider;
- universal agent graph;
- universal planner/retriever/supervisor runtime.

A project may activate one or more of these through:

```text
real requirement
        ↓
project architecture decision
        ↓
explicit milestone
```

---

# 36. Assignment activation model

A READY template should make new work look like:

```text
1. Capture assignment requirements
2. Identify mandatory / optional capabilities
3. Reuse baseline Application Core boundaries
4. Activate only needed deferred capabilities
5. Add project-specific adapters
6. Add project-specific domain/use cases
7. Add deterministic tests
8. Add AI evaluation where probabilistic behaviour changes
9. Validate security / observability / failure semantics
10. Deliver
```

Examples:

## If the assignment needs RAG

Activate:

```text
project corpus
→ loader/chunking
→ embeddings/index
→ RetrievalPort / adapter if justified
→ retrieved evidence
→ provenance / grounded generation
```

Do not modify the core LLM/provider ownership to add RAG.

---

## If the assignment needs agent tools

Activate:

```text
ToolRequest
→ authorization policy
→ concrete tool adapter
→ ToolResult
```

Do not give the LLM direct production callbacks.

---

## If the assignment needs persistence

Activate:

```text
Application Persistence Port
→ project-specific persistence adapter
```

Do not confuse persistence with DB-as-agent-tool.

---

## If the assignment needs durable human approval

Activate:

```text
human-review policy
→ persistence/checkpoint mechanism
→ review/resume workflow
```

Do not assume LangGraph interrupt/resume is the only implementation.

---

# 37. Readiness evidence package

A declaration of READY must be supported by evidence.

Minimum evidence:

## Architecture

- actual dependency direction matches approved architecture;
- no blocking `SURFACE DISCREPANCY`;
- no provider SDK leakage into Application Core;
- no LangGraph-specific type leakage into Application Core;
- composition root is explicit.

## Behaviour

- major failure/human-review semantics are tested;
- untrusted model output is validated;
- deterministic rules remain deterministic;
- no uncontrolled side-effect path exists.

## Prompt reproducibility

A real execution can identify its exact prompt revision/hash.

## Execution traceability

A real run can be correlated by application-owned execution identity.

## Tests

```text
poetry run pytest
→ PASS
```

## Type checking

```text
poetry run pyright
→ 0 errors
```

## Lint

```text
poetry run ruff check .
→ PASS
```

## Automated verification

- CI runs the required baseline quality gates;
- Docker build passes in CI;
- minimal startup/health smoke validation passes where practical;
- no live provider credentials or production secrets are required for baseline CI.

## Documentation

- architecture current;
- file-map current;
- README current;
- affected `docs/**` current;
- handoff current;
- deferred register current.

## Git

- intended readiness changes reviewed;
- working tree state understood;
- explicit Git boundary exists for the approved readiness baseline.

---

# 38. Final readiness review questions

Before declaring READY, answer all of these.

## Architecture

1. Can an Application Operation run without LangGraph?
2. Can an Application Operation run with a fake LLM without OpenAI?
3. Does Application Core avoid OpenAI, LangGraph, and LangSmith SDK types?
4. Is provider construction outside application/orchestration semantics?
5. Can FastAPI theoretically call the same Application Core directly?

## Prompt lifecycle

6. Can we identify the exact prompt revision used?
7. Is prompt identity application-owned?
8. Can a future prompt host be replaced without redefining prompt identity?

## Reliability

9. Are expected vs unexpected failures explicit?
10. Are retry semantics owned by the correct layer?
11. Can an unsafe/incomplete model result fail or escalate instead of silently succeeding?

## Security

12. Is model output treated as untrusted?
13. Is authorization application-owned?
14. Are secrets outside prompts/contracts/logs?
15. Are retrieved/tool/external contents treated as untrusted?
16. Is hidden chain-of-thought excluded from telemetry requirements?

## Tools

17. Is LLM inference clearly separated from controlled tool execution?
18. Could a future tool be added without granting the LLM uncontrolled authority?

## Retrieval

19. Is the template free of Customer Support-specific corpus?
20. Can a project activate RAG without undoing the Application Core/LLM boundary?

## Observability

21. Is execution identity application-owned?
22. Can telemetry exporters change without changing application contracts?
23. Is raw sensitive content excluded from automatic telemetry?

## Quality

24. Does pytest pass?
25. Does Pyright pass with zero errors?
26. Does Ruff pass?
27. Does the Docker build pass?
28. Does the minimal startup/health smoke validation pass where applicable?
29. Does `git diff --check` pass?
30. Does CI automatically enforce the baseline verification gates without live provider calls or production secrets?

## Reusability

31. Is the root README factual?
32. Are setup/config examples reusable rather than seed-specific?
33. Can a new session understand architecture and deferred capabilities without chat history?
34. Can a new project be started without mandatory cleanup/refactoring of the template?

## Agent decision quality

35. Can a future agent explain the problem this template is solving, not only list its components?
36. Can a future agent distinguish an approved invariant from a current implementation detail?
37. Is there a documented path for challenging an approved rule with evidence rather than silently overriding it?
38. Are architectural tripwires explicit enough to detect common forms of coupling and abstraction theatre?
39. Can a future agent choose between two valid designs using an explicit priority hierarchy?
40. Can a future agent identify when `KEEP` is better than introducing a new abstraction?
41. Can a future agent surface a missing readiness capability without automatically implementing it?

If any mandatory readiness question is **NO**, the corresponding mandatory gate is BLOCKED and the template is not READY.

---


## Mandatory gate status semantics

For this contract:

```text
Mandatory Readiness Gate
→ PASS | BLOCKED
```

`NOT APPLICABLE` is not valid for an entire mandatory gate.

Only a conditional sub-requirement inside a mandatory gate may be:

```text
PASS
NOT APPLICABLE — justified
BLOCKED
```

A gate is PASS only when all of its required sub-requirements are PASS and every conditional `NOT APPLICABLE` decision is explicitly justified.

---

# 39. Ready-state declaration

The repository may use the declaration:

```text
PRODUCTION AI RUNTIME TEMPLATE
BASELINE READY
```

only when:

```text
Mandatory Readiness Gates
        → PASS only

Blocking SURFACE DISCREPANCIES
        → 0

pytest
        → PASS

Pyright
        → 0 errors

Ruff
        → PASS

Docker build
        → PASS

Automated baseline CI
        → PASS

Documentation
        → synchronized

Git readiness boundary
        → approved + established
```

At that point:

```text
Template architecture work
        → baseline complete

New assignment
        → project bootstrap / requirement-specific activation
```

Further work should be justified by:

```text
real assignment requirement
```

rather than by the desire to make the template contain every possible production technology.

---

# 40. Change control for this document

Because this document defines the finish line, changes to it are consequential.

Do not modify readiness requirements because:

- a milestone is difficult;
- a test currently fails;
- a provider/framework makes another architecture easier;
- a deferred capability looks fashionable;
- a project-specific preference should become global.

A readiness rule changes only when:

1. the reusable template objective changes;
2. approved architecture changes;
3. a repeated real project requirement proves the baseline is insufficient;
4. a requirement is shown to be unnecessary or harmful for all template users.

Any such change requires explicit architecture review.

Project-specific requirements belong under:

```text
.ai/projects/<project>/
```

and do not silently redefine template readiness.

---

# 41. Relationship to milestone planning

This document defines **what must eventually be true**.

Milestones define **how we get there safely**.

Therefore:

```text
Template Readiness Contract
        ↓
identify next unsatisfied mandatory gate
        ↓
select smallest coherent milestone
        ↓
implement
        ↓
validate
        ↓
review
        ↓
Git boundary
        ↓
reassess readiness
```

Do not turn this document into a fixed implementation schedule.

A milestone may satisfy:

- one readiness gate;
- part of one gate;
- several tightly coupled gates;

as long as the milestone remains coherent and reviewable.

The current M1 planning around:

```text
Application LLM Execution Boundary
```

is an example of a milestone intended to satisfy major portions of:

- Real Application Core;
- Explicit Composition;
- Provider-neutral LLM Boundary;
- typed application/provider ownership.

The exact M1 delivery split is governed by the approved milestone plan, not by this readiness document.

---

# 42. Core principle

The template is not READY because it contains many technologies.

It is READY when:

> **the important production-AI ownership boundaries are already correct, the reusable baseline is clean and testable, and future project capabilities can be added without undoing the architecture.**

A future agent has understood this document correctly when it can do more than repeat its rules:

> **it can explain the problem behind them, detect when the repository is drifting away from that problem, preserve decisions that still earn their cost, and challenge decisions that no longer do — using evidence, explicit trade-offs, and controlled architecture review.**
