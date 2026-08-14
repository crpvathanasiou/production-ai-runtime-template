# Documentation rules

Documentation is part of Definition of Done. Implementation and `.ai/` (plus root `README.md` when identity/run instructions change) must stay synchronized.

Documentation must not silently redefine approved architecture. If behaviour changes, documents follow the milestone; they do not invent a new target model in passing.

## Required statement on every implementation change

Every future implementation milestone must explicitly state either:

```text
Documentation impact:
NONE — <reason>
```

or:

```text
Documentation impact:
UPDATE:
- <document>
```

“NONE” requires a reason. Silence is not `NONE`.

## What maps where

| Kind of change | Documents to update |
| --- | --- |
| Architecture / layering / ownership of a concern | `.ai/architecture/architecture.md` and/or a **project** architecture decision under `.ai/projects/<project>/`. Template vs project: do not promote a project choice into `.ai/architecture/**`. |
| Architecture invariant added/relaxed | `.ai/architecture/architecture-rules.md` (template change only) |
| Contract change | Specialized contract documentation under `.ai/contracts/` |
| File ownership / new area / moved responsibility | `.ai/architecture/file-map.md` |
| Configuration / environment / how to run | Root `README.md` and/or project documentation — do not rewrite runtime to make a README sentence true |
| Prompt identity / lifecycle / repository | Prompt lifecycle / contract documentation under `.ai/`. Also architecture if ownership changes. |
| Observability / telemetry exporters | Operations / observability documentation under `.ai/operations/` and architecture if the telemetry boundary changes |
| Error semantics / exception taxonomy | Error-handling documentation under `.ai/operations/` and `file-map.md` if ownership of errors moves |
| Activation of a deferred capability | `.ai/architecture/deferred-capabilities.md` **and** a project architecture decision under `.ai/projects/<project>/`. Status change is not an implementation permit by itself. |
| Engineering stack / workflow / doc process | `.ai/engineering/*` |
| Current milestone / blockers / next action | `.ai/handoff.md` only |

## Authority and duplication

- Stable template facts live once under `.ai/architecture/`, `.ai/engineering/`, and other template-wide `.ai/` areas (`contracts/`, `operations/`, `skills/` when present).
- Assignment-specific decisions live under `.ai/projects/<project>/`.
- Mutable status lives only in `.ai/handoff.md`.
- Seed notes under `docs/` are not architecture authority. Do not update them instead of `.ai/`.

## Fresh-session rule

A new ChatGPT or Cursor session must be able to recover architecture from `.ai/` plus `handoff.md`, without relying on chat history.

## Placeholders

Do not create documentation trees as empty placeholders to satisfy a mapping above. Record `Documentation impact` against the intended document and create that document only when the approved milestone includes it.
