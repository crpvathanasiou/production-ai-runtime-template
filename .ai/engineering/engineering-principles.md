# Engineering principles

Stable template standards. They apply to every project started from this repository unless the template itself is changed.

## Fixed stack

| Concern | Choice |
| --- | --- |
| Language | Python 3.11 |
| Packaging / venv | Poetry (`virtualenvs.in-project` as used by this repo) |
| Delivery | FastAPI |
| Typed models | Pydantic v2 |
| Lint | Ruff |
| Types | Pyright |
| Tests | pytest |
| Containers | Docker where justified |

Do not adopt another repository’s toolchain (`uv`, Pyrefly, Claude-specific runners, alternate test frameworks) as a silent replacement.

## Principles

**Typed contracts.** Inputs, outputs, and error-adjacent payloads are explicit types. Unstructured vendor blobs are not application meaning.

**Explicit error semantics.** Use the application exception taxonomy (`AppError` and subclasses in the seed) rather than swallowing failures or returning ambiguous `None` for distinct failure classes.

**Small responsibility boundaries.** A module has one reason to change: delivery, application policy, adapter I/O, or orchestration — not all four.

**Minimal abstractions.** Add a port or interface when a real boundary exists (provider SDK, optional framework). Do not add layers for hypothetical extension.

**Provider/framework independence where justified.** Application core stays free of OpenAI and LangGraph types. Independence is not a mandate to implement multiple providers.

**Composition over unnecessary coupling.** Prefer passing ports/services into use cases over global SDK clients and decorator-driven hidden control flow.

**Adapt existing components before parallel replacements.** Evolve `AsyncOpenAIWrapper`, FastAPI, schemas, and the example graph in place. Do not leave two LLM clients or two settings systems.

**No speculative infrastructure.** If it is on [`../architecture/deferred-capabilities.md`](../architecture/deferred-capabilities.md), it stays unimplemented until activated with a milestone.

**Deterministic logic for known rules.** Classification thresholds, allow/deny lists, and policy checks that are known rules stay in code, not in an extra LLM call.

**Testability through dependency boundaries.** Adapters are replaceable in tests. Do not require live OpenAI, LangSmith, or Redis for unit tests of application logic.

**Production-oriented simplicity.** Prefer a small, operable system over a demonstration of patterns. Completeness of a reference architecture elsewhere is not a requirement here.
