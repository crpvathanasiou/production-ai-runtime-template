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

## Last closed Git-boundary milestone

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

Runtime implementation: **COMPLETE** (IC1 + IC2 Pass 1 + Pass 2 + Pass 3)

Final reconciliation: **COMPLETE**

Final verification: **COMPLETE** (pending ChatGPT final review / Git authorization)

M3 is **not** committed and **not** pushed. There is still **ONE** final M3 Git boundary, unauthorized until explicit later approval.

```text
HEAD        = 97d4d9f  (pre-M3 governance HEAD; last closed milestone boundary remains 13fc9e1)
origin/main = 97d4d9f
working tree = intentionally dirty with complete uncommitted M3
```

## M3 factual completion summary

```text
M3 IC1 complete
→ ExecutionContext / LLMInvocationId
→ TelemetryPort + NoOpTelemetry / StdlibTelemetry
→ typed Application execution events
→ LLMPort correlation arguments

M3 IC2 complete
→ graph/node operational correlation logging
→ provider attempt/retry correlation under one invocation_id
→ explicit project-owned LangSmith tracing removed
→ direct langsmith dependency removed
→ dead LANGSMITH_ENABLED setting removed
→ transitive LangSmith may remain via LangGraph/langchain-core

M3 final reconciliation complete
→ architecture / observability / node docs / handoff reconciled to runtime
```

### Critical invariants (implemented)

- Application owns `ExecutionContext`; GraphState carries request/run/thread copies only.
- `invocation_id` is created by Application Operations before the LLM call; not GraphState state.
- all provider retries for one LLM invocation share one `invocation_id`.
- `PromptIdentity` does NOT enter `LLMPort`.
- `TelemetryPort` does NOT enter `LLMPort`.
- graph operational logging, Application telemetry, and provider operational logging are distinct layers.
- raw prompt/user/document/model content / exception messages are not generic telemetry or provider operational payloads.
- explicit project-owned LangSmith runtime ownership is removed; transitive package presence is allowed.
- no OpenTelemetry/custom observability platform is part of baseline M3.
- simple direct Application Operation path remains valid without LangGraph or external telemetry infrastructure.

### Delivery structure completed

ONE M3 architectural milestone with:

1. **Internal Checkpoint 1** → application execution / telemetry boundary — **DONE**
2. **Internal Checkpoint 2** → provider + graph end-to-end correlation / LangSmith cleanup — **DONE**
3. **Final reconciliation** → factual docs/governance + complete verification — **DONE**

Still required before any Git publication:

```text
ChatGPT final M3 review
→ explicit Git authorization
→ ONE final M3 Git boundary
```

## Known M2→M3 failure-traceability boundary — closed at Application layer

M3 Application telemetry emits `LLMInvocationStarted` (including `PromptIdentity`) before the provider call, so failed attempts remain correlatable at the Application layer even when no operation outcome returns to the node. This closes the M2→M3 Application-side failure-traceability gap described after M2.

## Latest validation

M3 final reconciliation verification (uncommitted working tree):

- full pytest: **167 PASS**
- focused IC2 (`tests/test_logging.py` + `tests/nodes` + wrapper): **PASS**
- IC1 telemetry/application: **PASS**
- Pyright: **0 errors**
- repository Ruff: **100** (pre-existing debt; no new debt from M3)
- `poetry check`: **PASS**
- `git diff --check`: **PASS**
- NO COMMIT / NO PUSH

## Known baseline debt / remaining readiness gaps

Classification: **pre-existing / later readiness**, not closed by M3 alone.

- repository-wide Ruff readiness closure remains
- CI / automated verification closure remains
- controlled tool executor / RAG backend / durable HITL — not implemented
- remote prompt-management platform — not required and not implemented
- OpenTelemetry / metrics / dashboards / distributed tracing — not implemented
- other already-documented deferred / project-specific capabilities remain deferred
- `.env.example` incomplete vs required `OPENAI_API_KEY`
- `docker-compose.yaml` still uses `fastapi-prod-starter-*` names
- `scripts/test.ps1`, `lint.ps1`, `typecheck.ps1` contain commented commands

M3 runtime implementation and reconciliation are complete for P0.3. Do **not** treat Template READY / P0.4 as achieved.

## Continuation-impacting blockers

None for final ChatGPT M3 review / Git-authorization decision.

## Next approved action

Await ChatGPT final M3 review and explicit authorization for the **ONE** final M3 Git boundary.

Until that authorization exists:

```text
NO COMMIT
NO PUSH
```

## Forbidden / unapproved next actions

- M3 commit / push without explicit final Git-boundary authorization
- declaring TEMPLATE READY
- declaring P0.4 complete
- RAG implementation
- unrelated readiness cleanup / repository-wide Ruff cleanup
- unapproved architecture or scope changes
- tool-specific parallel handoff/status files
- mixing documentation redesign or runtime changes into the pending Git boundary without review
