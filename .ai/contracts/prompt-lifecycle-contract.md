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

`content_hash` is computed from the stored static prompt definition (system + user templates) the application resolves. It is application-owned evidence of the immutable revision, not a hash of final rendered customer values and not a vendor run id.

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

Production-relevant prompt execution must be attributable to at least:

```text
prompt_id
revision
content_hash
```

so execution evidence can identify the exact immutable prompt revision that was resolved.

### CURRENT RUNTIME (M2→M3 evidence)

- Successful/handled M2 Application Operation outcomes carry `PromptIdentity`.
- Triage/ResponseDrafting provider failures that return no outcome currently do not surface that identity into node error metadata.
- This is a current M2→M3 evidence gap, not a redefinition of the normative requirement above.
- `ExecutionContext` / application execution events / `TelemetryPort` will provide the cross-cutting mechanism for failed-attempt correlation.
- `PromptIdentity` is not a substitute for execution identity.

## Evaluation linkage

AI evaluation (see [`../engineering/evaluation-strategy.md`](../engineering/evaluation-strategy.md)) must be attributable to a prompt revision (plus model, configuration, and dataset/version). “Latest production prompt” is not an evaluation identity.

## Rollback linkage

Rollback means selecting a previously resolved `PromptRef` (an earlier immutable revision), not mutating the current revision in place.

## Portability

`PromptRepository` is the application-owned lookup port. A later prompt-management adapter (including LangSmith) may sit behind that port. Vendor prompt objects are not application contracts.

## Versioned resolution

Resolution always takes an explicit `PromptRef` (or an application rule that selects one **before** execute). Defaulting to an unpinned moving head at execute time is out of contract.

## CURRENT RUNTIME (factual)

Seeded prompts are immutable code-backed `PromptDefinition`s under `app/prompts/*_prompts.py` with explicit `PromptRef` revisions (`input-shield@1`, `triage@1`, `planner@1`, `response-drafting@1`). `LocalPromptRepository` resolves them to `ResolvedPrompt` carrying `content_hash`. Prompt identity remains Application-owned; Application Operations resolve `PromptRef`s; `LLMPort` and provider adapters stay prompt-lifecycle agnostic. Remote/vendor prompt hosting remains optional/deferred.

```text
SURFACE DISCREPANCY
```

if documentation treats a remote prompt-management platform, moving aliases (`latest`/`production`), or full failed-attempt `ExecutionContext`/telemetry correlation as already required or already implemented for the baseline.
