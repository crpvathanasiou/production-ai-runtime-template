# Testing strategy

Testing owns **deterministic software/system verification**.

It does **not** own probabilistic AI quality. That is [`evaluation-strategy.md`](evaluation-strategy.md).

Passing pytest does not prove AI quality. Passing AI evaluation does not prove software correctness. The same feature may need both.

## Proportional reasoning

For a meaningful change, reason:

```text
What changed?
        ↓
What contract / invariant / risk is affected?
        ↓
What is the smallest meaningful automated test?
        ↓
What exact command runs it?
        ↓
What does passing actually prove?
        ↓
What realistic defect would make it fail?
        ↓
What relevant behaviour remains untested?
```

Do not use artificial test-count targets. Do not require every layer for every trivial change (for example a comment-only or docs-only milestone may have no new automated test).

## Layers (when material)

Distinguish, where the change actually touches them:

| Concern | Typical test |
| --- | --- |
| Happy path | expected success for the contract |
| Failure path | explicit error/category, no silent success |
| Edge / contract validation | schema, bounds, forbidden combinations |
| Integration / framework semantics | only if that framework path is in the change |

## Proportional examples

```text
pure contract
        → unit / contract test

provider adapter
        → fake-client adapter test

FastAPI mapping
        → API integration test

LangGraph semantics
        → real graph / runtime test ONLY when LangGraph capability is actually active
```

Do not add a LangGraph runtime test because the seed contains a graph if the milestone did not change graph semantics.

Prefer fakes at adapter boundaries. Do not require live OpenAI, LangSmith, or Redis for unit tests of application logic ([`engineering-principles.md`](engineering-principles.md)).

## Commands (template baseline)

Exact commands are confirmed in the project’s `development-environment.md` when a project workspace exists. Template defaults:

```powershell
poetry run pytest
poetry run ruff check .
poetry run pyright
```

If this document (or a project environment doc) says a command works and the actual environment fails:

```text
SURFACE DISCREPANCY
```

Do not change runtime/tests/dependencies to clear **unrelated** seeded baseline failures unless the milestone allows those files.

## What a pass does not prove

- production-readiness of the seeded runtime;
- AI semantic quality;
- that deferred capabilities are implemented;
- that documentation is synchronized (that is an approval-gate concern in [`documentation-rules.md`](documentation-rules.md)).
