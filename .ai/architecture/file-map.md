# File map — current repository

This map describes the repository **as it exists now**. It does not invent a future runtime directory structure.

Classification key:

- **reusable/core-related** — candidate application-core or shared engineering meaning
- **adapter** — vendor/framework implementation that should sit behind a port
- **delivery** — transport/entry surface
- **domain/example-specific** — seeded Customer Support Triage behaviour
- **engineering / test / infrastructure** — toolchain, tests, deploy, governance

Dependency direction for the **target** architecture:

```text
Client → Delivery Adapter → [optional LangGraph driving/orchestration] → Application Core → Ports ← outbound/driven adapters
```

The seed previously violated that direction (nodes importing the OpenAI wrapper directly). After M2, active LLM paths go Node → Application Operation → `PromptRepository` → `ResolvedPrompt` → `LLMPort` → adapter; GraphState and LangGraph remain orchestration concerns. Do not invent a future runtime layout beyond what exists.

Documentation vs runtime (do not conflate):

```text
Template architecture/governance documentation
    → .ai/architecture/**, .ai/engineering/**, .ai/quick-start.md

Specialized contracts / operations / testing / project-workflow documentation
    → .ai/contracts/, .ai/operations/, .ai/projects/, .ai/skills/, .ai/engineering/testing-strategy.md
      (when those documents exist)

Runtime application contracts and ports
    → present after M2: `app/application/` + `LLMPort` + prompt lifecycle types/`PromptRepository`; not a full `app/ports/` / `app/adapters/` tree
```

The current tree includes template architecture/governance plus specialized `.ai/contracts/`, `.ai/operations/`, `.ai/projects/` (`_template` only; no active project), `.ai/skills/`, and the remaining engineering strategy documents. Runtime `app/ports/` and `app/adapters/` packages are **not** present as separate trees; M1 placed the LLM port under `app/application/ports/`, and M2 placed prompt lifecycle contracts under `app/application/prompts/`. Do not invent a future runtime layout here. Documentation of contracts is not Python contract implementation.

---

## `app/`

**Current responsibility:** Python package for the seeded Customer Support Triage copilot: FastAPI process, LangGraph workflow, Application Core LLM operations, prompt lifecycle (`PromptRepository` + local immutable definitions), OpenAI adapter behind `LLMPort`, guardrails, and a seeded retrieval entrypoint/seam (currently inert).

**Role:** mixed (delivery + domain/example + application core + adapter code in one tree)

**Depends on:** FastAPI, Pydantic, LangGraph, OpenAI SDK, LangSmith, Redis client

**Must not introduce:** new runtime layers beyond approved milestones, extra providers, generic executors, or a parallel app package

**Change belongs here:** approved runtime milestones only. Documentation/governance work does not change `app/`.

---

## `app/application/`

Files: `input_shield.py`, `triage.py`, `planner.py`, `response_drafting.py`, `ports/llm.py`, `prompts/` (plus package `__init__` modules)

**Current responsibility:** Application Core for the four live LLM use cases. Owns application/use-case semantics, explicit `PromptRef` resolution through `PromptRepository`, domain → prompt-variable preprocessing, `LLMPort` usage, Input Shield deterministic max-prompt policy and normalization/fallback, Planner normalization/fallback, Triage and Response Drafting LLM execution, and `PromptIdentity` on operation outcomes where a prompt was resolved.

**Role:** reusable/core-related (Application Core for LLM paths)

**Depends on:** `LLMPort`, `PromptRepository` / `PromptRef` / `ResolvedPrompt`, schemas/domain types used by operations — **not** `GraphState`, LangGraph, OpenAI SDK, LangSmith, concrete provider models, `LocalPromptRepository`, `PromptDefinition`, `request_id`, or `workflow_outcome`

**Must not introduce:** GraphState/framework/provider leakage into Application Core; domain-specific knowledge into the prompt repository port

**Change belongs here:** application LLM use-case semantics under approved milestones. `ExecutionContext` / Telemetry are **not** implemented here yet.

---

## `app/application/prompts/`

Files: `models.py`, `repository.py`, `__init__.py`

**Current responsibility:** application-owned prompt lifecycle contracts — `PromptRef`, `PromptIdentity`, `ResolvedPrompt`, `PromptRepository` protocol, and resolution error types.

**Role:** reusable/core-related (Application Core prompt identity)

**Depends on:** stdlib / typing only (domain-neutral)

**Must not introduce:** Customer Support schemas, LangGraph, provider SDKs, or remote prompt hosts

**Change belongs here:** portable prompt-identity contracts under approved milestones.

---

## `app/composition.py`

**Current responsibility:** explicit production composition root. Reads settings; constructs four configured `AsyncOpenAIWrapper` instances; constructs one shared `LocalPromptRepository` supplying all four immutable V1 definitions; constructs four Application Operations with explicit `PromptRef`s; supplies them to `build_graph(...)`; supplies model-name labels only for orchestration observability.

**Role:** composition / wiring (not Application Core business semantics)

**Depends on:** settings, Application Operations, `LocalPromptRepository`, V1 prompt definitions, `AsyncOpenAIWrapper`, `app.graph.build_graph`

**Must not introduce:** business policy inside composition beyond wiring

**Change belongs here:** production wiring for the live seeded runtime.

---

## `app/core/`

Files: `settings.py`, `exceptions.py`, `logging.py`

**Current responsibility:** environment settings (`pydantic-settings`), application exception types, stdlib logging helpers.

**Role:** reusable/core-related (settings also encode OpenAI/LangSmith/Redis and Customer Support model-name fields)

**Depends on:** `pydantic-settings`, stdlib logging

**Must not introduce:** vendor SDK types, LangGraph types, or project-only business policy

**Change belongs here:** shared configuration, error taxonomy, and logging helpers — adapted in place, not replaced.

---

## `app/llm/`

File: `openai_wrapper.py`

**Current responsibility:** concrete outbound OpenAI adapter behind `LLMPort` — async chat/structured-output with retries, timeouts, provider parsing, wrapper-level guardrails, and LangSmith `@traceable`. Constructed in `app/composition.py`; **not** constructed or called directly by LangGraph nodes. Prompt-lifecycle agnostic (no `PromptRef` / revision / `content_hash`).

**Role:** outbound/driven adapter (OpenAI implementation of the LLM boundary)

**Depends on:** OpenAI SDK, LangSmith, `app.core.settings`, `app.core.exceptions`

**Must not introduce:** additional provider SDKs, or application/domain contracts defined in OpenAI types

**Change belongs here:** OpenAI adapter behaviour. Do not add a second wrapper beside it.

---

## `app/prompts/`

Files: `local_repository.py`, `input_shield_prompts.py`, `triage_prompts.py`, `planner_prompts.py`, `response_drafting_prompts.py`

**Current responsibility:**

- `local_repository.py` — concrete code-backed `LocalPromptRepository`: deterministic rendering, exact `PromptRef` resolution, SHA-256 static-definition `content_hash` (system_template + user_template; not runtime variables)
- `*_prompts.py` — immutable code-backed V1 `PromptDefinition`s for the Customer Support seed (`input-shield@1`, `triage@1`, `planner@1`, `response-drafting@1`); one revision owns the complete system+user template bundle

These files are seeded prompt content / the local repository adapter — **not** the application prompt contracts themselves (`app/application/prompts/` owns those).

**Role:** mixed — `LocalPromptRepository` is a reusable local adapter pattern; V1 definitions are domain/example-specific

**Depends on:** application prompt contracts; seeded definitions may reference schema field names only as template variable conventions via operation-owned preprocessing

**Must not introduce:** LangSmith as prompt owner, moving aliases (`latest` / `production`), remote/DB prompt stores, or environment-driven revision selection

**Change belongs here:** seed prompt text and local repository behaviour; remote prompt-management remains optional/deferred.

---

## `app/nodes/`

Files: `input_shield.py`, `triage.py`, `planner.py`, `execute_plan.py`, `guardrails.py`, `human_review.py`, `finalize.py`

**Current responsibility:** LangGraph orchestration adapters for the Customer Support workflow. Live LLM nodes receive Application Operations through typed factory closures; own GraphState mapping, orchestration prerequisites, `workflow_outcome` mapping, and request_id/logging/metadata. Copy safe prompt identity (`prompt_id`, `prompt_revision`, `prompt_content_hash`) into `additional_metadata` when an operation outcome exists. Do **not** resolve prompts, construct OpenAI providers, or own reusable prompt/LLM application semantics. `execute_plan` retains current retrieval/PlanStep orchestration and delegates response drafting generation to `ResponseDraftingOperation`.

**Role:** domain/example-specific driving/orchestration

**Depends on:** `GraphState`, injected Application Operations, guardrails, retrieval service, LangSmith

**Must not introduce:** reusable business contracts, provider construction, prompt resolution, or tool authorization as node-private SDK types

**Change belongs here:** this example graph’s orchestration only. Do not turn these nodes into a generic business graph.

---

## `app/guardrails/`

Files: `input_guardrails.py`, `response_guardrails.py`

**Current responsibility:** deterministic input sanitization/classification helpers and response-draft safety checks for the support example (refund/security overclaim patterns, etc.). Distinct from wrapper `BaseGuardrail` in `app/llm/`.

**Role:** mixed — pattern is reusable/core-related; current rules are domain/example-specific

**Depends on:** `app.schemas`, `GraphState`

**Must not introduce:** LLM-based policy as a hidden side effect, or vendor moderation objects as domain contracts

**Change belongs here:** this example’s deterministic policy checks; template-wide policy engines are not implied.

---

## `app/services/`

File: `retrieval_service.py`

**Current responsibility:** seeded retrieval extension point / entrypoint for the example workflow; currently no active retrieval backend and returns no documents. Not a vector RAG stack.

**Role:** domain/example-specific retrieval seam

**Depends on:** `RetrievedDocument` schema

**Must not introduce:** vector databases, embeddings pipelines, or generic tool execution

**Change belongs here:** this seed’s retrieval entrypoint only. RAG/vector storage is deferred.

---

## `app/graph.py`

**Current responsibility:** owns graph topology/wiring for the Customer Support `StateGraph` (nodes, conditional edges, `START`/`END`). Receives injected Application Operations and model-name labels; does **not** construct providers.

**Role:** domain/example-specific LangGraph **driving/orchestration** adapter (not an outbound LLM/tool adapter)

**Depends on:** LangGraph, `GraphState`, `app.nodes.*`, Application Operation types

**Must not introduce:** a generic runtime, checkpointing, provider construction, or template-wide graph factory

**Change belongs here:** wiring for this example graph only.

---

## `app/graph_state.py`

**Current responsibility:** Pydantic `GraphState` for one Customer Support run (`request_id`, ticket, shield/triage/plan/draft fields, safety/HITL flags, `workflow_outcome`).

**Role:** domain/example-specific graph-specific state — **not** business/domain persistence and **not** `ExecutionContext`

**Depends on:** `app.schemas`

**Must not introduce:** OpenAI/LangGraph SDK types, vendor telemetry objects, or durable store documents

**Change belongs here:** this graph’s working state. Keep it distinct from application business state.

---

## `app/main.py`

**Current responsibility:** FastAPI app (`title="Customer Support Triage"`), logging setup, `/health` (optional Redis ping), `/version`. Does not expose the graph as an API.

**Role:** delivery / driving adapter

**Depends on:** FastAPI, Redis client, `app.core.settings`

**Must not introduce:** business policy, prompt identity, or LLM calls in the delivery module

**Change belongs here:** HTTP delivery for this process. Graph/use-case endpoints only when an approved runtime milestone defines them.

---

## `app/schemas.py`

**Current responsibility:** seeded Pydantic models: `SupportTicket`, `ShieldOutput`, `TriageOutput`, `RetrievedDocument`, `ResponseDrafting`, `PlanStep`, `SupportAgentState`.

**Role:** domain/example-specific contracts (typed, but not the reusable template contract set)

**Depends on:** Pydantic

**Must not introduce:** OpenAI/LangGraph/LangSmith types, or silent promotion of these models into template-wide contracts

**Change belongs here:** this example’s request/workflow shapes. Reusable **runtime** application contracts and ports are implemented in `app/` under approved runtime milestones. Specialized **documentation** of contracts belongs under `.ai/contracts/` when that documentation exists. Do not silently rewrite this file into a template-wide contract set.

---

## `tests/`

**Current responsibility:** pytest suite — FastAPI health, Application Operation tests with FakeLLM, prompt model/repository contract tests, immutable V1 hash regression tests, exact parity tests, OpenAI adapter unit tests, node tests with fake Application Operations (including safe prompt-identity metadata), composition tests, per-node behavioural coverage, smoke test.

**Role:** engineering / test

**Depends on:** `app`, pytest, httpx/TestClient

**Must not introduce:** production behaviour, new runtime packages, or dependency changes to “make tests green” outside an approved milestone

**Change belongs here:** tests for existing seed / approved milestone behaviour. Documentation/governance work does not modify tests.

---

## `scripts/`

PowerShell helpers (`dev.ps1`, `test.ps1`, `lint.ps1`, `typecheck.ps1`) and `run_graph_once.py` (manual graph invocation via `app.composition.build_runtime_graph()`). Several `.ps1` files contain commented commands rather than live invocations.

**Role:** engineering / infrastructure

**Must not introduce:** new runtime architecture or CI systems in a documentation/governance milestone

**Change belongs here:** developer convenience only, under later approved milestones.

---

## `Dockerfile`

Multi-stage Python 3.11 image: Poetry install, build-time pytest/ruff/pyright, runtime uvicorn (`app.main:app`).

**Role:** engineering / infrastructure

**Must not introduce:** extra services, Kubernetes, or build-time architecture changes in a documentation/governance milestone

**Change belongs here:** container packaging of the existing app.

---

## `docker-compose.yaml`

Runs the app plus Redis 7. Container names still use `fastapi-prod-starter-*`. Redis is wired as `REDIS_URL` for the health-check ping.

**Role:** engineering / infrastructure

**Must not introduce:** Postgres, brokers, or treating Redis as application state without an approved activation

**Change belongs here:** local/dev composition of the current seed.

---

## `pyproject.toml`

Package name `production-ai-runtime-template`. Runtime deps: FastAPI, uvicorn, pydantic-settings, redis, langgraph, openai, langsmith. Dev: pytest, httpx, ruff, pyright, pytest-asyncio. Python `^3.11`.

**Role:** engineering / infrastructure

**Must not introduce:** `uv`, alternate type checkers, extra providers, or toolchain copied from other repositories

**Change belongs here:** approved dependency/tooling milestones only. Documentation/governance work does not change this file.

---

## `README.md`

Root human entry for identity, local run, and quality commands. Identity is `production-ai-runtime-template`; Compose service names may still reflect an older starter name.

**Role:** engineering / infrastructure (navigation)

**Change belongs here:** repository identity and pointers to `.ai/`. Architecture authority lives in `.ai/`, not here.

---

## `.ai/`

Persistent human/AI engineering continuity layer. **One** shared tool-neutral workspace. **One** canonical `handoff.md`.

| Path | Role |
| --- | --- |
| `README.md` | Session entry point |
| `quick-start.md` | Template project bootstrap |
| `handoff.md` | Shared continuation state (next approved action) |
| `architecture/template-readiness.md` | Normative template-level finish-line / readiness authority |
| `architecture/*` | Stable template architecture, file map, deferred register |
| `contracts/` | Agent behaviour, prompt lifecycle, tool-execution contracts |
| `engineering/` | Principles, workflow, delivery method, testing, evaluation, security, documentation protocol |
| `operations/` | Observability and error-handling strategy |
| `projects/` | Project workspaces; `_template` only until an assignment is created |
| `skills/` | Recurring review/planning procedures (not runtime) |

### `architecture/template-readiness.md` ownership

**Owns:**

- definition of template READY;
- mandatory readiness capability set;
- readiness gates;
- mandatory vs deferred / project-specific distinction.

**Does not own:**

- current milestone;
- Git state;
- current bugs;
- temporary migration state.

`.ai/` role: engineering / governance (not runtime)

**Must not introduce:** tool-private handoff/status files, empty placeholder trees, runtime code, or mutable status duplicated into architecture docs

**Change belongs here:** documentation/governance per approved milestone.

---

## Other current areas (not runtime architecture)

| Path | Notes |
| --- | --- |
| `docs/` | Seeded Customer Support workflow notes (Greek/English). **Not** the template control plane. Do not treat as architecture authority. |
| `.env.example` | Incomplete starter env (`APP_ENV`, `APP_VERSION`, `LOG_LEVEL`). `Settings` also requires `OPENAI_API_KEY`. |
| `pyrightconfig.json` | Pyright: Python 3.11, `app` + `tests`, `.venv` |
| `.gitignore` | `.venv`, `.env`, caches |
