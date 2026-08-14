# production-ai-runtime-template

Reusable **production-oriented AI runtime template** in preparation. Governance and architecture documentation live under [`.ai/`](.ai/README.md). The Python tree still contains a **seeded Customer Support Triage** example; that seed is useful code, not a claim that the approved ports-and-adapters runtime, prompt lifecycle, or M1+ contracts already exist.

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

FastAPI serves `/health` and `/version`. A LangGraph Customer Support workflow (input shield, triage, planner, execute plan, guardrails, human review, finalize) lives under `app/` and is exercised by tests and `scripts/run_graph_once.py`. OpenAI is called through `app/llm/openai_wrapper.py`. Optional Redis is used only for a health-check ping when `REDIS_URL` is set.

That behaviour is the seed. The intended reusable architecture is documented in [`.ai/architecture/architecture.md`](.ai/architecture/architecture.md).

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
