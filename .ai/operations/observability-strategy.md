# Observability strategy

Reusable operational observability strategy. Not a tracing product. Not implemented by this document.

## Architectural boundary

```text
Application-owned ExecutionContext / execution events
        ↓
TelemetryPort
        ↓
exporters
```

Possible exporters:

- structured logging;
- LangSmith;
- OpenTelemetry;
- a future exporter.

**No exporter is architectural owner.** Vendor run/span objects are not application or domain contracts ([`../architecture/architecture-rules.md`](../architecture/architecture-rules.md)).

Do not design a custom tracing framework. OpenTelemetry exporter remains **DEFER** until justified ([`../architecture/deferred-capabilities.md`](../architecture/deferred-capabilities.md)).

## `ExecutionContext` minimum

Conceptual identity (not claimed as implemented in seeded Python):

```text
request_id
run_id
optional thread_id
```

Additional fields (user, tenant, actor, policy context, extra correlation) are **requirement-driven**.

`ExecutionContext` must not become an arbitrary secret or raw-payload container.

## Decision visibility ≠ hidden reasoning

Operational visibility **may** include, where appropriate:

- routing outcome;
- policy result;
- reason code;
- provider / model identity;
- prompt revision;
- tool selection;
- latency;
- retries;
- rate limits;
- error category;
- token usage;
- estimated cost where available;
- final outcome.

Do **not** require chain-of-thought / hidden model reasoning capture. That must not be persisted or logged as an observability requirement ([`../engineering/security-principles.md`](../engineering/security-principles.md)).

## Raw content is not automatic telemetry

Do **not** automatically log:

- prompts;
- user messages;
- PII;
- secrets;
- retrieved content;
- tool arguments / results;
- model responses.

Apply:

```text
minimize
redact
classify
sample deliberately
retain deliberately
```

according to project and security requirements.

## Cost and tokens

Token usage and estimated cost are **requirement-driven** operational fields. Provider-specific cost logic must not become application contracts.

## Verifiability

Where material for production support, observability itself should be verifiable (for example: a test that a correlation id is present on a handled failure path). That is software testing, not an eval platform.

## SURFACE DISCREPANCY

Seeded runtime mixes stdlib logging and LangSmith `@traceable` in the wrapper and nodes, without an application `TelemetryPort` or `ExecutionContext` type.

```text
SURFACE DISCREPANCY
```

if this strategy is treated as current implementation.
