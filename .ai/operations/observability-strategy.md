# Observability strategy

Reusable operational observability strategy. Not a tracing product. This document describes the approved baseline and the current M3 seeded implementation.

## Architectural boundary

```text
Application-owned ExecutionContext / execution events
        ↓
TelemetryPort
        ↓
exporters
```

Possible exporters:

- structured logging (current baseline: `StdlibTelemetry`);
- LangSmith (deferred outbound option; not project-owned today);
- OpenTelemetry (deferred);
- a future exporter.

**No exporter is architectural owner.** Vendor run/span objects are not application or domain contracts ([`../architecture/architecture-rules.md`](../architecture/architecture-rules.md)).

Do not design a custom tracing framework. OpenTelemetry exporter remains **DEFER** until justified ([`../architecture/deferred-capabilities.md`](../architecture/deferred-capabilities.md)).

The reusable baseline does **not** depend on LangSmith ownership, OpenTelemetry, a custom span framework, or a metrics backend.

## Three distinct observability layers (current M3)

These layers are separate abstractions. Do not merge them into one generic tracing system.

### 1. Graph / node operational logging

Seeded graph nodes emit visibly rendered stdlib operational logs with:

```text
event identity
node_name
request_id
run_id
thread_id when present
```

Covered nodes: `input_shield`, `triage`, `planner`, `execute_plan`, `guardrails`, `human_review`, `finalize`.

Mechanism: Python stdlib logging + `format_operational_log` (minimal rendered JSON in the log message). No contextvars, spans, global trace context, logging platform, or `TelemetryPort` integration at this layer.

### 2. Application typed telemetry

Application Core owns:

```text
ExecutionContext
├── request_id
├── run_id
└── optional thread_id

LLMInvocationId
└── invocation_id

TelemetryPort → NoOpTelemetry / StdlibTelemetry
```

Typed application execution events:

```text
OperationStarted
LLMInvocationStarted
OperationCompleted
OperationFallback
OperationFailed
```

Application-level error categories:

```text
prompt_resolution
provider
model_output
unexpected
```

`LLMInvocationStarted` carries `PromptIdentity` at the Application layer. `PromptIdentity` does **not** enter `LLMPort`. The four Application Operations require explicit telemetry injection; composition injects one shared `StdlibTelemetry`.

Telemetry remains thin, synchronous, best-effort, and dependency-free as a baseline. It is not an event bus, span framework, OpenTelemetry, metrics platform, or LangSmith abstraction.

### 3. Provider adapter operational logging

The structured `AsyncOpenAIWrapper` path consumes already-propagated `ExecutionContext` + `LLMInvocationId` and emits provider operational events:

```text
llm_provider.attempt_started
llm_provider.attempt_succeeded
llm_provider.retry_scheduled
llm_provider.failed
```

Safe correlation fields include `request_id`, `run_id`, optional `thread_id`, `invocation_id`, `provider`, `model_name`, and attempt information.

Invariant:

```text
ONE LLMInvocationId
→ ONE LLMPort invocation
→ ALL provider retries for that invocation
```

Provider transport failure is distinct from later model-output/application failure. A successful provider SDK call may log `attempt_succeeded` even if subsequent structured parsing fails. Provider failure categories are intentionally minimal: `timeout`, `api_error`.

Provider logs do **not** use `TelemetryPort`.

## `ExecutionContext` minimum

Implemented identity:

```text
request_id
run_id
optional thread_id
```

`thread_id` is optional continuity across runs. It does not imply checkpointing or durable HITL persistence. One top-level graph execution has one `run_id`.

Additional fields (user, tenant, actor, policy context, extra correlation) remain **requirement-driven**.

`ExecutionContext` must not become an arbitrary secret or raw-payload container. `GraphState` may carry request/run/thread copies for orchestration; Application owns execution identity. `invocation_id` is not GraphState state.

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

Baseline data-minimization behaviour: operational logging and Application telemetry are intentionally limited to correlation identifiers and safe operational summaries.

Do **not** automatically log:

- prompts;
- user messages;
- PII;
- secrets;
- retrieved content;
- tool arguments / results;
- model responses;
- exception messages as generic telemetry/log payload.

This is implemented baseline behaviour, not a formal compliance/privacy certification.

Apply project-specific controls where required:

```text
minimize
redact
classify
sample deliberately
retain deliberately
```

## Cost and tokens

Token usage and estimated cost are **requirement-driven** operational fields. Provider-specific cost logic must not become application contracts. They are not part of the current M3 baseline event set.

## Verifiability

Where material for production support, observability itself should be verifiable (for example: a test that a correlation id is present on a handled failure path). That is software testing, not an eval platform.

## LangSmith ownership (current)

Explicit project-owned LangSmith tracing integration has been removed from nodes and the wrapper.

- no direct runtime `langsmith` imports under `app/**`
- no active `LANGSMITH_ENABLED` / `langsmith_enabled` project setting
- no direct `langsmith` dependency in `pyproject.toml`

LangSmith may remain transitively installed via LangGraph/langchain-core. That is not project-owned runtime observability ownership.

## Current implementation status

After M3, the three layers above are implemented in the seeded runtime. OpenTelemetry, metrics export, dashboards, alerts, sampling platforms, and distributed tracing are **not** implemented and remain deferred unless separately justified.
