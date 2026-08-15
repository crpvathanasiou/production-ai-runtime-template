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

M2 — Prompt Identity / Immutable Prompt Resolution

Architecture: **APPROVED**

Implementation:

- `PromptRef` implemented
- `PromptIdentity` implemented
- `ResolvedPrompt` implemented
- `PromptRepository` implemented
- `LocalPromptRepository` implemented
- four live immutable V1 definitions (`input-shield@1`, `triage@1`, `planner@1`, `response-drafting@1`)
- four Application Operations use prompt resolution
- one shared repository wired through `app/composition.py`
- V1 hash regression evidence
- safe identity in Application Operation outcomes
- safe identity copied to node metadata where outcomes exist
- documentation reconciled with live M2 prompt lifecycle

**M2 status: IMPLEMENTATION + DOCS COMPLETE — NOT COMMITTED.**

Git has not established the M2 boundary. Await ChatGPT final M2 review before any M2 commit.

## Last approved milestone

M1 — Application LLM Execution Boundary (committed / pushed; HEAD baseline for this work: `250f256`)

## Current M2 architecture implemented

```text
LangGraph Node
  → Application Operation
  → PromptRef / PromptRepository
  → ResolvedPrompt
  → LLMPort
  → AsyncOpenAIWrapper / OpenAI
```

Explicit composition: `app/composition.py` (`build_runtime_graph()`)

- one shared `LocalPromptRepository`
- four immutable code-backed V1 `PromptDefinition`s
- Application Operations own domain → prompt-variable preprocessing and `PromptRef` resolution
- `LLMPort` remains prompt-lifecycle neutral
- nodes do not resolve prompts; they copy only safe identity fields when an outcome exists

## Known M2→M3 failure-traceability boundary

For Triage and ResponseDrafting, prompt resolution occurs before provider execution. If the subsequent provider/model call raises and no Application Operation outcome is returned, current node error metadata does **not** contain prompt identity.

This is intentional in M2. It is **not** an M2 architectural defect and does **not** mean prompt identity is absent from the architecture. The immutable prompt was resolved correctly; what remains missing is a cross-cutting execution-event/correlation mechanism that can record identity before/around an attempted provider call even when the operation raises.

That belongs to **M3 / P0.3**: `ExecutionContext` + application execution events + `TelemetryPort`.

M2 establishes immutable identity + resolution + result evidence. Full failed-attempt execution traceability remains dependent on M3. The normative prompt-traceability requirement remains unchanged; complete failed-attempt evidence is still BLOCKED on the M3 cross-cutting execution boundary.

## Latest validation

Final M2 documentation-reconciliation validation (this prompt):

- `poetry run pytest` — **120 passed**
- `poetry run pyright` — **0 errors**
- `poetry run ruff check .` — **104 existing Ruff errors remain.** No unrelated repository-wide Ruff cleanup was performed.
- Targeted Ruff over M2 structural/runtime + test files (excluding immutable V1 prompt-template string literals) — **passed**
- Six `E501` findings remain inside immutable V1 prompt template text in `app/prompts/*_prompts.py`. Fixing them would mutate V1 content/`content_hash`; they are accepted prompt-content line-length debt, not new structural debt from this documentation pass.
- `git diff --check` — **PASS**

Committed HEAD at start of this prompt: `250f256` (`feat: establish application LLM execution boundary`). M2 runtime + documentation remain uncommitted.

## Known baseline debt

Classification: **pre-existing / later readiness**, not closed by M2.

- repository-wide Ruff debt still exists (**104**); Template **READY** is **NOT** achieved
- M2 structural/test files pass targeted Ruff; immutable V1 prompt-template `E501` lines remain by design of the seeded content
- `ExecutionContext` — not implemented
- `TelemetryPort` / application telemetry boundary — not implemented
- complete failed-attempt identity telemetry (M2→M3 boundary above) — not implemented
- controlled tool executor / RAG backend / durable HITL / CI readiness closure — not implemented
- remote prompt-management platform — not required and not implemented
- `.env.example` incomplete vs required `OPENAI_API_KEY`
- `docker-compose.yaml` still uses `fastapi-prod-starter-*` names
- `scripts/test.ps1`, `lint.ps1`, `typecheck.ps1` contain commented commands

**SURFACE DISCREPANCY (narrowed after M2):** Application LLM boundary + Prompt Identity / Immutable Prompt Resolution are implemented for active LLM paths. Remaining approved-target gaps that are still absent: `ExecutionContext`, Telemetry, `ToolRequest`/`ToolResult` controlled execution, and other Template Readiness items. Do not treat Template READY as achieved.

## Continuation-impacting blockers

None for ChatGPT final M2 review.

## Next approved action

ChatGPT final M2 review → if approved, **ONE M2 Git boundary** (commit of reviewed M2 runtime + documentation).

## Forbidden / unapproved next actions

- M2 commit without ChatGPT final review / explicit authorization
- Prompt M3
- introducing `ExecutionContext`
- introducing Telemetry / `TelemetryPort`
- RAG implementation
- unrelated readiness cleanup / repository-wide Ruff cleanup
- unapproved architecture or scope changes
- declaring TEMPLATE READY
- tool-specific parallel handoff/status files
