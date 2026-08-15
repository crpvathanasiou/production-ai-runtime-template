import time
from typing import Protocol

from langsmith import traceable

from app.application.response_drafting import ResponseDraftingOutcome
from app.core.logging import bind_log_context, get_logger
from app.graph_state import GraphState
from app.schemas import (
    PlanStep,
    RetrievedDocument,
    SupportTicket,
    TriageOutput,
)
from app.services.retrieval_service import retrieve_relevant_documents

logger = get_logger(__name__)


class SupportsResponseDraftingExecute(Protocol):
    async def execute(
        self,
        *,
        ticket: SupportTicket,
        triage_result: TriageOutput,
        retrieved_documents: list[RetrievedDocument],
    ) -> ResponseDraftingOutcome: ...


# This helper creates a fresh copy of a step and marks it as completed.
#
# We do this instead of mutating the original step directly because:
# - it keeps updates explicit
# - it makes debugging easier
# - it fits well with state-based workflow thinking
def _mark_step_completed(step: PlanStep, result: str | None = None) -> PlanStep:
    return PlanStep(
        step_id=step.step_id,
        title=step.title,
        description=step.description,
        owner=step.owner,
        status="completed",
        requires_human_approval=step.requires_human_approval,
        result=result,
        error=None,
    )


# This helper marks a step as failed and stores the error message on the step itself.
#
# Why store the error on the step?
# Because later, when we inspect the graph state, we want to know:
# - which step failed
# - why it failed
# - whether we should route to human review
def _mark_step_failed(step: PlanStep, error: str) -> PlanStep:
    return PlanStep(
        step_id=step.step_id,
        title=step.title,
        description=step.description,
        owner=step.owner,
        status="failed",
        requires_human_approval=step.requires_human_approval,
        result=None,
        error=error,
    )


# This helper keeps a step in pending state.
#
# In our workflow, this is mainly used for human-owned steps.
# execute_plan_node does not perform human review itself.
# It only prepares the workflow so that the later human_review node can handle it.
def _mark_step_pending(step: PlanStep) -> PlanStep:
    return PlanStep(
        step_id=step.step_id,
        title=step.title,
        description=step.description,
        owner=step.owner,
        status="pending",
        requires_human_approval=step.requires_human_approval,
        result=step.result,
        error=step.error,
    )


# The planner decides THAT retrieval is needed.
# The executor decides HOW to turn that decision into a query.
#
# This builds a simple query from workflow context. The retrieval entrypoint
# currently has no active backend, so the call returns no documents.
#
# ticket = "I was charged twice and want a refund"
# step.title = "Retrieve refund policy"
# step.description = "Retrieve refund and billing policy relevant to the ticket"
# triage.issue_category = "refund"
# triage.intent = "complaint"
# Result: I was charged twice and want a refund Retrieve refund policy
# Retrieve refund and billing policy relevant to the ticket refund complaint ...
def _build_retrieval_query(state: GraphState, step: PlanStep) -> str:
    triage = state.triage_result
    ticket = state.initial_ticket.customer_message

    parts = [ticket, step.title, step.description]

    if triage:
        parts.extend(
            [
                triage.issue_category,
                triage.intent,
                triage.reasoning_summary,
            ]
        )

    return " ".join(part for part in parts if part)


# After execution, we want to know what the next actionable step is.
#
# Example:
# - retrieval step completed
# - drafting step completed
# - human review step still pending
#
# In that case, the next pending step should be the human review step.
def _get_next_pending_step_id(plan: list[PlanStep]) -> str | None:
    for step in plan:
        if step.status == "pending":
            return step.step_id
    return None


# Execute a retrieval-shaped plan step.
#
# What happens here:
# 1. Build a retrieval query from current workflow context
# 2. Call the retrieval entrypoint
# 3. Persist returned documents into state.retrieved_documents
# 4. Mark the step completed when documents are returned
# 5. Mark the step failed when an explicitly requested retrieval returns none
#
# Important:
# The planner does NOT retrieve docs itself.
# It only says a retrieval step should run.
# This function preserves that orchestration seam.
# Zero documents for an explicit retrieval request is unmet retrieval, not success.
async def _execute_retrieval_step(state: GraphState, step: PlanStep) -> tuple[PlanStep, int]:
    query = _build_retrieval_query(state, step)
    documents = retrieve_relevant_documents(query=query, max_documents=3)

    state.retrieved_documents = documents

    if not documents:
        updated_step = _mark_step_failed(step, "Retrieval returned no documents.")
        return updated_step, 0

    result_summary = f"Retrieved {len(documents)} document(s)."
    updated_step = _mark_step_completed(step, result=result_summary)

    return updated_step, len(documents)


# Execute a response drafting step via the injected Application Operation.
async def _execute_response_step(
    state: GraphState,
    step: PlanStep,
    *,
    response_drafting_operation: SupportsResponseDraftingExecute,
    model_name: str,
) -> PlanStep:
    # We require triage before drafting because the draft should reflect
    # issue type, urgency, tone, and human-review sensitivity.
    if state.triage_result is None:
        return _mark_step_failed(step, "Missing triage_result for response drafting.")

    result = await response_drafting_operation.execute(
        ticket=state.initial_ticket,
        triage_result=state.triage_result,
        retrieved_documents=state.retrieved_documents or [],
    )

    parsed = result.output

    # Save the draft into state.
    # This becomes the main input for the guardrails node.
    state.response_draft = parsed

    # Save useful execution metadata for tracing/debugging.
    state.additional_metadata["response_drafting"] = {
        "request_id": state.request_id,
        "model_name": model_name,
        "latency_ms": result.execution.latency_ms,
        "attempts": result.execution.attempts,
        "used_documents": len(parsed.related_documents),
        "prompt_id": result.prompt_identity.ref.prompt_id,
        "prompt_revision": result.prompt_identity.ref.revision,
        "prompt_content_hash": result.prompt_identity.content_hash,
    }

    has_retrieved_context = bool(state.retrieved_documents)
    result_summary = (
        "Drafted grounded customer response."
        if has_retrieved_context
        else "Drafted customer response without retrieved context."
    )

    return _mark_step_completed(step, result=result_summary)


def make_execute_plan_node(
    response_drafting_operation: SupportsResponseDraftingExecute,
    *,
    model_name: str,
):
    # Main executor node.
    #
    # This node is the "Act" part of the pattern:
    # Plan -> Act -> Validate
    #
    # Upstream:
    # - planner created the plan
    #
    # This node:
    # - reads the plan
    # - executes supported steps
    # - updates state artifacts
    #
    # Downstream:
    # - guardrails validates the drafted response
    @traceable(run_type="chain", name="execute_plan_node")
    async def execute_plan_node(state: GraphState) -> GraphState:
        started = time.perf_counter()
        request_id = state.request_id

        logger.info(
            "execute_plan.started",
            extra=bind_log_context(
                request_id=request_id,
                node_name="execute_plan",
            ),
        )

        # Safety check:
        # if there is no plan, this node has nothing meaningful to execute.
        if state.agent_state is None or not state.agent_state.plan:
            state.workflow_outcome = "blocked"
            state.additional_metadata["execute_plan_error"] = {
                "request_id": request_id,
                "error_type": "MissingPlan",
                "message": "execute_plan_node called without an executable plan.",
            }
            return state

        updated_plan: list[PlanStep] = []
        retrieval_count = 0

        # Walk through the plan in order.
        # For v1, we support:
        # - retrieval_agent steps
        # - response_agent steps
        # - human steps (kept pending)
        for step in state.agent_state.plan:
            # Retrieval-shaped steps: build query → call entrypoint → store returned docs.
            if step.owner == "retrieval_agent" and step.status == "pending":
                try:
                    updated_step, docs_count = await _execute_retrieval_step(state, step)
                    retrieval_count += docs_count
                    updated_plan.append(updated_step)
                except Exception as exc:
                    # Important production-minded behavior:
                    # one step failure should not crash the whole workflow.
                    updated_plan.append(_mark_step_failed(step, str(exc)))

            # Response steps create the customer-facing draft.
            elif step.owner == "response_agent" and step.status == "pending":
                try:
                    updated_step = await _execute_response_step(
                        state,
                        step,
                        response_drafting_operation=response_drafting_operation,
                        model_name=model_name,
                    )
                    updated_plan.append(updated_step)
                except Exception as exc:
                    updated_plan.append(_mark_step_failed(step, str(exc)))

            # Human steps are intentionally not executed here.
            # They remain pending so that the human_review node can handle them later.
            elif step.owner == "human":
                updated_plan.append(_mark_step_pending(step))

            # Any unsupported or already-resolved steps are carried forward unchanged.
            else:
                updated_plan.append(step)

        # Save the updated plan back into the graph state.
        state.agent_state.plan = updated_plan
        state.agent_state.current_step_id = _get_next_pending_step_id(updated_plan)

        failed_steps = [step for step in updated_plan if step.status == "failed"]
        pending_human_steps = [
            step
            for step in updated_plan
            if step.owner == "human" and step.status == "pending"
        ]

        # Decide the current workflow outcome after execution.
        #
        # Failed steps and unresolved human PlanSteps are explicit human-review gates.
        # Only when neither applies does the workflow stay "running".
        if failed_steps:
            state.workflow_outcome = "needs_human_review"
        elif pending_human_steps:
            state.workflow_outcome = "needs_human_review"
        else:
            state.workflow_outcome = "running"

        latency_ms = round((time.perf_counter() - started) * 1000, 2)

        # Store execution metadata for observability.
        # This helps later with:
        # - debugging
        # - tracing
        # - latency inspection
        # - future metrics collection
        state.additional_metadata["execute_plan"] = {
            "request_id": request_id,
            "latency_ms": latency_ms,
            "retrieved_documents_count": len(state.retrieved_documents or []),
            "failed_steps": [step.step_id for step in failed_steps],
            "next_step_id": state.agent_state.current_step_id,
        }

        logger.info(
            "execute_plan.completed",
            extra=bind_log_context(
                request_id=request_id,
                node_name="execute_plan",
                latency_ms=latency_ms,
                retrieved_documents_count=len(state.retrieved_documents or []),
                failed_steps=len(failed_steps),
                next_step_id=state.agent_state.current_step_id,
            ),
        )

        return state

    return execute_plan_node
