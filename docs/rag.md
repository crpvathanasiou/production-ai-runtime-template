# Retrieval-shaped workflow vs RAG (current template)

This document explains the seeded **orchestration seam** for retrieval-augmented
generation. It does **not** claim that active RAG exists in the current template.

## Current baseline

```text
repository knowledge corpus     → NONE
active retrieval backend        → NONE
active local keyword retrieval  → NONE
active RAG                      → NONE
RAG / vector retrieval          → DEFER
```

`retrieve_relevant_documents(...)` is an **inert / placeholder** retrieval
entrypoint. It preserves the seed workflow call site and currently returns `[]`.

So the code demonstrates:

**retrieval workflow shape / seam**

not:

**a complete working RAG system**

Retrieval-shaped engineering is intentionally preserved so a later assignment
can activate a project-specific backend without rebuilding orchestration.

---

## Workflow shape that still exists

```text
planner
  → retrieval decision (retrieval_agent step) [optional / future-activated]
  → query construction (_build_retrieval_query)
  → retrieval entrypoint (retrieve_relevant_documents)
  → optional retrieved_documents in state
  → response drafting
```

### Current-baseline planner behavior

Ordinary current-baseline plans should **not** request retrieval by default.
If required external policy/FAQ/SOP knowledge is unavailable, prefer human
review rather than inventing knowledge. Drafting may proceed directly from
ticket/triage context. `retrieval_agent` remains a valid owner for a future
project that activates retrieval.

### When a retrieval step is actually requested

```text
retrieval_agent step
        ↓
_build_retrieval_query(...)
        ↓
retrieve_relevant_documents(...)
        ↓
documents returned?

YES → retrieval step completed
    → state.retrieved_documents populated
    → draft may use retrieved documents
    → grounding provenance is validated

NO  → retrieval step failed ("Retrieval returned no documents.")
    → workflow_outcome = needs_human_review
    → executor MAY still create a cautious draft for human review
    → must NOT silently complete as successful retrieval
```

---

## What `_build_retrieval_query` does

`_build_retrieval_query(...)` does **not** retrieve documents.

It builds a **search query string** from ticket / step / triage context and
passes it to the retrieval entrypoint.

---

## Drafting

**With retrieved evidence**

- grounded drafting path
- `related_documents` may cite a subset of actual retrieved documents
- inventing sources is forbidden

**Without retrieved evidence**

- cautious non-corpus-grounded draft
- `related_documents` must be `[]`
- no claim of corpus grounding
- no invented policy/FAQ/SOP facts

---

## Guardrails

- grounding is required only when retrieved evidence exists
- model citations must match actual `state.retrieved_documents`
- fabricated/mismatched `related_documents` fail validation
- empty `related_documents` is valid when no retrieval evidence existed

---

## How this relates to RAG

**Retrieval-Augmented Generation**, when activated, would mean a real retrieval
source exists, documents are retrieved, and those documents augment generation.

The current seed preserves the orchestration seam and contracts for that path.
It does **not** implement active RAG.

```text
retrieval-shaped workflow contract / seam exists
        ≠
retrieval implementation is active
        ≠
RAG is active
```

RAG / vector retrieval remains **DEFER**.

---

## Takeaway

* The seed preserves the **orchestration seam** for future retrieval/RAG.
* The current retrieval entrypoint is **inert** and returns no documents.
* No repository corpus is shipped and active RAG is not implemented.
* Explicit retrieval returning zero documents is unmet retrieval, not success.
* `_build_retrieval_query` is query formulation only — not retrieval and not RAG.
