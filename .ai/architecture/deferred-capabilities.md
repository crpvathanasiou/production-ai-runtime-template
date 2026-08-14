# Deferred capabilities

Authoritative anti-overengineering register for the reusable template.

**Presence here is not permission to implement.** Activation requires a real assignment need, an approved project architecture decision, and an explicit milestone. Until then, do not scaffold, stub, or “just add the interface.”

## Database tool vs application persistence

These are different architectural concepts. Keep both deferred until separately justified. A database is not an LLM/tool interface merely because the application stores data there.

```text
Database exposed as an agent/tool capability
    ↓
ToolAdapter boundary
    ↓
Controlled tool execution policy
```

versus:

```text
Application/domain persistence
    ↓
Persistence Port
    ↓
Persistence Adapter / database driver
```

Do not implement a persistence port or a tool adapter unless an approved milestone activates that specific capability.

---

## Generic `ControlledToolExecutor`

- **Status:** DEFER
- **Why deferred:** Baseline needs the *principle* (`ToolRequest` / `ToolResult`, no unconstrained LLM side effects), not a generic executor framework.
- **Trigger for activation:** Multiple distinct tool backends in one project, with shared authorization/timeout/idempotency rules that would otherwise be duplicated unsafely.
- **Expected architectural boundary:** Application-owned execution policy calling adapters; not a LangGraph node-private helper and not an LLM callback sandbox.
- **What must not be implemented speculatively:** plugin registries, permission DSLs, parallel executor types beside node code.
- **Reference pattern:** typed `ToolRequest` in → policy check → adapter → typed `ToolResult` out.

## MCP tool adapter

- **Status:** DEFER
- **Why deferred:** No current requirement to host or consume MCP tools.
- **Trigger for activation:** Assignment explicitly requires MCP as the tool transport.
- **Expected architectural boundary:** ToolAdapter behind application-owned `ToolRequest` / `ToolResult`; MCP types stay adapter-private.
- **What must not be implemented speculatively:** MCP client/server scaffolding, tool catalogs, or making MCP the default tool bus.
- **Reference pattern:** same `ToolRequest` / `ToolResult` contracts and ToolAdapter boundary as any other tool backend.

## REST tool adapter

- **Status:** DEFER
- **Why deferred:** Seed has no outbound business HTTP tools.
- **Trigger for activation:** A named external HTTP API must be invoked as a controlled side effect.
- **Expected architectural boundary:** HTTP client ToolAdapter behind `ToolRequest` / `ToolResult`; not ad-hoc `httpx` inside nodes as a permanent pattern.
- **What must not be implemented speculatively:** generic REST gateway, OpenAPI-to-tool codegen.
- **Reference pattern:** one adapter per justified API family.

## DB tool adapter

- **Status:** DEFER
- **Why deferred:** No requirement to expose a database as an agent/tool capability. Application persistence, if ever needed, is a different boundary (see Persistence backends).
- **Trigger for activation:** Assignment requires the workflow/LLM path to invoke database operations as a **controlled tool** (`ToolRequest` → authorized execution → `ToolResult`).
- **Expected architectural boundary:** ToolAdapter behind application-owned `ToolRequest` / `ToolResult` and controlled-execution policy. Not a persistence port, and not graph checkpoint state.
- **What must not be implemented speculatively:** treating the application data store as a tool; unrestricted “tools that run SQL”; conflating ORM repositories with tool adapters.
- **Reference pattern:** `ToolRequest` → controlled execution policy → DB ToolAdapter → `ToolResult`.

## Persistent idempotency

- **Status:** DEFER
- **Why deferred:** Seed is a single in-process graph run with no durable write side effects.
- **Trigger for activation:** Retryable side effects that must not duplicate (payments, tickets, emails, mutations).
- **Expected architectural boundary:** Application policy + store adapter keyed by idempotency keys; not LLM memory.
- **What must not be implemented speculatively:** distributed idempotency service, outbox “just in case.”

## Generic LangGraph runtime extensions

- **Status:** DEFER
- **Why deferred:** LangGraph is optional orchestration for a specific graph, not a productized agent OS.
- **Trigger for activation:** A justified, repeated orchestration need that cannot live in application services.
- **Expected architectural boundary:** Thin LangGraph driving/orchestration adapter; business semantics stay in the application core.
- **What must not be implemented speculatively:** universal agent graph, node marketplaces, subgraph frameworks.
- **Reference pattern:** one compiled graph per justified workflow.

## Checkpointing

- **Status:** DEFER
- **Why deferred:** Current graph compiles without a checkpointer; durable run state is not required.
- **Trigger for activation:** Process must resume after process restart or across requests with LangGraph checkpoint semantics.
- **Expected architectural boundary:** LangGraph checkpointer adapter. Distinct from business persistence.
- **What must not be implemented speculatively:** custom checkpoint stores “for production readiness.”
- **Reference pattern:** framework checkpoint ≠ domain aggregate.

## Durable HITL

- **Status:** DEFER
- **Why deferred:** Seed `human_review` is in-graph signalling, not a durable review inbox.
- **Trigger for activation:** Humans must approve/reject across sessions with stored review state.
- **Expected architectural boundary:** Application-owned review records + delivery APIs; LangGraph `interrupt()` only as orchestration if justified.
- **What must not be implemented speculatively:** full case-management product, email/Slack review bots.

## Persistence backends (general)

- **Status:** DEFER
- **Why deferred:** No durable application/domain state in the baseline beyond process memory / graph-specific state.
- **Trigger for activation:** A specific durable entity the assignment must keep as **application/domain persistence** (not as an LLM tool).
- **Expected architectural boundary:** Persistence Port → Persistence Adapter / database driver. Distinct from a DB tool adapter and from LangGraph checkpointing.
- **What must not be implemented speculatively:** repository-per-table sprawl, multi-backend support, or exposing the store as a generic agent tool “because a database exists.”

## PostgreSQL

- **Status:** DEFER
- **Why deferred:** No relational data requirement.
- **Trigger for activation:** Relational integrity / SQL reporting needed by the assignment.
- **Expected architectural boundary:** persistence adapter (Persistence Port), not compose-by-default infrastructure, and not a DB tool adapter.
- **What must not be implemented speculatively:** adding Postgres to Compose “because production apps have a DB.”

## MongoDB

- **Status:** DEFER
- **Why deferred:** No document-store requirement.
- **Trigger for activation:** Assignment explicitly needs a document model Postgres would not serve.
- **Expected architectural boundary:** persistence adapter (Persistence Port). Not a DB tool adapter.
- **What must not be implemented speculatively:** dual SQL+Mongo stacks.

## Long-term memory

- **Status:** DEFER
- **Why deferred:** Seed is per-ticket. Cross-session memory is a product decision, not a template default.
- **Trigger for activation:** Assignment requires recall across conversations with defined retention/policy.
- **Expected architectural boundary:** application memory port; not raw vector dump of transcripts.
- **What must not be implemented speculatively:** always-on memory layers, “agent memory” frameworks.

## RAG / vector storage

- **Status:** DEFER
- **Why deferred:** Seed retrieval is local keyword search over markdown files.
- **Trigger for activation:** Corpus size/quality needs embeddings and a vector index, with an evaluation story.
- **Expected architectural boundary:** retrieval port; vector DB is an adapter. Prompts still application-owned.
- **What must not be implemented speculatively:** embedding pipelines, chunkers, hybrid search stacks beside the keyword service without replacing it under an approved milestone.
- **Reference pattern:** adapt `retrieval_service.py` before adding a parallel RAG subsystem.

## Additional LLM providers

- **Status:** DEFER
- **Why deferred:** OpenAI wrapper is the only provider path. Portability is a port, not N implementations.
- **Trigger for activation:** A second provider is a real assignment constraint (cost, region, vendor).
- **Expected architectural boundary:** new adapter behind `LLMPort`. Application core unchanged.
- **What must not be implemented speculatively:** provider factory matrices, fallback routers, fake second clients.

## Kafka

- **Status:** DEFER
- **Why deferred:** No event-stream requirement.
- **Trigger for activation:** Assignment requires durable pub/sub at Kafka semantics.
- **Expected architectural boundary:** messaging adapter behind an application port.
- **What must not be implemented speculatively:** event-sourcing platform.

## RabbitMQ

- **Status:** DEFER
- **Why deferred:** No AMQP/work-queue requirement.
- **Trigger for activation:** Assignment requires work queues with those semantics.
- **Expected architectural boundary:** messaging adapter.
- **What must not be implemented speculatively:** adding a broker next to Redis because Compose already has Redis.

## Kubernetes

- **Status:** DEFER
- **Why deferred:** Docker/Compose covers current packaging. Cluster orchestration is an ops choice.
- **Trigger for activation:** Real deployment target is Kubernetes.
- **Expected architectural boundary:** deploy manifests / ops docs — not application core.
- **What must not be implemented speculatively:** Helm charts, operators, service mesh.

## Streaming

- **Status:** DEFER
- **Why deferred:** Seed returns whole node/graph results. Token streaming is delivery/orchestration, not core meaning.
- **Trigger for activation:** UX/API must stream tokens or node events.
- **Expected architectural boundary:** delivery adapter (+ optional LangGraph streaming). Contracts remain typed; streams are a transport.
- **What must not be implemented speculatively:** custom SSE frameworks, websocket platforms.

## History / thread APIs

- **Status:** DEFER
- **Why deferred:** No conversation-history product surface.
- **Trigger for activation:** Clients must list/resume threads with defined retention.
- **Expected architectural boundary:** application history records; LangGraph `thread_id` only if graph checkpointing is also justified.
- **What must not be implemented speculatively:** ChatGPT-like thread products.

## LangSmith prompt-management adapter

- **Status:** DEFER
- **Why deferred:** Application owns prompt identity. LangSmith is currently a tracing decorator, not prompt storage.
- **Trigger for activation:** Operations need hosted prompt management *without* transferring ownership of `prompt_id` / `revision` / `content_hash`.
- **Expected architectural boundary:** adapter behind `PromptRepository`. LangSmith objects are not domain contracts.
- **What must not be implemented speculatively:** making LangSmith Hub the source of truth.

## OpenTelemetry exporter

- **Status:** DEFER
- **Why deferred:** Need a thin application telemetry boundary first; OTEL is an exporter.
- **Trigger for activation:** Operations require OTEL pipelines (traces/metrics/logs) to an existing collector.
- **Expected architectural boundary:** exporter behind the application telemetry port. No custom tracing framework.
- **What must not be implemented speculatively:** in-house APM, dual LangSmith+OTEL instrumentation sprawl without a boundary.

## Custom evaluation platform

- **Status:** DEFER
- **Why deferred:** pytest covers engineering tests. Offline eval/product metrics are a later operations concern.
- **Trigger for activation:** Assignment needs repeatable quality eval against datasets/policies.
- **Expected architectural boundary:** operations/eval harness using application contracts; not a second runtime.
- **What must not be implemented speculatively:** eval SaaS clones, golden-set frameworks inside `app/`.

---

## Related seed items (not activations)

- **Redis** is already in Compose and health-check ping. That is not approval to use Redis for checkpointing, queues, or memory.
- **LangSmith tracing** in the wrapper/nodes is not approval for LangSmith prompt ownership or a telemetry domain model.
- **Keyword `knowledge_base/` retrieval** is not approval for vector RAG.
