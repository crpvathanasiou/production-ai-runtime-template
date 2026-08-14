# Development workflow

Fixed governance lifecycle for this template: **roles, approvals, and milestone lifecycle**.

This is not [`delivery-method.md`](delivery-method.md).

| Document | Owns |
| --- | --- |
| **This file** | Who decides, one-milestone lifecycle, APPROVE / CORRECTION-ONLY |
| [`delivery-method.md`](delivery-method.md) | Execution discipline **inside** an approved milestone |
| [`documentation-rules.md`](documentation-rules.md) | Shared Documentation Synchronization Protocol |

ChatGPT owns architecture, planning, review, and approval. Cursor is the controlled implementation executor.

## Lifecycle

```text
Requirement / approved architecture
        ↓
ChatGPT selects ONE milestone
        ↓
objective
        ↓
allowed files
        ↓
forbidden files
        ↓
contracts
        ↓
Definition of Done
        ↓
documentation impact
        ↓
Cursor prompt ONLY when explicitly requested
        ↓
Cursor implementation
        ↓
validation
        ↓
ChatGPT review
        ↓
APPROVE or CORRECTION-ONLY
        ↓
Git milestone commit
        ↓
next milestone
```

One milestone is in flight at a time. “While we are here” work is out of process.

## Ownership

### ChatGPT owns

- architecture
- planning
- contracts
- milestone scope (objective, allowed/forbidden files, DoD, documentation impact)
- review
- **APPROVE** or **CORRECTION-ONLY**
- when a Git milestone commit is requested

### Cursor owns

- implementing the current milestone inside the allowed file set
- running the validation commands the milestone specifies
- reporting results, deviations, and out-of-scope necessities without expanding scope

Cursor is the controlled implementation executor, not a co-architect.

## Cursor must not independently decide

- architecture
- abstractions
- dependencies
- repository restructuring
- scope expansion
- opportunistic refactoring
- deferred capability activation
- continuation to another milestone

If implementation appears to require a forbidden file or a new abstraction, Cursor stops, reports it, and waits.

## Milestone completion

A milestone is **not** complete because Cursor reports success, tests pass, or files exist.

Completion requires:

1. ChatGPT review against the milestone Definition of Done and architecture invariants
2. explicit **APPROVE** or **CORRECTION-ONLY**
3. correction cycle if required (still the same milestone)
4. Git milestone commit only when ChatGPT asks for it

`.ai/handoff.md` is the single shared continuation document (next approved action). It does not replace this workflow and is not proof that a Git commit exists.

Documentation changes follow [`documentation-rules.md`](documentation-rules.md): Expected Documentation Impact before implementation, Actual Documentation Impact Reconciliation after, handoff last among documentation updates. Active-project `implementation-status.md` is updated only when an active project exists and is applicable.

## Cursor prompts

ChatGPT writes or authorizes the Cursor prompt. Cursor must not start the next milestone from a handoff hint alone.

## Validation

Each milestone states its validation. Typical engineering checks for runtime work (not all required for documentation-only milestones):

```powershell
poetry run ruff check .
poetry run pyright
poetry run pytest
```

Do not change Python, tests, or dependencies to clear unrelated baseline failures unless that milestone allows those files.
