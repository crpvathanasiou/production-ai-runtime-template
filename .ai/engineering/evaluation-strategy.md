# AI evaluation strategy

Evaluation owns **probabilistic AI quality / regression evidence**.

| Document | Owns |
| --- | --- |
| [`testing-strategy.md`](testing-strategy.md) | software / system correctness |
| **This file** | AI behaviour quality |

Both may be required for the same feature.

Passing pytest does not prove AI quality. Passing AI evaluation does not prove software correctness.

## When evaluation is relevant

Use evaluation when a change can alter probabilistic behaviour, including:

- representative / golden cases;
- evaluation datasets;
- task-success metrics;
- semantic correctness;
- structured-output quality;
- routing / tool-selection quality;
- prompt regression;
- model regression;
- baseline vs candidate comparison;
- deterministic metrics where possible (schema validity rates, exact-match where defined);
- human evaluation;
- LLM-as-judge as **optional** evidence;
- promotion acceptance criteria.

LLM-as-judge is **not** unquestioned ground truth. Treat it as one signal, contested by humans and by deterministic checks where those exist.

## Traceability

An evaluation result is not interpretable without:

```text
prompt revision
+ model
+ model configuration
+ evaluation dataset / version
+ evaluation result
```

Unpinned “current production prompt” or “whatever model is in env” is not an evaluation identity. See [`../contracts/prompt-lifecycle-contract.md`](../contracts/prompt-lifecycle-contract.md).

## Discipline

**BASELINE** — evaluation is a required *discipline* when AI behaviour is in play: compare against a recorded baseline, attribute the run, and state what promotion would accept.

**Custom evaluation platform / infrastructure — DEFER.** Do not build an in-house eval product inside `app/`. Presence of this document is not permission to implement one. See [`../architecture/deferred-capabilities.md`](../architecture/deferred-capabilities.md).

**LangSmith evaluation** is an optional evaluation platform / harness / tooling choice, not architectural owner of quality evidence. Another evaluation platform is likewise an optional implementation choice. LangSmith is not mandatory.

Do not implement evaluation runtime in a documentation/governance milestone.

## Promotion

Software tests green + evaluation silent is insufficient when the change is probabilistic. Evaluation green + tests missing for the contract is insufficient when the change is deterministic.

If evaluation is required and absent:

```text
SURFACE DISCREPANCY
```

relative to this strategy — report it; do not invent a platform to close the gap.
