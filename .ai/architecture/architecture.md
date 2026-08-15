# Minimal Target Architecture

This document is the approved **target** architecture for the reusable template. It is not a description of the seeded Customer Support Triage runtime, and it does not invent a final package layout.

## Approved target vs current seed

**Approved target architecture** is the model below. Future work must move toward it.

**Currently implemented in the seeded repository (after M1):**

- FastAPI app with `/health` and `/version`
- optional Redis ping in the health check
- a Customer Support Triage LangGraph workflow (`input_shield` → `triage` → `planner` → `execute_plan` → `guardrails` → `human_review` → `finalize`)
- real Application Core under `app/application/` with four live operations:
  `InputShieldOperation`, `TriageOperation`, `PlannerOperation`, `ResponseDraftingOperation`
- provider-neutral `LLMPort` (`app/application/ports/llm.py`)
- `AsyncOpenAIWrapper` as the concrete OpenAI outbound adapter satisfying that boundary
- explicit production composition in `app/composition.py` (`build_runtime_graph()`)
- active LLM paths: LangGraph Node → Application Operation → `LLMPort` → `AsyncOpenAIWrapper` / OpenAI
- prompt text still built in Python modules under `app/prompts/` (invoked by Application Operations; no prompt identity/revision/hash)
- a seeded retrieval entrypoint / workflow seam (no repository-level knowledge corpus; no active retrieval backend; current placement in `execute_plan` unchanged by M1)
- LangSmith `@traceable` on selected calls and nodes

**Not yet implemented (later readiness / deferred):** Prompt Identity / `PromptRepository`, `ExecutionContext`, `TelemetryPort`, controlled tool runtime, RAG backend, durable HITL, CI readiness closure, multiple providers. Do not document those as already implemented. M1 does **not** make the entire Template Readiness baseline complete.

GraphState remains outside Application Core. Prompt invocation for the four live LLM paths is application-owned.

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

The application owns a correlation/execution context. This concept is **not** implemented in the seeded Python runtime.

Baseline identity (conceptual minimum):

```text
request_id
run_id
optional thread_id
```

Additional fields are **requirement-driven**, not baseline-required:

```text
user identity
tenant
actor
policy context
extra correlation metadata
```

Graph-specific state may carry a copy of identifiers; it is not the owner of execution semantics. Do not design a custom tracing framework around this.

### Provider-neutral `LLMPort`

The application calls language models through a provider-neutral **port**. After M1, `LLMPort` exists and `AsyncOpenAIWrapper` is the concrete OpenAI outbound adapter behind that boundary for the four live Application Operations. Multiple providers are not implemented. Do not imply that they are.

### Prompt identity and `PromptRepository`

The application owns:

```text
prompt_id
revision
content_hash
```

A portable `PromptRepository` is the application-owned store/lookup **port** for prompt content. A prompt-management product may later be an outbound adapter behind that port; it is not the architectural owner of prompt identity.

Current seed: prompt strings live in `app/prompts/*.py` with no revision/hash identity.

### Application-owned telemetry boundary

The application owns `ExecutionContext` and a **thin** telemetry boundary (what was invoked, latency, outcome, correlation ids). LangSmith and OpenTelemetry may later be outbound exporters behind that boundary. Do not design a custom tracing platform.

Current seed: stdlib logging plus LangSmith `@traceable` mixed into wrapper and nodes.

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

Current seed: no tool-request contracts; `execute_plan` retains retrieval-shaped PlanStep orchestration through the seeded retrieval entrypoint (currently no active retrieval source; placement unchanged by M1). Response drafting generation is delegated to `ResponseDraftingOperation` via `LLMPort`.

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
