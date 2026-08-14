# Error-handling strategy

Reusable operational error semantics. Framework-neutral. Does not prescribe HTTP status maps, DLQs, Kafka, or RabbitMQ by default. Those are architecture/runtime decisions only when a project requirement justifies them.

## Reason across

For each failure, address:

- category;
- owner / layer;
- recoverability;
- retryability;
- user / caller / workflow impact;
- state impact;
- observability requirement;
- external representation.

Questions:

```text
What failed?
Who owns it?
Is retry safe / useful?
Should execution continue, fail, fallback, or escalate?
What state remains valid?
What does the caller / user observe?
What must be logged / observed?
```

## Categories

| Category | Typical owner | Retry? |
| --- | --- | --- |
| Validation | delivery / application contracts | no — caller must correct |
| Policy / guardrail | application policy | no — not an upstream blip |
| Domain / application | application core | usually no |
| Provider / upstream | outbound adapter | maybe, if transient |
| Transient infrastructure | infrastructure adapter | often yes, with bounds |
| Permanent infrastructure / configuration | operations / config | no until config changes |
| Unexpected internal | application (defect) | no by default; fail closed |

Retry only when the operation is safe to repeat or protected by requirement-driven idempotency ([`../contracts/tool-execution-contract.md`](../contracts/tool-execution-contract.md)). Do not retry policy denials or validation failures.

## Workflow and user impact

Decide explicitly whether the workflow:

- continues with a degraded but valid state;
- fails the use case;
- falls back to a deterministic path;
- escalates under the agent-behaviour human-escalation *principle* (not an implied HITL product).

The caller/user must observe an explicit outcome. Silent success after a swallowed exception is out of strategy.

## State impact

State that remains after failure must still be valid. Do not leave “half side effects” without a `ToolResult` that records failure. Graph/checkpoint state is not business persistence ([`../architecture/architecture-rules.md`](../architecture/architecture-rules.md)).

## Observability

Log category, owner, correlation (`request_id` / `run_id` / optional `thread_id`), and retry/final outcome — not raw payloads by default ([`observability-strategy.md`](observability-strategy.md)).

## Seeded taxonomy (factual, not this strategy’s runtime)

The seed defines `AppError` subclasses (`ValidationAppError`, `GuardrailBlockedError`, `ModelOutputParsingError`, `UpstreamServiceError`, `NodeExecutionError`). That is current code. This document does not claim those names are the final portable taxonomy.

If a new error class appears in code without documentation, or this strategy claims a behaviour tests do not cover:

```text
SURFACE DISCREPANCY
```
