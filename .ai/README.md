# `.ai/` — Engineering Continuity Layer

`.ai/` is the persistent human/AI engineering control plane for this repository. A new human, ChatGPT, or Cursor session starts here.

It records how this reusable template is governed: what is architecturally true, what is project-specific, what is current work, and what must not be invented. It is not application runtime code.

## Documentation authority

There are three authority classes. Do not mix them.

| Class | Location | Changes when |
| --- | --- | --- |
| **Stable template knowledge** | `.ai/architecture/**`, `.ai/engineering/**`, `.ai/quick-start.md`, and other template-wide `.ai/` areas such as `contracts/`, `operations/`, and `skills/` when those documents exist | Only when the reusable template itself changes |
| **Mutable project knowledge** | `.ai/projects/<project>/` | When a specific assignment decides something that must not become a template rule |
| **Mutable continuation state** | `.ai/handoff.md` | When milestone, validation, blockers, or next approved action change |

`.ai/handoff.md` owns only current state. It does not redefine architecture.

Project-specific decisions must never silently become template-wide rules. Template rules must never be rewritten in a project folder to avoid an inconvenient invariant.

## Template vs project knowledge

This repository is a **reusable production-oriented AI runtime template**. The Python tree contains a seeded Customer Support Triage example. That seed is useful code, not the approved reusable architecture.

- **Template knowledge** applies to every future project started from this repository.
- **Project knowledge** captures one assignment: requirements, constraints, justified capability activation, and project architecture decisions.
- **Project-specific knowledge belongs under `.ai/projects/`**. Treat Customer Support Triage as seeded example implementation unless an approved project workspace names it as the active project.

## Where architecture and governance live

| Document | Responsibility |
| --- | --- |
| [`architecture/architecture.md`](architecture/architecture.md) | Approved Minimal Target Architecture |
| [`architecture/architecture-rules.md`](architecture/architecture-rules.md) | Normative architecture invariants |
| [`architecture/file-map.md`](architecture/file-map.md) | Current repository areas and ownership |
| [`architecture/deferred-capabilities.md`](architecture/deferred-capabilities.md) | Anti-overengineering register |
| [`engineering/engineering-principles.md`](engineering/engineering-principles.md) | Fixed stack and engineering standards |
| [`engineering/development-workflow.md`](engineering/development-workflow.md) | ChatGPT/Cursor milestone lifecycle |
| [`engineering/documentation-rules.md`](engineering/documentation-rules.md) | Documentation-impact Definition of Done |
| [`quick-start.md`](quick-start.md) | How a new project bootstraps from this template |

Specialized template documentation, when present, lives under:

- `.ai/contracts/` — specialized contract documentation
- `.ai/operations/` — operations documentation
- `.ai/projects/` — project workspaces
- `.ai/skills/` — reusable skills

Do not invent placeholders for absent areas. Current presence or absence is recorded only in [`.ai/handoff.md`](handoff.md).

## Current milestone and continuation

Read [`.ai/handoff.md`](handoff.md) for:

- active project
- current milestone
- last approved milestone
- validation status
- blockers
- next approved action
- forbidden/unapproved actions

Do not copy mutable status into this file.

## ChatGPT / Cursor governance

ChatGPT owns architecture, planning, contracts, milestone scope, review, and approval or correction-only follow-up.

Cursor is the controlled implementation executor. Cursor must not independently decide architecture, abstractions, dependencies, repository structure, scope expansion, opportunistic refactoring, deferred-capability activation, or continuation to another milestone.

A milestone is not complete because Cursor reports success. Completion requires ChatGPT review and an explicit **APPROVE** or **CORRECTION-ONLY** decision, then a Git milestone commit when instructed.

See [`engineering/development-workflow.md`](engineering/development-workflow.md).

## Recommended reading order

1. `.ai/README.md` (this file)
2. `.ai/handoff.md`
3. active project documents when they exist
4. `architecture/architecture.md`
5. `architecture/architecture-rules.md`
6. relevant engineering / contract / operations documents
7. relevant reusable skill
