# Handoff — current continuation state

ONE shared, tool-neutral continuation document for ChatGPT, Cursor, humans, and future AI engineering tools.

This file is the only authority for **what am I allowed to do next?**

It does **not** own architecture, project decision rationale, or factual proof that a Git commit exists. Git is authoritative for HEAD, commit hashes, working-tree state, and milestone Git boundaries.

Template readiness / finish-line authority lives in [`architecture/template-readiness.md`](architecture/template-readiness.md).

```text
IMPLEMENTED  → workflow / documentation state (this file may record)
APPROVED     → governance / documentation state (this file may record)
COMMITTED    → factual Git state (Git only)
```

---

## Repository

`production-ai-runtime-template`  
https://github.com/crpvathanasiou/production-ai-runtime-template

## Branch

`main`

## Active project

None / template preparation

No `.ai/projects/<active-project>/` workspace. Only `_template` exists. Seeded Customer Support Triage remains example code in `app/`.

## Current milestone

M1 — Application LLM Execution Boundary

Architecture: **APPROVED**

Delivery structure: **ONE M1 / TWO INTERNAL CHECKPOINTS**

Implementation state:

- Internal Checkpoint 1 — complete / reviewed
- Internal Checkpoint 2 runtime migration — complete / reviewed
- documentation reconciliation — complete
- final M1 validation — complete (commands below)

**M1 is NOT COMMITTED.** Git has not established the M1 boundary. Await ChatGPT final review before any M1 commit.

## Last approved milestone

M0B (and Template Readiness governance integration as the pre-M1 documentation boundary)

## Current M1 architecture implemented

```text
LangGraph Node
  → Application Operation
  → LLMPort
  → AsyncOpenAIWrapper / OpenAI
```

Explicit composition: `app/composition.py` (`build_runtime_graph()`)

Live Application Operations:

- `InputShieldOperation`
- `TriageOperation`
- `PlannerOperation`
- `ResponseDraftingOperation`

## Latest validation

Final M1 documentation-reconciliation validation (this prompt):

- `poetry run pytest` — **74 passed**
- `poetry run pyright` — **0 errors**
- `poetry run ruff check .` — **104 existing Ruff errors remain.** Pre-M1 baseline was 119; M1 introduced no new Ruff violations and reduced the count only through files already touched by M1. No unrelated repository-wide Ruff cleanup was performed.
- `git diff --check` — **PASS**

Committed HEAD at start of this prompt: `e8e213e` (`docs: integrate template readiness governance`). M1 runtime + docs remain uncommitted.

## Known baseline debt

Classification: **pre-existing / later readiness**, not closed by M1.

- repository-wide Ruff debt still exists (**104**); Template **READY** is **NOT** achieved
- M1 introduced no new Ruff violations. New M1 files and the targeted migrated files passed Ruff checks; pre-existing Ruff debt remains in existing files such as `openai_wrapper.py` / `run_graph_once.py`.
- Prompt Identity / Immutable Prompt Resolution — not implemented (likely next major readiness gap)
- `ExecutionContext` — not implemented
- `TelemetryPort` / application telemetry boundary — not implemented
- controlled tool executor / RAG backend / durable HITL / CI readiness closure — not implemented
- `.env.example` incomplete vs required `OPENAI_API_KEY`
- `docker-compose.yaml` still uses `fastapi-prod-starter-*` names
- `scripts/test.ps1`, `lint.ps1`, `typecheck.ps1` contain commented commands

**SURFACE DISCREPANCY (narrowed after M1):** Application LLM boundary (`LLMPort` + Operations + composition) is implemented for active LLM paths. Remaining approved-target gaps that are still absent: Prompt Identity / `PromptRepository`, `ExecutionContext`, Telemetry, `ToolRequest`/`ToolResult` controlled execution, and other Template Readiness items. Do not treat Template READY as achieved.

## Continuation-impacting blockers

None for ChatGPT final M1 review.

## Next approved action

ChatGPT final M1 review → if approved, **ONE M1 Git boundary** (commit of reviewed M1 runtime + documentation).

## Forbidden / unapproved next actions

- M1 commit without ChatGPT final review / explicit authorization
- Prompt M2
- introducing `ExecutionContext`
- introducing Telemetry / `TelemetryPort`
- Prompt Identity / `PromptRepository` implementation
- RAG implementation
- unrelated readiness cleanup / repository-wide Ruff cleanup
- unapproved architecture or scope changes
- declaring TEMPLATE READY
- tool-specific parallel handoff/status files
