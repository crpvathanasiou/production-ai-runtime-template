# Quick start — new project from this template

This is **project bootstrap guidance**. Ordinary Python/Poetry/Docker setup belongs in the root `README.md`. Do not treat this file as an install runbook.

The seeded Customer Support Triage code is example implementation. Starting a new project does not mean extending that example by default.

## Bootstrap workflow

```text
start from template
        ↓
establish project workspace
        ↓
capture project-context
        ↓
capture expected / actual development environment
        ↓
identify requirements, constraints, and unknowns
        ↓
assess security / evaluation requirements where relevant
        ↓
inspect template architecture + deferred capabilities
        ↓
approve project architecture decisions
        ↓
establish delivery plan
        ↓
define one milestone
        ↓
Expected Documentation Impact
        ↓
controlled implementation
```

### 1. Start from the template

Template rules in `.ai/architecture/` and `.ai/engineering/` apply unless a later approved template change supersedes them. Do not merge other repositories into the template.

### 2. Establish the project workspace

Copy [`.ai/projects/_template/`](projects/_template/project-context.md) to `.ai/projects/<project>/`. See [`projects/README.md`](projects/README.md). Do not treat Customer Support Triage as the active project unless [`.ai/handoff.md`](handoff.md) says so.

### 3. Capture project-context

Fill `project-context.md`: goal, problem, deliverables, deadline, requirements, constraints, facts vs unknowns, assumptions, success and acceptance criteria.

### 4. Capture expected / actual development environment

Fill `development-environment.md` as operational **reference**. If it says X and the actual environment says Y:

```text
SURFACE DISCREPANCY
```

Do not redefine the template stack from that file.

### 5. Identify requirements, constraints, and unknowns

Unknowns are not permission to speculate infrastructure.

### 6. Assess security and evaluation

Use [`engineering/security-principles.md`](engineering/security-principles.md) and [`engineering/evaluation-strategy.md`](engineering/evaluation-strategy.md) where the assignment involves untrusted content or probabilistic AI behaviour. Project-specific threat/IAM/compliance work stays requirement-driven.

### 7. Inspect template architecture and deferred capabilities

Read [`architecture/architecture.md`](architecture/architecture.md), [`architecture/architecture-rules.md`](architecture/architecture-rules.md), [`architecture/deferred-capabilities.md`](architecture/deferred-capabilities.md).

Approved model:

```text
Client → FastAPI / Delivery Adapter → [optional LangGraph] → Application Core → Ports → outbound adapters
```

FastAPI may call the application core without LangGraph. After M2, active LLM paths follow Application Operation → `PromptRepository` → `ResolvedPrompt` → `LLMPort` → OpenAI adapter with explicit composition and local immutable prompt revisions; LangGraph remains the active seeded orchestration example; FastAPI still exposes health/version only (no project/business use-case endpoint yet). A simple project can use Application Operation + `PromptRepository` + `LLMPort` with `LocalPromptRepository` and requires no LangGraph, database, network prompt host, or prompt-management platform. Next major readiness gap: `ExecutionContext` + application-owned telemetry boundary (`SURFACE DISCREPANCY` if treated as complete Template READY).

Presence on the deferred register is not permission to implement.

### 8. Approve project architecture decisions

Record choices and explicit deviations in `architecture-decisions.md`. Template invariants still apply.

### 9. Establish delivery plan

Prospective milestones, gates, and validation expectations in `delivery-plan.md`. Not a progress ledger.

### 10. Define one milestone

ChatGPT selects **one** milestone (allowed/forbidden files, contracts, DoD). See [`engineering/development-workflow.md`](engineering/development-workflow.md).

### 11. Expected Documentation Impact

Before implementation ([`engineering/documentation-rules.md`](engineering/documentation-rules.md)):

```text
Expected Documentation Impact:
NONE — <specific reason>
```

or:

```text
Expected Documentation Impact:
UPDATE
- <document>
```

### 12. Controlled implementation

Cursor implements only after an explicit Cursor prompt for that milestone ([`engineering/delivery-method.md`](engineering/delivery-method.md)). Cursor does not choose the next milestone. Next action lives only in [`.ai/handoff.md`](handoff.md).

## What not to do at bootstrap

- Do not start runtime refactors during documentation/governance milestones.
- Do not promote seeded Customer Support types into template-wide contracts.
- Do not create parallel replacements before adapting existing components.
- Do not treat LangGraph, LangSmith, Redis, or OpenAI as the application core.
- Do not create tool-specific handoff files.
