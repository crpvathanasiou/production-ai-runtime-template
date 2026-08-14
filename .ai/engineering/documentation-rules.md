# Documentation rules

Canonical owner of the shared **Documentation Synchronization Protocol**.

The `.ai/` workspace and this protocol are **tool-neutral**. The same rules apply to ChatGPT, Cursor, human developers, and future AI coding/review tools.

```text
ONE shared .ai/ workspace
ONE Documentation Synchronization Protocol
ONE canonical .ai/handoff.md
```

No tool may create a private competing handoff, status file, synchronization workflow, or authority system.

Forbidden examples: `cursor-handoff.md`, `chatgpt-handoff.md`, `cursor-status.md`, `chatgpt-status.md`, `private-agent-state.md`.

Legitimate canonical documents such as `implementation-status.md` and `delivery-plan.md` are allowed (one set per project, not per tool).

Documentation is part of Definition of Done. Documentation must not silently redefine approved architecture.

## Normative vs factual

Approved documentation is **what should be true**.

Source code, Git, configuration, actual environment, actual commands, and actual test results are **what currently is true**.

If documentation says X and evidence says Y:

```text
SURFACE DISCREPANCY
```

Do not infer approval because code exists. Do not infer implementation because a document describes it. Do not rewrite history to hide disagreement.

## Two-stage documentation impact

### Stage A — before implementation (planning)

```text
Expected Documentation Impact:
NONE — <specific reason>
```

or:

```text
Expected Documentation Impact:
UPDATE
- <expected document>
```

`NONE` requires a specific reason. Silence is not `NONE`. This belongs to milestone planning ([`../skills/implementation-planning.md`](../skills/implementation-planning.md)).

### Stage B — after implementation

```text
Actual Documentation Impact:
NONE — <specific reason>
```

or:

```text
Actual Documentation Impact:
UPDATE
- <actual document>
```

Reconcile EXPECTED vs ACTUAL:

- Did implementation affect exactly the expected concerns?
- Did an additional concern change?
- Did an expected update prove unnecessary?
- Did dependencies / config / environment change?
- Did security / trust boundaries change?
- Did AI evaluation requirements change?
- Did observability / error semantics change?
- Did file ownership / layout change?
- Was a DEFER capability activated?

If a **material unapproved** scope or architecture change is discovered:

```text
STOP
→ SURFACE DISCREPANCY / SCOPE DEVIATION
→ ChatGPT review
```

Do not retroactively justify scope expansion.

## Authority by concern

Do not use one global document ranking.

| Concern | Authority |
| --- | --- |
| Architecture invariants | `architecture/architecture-rules.md` |
| Canonical structure / concepts | `architecture/architecture.md` |
| Contract domain | `contracts/*` (that domain only) |
| Reusable engineering policy / procedure | `engineering/*` |
| Reusable operational strategy | `operations/*` |
| Project requirements | `projects/<project>/project-context.md` |
| Project operational reference | `projects/<project>/development-environment.md` |
| Project architecture choices / deviations | `projects/<project>/architecture-decisions.md` |
| Intended delivery path | `projects/<project>/delivery-plan.md` |
| Project execution ledger | `projects/<project>/implementation-status.md` |
| Current continuation / next action | `.ai/handoff.md` |

A project decision may specialize the template. It must not silently override a template invariant. Deviation path: real requirement → explicit deviation → architecture review → rationale/trade-off → scoped project decision.

## Change-to-document mapping (by concern)

Update only documents whose concern actually changed. Do not mechanically touch every file.

| Kind of change | Document |
| --- | --- |
| Architecture structure | `architecture/architecture.md` |
| Architecture invariant | `architecture/architecture-rules.md` |
| Project-specific architecture choice / deviation | `projects/<project>/architecture-decisions.md` |
| Application / runtime contract semantics | relevant `contracts/*` |
| Prompt identity / lifecycle | `contracts/prompt-lifecycle-contract.md` |
| Tool semantics / authorization / side effects | `contracts/tool-execution-contract.md` |
| Reusable security policy | `engineering/security-principles.md` |
| Project-specific security architecture | project `architecture-decisions.md` |
| Observability semantics | `operations/observability-strategy.md` |
| Error / failure semantics | `operations/error-handling-strategy.md` |
| Software-testing methodology | `engineering/testing-strategy.md` |
| AI-evaluation methodology | `engineering/evaluation-strategy.md` |
| Environment / config / run command / external service | `projects/<project>/development-environment.md` (and root `README.md` only when template-wide identity/run instructions change) |
| Requirement / constraint / deliverable / deadline | `projects/<project>/project-context.md` |
| Approved milestone scope / order / gate | `projects/<project>/delivery-plan.md` |
| Actual implementation / validation / defect / progress | `projects/<project>/implementation-status.md` |
| Current milestone / continuation-impacting blocker / next approved action / forbidden action | `.ai/handoff.md` |
| Repository ownership / layout | `architecture/file-map.md` |
| Deferred capability activation | `architecture/deferred-capabilities.md` **and** project `architecture-decisions.md` **and** affected concern-specific docs |

## Documentation update order

1. Affected normative architecture / contracts / engineering / operational policy.
2. Affected project-specific context / environment / architecture decisions / delivery plan, **when an active project exists**.
3. Active-project `implementation-status.md`, **when applicable**.
4. `.ai/handoff.md` — **last documentation update**.

“Handoff last” means last **documentation** update, not last command executed. Validation and final Git inspection follow the milestone’s locked execution sequence. Mutable continuation must not claim a final state before authoritative/project docs are synchronized and actual validation results are available.

When there is **no** active project (template milestones such as this layer’s completion), skip steps 2–3. Do not invent a project workspace to satisfy the sequence.

## Approval gate

A milestone cannot receive **APPROVE** if materially affected documentation is stale or inconsistent. Passing tests alone is insufficient.

Review must ask:

- What changed?
- Which documents should therefore have changed?
- Were they updated?
- Does documentation accurately represent resulting implementation/config?
- Does Git/runtime/test evidence contradict documentation?
- Is `implementation-status` accurate when applicable?
- Is `handoff.md` accurate?
- Is any authoritative doc stale?
- Was a deferred capability activated and documented?

When disagreement exists:

```text
SURFACE DISCREPANCY
```

## Placeholders

Do not create empty documentation trees to satisfy a mapping. Create a document only when the approved milestone includes it.
