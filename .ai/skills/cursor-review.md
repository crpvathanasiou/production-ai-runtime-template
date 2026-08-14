# Skill — Cursor review

Reusable ChatGPT **post-implementation** review. It does **not** authorize continuation automatically.

Final result is only:

```text
APPROVE
```

or:

```text
CORRECTION-ONLY
```

A Git milestone commit is a separate instruction after APPROVE. Review must not claim a commit exists; Git is factual authority.

## Review the actual change

Use the actual Git diff, not the executor’s summary alone.

Cover:

- actual Git diff;
- allowed / forbidden scope;
- architecture compliance;
- contract compliance;
- data / state integrity where relevant;
- dependency changes;
- configuration / environment changes;
- failure semantics;
- error handling;
- security impact;
- observability impact;
- AI-evaluation impact;
- tests / evidence;
- documentation synchronization (Expected vs Actual Documentation Impact);
- deferred-capability activation;
- deviations;
- unresolved issues.

## Explicit questions

Did this introduce a dependency? Was it approved?

Did config / environment behaviour change? Was documentation synchronized?

Did trust boundary or authorization surface change?

Did probabilistic AI behaviour change? Is evaluation evidence required?

Was a DEFER capability silently activated?

What do the tests actually prove?

What realistic defect would make them fail?

What remains untested?

Does Git / runtime / config / test evidence contradict documentation? If yes:

```text
SURFACE DISCREPANCY
```

A milestone cannot receive APPROVE if materially affected documentation is stale or inconsistent. Passing tests alone is insufficient ([`../engineering/documentation-rules.md`](../engineering/documentation-rules.md)).

## Continuation

Next approved action remains [`.ai/handoff.md`](../handoff.md) after ChatGPT updates it. This review does not start M1 or create a commit.
