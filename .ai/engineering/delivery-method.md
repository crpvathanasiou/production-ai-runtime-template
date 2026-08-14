# Delivery method

Execution discipline **inside one approved milestone**.

This is not [`development-workflow.md`](development-workflow.md).

| Document | Owns |
| --- | --- |
| [`development-workflow.md`](development-workflow.md) | Roles, approvals, milestone lifecycle (ChatGPT plans/reviews; Cursor implements) |
| **This file** | How work is executed once that milestone is approved |
| [`documentation-rules.md`](documentation-rules.md) | Shared Documentation Synchronization Protocol |

## Canonical discipline

```text
read authoritative context
        ↓
restate approved objective / scope
        ↓
inspect contracts / constraints
        ↓
establish Expected Documentation Impact
        ↓
identify smallest valid change
        ↓
implement approved scope
        ↓
perform Actual Documentation Impact Reconciliation
        ↓
synchronize affected normative / project documentation
        ↓
update active-project implementation-status when applicable
        ↓
run relevant validation
        ↓
update .ai/handoff.md as the LAST documentation-state update
   (using the ACTUAL latest validation results)
        ↓
perform FINAL Git scope inspection
        ↓
explain / report evidence
        ↓
safe-stop
        ↓
STOP
```

“Handoff last” means the final **documentation** update, not the final command of the milestone. Validation must occur **before** the final handoff update when the handoff must contain the latest validation results. Final Git inspection and reporting occur **after** that handoff update.

Update active-project `implementation-status` **when applicable**. Do not require `implementation-status.md` when there is no active project.

Do not start the next milestone from this sequence. Continuation authority is [`.ai/handoff.md`](../handoff.md).

## Principles

**Contracts before implementation logic where relevant.** Read the applicable `.ai/contracts/*` and architecture invariants before writing behaviour.

**Smallest valid change.** Implement only what the milestone allows. No opportunistic refactoring, no extra abstractions, no dependency or repository-structure decisions.

**Explicit scope.** Allowed files, forbidden files, and Definition of Done come from the approved milestone plan. If a forbidden path appears necessary: safe-stop and report.

**Expected Documentation Impact before implementation.** Form:

```text
Expected Documentation Impact:
NONE — <specific reason>
```

or:

```text
Expected Documentation Impact:
UPDATE
- <document>
```

`NONE` is not a default. See [`documentation-rules.md`](documentation-rules.md).

**Actual Documentation Impact Reconciliation after implementation.** Compare expected vs actual. Material unapproved change:

```text
STOP → SURFACE DISCREPANCY / SCOPE DEVIATION → ChatGPT review
```

Do not retroactively justify scope expansion.

**Explicit evidence.** Validation commands, what passing proves, and what remains untested belong in the report. Passing tests is not approval.

**Safe-stop.** After report, stop. Do not continue to M1, deferred-capability activation, or a Git commit unless the approved milestone explicitly includes that action (this template’s Cursor executor does not create milestone commits unless instructed).

## Tool-neutral workspace

ChatGPT, Cursor, humans, and future AI tools use this same discipline against the same `.ai/` workspace. No tool-private delivery method.
