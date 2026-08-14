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

The seed often violates that (nodes import the OpenAI wrapper and LangSmith directly). Do not “fix” that in a documentation/governance milestone.

Documentation vs runtime (do not conflate):

```text
Template architecture/governance documentation
    → .ai/architecture/**, .ai/engineering/**, .ai/quick-start.md

Specialized contracts / operations / testing / project-workflow documentation
    → .ai/contracts/, .ai/operations/, .ai/projects/, .ai/skills/, .ai/engineering/testing-strategy.md
      (when those documents exist)

Runtime application contracts and ports
    → implemented in app/ under approved runtime milestones — not by documentation work
```

The current tree has the template architecture/governance documents under `.ai/`. Specialized `.ai/contracts/`, `.ai/operations/`, `.ai/projects/`, `.ai/skills/`, and `.ai/engineering/testing-strategy.md` are not present. Runtime `app/ports/` and `app/adapters/` packages are not present. Do not create them as placeholders, and do not invent a future runtime layout here.

---

## `app/`

**Current responsibility:** Python package for the seeded Customer Support Triage copilot: FastAPI process, LangGraph workflow, OpenAI calls, prompts, guardrails, and local retrieval.

**Role:** mixed (delivery + domain/example + adapter code in one tree)

**Depends on:** FastAPI, Pydantic, LangGraph, OpenAI SDK, LangSmith, Redis client, local files

**Must not introduce:** new runtime layers, extra providers, generic executors, or a parallel app package

**Change belongs here:** approved runtime milestones only. Documentation/governance work does not change `app/`.

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

**Current responsibility:** async OpenAI chat/structured-output wrapper with retries, timeout, wrapper-level guardrails, and LangSmith `@traceable`. Nodes call this class directly.

**Role:** outbound/driven adapter (today used as the LLM interface, not behind `LLMPort`)

**Depends on:** OpenAI SDK, LangSmith, `app.core.settings`, `app.core.exceptions`

**Must not introduce:** additional provider SDKs, or application/domain contracts defined in OpenAI types

**Change belongs here:** eventually becoming the OpenAI implementation of `LLMPort`. Do not add a second wrapper beside it.

---

## `app/prompts/`

Files: `input_shield_prompts.py`, `triage_prompts.py`, `planner_prompts.py`, `response_drafting_prompts.py`

**Current responsibility:** Python string builders for Customer Support node prompts. No `prompt_id` / `revision` / `content_hash`.

**Role:** domain/example-specific (target prompt identity is application-owned; this is not yet a `PromptRepository`)

**Depends on:** `app.schemas` for ticket/context interpolation

**Must not introduce:** LangSmith as prompt owner, or template-wide prompt APIs invented here

**Change belongs here:** seed prompt text for this example workflow; portable prompt lifecycle is a later approved runtime milestone.

---

## `app/nodes/`

Files: `input_shield.py`, `triage.py`, `planner.py`, `execute_plan.py`, `guardrails.py`, `human_review.py`, `finalize.py`

**Current responsibility:** LangGraph node functions for the Customer Support workflow, including LLM calls, retrieval, routing-relevant flags, and terminal outcome helpers.

**Role:** domain/example-specific driving/orchestration (should call application behaviour; currently owns much of it)

**Depends on:** `GraphState`, OpenAI wrapper, prompts, guardrails, retrieval service, LangSmith

**Must not introduce:** reusable business contracts, provider choice, or tool authorization as node-private SDK types

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

**Current responsibility:** local keyword scoring over `knowledge_base/*.md`. Tutorial-scale retrieval, not a vector RAG stack.

**Role:** domain/example-specific (looks like an adapter to a local corpus)

**Depends on:** filesystem, `RetrievedDocument` schema

**Must not introduce:** vector databases, embeddings pipelines, or generic tool execution

**Change belongs here:** this seed’s retrieval only. RAG/vector storage is deferred.

---

## `app/graph.py`

**Current responsibility:** builds and compiles the Customer Support `StateGraph` (nodes, conditional edges, `START`/`END`).

**Role:** domain/example-specific LangGraph **driving/orchestration** adapter (not an outbound LLM/tool adapter)

**Depends on:** LangGraph, `GraphState`, `app.nodes.*`

**Must not introduce:** a generic runtime, checkpointing, or template-wide graph factory

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

**Current responsibility:** pytest suite — FastAPI health, OpenAI wrapper unit tests, per-node tests, smoke test.

**Role:** engineering / test

**Depends on:** `app`, pytest, httpx/TestClient

**Must not introduce:** production behaviour, new runtime packages, or dependency changes to “make tests green” outside an approved milestone

**Change belongs here:** tests for existing seed behaviour. Documentation/governance work does not modify tests.

---

## `knowledge_base/`

Markdown FAQs/policies for the support example (`shipping_faq.md`, `refund_policy.md`, etc.).

**Role:** domain/example-specific content corpus

**Depends on:** nothing in code except `retrieval_service.py` reading `*.md`

**Must not introduce:** vector indexes or treating this folder as template documentation

**Change belongs here:** example retrieval documents only.

---

## `scripts/`

PowerShell helpers (`dev.ps1`, `test.ps1`, `lint.ps1`, `typecheck.ps1`) and `run_graph_once.py` (manual graph invocation). Several `.ps1` files contain commented commands rather than live invocations.

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

Persistent human/AI engineering continuity layer. Present today:

| Path | Role |
| --- | --- |
| `README.md` | Session entry point |
| `quick-start.md` | Template project bootstrap |
| `handoff.md` | Mutable continuation state |
| `architecture/*` | Stable template architecture |
| `engineering/engineering-principles.md` | Engineering standards |
| `engineering/development-workflow.md` | ChatGPT/Cursor workflow |
| `engineering/documentation-rules.md` | Documentation-impact rules |

**Role:** engineering / governance (not runtime)

**Must not introduce:** empty placeholder trees, runtime code, or mutable status duplicated into architecture docs

**Change belongs here:** documentation/governance per approved milestone.

---

## Other current areas (not runtime architecture)

| Path | Notes |
| --- | --- |
| `docs/` | Seeded Customer Support workflow notes (Greek/English). **Not** the template control plane. Do not treat as architecture authority. |
| `.env.example` | Incomplete starter env (`APP_ENV`, `APP_VERSION`, `LOG_LEVEL`). `Settings` also requires `OPENAI_API_KEY`. |
| `pyrightconfig.json` | Pyright: Python 3.11, `app` + `tests`, `.venv` |
| `.gitignore` | `.venv`, `.env`, caches |
