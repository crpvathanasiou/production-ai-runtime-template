# Prompt lifecycle contract

Normative reusable prompt-identity and resolution contract. The **application** owns prompt identity. LangSmith (or any vendor host) is not the architectural owner. Storage/management technology must remain replaceable.

This contract is **what should be true**. It does not implement prompt runtime.

## Conceptual types

### `PromptRef`

Immutable reference to a prompt revision:

```text
prompt_id
revision
```

A `PromptRef` names a specific revision. It is not “whatever is currently production.”

### `ResolvedPrompt`

A fully resolved, executable prompt:

```text
prompt_id
revision
content
content_hash
optional variables / schema metadata where useful
```

`content_hash` is computed from the resolved content the application will execute. It is application-owned evidence, not a vendor run id.

## Required lifecycle

```text
resolve explicit immutable revision
        ↓
obtain ResolvedPrompt
        ↓
record prompt identity / hash
        ↓
execute
```

Do **not** execute as “call whatever prompt is current production at runtime” without first resolving a concrete immutable revision.

If resolution cannot produce a `ResolvedPrompt` for the requested `PromptRef`, fail. Do not silently fall forward to a different revision.

## Immutable identity

Once a revision is published for use, its content for that `(prompt_id, revision)` does not change. A content change is a new `revision`.

## Traceability

Execution records at least:

```text
prompt_id
revision
content_hash
```

so a run can be tied to the exact prompt that ran. Correlation belongs with `ExecutionContext` (`request_id`, `run_id`, optional `thread_id`); prompt identity is not a substitute for execution identity.

## Evaluation linkage

AI evaluation (see [`../engineering/evaluation-strategy.md`](../engineering/evaluation-strategy.md)) must be attributable to a prompt revision (plus model, configuration, and dataset/version). “Latest production prompt” is not an evaluation identity.

## Rollback linkage

Rollback means selecting a previously resolved `PromptRef` (an earlier immutable revision), not mutating the current revision in place.

## Portability

`PromptRepository` is the application-owned lookup port. A later prompt-management adapter (including LangSmith) may sit behind that port. Vendor prompt objects are not application contracts.

## Versioned resolution

Resolution always takes an explicit `PromptRef` (or an application rule that selects one **before** execute). Defaulting to an unpinned moving head at execute time is out of contract.

## SURFACE DISCREPANCY

Seeded prompts live as Python string builders under `app/prompts/` with no `prompt_id` / `revision` / `content_hash`. That is current runtime fact, not this contract.

```text
SURFACE DISCREPANCY
```

if documentation of the lifecycle is treated as if the runtime already implements it.
