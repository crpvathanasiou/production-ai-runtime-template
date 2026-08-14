# Handoff — current continuation state

Mutable continuation only. This file does not redefine architecture, engineering principles, or file ownership.

## Repository

`production-ai-runtime-template`  
https://github.com/crpvathanasiou/production-ai-runtime-template

## Branch

`main`

## Active project

None / template preparation

The seeded Customer Support Triage implementation remains example code in `app/`. It is not an active `.ai/projects/<project>/` workspace. That workspace is documentation under `.ai/projects/` when created; creating it is M0B work and is not yet permitted.

## Architecture status

Minimal Target Architecture is documented under `.ai/architecture/` as **approved target architecture**.

The seeded runtime does **not** yet implement that architecture (no `LLMPort`, `ExecutionContext`, portable `PromptRepository`, or application-owned tool contracts in code). Distinguishing target from seed is intentional. Runtime alignment is not M0A work.

## Current milestone

M0A approved.

M0A is documentation/governance only. The approved M0A milestone must now be established as a clean Git boundary before M0B may begin.

## Last approved milestone

M0A

## Last validation

CORRECTION-ONLY scope check: only `README.md` modified and `.ai/` untracked (no new paths beyond approved M0A files).

Quality (seeded runtime, unchanged by this pass):

- `poetry run ruff check .` — **fail**, 127 errors in `app/`, `tests/`, `scripts/` (pre-existing)
- `poetry run pyright` — **fail**, 1 error in `app/nodes/input_shield.py` (pre-existing)
- `poetry run pytest` — **pass**, 23 tests

M0A has been reviewed and approved. The validation results above describe the approved M0A working-tree state before establishment of the Git milestone boundary.

## Blockers / issues

- The approved M0A Git milestone boundary has not yet been established.
- M0B must not begin until the approved M0A files are committed and a clean Git boundary is verified.
- `.env.example` is an incomplete settings catalog relative to `app/core/settings.py` (requires `OPENAI_API_KEY`). Not changed: outside M0A scope
- Pre-existing Ruff (127) and Pyright (1) failures in seeded Python; not fixed (forbidden runtime/test scope)
- `docker-compose.yaml` still uses `fastapi-prod-starter-*` container names. Not renamed: outside M0A scope
- `scripts/test.ps1`, `lint.ps1`, `typecheck.ps1` contain commented commands rather than live invocations. Not changed: outside M0A scope

## Next approved action

Establish or verify the approved M0A Git milestone boundary.

After that boundary exists and the working tree is clean, M0B implementation may begin using the approved M0B prompt.

## Forbidden / unapproved next actions

- M0B until the approved M0A Git milestone boundary exists and the working tree is clean
- M1
- runtime behaviour changes
- Python implementation / contracts / prompt lifecycle / OpenAI-wrapper / LangGraph changes
- dependency, test, Docker, or configuration changes
- creating `.ai/contracts/**`, `.ai/operations/**`, `.ai/projects/**`, `.ai/skills/**`, or `.ai/engineering/testing-strategy.md`
- activating deferred capabilities
- M1
