# Handoff — current continuation state

ONE shared, tool-neutral continuation document for ChatGPT, Cursor, humans, and future AI engineering tools.

This file is the only authority for **what am I allowed to do next?**

It does **not** own architecture, project decision rationale, or factual proof that a Git commit exists. Git is authoritative for HEAD, commit hashes, working-tree state, and milestone Git boundaries.

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

M0B approved.

M0B is documentation/governance only.

M0B is implemented, reviewed, and approved. It is **not** committed. The approved M0B milestone must now be established as a clean Git boundary before M1 may begin.

## Last approved milestone

M0B

## Latest validation

Results from the M0B correction-only run (seeded runtime; M0B did not change Python/tests/config):

- `poetry run ruff check .` — **fail**, 127 errors (app/, tests/, scripts/)
- `poetry run pyright` — **fail**, 1 error: `app/nodes/input_shield.py:157` (`T@generate_structured` not assignable to `ShieldOutput`)
- `poetry run pytest` — **pass**, 23 tests

## Known baseline debt

Classification: **pre-existing seeded-runtime condition**, not addressed by M0 documentation/governance work.

M0 complete does **not** mean runtime quality gates are clean.

Also unchanged (out of M0B scope):

- `.env.example` incomplete vs required `OPENAI_API_KEY`
- `docker-compose.yaml` still uses `fastapi-prod-starter-*` names
- `scripts/test.ps1`, `lint.ps1`, `typecheck.ps1` contain commented commands

**SURFACE DISCREPANCY (docs vs runtime, already recorded in M0A architecture):** target ports/adapters, `ExecutionContext`, prompt identity, and `ToolRequest`/`ToolResult` are documented as approved target; seeded `app/` does not implement them.

## Continuation-impacting blockers

- The approved M0B Git milestone boundary has not yet been established.
- M1 must not begin until the approved M0B files are committed and a clean Git boundary is verified.
- Seeded Ruff/Pyright failures remain; do not “fix” them in a docs milestone

## Next approved action

Establish or verify the approved M0B Git milestone boundary.

After that boundary exists and the working tree is clean, M1 planning may begin only when explicitly authorized.

## Forbidden / unapproved next actions

- M1 (until the approved M0B Git milestone boundary exists and the working tree is clean)
- runtime implementation / runtime changes
- M1 implementation
- unapproved architecture or scope changes
- activating deferred capabilities
- unrelated documentation changes
- creating an active project workspace unless a later approved milestone says to
- tool-specific parallel handoff/status files
