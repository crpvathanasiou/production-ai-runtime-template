# Skill — architecture review

Reusable ChatGPT architecture-review procedure. It does **not** predetermine the architecture result.

Use after requirements are captured and before a project architecture decision is accepted (or before a template architecture change).

## Inputs

- [`.ai/handoff.md`](../handoff.md) (continuation only)
- relevant `project-context.md` when a project exists
- [`../architecture/architecture.md`](../architecture/architecture.md)
- [`../architecture/architecture-rules.md`](../architecture/architecture-rules.md)
- [`../architecture/deferred-capabilities.md`](../architecture/deferred-capabilities.md)
- [`../architecture/file-map.md`](../architecture/file-map.md)
- applicable contracts and engineering/operations docs
- **facts** from code, Git, config, and tests (not inferred from docs alone)

## Review coverage

1. **Requirements** — what must be true vs nice-to-have.
2. **Facts vs assumptions** — label each; do not promote assumptions to architecture.
3. **Constraints** — time, safety, providers, compliance as stated.
4. **Boundaries** — delivery vs core vs ports vs outbound adapters; LangGraph as optional driving adapter only.
5. **Existing reusable components** — adapt before replacing ([`../engineering/engineering-principles.md`](../engineering/engineering-principles.md)).
6. **Risks** and **failure modes**.
7. **Production concerns** — operability, failure behaviour, not speculative infra.
8. **Security** — trust boundaries, authn vs authz ([`../engineering/security-principles.md`](../engineering/security-principles.md)).
9. **Testing / evaluation impact** — deterministic tests vs probabilistic eval.
10. **Operational implications** — observability and errors without requiring CoT logs.
11. **Overengineering check** — anything on the deferred register without a trigger stays DEFER.

## Classification (existing pieces)

For each relevant current component:

| Label | Meaning |
| --- | --- |
| KEEP | remains as-is for this project |
| ADAPT | stays, with a defined change toward the target architecture |
| REPLACE | retired only under an approved milestone that removes the old path |
| OMIT | not used |
| DEFER | capability exists on the register; not activated |

Do not KEEP a seed behaviour as template architecture merely because the code exists.

## Output

- findings;
- explicit deviations (or none);
- deferred items remaining deferred;
- `SURFACE DISCREPANCY` where docs and runtime/Git/config disagree;
- recommendation: accept, accept with scoped decision, or reject.

This skill does not authorize implementation or the next milestone.
