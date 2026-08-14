# Development environment

**Purpose: HOW THIS PROJECT IS EXPECTED TO RUN / DEVELOP**

This is the **project operational contract/reference**. It is **not** infallible factual truth.

If this document says X and actual environment, commands, config, or test evidence say Y:

```text
SURFACE DISCREPANCY
```

Do not redefine the template-wide engineering stack from this file ([`../../engineering/engineering-principles.md`](../../engineering/engineering-principles.md) remains template authority). Record project-only deviations in `architecture-decisions.md` when they are real, reviewed choices.

Next approved action is **not** owned here: [`.ai/handoff.md`](../../handoff.md).

---

## Python / runtime version

Expected: Python 3.11 (template). Record the version actually used if it differs — that difference is a discrepancy until decided.

## Package manager

Expected: Poetry. Do not switch to `uv` or another manager in this file as a silent template change.

## Virtual environment

Expected: in-project `.venv` (`poetry config virtualenvs.in-project true` as used by this repository).

## Environment variables

List variables this project expects. Distinguish **required** vs optional.

Secrets: name the variable; do not put values here. Secret ownership (who issues, where stored) belongs in this section as process, not as the secret itself.

If `.env.example` or Settings and this list disagree:

```text
SURFACE DISCREPANCY
```

## Secret ownership

Who provides keys, which adapter consumes them, and that credentials must not appear in contracts, prompts, source, or logs.

## Local run commands

Document the expected command. Confirm it against the actual environment when executing.

## Test / lint / type-check commands

Template defaults (verify factually when used):

```powershell
poetry run pytest
poetry run ruff check .
poetry run pyright
```

## Docker / container commands

Only if this project uses them. Compose service names in the seed may still reflect an older identity; do not treat that as this project’s product name.

## External services

What must be running (or mocked). Redis in the seed is a health-check ping, not application state, unless a project decision says otherwise.

## Local vs container differences

## Platform-specific notes

## Known environment limitations
