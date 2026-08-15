# execute_plan_node (current semantics)

The planner produces an executable plan. `execute_plan_node` executes supported
steps and updates state.

## What the node does

* reads `state.agent_state.plan`
* executes steps serially
* for a `retrieval_agent` step (current seeded placement; unchanged by M1):
  * builds a retrieval query
  * invokes the retrieval entrypoint
  * stores returned documents in `state.retrieved_documents`
  * marks the step **completed** when documents are returned
  * marks the step **failed** with `"Retrieval returned no documents."` when an
    explicitly requested retrieval returns none
* for a `response_agent` step:
  * orchestrates the response PlanStep
  * delegates drafting generation to `ResponseDraftingOperation`
    (`ResponseDraftingOperation` → `LLMPort` → provider adapter)
  * with retrieved evidence → `"Drafted grounded customer response."`
  * without retrieved evidence → `"Drafted customer response without retrieved context."`
  * maps the draft into `state.response_draft`
* updates step `status` / `result` / `error`
* leaves `human` steps pending (not executed here); `current_step_id` points to the next pending step
* if any step failed → `workflow_outcome = "needs_human_review"`
* if a pending human PlanStep remains → `workflow_outcome = "needs_human_review"`
* otherwise → `workflow_outcome = "running"`

## Ownership split (response drafting)

```text
execute_plan
  → response PlanStep orchestration
  → ResponseDraftingOperation
  → LLMPort
  → provider
```

**ResponseDraftingOperation owns:**

* drafting prompt invocation
* typed LLM generation

**execute_plan still owns:**

* retrieval-shaped PlanStep execution (current seeded placement; unchanged by M1)
* response/human PlanStep status transitions
* `retrieved_documents` state
* `response_draft` state mapping
* failure marking
* next-step computation
* `workflow_outcome`

Do **not** treat retrieval as permanently owned by LangGraph — only as the
current seeded placement left unchanged by M1.

## Current baseline

* no repository-backed knowledge corpus is shipped
* no active retrieval backend exists
* `retrieve_relevant_documents(...)` currently returns `[]`
* active RAG is not implemented
* retrieval-shaped orchestration is intentionally preserved

Therefore:

* ordinary current-baseline plans should not request retrieval by default
* if a plan does request retrieval and the entrypoint returns none, that is
  unmet retrieval / failed plan step, not false success
* a cautious draft may still be produced for human review

## Supported step owners in v1

* `retrieval_agent` — retrieval seam (may succeed when a backend returns docs)
* `response_agent` — drafting (generation via `ResponseDraftingOperation`)
* `human` — marker only; not executed here

## Why this matters

This preserves the RAG-ready surface:

```text
Application/workflow
    ↓
retrieval boundary (retrieve_relevant_documents)
    ↓
project-specific backend (future)
    ↓
corpus/index (future)
```

without pretending the current template already has an active backend.
