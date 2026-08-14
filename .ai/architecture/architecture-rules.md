# Architecture invariants

Normative. Use these directly in ChatGPT/Cursor reviews. A change that violates an invariant is out of architecture, even if tests pass.

1. **Application core must not import OpenAI SDK types.** OpenAI types stay in the OpenAI adapter. Application contracts use application types.

2. **Application core must not depend on LangGraph-specific types.** `StateGraph`, graph state classes, checkpoint tuples, and `thread_id` mechanics are orchestration concerns, not business contracts.

3. **Provider SDK objects must not leak into application contracts.** Raw SDK responses, vendor message objects, and vendor tool payloads are adapter-private.

4. **Prompt identity and revision are application-owned.** `prompt_id`, `revision`, and `content_hash` are application concerns. LangSmith (or any vendor prompt host) is not the owner.

5. **Vendor telemetry objects must not become application/domain contracts.** LangSmith runs, OpenTelemetry spans, and similar exporter objects are not domain models. The application owns `ExecutionContext` and a thin telemetry boundary.

6. **Business state and graph/checkpoint state are distinct.** Durable business facts are not LangGraph checkpoint blobs. Graph state may hold working data for a run; it does not replace application/domain persistence.

7. **LangGraph nodes orchestrate application behaviour; they do not own reusable business semantics.** Node functions may call use cases/services. They must not become the only place a business rule exists if that rule must be reused.

8. **LangGraph is optional.** Template architecture must not assume a graph is always present. Delivery adapters may call application services without a graph.

9. **No generic business graph belongs in the baseline.** Do not introduce a speculative “universal agent graph.” Graphs, when used, are justified per project and remain orchestration.

10. **LLMs cannot bypass controlled side-effect policy.** Model output is data. Side effects happen only through authorized `ToolRequest` handling (or equivalent application-controlled execution). The model does not get unconstrained callbacks into production systems.

11. **Optional infrastructure must not become a dependency without a real requirement.** Redis, Postgres, MongoDB, brokers, Kubernetes, vector stores, and similar items stay out of the core path until activated from the deferred register with a project decision.

12. **Project-specific choices must not silently become template rules.** Assignment decisions live under `.ai/projects/<project>/`. Do not rewrite `.ai/architecture/**` or `.ai/engineering/**` to encode one project’s preference.

13. **Framework and vendor choices belong behind justified adapter boundaries.** FastAPI, LangGraph, OpenAI, LangSmith, and Docker are chosen tools, not the application core.

14. **Prefer minimal abstractions to speculative extensibility.** Do not add ports, factories, or plugin systems “in case” a second provider or tool host appears.

15. **Adapt existing components before creating parallel replacements.** The OpenAI wrapper, typed schemas, guardrail helpers, and FastAPI app are the starting points. Do not add a second LLM client, second settings system, or second graph runtime beside them without an approved milestone that retires the old path.
