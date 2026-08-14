# Planner notes (current baseline)

## Current-baseline planning

* No active retrieval backend is shipped.
* Ordinary low-risk plans should draft from ticket/triage context without
  requesting retrieval by default.
* If required external policy/FAQ/SOP knowledge is unavailable, prefer human
  review rather than inventing knowledge.
* `retrieval_agent` remains a valid owner for a future project that activates
  retrieval.

## Retrieval-capable plan shape (future-activated / synthetic)

The plan contract can still carry a retrieval-shaped plan. This proves the
RAG-ready surface, not that an active backend exists:

```python
SupportAgentState(
    plan=[
        PlanStep(
            step_id="step_retrieve_refund_policy",
            title="Retrieve refund policy context",
            description="Retrieve refund and billing policy relevant to the ticket.",
            owner="retrieval_agent",
            status="pending",
        ),
        PlanStep(
            step_id="step_draft_refund_response",
            title="Draft grounded refund response",
            description="Draft a response grounded in the retrieved refund policy.",
            owner="response_agent",
            status="pending",
        ),
        PlanStep(
            step_id="step_human_review",
            title="Human review",
            description="Review the case before any final customer-facing response.",
            owner="human",
            status="pending",
            requires_human_approval=True,
        ),
    ],
    current_step_id="step_retrieve_refund_policy",
)
```

## Fallback on planner failure

Fallback must agree with `workflow_outcome = needs_human_review` and must not
pretend retrieval exists:

* `step_draft_response` — cautious draft without corpus grounding
* `step_human_review` — always present in fallback
