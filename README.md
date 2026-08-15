# production-ai-runtime-template

Reusable **production-oriented AI runtime template** in preparation. Governance and architecture documentation live under [`.ai/`](.ai/README.md). The Python tree still contains a **seeded Customer Support Triage** example; that seed is useful code and now includes the M1 Application LLM Execution Boundary plus M2 Prompt Identity / Immutable Prompt Resolution for active LLM paths. Later readiness capabilities (`ExecutionContext`, Telemetry, and others) remain unimplemented — see [`.ai/architecture/template-readiness.md`](.ai/architecture/template-readiness.md).

This repository is no longer the `fastapi-prod-starter` sample. Docker Compose service names in `docker-compose.yaml` may still reflect that older identity; renaming them is an infrastructure change, not a documentation correction.

## Architecture, governance, and continuation

**Start here: [`.ai/README.md`](.ai/README.md)**

That tree is the persistent human/AI engineering continuity layer:

- approved target architecture and invariants
- current repository file map
- deferred capabilities
- ChatGPT/Cursor workflow
- continuation state in [`.ai/handoff.md`](.ai/handoff.md)

## Seeded implementation (current code)

FastAPI still exposes `/health` and `/version` only. The Customer Support LangGraph example remains the live seeded workflow under `app/` (input shield, triage, planner, execute plan, guardrails, human review, finalize). It is exercised by tests and `scripts/run_graph_once.py`.

Active LLM paths now use:

```text
LangGraph Node
  → Application Operation
  → PromptRef / PromptRepository
  → ResolvedPrompt
  → LLMPort
  → OpenAI Adapter
```

Prompt revisions are local, code-backed, and immutable (`input-shield@1`, `triage@1`, `planner@1`, `response-drafting@1`) with explicit prompt identity (`prompt_id`, `revision`, `content_hash`). No prompt-management platform is required for the baseline.

Explicit production composition lives in `app/composition.py` (`build_runtime_graph()`). `scripts/run_graph_once.py` uses that composed runtime graph. LangGraph remains optional in the target architecture even though it is the active seeded orchestration example. `ExecutionContext` and Telemetry remain later readiness gaps.

Authoritative detail: [`.ai/architecture/architecture.md`](.ai/architecture/architecture.md) and [`.ai/architecture/file-map.md`](.ai/architecture/file-map.md). Optional Redis is used only for a health-check ping when `REDIS_URL` is set.

## Requirements

- Python 3.11
- Poetry
- Docker + Docker Compose (Docker Desktop on Windows/macOS) when using the Compose file

## Local setup (Windows PowerShell)

1) Install dependencies:

```powershell
poetry config virtualenvs.in-project true
poetry install
```

2) Provide a local `.env`. Current settings require `OPENAI_API_KEY`. `.env.example` is only a partial starter (`APP_ENV`, `APP_VERSION`, `LOG_LEVEL`); it is not a full settings catalog.

3) Run the FastAPI app:

```powershell
poetry run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## Quality checks

```powershell
poetry run ruff check .
poetry run pyright
poetry run pytest
```

## Docker Compose

`docker-compose.yaml` builds the app image and runs Redis beside it. Redis is not application state in the seed.

```powershell
docker compose up --build
```
