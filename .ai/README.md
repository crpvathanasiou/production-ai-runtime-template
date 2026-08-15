# `.ai/` — Engineering Continuity Layer

`.ai/` is the persistent human/AI engineering control plane for this repository. A new human, ChatGPT, Cursor, or future AI engineering/review tool starts here.

There is **one** shared, tool-neutral `.ai/` workspace, **one** Documentation Synchronization Protocol ([`engineering/documentation-rules.md`](engineering/documentation-rules.md)), and **one** canonical [`.ai/handoff.md`](handoff.md). Do not create tool-specific parallel state (`cursor-handoff.md`, `chatgpt-status.md`, and similar).

It is not application runtime code.

## Documentation authority (by concern)

Do not use a single global ranking. Authority is by concern:

| Concern | Authority |
| --- | --- |
| Architecture invariants | [`architecture/architecture-rules.md`](architecture/architecture-rules.md) |
| Canonical architecture | [`architecture/architecture.md`](architecture/architecture.md) |
| Template readiness / finish line | [`architecture/template-readiness.md`](architecture/template-readiness.md) |
| Contract domains | [`contracts/`](contracts/) |
| Engineering policies / procedures | [`engineering/`](engineering/) |
| Operational strategy | [`operations/`](operations/) |
| Project requirements | `projects/<project>/project-context.md` |
| Project operational reference | `projects/<project>/development-environment.md` |
| Project architecture decisions | `projects/<project>/architecture-decisions.md` |
| Intended delivery path | `projects/<project>/delivery-plan.md` |
| Project execution ledger | `projects/<project>/implementation-status.md` |
| **What am I allowed to do next?** | [`.ai/handoff.md`](handoff.md) only |

[`architecture/template-readiness.md`](architecture/template-readiness.md) is the explicit authority for **TEMPLATE READY**, mandatory readiness gates, and template finish-line criteria. It does not replace handoff for continuation decisions.

Stable template knowledge changes only when the reusable template changes. Project knowledge must not silently become template rules. Handoff owns only current continuation state; it does not redefine architecture or prove that a Git commit exists (Git is factual for commits).

## Template vs project

This repository is a reusable production-oriented AI runtime template. The Python tree contains a seeded Customer Support Triage example — useful code, not the approved reusable architecture.

Project-specific knowledge belongs under [`.ai/projects/`](projects/README.md). Copy `_template`; do not treat the seed as an active project unless handoff names one.

## Normative vs factual — `SURFACE DISCREPANCY`

Approved documentation is **what should be true**. Code, Git, configuration, environment, commands, and tests are **what currently is true**. If they disagree:

```text
SURFACE DISCREPANCY
```

Do not infer implementation from docs, or approval from existing code.

## Where things live

| Area | Responsibility |
| --- | --- |
| [`architecture/`](architecture/architecture.md) | Target architecture, invariants, file map, deferred capabilities |
| [`contracts/`](contracts/agent-behavior-contract.md) | Agent behaviour, prompt lifecycle, tool execution |
| [`engineering/`](engineering/engineering-principles.md) | Stack, workflow, delivery method, testing, evaluation, security, documentation protocol |
| [`operations/`](operations/observability-strategy.md) | Observability and error-handling strategy |
| [`projects/`](projects/README.md) | Per-assignment workspace (`_template` only until a project is created) |
| [`skills/`](skills/README.md) | Recurring review/planning procedures (not runtime) |
| [`handoff.md`](handoff.md) | Shared continuation state |

## Continuation

Read [`.ai/handoff.md`](handoff.md) for active project, current milestone, last approved milestone, validation, blockers, **next approved action**, and forbidden actions. Do not copy mutable status into this file.

## ChatGPT / Cursor

ChatGPT owns architecture, planning, contracts, milestone scope, review, and APPROVE / CORRECTION-ONLY. Cursor is the controlled implementation executor ([`engineering/development-workflow.md`](engineering/development-workflow.md), [`engineering/delivery-method.md`](engineering/delivery-method.md)). A milestone is not complete because Cursor reports success.

## Recommended reading order

A new session should **not** read every `.ai/` file.

1. `.ai/README.md` (this file)
2. `.ai/handoff.md`
3. `.ai/architecture/template-readiness.md` when template readiness / overall finish-line reasoning is relevant
4. active project documents when present
5. relevant architecture, contracts, engineering, operations
6. relevant skill
