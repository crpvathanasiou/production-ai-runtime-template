# Quick start — new project from this template

This is **project bootstrap guidance**. Ordinary Python/Poetry/Docker setup belongs in the root `README.md`. Do not treat this file as an install runbook.

The seeded Customer Support Triage code is example implementation inside the template. Starting a new project does not mean extending that example by default. It means capturing the assignment, reviewing the template architecture, and activating only what the assignment justifies.

## Bootstrap workflow

```text
start from template
        ↓
create project workspace
        ↓
capture assignment / context
        ↓
identify requirements, constraints, and unknowns
        ↓
review template architecture
        ↓
review deferred capabilities
        ↓
activate only justified capabilities
        ↓
approve project architecture
        ↓
define one milestone
        ↓
Cursor implementation under ChatGPT supervision
```

### 1. Start from the template

Use this repository as the reusable baseline. Template rules in `.ai/architecture/` and `.ai/engineering/` apply unless a later approved template change supersedes them.

Do not copy architecture from another codebase into the template. Do not merge reference repositories.

### 2. Create the project workspace

Project-specific knowledge belongs under `.ai/projects/<project>/`.

Do not treat Customer Support Triage as the active project unless an approved project workspace says so. Assignment-specific decisions belong in the project workspace. They must not be written into template architecture documents as if they were universal.

### 3. Capture assignment and context

Record, as project knowledge:

- what the system must do
- who it serves
- delivery constraints
- provider/environment constraints
- what is explicitly out of scope

### 4. Identify requirements, constraints, and unknowns

Separate:

- hard requirements
- constraints (compliance, latency, human review, side effects)
- unknowns that block architecture approval

Unknowns are not permission to speculate infrastructure.

### 5. Review template architecture

Read:

- [`architecture/architecture.md`](architecture/architecture.md)
- [`architecture/architecture-rules.md`](architecture/architecture-rules.md)
- [`architecture/file-map.md`](architecture/file-map.md)

The approved model is:

```text
Client → FastAPI / Delivery Adapter → [optional LangGraph] → Application Core → Ports → outbound adapters
```

FastAPI may also call the application core directly, without LangGraph. The seeded runtime does not yet implement that model.

### 6. Review deferred capabilities

Read [`architecture/deferred-capabilities.md`](architecture/deferred-capabilities.md). Presence on that list is **not** permission to implement. A capability stays deferred until a real requirement and an approved project architecture decision activate it.

### 7. Activate only justified capabilities

Activation requires:

- a concrete assignment need
- an expected architectural boundary
- an explicit project decision

Do not activate MCP, extra providers, checkpointing, RAG platforms, or other deferred items “for completeness.”

### 8. Approve project architecture

ChatGPT records the project architecture decision under `.ai/projects/<project>/`. Template invariants still apply. Project choices that conflict with invariants require a template change, not a silent local override.

### 9. Define one milestone

ChatGPT selects **one** milestone with objective, allowed files, forbidden files, contracts, Definition of Done, and documentation impact. See [`engineering/development-workflow.md`](engineering/development-workflow.md).

### 10. Cursor implementation under ChatGPT supervision

Cursor implements only after ChatGPT explicitly requests a Cursor prompt for that milestone. Cursor does not choose the next milestone.

## What not to do at bootstrap

- Do not start runtime refactors during documentation/governance milestones.
- Do not promote seeded Customer Support types, nodes, or prompts into template-wide contracts.
- Do not create parallel replacements for existing components before adapting them.
- Do not treat LangGraph, LangSmith, Redis, or OpenAI as the application core.
