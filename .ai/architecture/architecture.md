# Minimal Target Architecture

This document is the approved **target** architecture for the reusable template. It is not a description of the seeded Customer Support Triage runtime, and it does not invent a final package layout.

## Approved target vs current seed

**Approved target architecture** is the model below. Future work must move toward it.

**Currently implemented in the seeded repository (after M3):**

- FastAPI app with `/health` and `/version`
- optional Redis ping in the health check
- a Customer Support Triage LangGraph workflow (`input_shield` → `triage` → `planner` → `execute_plan` → `guardrails` → `human_review` → `finalize`)
- real Application Core under `app/application/` with four live operations:
  `InputShieldOperation`, `TriageOperation`, `PlannerOperation`, `ResponseDraftingOperation`
- provider-neutral `LLMPort` (`app/application/ports/llm.py`)
- `AsyncOpenAIWrapper` as the concrete OpenAI outbound adapter satisfying that boundary
- explicit production composition in `app/composition.py` (`build_runtime_graph()`)
- active LLM paths: LangGraph Node → Application Operation → `PromptRef` / `PromptRepository` → `ResolvedPrompt` → `LLMPort` → `AsyncOpenAIWrapper` / OpenAI
- application-owned prompt lifecycle: `PromptRef`, `PromptIdentity`, `ResolvedPrompt`, `PromptRepository`
- concrete baseline `LocalPromptRepository` over four immutable code-backed V1 definitions (`input-shield@1`, `triage@1`, `planner@1`, `response-drafting@1`)
- Application Operations resolve explicit revisions; nodes copy safe prompt identity into orchestration metadata when an outcome exists
- application-owned `ExecutionContext` (`request_id`, `run_id`, optional `thread_id`) and `LLMInvocationId`
- thin Application `TelemetryPort` with `NoOpTelemetry` / `StdlibTelemetry` and typed operation execution events
- `LLMPort.generate_structured(...)` receives `ExecutionContext` + `LLMInvocationId` + rendered prompts + schema; it does **not** receive `PromptIdentity`, `TelemetryPort`, `operation_name`, or GraphState
- graph nodes emit stdlib operational logs with visible `request_id` / `run_id` / optional `thread_id` correlation
- structured OpenAI adapter emits provider operational logs correlating attempts/retries under one `invocation_id`
- explicit project-owned LangSmith `@traceable` integration removed from nodes and wrapper; no direct `langsmith` project dependency (transitive presence via LangGraph/langchain-core may remain)

**Not yet implemented (later readiness / deferred):** controlled tool runtime, RAG backend, durable HITL / checkpointing, CI readiness closure, multiple providers, remote prompt-management platform, OpenTelemetry / metrics backends. Do not document those as already implemented. M3 does **not** make the entire Template Readiness baseline complete.

GraphState remains outside Application Core. Prompt identity and resolution for the four live LLM paths are application-owned.

## Canonical model

LangGraph is an optional **driving/orchestration adapter**. It is not an outbound/driven adapter beside OpenAI, prompt repositories, or telemetry exporters.

With optional orchestration:

```text
Client
  ↓
FastAPI / Delivery Adapter
  ↓
[Optional LangGraph Orchestration]
  ↓
Application Core
  ↓
Application Ports
  ↓
Outbound / Driven Adapters
```

The application core may also be called directly without LangGraph:

```text
Client
  ↓
FastAPI / Delivery Adapter
  ↓
Application Core
```

```text
┌──────────────────────────────────────────┐
│ Client                                   │
└─────────────────────┬────────────────────┘
                      ↓
┌──────────────────────────────────────────┐
│ Delivery Adapter                         │
│ FastAPI HTTP/API surface                 │
└─────────────────────┬────────────────────┘
                      ↓
┌──────────────────────────────────────────┐
│ Optional driving / orchestration adapter │
│ LangGraph (may be omitted)               │
└─────────────────────┬────────────────────┘
                      ↓
┌──────────────────────────────────────────┐
│ Application Core                         │
│ business semantics · policy              │
│ prompt identity · ExecutionContext       │
│ contracts: ToolRequest / ToolResult      │
│ controlled side-effect policy            │
└─────────────────────┬────────────────────┘
                      ↓
┌──────────────────────────────────────────┐
│ Application Ports                        │
│ LLMPort · PromptRepository               │
│ telemetry boundary                       │
└─────────────────────┬────────────────────┘
                      ↓
┌──────────────────────────────────────────┐
│ Outbound / driven adapters               │
│ OpenAI wrapper (LLMPort impl)            │
│ prompt-management / telemetry exporters  │
│ future tool / persistence adapters       │
└──────────────────────────────────────────┘
```

Driving adapters (FastAPI, optional LangGraph) call inward. Outbound adapters implement application ports. The application core does not depend on adapter SDKs or framework types.

## Application core ownership

The application core owns:

- business semantics
- application/domain contracts, including `ToolRequest` and `ToolResult`
- prompt identity (`prompt_id`, `revision`, `content_hash`)
- execution context
- policy
- controlled side-effect policy

LangGraph, OpenAI, LangSmith, Redis, and FastAPI do not own those concerns.

## Approved concepts

### Typed contracts

Application and domain meaning is expressed as typed contracts (Pydantic models / explicit types), not as unstructured SDK payloads. Provider objects must not become those contracts.

Application-owned tool contracts (baseline concepts, not ports):

```text
Application Contracts
├── ToolRequest
└── ToolResult
```

### Application-service / use-case ownership

Reusable business behaviour belongs in application services / use cases as a **principle**. When LangGraph is used, nodes orchestrate that behaviour; they do not become the long-term home of reusable semantics. This does not require a speculative new service layer, and it does not authorize a speculative generic business graph.

### `ExecutionContext`

The application owns a correlation/execution context. After M3 this is implemented as `ExecutionContext` in Application Core:

```text
request_id
run_id
optional thread_id
```

`thread_id` is optional continuity across runs. It does **not** imply LangGraph checkpointing or durable HITL persistence. One top-level graph execution has one `run_id`.

Additional fields remain **requirement-driven**, not baseline-required:

```text
user identity
tenant
actor
policy context
extra correlation metadata
```

`GraphState` carries request/run/thread copies for orchestration; it is not the owner of execution semantics. Separately, Application Operations create a transient `LLMInvocationId` for each `LLMPort` call; all provider retries for that call share the same `invocation_id`. `invocation_id` is not stored in `GraphState` or `additional_metadata`. Do not design a custom tracing framework around this.

### Provider-neutral `LLMPort`

The application calls language models through a provider-neutral **port**. After M1, `LLMPort` exists and `AsyncOpenAIWrapper` is the concrete OpenAI outbound adapter behind that boundary for the four live Application Operations. After M3, `generate_structured(...)` also receives `ExecutionContext` and `LLMInvocationId` for correlation. It does **not** receive `PromptIdentity`, `TelemetryPort`, `operation_name`, GraphState, or vendor tracing objects. Multiple providers are not implemented. Do not imply that they are.

### Prompt identity and `PromptRepository`

The application owns:

```text
prompt_id
revision
content_hash
```

A portable `PromptRepository` is the application-owned store/lookup **port** for prompt content. A prompt-management product may later be an outbound adapter behind that port; it is not the architectural owner of prompt identity.

Current seed (after M3): `PromptRef` / `PromptIdentity` / `ResolvedPrompt` / `PromptRepository` exist under `app/application/prompts/`. `LocalPromptRepository` resolves four immutable code-backed V1 definitions. `content_hash` identifies the stored static system+user templates, not runtime customer values. Application Operations resolve explicit revisions; `PromptIdentity` stays outside `LLMPort`. Nodes expose safe identity metadata on successful/handled outcomes. Application telemetry emits `LLMInvocationStarted` (with `PromptIdentity`) before the provider call, so failed attempts remain correlatable at the Application layer even when no operation outcome is returned to the node.

### Application-owned telemetry boundary

The application owns `ExecutionContext` and a **thin** `TelemetryPort` (what was invoked, latency, outcome, correlation ids). After M3 the seeded baseline implements `TelemetryPort` with `NoOpTelemetry` / `StdlibTelemetry` and typed events (`OperationStarted`, `LLMInvocationStarted`, `OperationCompleted`, `OperationFallback`, `OperationFailed`). Composition injects one shared `StdlibTelemetry`; direct callers/tests may use `NoOpTelemetry`. This is not an event bus, span framework, OpenTelemetry, metrics platform, or LangSmith abstraction. OpenTelemetry or other exporters remain deferred outbound options behind the port. Do not design a custom tracing platform.

Distinct from Application telemetry:

- graph/node **operational logging** (stdlib + minimal rendered correlation fields)
- provider-adapter **operational logging** (attempt/retry/transport-failure correlation under one `invocation_id`)

Explicit project-owned LangSmith `@traceable` ownership has been removed from nodes and the wrapper.

### `ToolRequest` / `ToolResult` and controlled execution

`ToolRequest` and `ToolResult` are **application-owned contracts**, not ports.

```text
ToolRequest / ToolResult contracts
    → baseline architectural contracts

Controlled execution principle
    → baseline architectural principle

Generic ControlledToolExecutor implementation
    → DEFER

MCP / REST / DB tool adapters
    → DEFER
```

The LLM cannot perform side effects by itself. Any tool/side effect is an application-authorized `ToolRequest` that yields a typed `ToolResult`. Future execution boundaries and tool adapters are separate from these contracts. A generic `ControlledToolExecutor` implementation is deferred. MCP / REST / DB tool adapters are deferred.

Current seed: no tool-request contracts; `execute_plan` retains retrieval-shaped PlanStep orchestration through the seeded retrieval entrypoint (currently no active retrieval source). Response drafting generation is delegated to `ResponseDraftingOperation` via `PromptRepository` → `ResolvedPrompt` → `LLMPort`.

### FastAPI as delivery adapter

FastAPI is the HTTP **delivery / driving adapter**. It adapts transport to application use cases (directly, or via optional LangGraph). It must not own business policy, prompt identity, or provider choice.

Current seed: FastAPI exposes health/version only; the graph is invoked from scripts/tests, not from a production API use-case surface.

### Optional LangGraph orchestration

LangGraph is an optional **driving/orchestration adapter**. A project may use it; the template remains correct when FastAPI calls the application core without a graph.

LangGraph may own framework-specific concerns when justified:

- `StateGraph`
- graph-specific state
- routing
- `thread_id`
- checkpointing
- `interrupt()` / resume
- streaming

LangGraph may **not** own:

- business contracts
- business policy
- prompt identity
- provider selection
- tool authorization
- operational/domain persistence

OpenAI, prompt-management implementations, telemetry exporters, and persistence adapters remain **outbound/driven adapters** behind application-owned ports where applicable.

Do not propose a generic business graph or a speculative generic LangGraph runtime. Checkpointing, durable HITL, streaming, and history APIs are deferred until justified.

### Deployment / provider portability

The same application core should be deployable with different delivery and provider adapters. Portability is achieved through ports, not through premature multi-provider implementations or extra infrastructure.

## LLM decision

One provider path is in scope for the seed: OpenAI via `AsyncOpenAIWrapper` behind `LLMPort`. Additional providers stay on the deferred register until a real requirement exists.

## What this document does not decide

- a final target directory tree
- runtime Python module layout for contracts and ports
- which deferred capabilities any future project will activate
- replacement of the seeded Customer Support workflow
