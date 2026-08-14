# Skill — implementation planning

Reusable planning procedure **before** Cursor (or other executor) implementation.

ChatGPT produces one milestone plan. Cursor does not plan architecture, dependencies, or the next milestone.

## Milestone plan contents

- objective;
- approved architecture context (pointers, not a rewrite);
- exact allowed files;
- exact forbidden files;
- contracts / behaviour in scope;
- dependencies if any (default: none unless approved);
- Definition of Done;
- tests / validation (commands and what they must prove);
- rollback / safe-stop;
- **Expected Documentation Impact** (before implementation).

See [`../engineering/development-workflow.md`](../engineering/development-workflow.md) and [`../engineering/delivery-method.md`](../engineering/delivery-method.md).

## Expected Documentation Impact (required, before implementation)

```text
Expected Documentation Impact:
NONE — <specific reason>
```

or:

```text
Expected Documentation Impact:
UPDATE
- <document>
- <document>
```

`NONE` is not a meaningless default. It needs a specific reason (for example: comment-only change with no behaviour, contract, config, or ownership effect).

Mapping and order: [`../engineering/documentation-rules.md`](../engineering/documentation-rules.md).

## Constraints the plan must state

- Cursor must not independently decide architecture, dependencies, abstractions, repository restructuring, deferred-capability activation, scope expansion, or the next milestone.
- If a forbidden file appears necessary: stop and report; do not widen the plan after the fact.
- No Git milestone commit unless the plan (and later ChatGPT instruction) includes it.

## Output

Produce **one bounded milestone plan** covering the contents above.

```text
planning
        ≠
implementation authorization
```

Planning by itself does **not** authorize implementation.

A Cursor-ready implementation prompt (or equivalent executor brief) is produced **only** when explicitly requested or authorized. Do not auto-generate a Cursor implementation prompt as a byproduct of planning. Do not start implementation from a handoff hint alone.
