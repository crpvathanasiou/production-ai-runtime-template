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

Template Readiness governance integration: established as the required pre-M1 documentation boundary.

## Last approved milestone

M0B (and Template Readiness governance integration as the pre-M1 documentation boundary)

## Current implementation position

Internal Checkpoint 1 / Prompt 1 — correction/review cycle

- Prompt 2: **NOT YET AUTHORIZED**
- Internal Checkpoint 2: **NOT YET AUTHORIZED**

## Latest validation

Factual pre-M1 runtime baseline (before Prompt-1 runtime work):

- `poetry run pytest` — **31 passed**
- `poetry run pyright` — **1 known M1-related error** at `app/nodes/input_shield.py:157`
- `poetry run ruff check .` — **119 existing errors**

Do not treat uncommitted Prompt-1 results as an approved milestone result yet.

## Known baseline debt

Classification: **pre-existing seeded-runtime condition**, not addressed by documentation/governance work alone.

Also unchanged (out of current governance scope unless a later approved milestone says otherwise):

- `.env.example` incomplete vs required `OPENAI_API_KEY`
- `docker-compose.yaml` still uses `fastapi-prod-starter-*` names
- `scripts/test.ps1`, `lint.ps1`, `typecheck.ps1` contain commented commands

**SURFACE DISCREPANCY (docs vs runtime):** target ports/adapters, `ExecutionContext`, prompt identity, and `ToolRequest`/`ToolResult` are documented as approved target; seeded `app/` does not fully implement them yet. M1 Internal Checkpoint 1 begins the application LLM boundary only.

## Continuation-impacting blockers

None for starting/completing the authorized Prompt-1 correction/review cycle.

Prompt 2 and Internal Checkpoint 2 remain unauthorized until ChatGPT review explicitly allows them.

## Next approved action

Complete/review M1 Internal Checkpoint 1 / Prompt 1 correction → ChatGPT review → only then authorize Prompt 2.

## Forbidden / unapproved next actions

- Prompt 2 before ChatGPT review / explicit authorization
- Internal Checkpoint 2
- Prompt M2
- introducing `ExecutionContext`
- introducing Telemetry / `TelemetryPort`
- RAG implementation
- unrelated cleanup
- unapproved architecture or scope changes
- tool-specific parallel handoff/status files
