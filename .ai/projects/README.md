# Project workspaces

Project-specific knowledge lives here. It **specializes** the reusable template. It does **not** silently modify template architecture, invariants, contracts, or engineering policy.

There is one shared `.ai/` workspace and one canonical [`.ai/handoff.md`](../handoff.md). Project folders are not a second handoff.

## Create a workspace from `_template`

1. Copy `.ai/projects/_template/` to `.ai/projects/<project>/`.
2. Replace placeholder content with the assignment.
3. Keep the five documents; do not invent a parallel status file (`cursor-status.md`, `chatgpt-handoff.md`, and similar are forbidden).
4. Record the active project name only in [`.ai/handoff.md`](../handoff.md) when ChatGPT approves that project as active.

Do not create an active project workspace during generic template milestones unless the approved milestone says to.

`_template` is a starter, not an active project.

## What each document owns

| File | Purpose |
| --- | --- |
| `project-context.md` | What must be solved (requirements, deliverables, acceptance) |
| `development-environment.md` | How this project is expected to run (operational reference, not infallible fact) |
| `architecture-decisions.md` | Approved project-specific technical choices / explicit deviations |
| `delivery-plan.md` | Intended approved delivery path (prospective) |
| `implementation-status.md` | Detailed execution ledger (not next action) |

A genuine deviation from a template invariant requires: real requirement → explicit deviation → architecture review → rationale/trade-off → scoped project decision in `architecture-decisions.md`. Silent override is out of process.

## Relation to the shared handoff

| Question | Authority |
| --- | --- |
| What must we solve? | `project-context.md` |
| How should we run it? | `development-environment.md` (reference) vs actual env evidence |
| What did we decide technically? | `architecture-decisions.md` |
| What did we intend to deliver? | `delivery-plan.md` |
| What have we actually done? | `implementation-status.md` |
| **What am I allowed to do next?** | **[`.ai/handoff.md`](../handoff.md) only** |

`implementation-status.md` is updated **when an active project exists and is applicable**. Template-only milestones do not invent a project to satisfy that step.

If a project document says X and Git/runtime/config/tests say Y:

```text
SURFACE DISCREPANCY
```

## Fresh-session reading order (active project)

1. [`.ai/README.md`](../README.md)
2. [`.ai/handoff.md`](../handoff.md)
3. This project’s `project-context.md`
4. `architecture-decisions.md` and `delivery-plan.md` as needed
5. `development-environment.md` when running or validating
6. `implementation-status.md` for ledger, not for next action
7. Relevant architecture / contracts / engineering / operations / skills
