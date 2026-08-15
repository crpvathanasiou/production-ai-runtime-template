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

## Last closed milestone

M2 — Prompt Identity / Immutable Prompt Resolution

Status: **CLOSED / APPROVED / COMMITTED / PUSHED**

Git boundary:

```text
13fc9e1
feat: add immutable prompt identity and resolution
```

## Current milestone

M3 / P0.3 — Execution correlation + thin application-owned telemetry boundary

Architecture: **APPROVED**

Implementation: **NOT STARTED**

M3 is **not** implemented, **not** committed, and **not** pushed.

## Approved M3 architectural direction

```text
ExecutionContext
├── request_id
├── run_id
└── optional thread_id

LLMInvocationId
└── invocation_id

Application Operations
→ typed application execution events
→ TelemetryPort
→ NoOpTelemetry / StdlibTelemetry

Application Operation
→ LLMPort(
      ExecutionContext,
      LLMInvocationId,
      rendered prompt
  )
→ Provider Adapter
```

### Critical invariants

- GraphState carries request/run/thread copies; it is not execution-identity owner.
- `invocation_id` is transient per `LLMPort` call and is not GraphState state.
- all provider retries for one LLM invocation share one `invocation_id`.
- `PromptIdentity` does NOT enter `LLMPort`.
- `TelemetryPort` does NOT enter `LLMPort`.
- raw prompt/user/document/model content is not generic telemetry.
- LangSmith is not application telemetry owner.
- no OpenTelemetry/custom observability platform is part of baseline M3.
- simple direct Application Operation path remains valid without LangGraph or external telemetry infrastructure.

### Delivery structure

ONE M3 architectural milestone with:

1. **Internal Checkpoint 1** → application execution / telemetry boundary
2. **Internal Checkpoint 2** → provider + graph end-to-end correlation / LangSmith cleanup

ONE final M3 Git boundary after complete review.

## Known M2→M3 failure-traceability boundary

For Triage and ResponseDrafting, prompt resolution occurs before provider execution. If the subsequent provider/model call raises and no Application Operation outcome is returned, current node error metadata does **not** contain prompt identity.

This was intentional in M2. Complete failed-attempt execution traceability remains dependent on M3 (`ExecutionContext` + application execution events + `TelemetryPort`). The normative prompt-traceability requirement remains unchanged; complete failed-attempt evidence is still BLOCKED on the M3 cross-cutting execution boundary.

## Latest validation

M2 Git boundary validation (closed milestone):

- HEAD / `origin/main` = `13fc9e1` (`feat: add immutable prompt identity and resolution`)
- working tree clean at M2 close

M3 runtime validation: **not yet applicable** (implementation not started).

## Known baseline debt / remaining readiness gaps

Classification: **pre-existing / later readiness**, not closed by M2. M3 does not close them by architecture approval alone.

- M3 runtime not yet implemented
- repository-wide Ruff readiness closure remains
- CI / automated verification closure remains
- `ExecutionContext` / `TelemetryPort` / application telemetry boundary — approved, not implemented
- complete failed-attempt identity telemetry (M2→M3 boundary above) — not implemented
- controlled tool executor / RAG backend / durable HITL — not implemented
- remote prompt-management platform — not required and not implemented
- other already-documented deferred / project-specific capabilities remain deferred
- `.env.example` incomplete vs required `OPENAI_API_KEY`
- `docker-compose.yaml` still uses `fastapi-prod-starter-*` names
- `scripts/test.ps1`, `lint.ps1`, `typecheck.ps1` contain commented commands

**SURFACE DISCREPANCY:** Application LLM boundary (M1) + Prompt Identity / Immutable Prompt Resolution (M2) are implemented. Remaining approved-target gaps that are still absent include M3 execution correlation / telemetry, `ToolRequest`/`ToolResult` controlled execution, and other Template Readiness items. Do not treat Template READY as achieved.

## Continuation-impacting blockers

None for M3 Internal Checkpoint 1 implementation planning.

## Next approved action

M3 Internal Checkpoint 1 implementation planning / Cursor prompt.

## Forbidden / unapproved next actions

- M3 runtime implementation without approved Internal Checkpoint 1 planning / Cursor prompt
- M3 commit / push before complete M3 review and final Git-boundary authorization
- RAG implementation
- unrelated readiness cleanup / repository-wide Ruff cleanup
- unapproved architecture or scope changes
- declaring TEMPLATE READY
- tool-specific parallel handoff/status files
