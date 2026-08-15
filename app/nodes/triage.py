import time
from typing import Protocol

from langsmith import traceable

from app.application.ports.llm import StructuredLLMResult
from app.core.exceptions import ModelOutputParsingError, UpstreamServiceError
from app.core.logging import bind_log_context, get_logger
from app.graph_state import GraphState
from app.schemas import ShieldOutput, SupportTicket, TriageOutput

logger = get_logger(__name__)


class SupportsTriageExecute(Protocol):
    async def execute(
        self,
        *,
        ticket: SupportTicket,
        shield_result: ShieldOutput,
    ) -> StructuredLLMResult[TriageOutput]: ...


def make_triage_node(
    operation: SupportsTriageExecute,
    *,
    model_name: str,
):
    @traceable(
        run_type="chain",
        name="triage_node",
    )
    async def triage_node(state: GraphState) -> GraphState:
        started = time.perf_counter()
        request_id = state.request_id

        logger.info(
            "triage.started",
            extra=bind_log_context(
                request_id=request_id,
                node_name="triage",
            ),
        )

        if state.shield_result is None:
            state.workflow_outcome = "blocked"
            state.additional_metadata["triage_error"] = {
                "request_id": request_id,
                "error_type": "MissingShieldResult",
                "message": "triage_node called without shield_result",
            }
            return state

        if state.shield_result.decision in {"block", "needs_clarification"}:
            state.workflow_outcome = "blocked"
            state.additional_metadata["triage"] = {
                "request_id": request_id,
                "skipped": True,
                "reason": f"shield_decision={state.shield_result.decision}",
            }
            return state

        try:
            result = await operation.execute(
                ticket=state.initial_ticket,
                shield_result=state.shield_result,
            )

            parsed = result.parsed
            state.triage_result = parsed

            if parsed.requires_human_approval or parsed.requires_escalation:
                state.workflow_outcome = "needs_human_review"
            else:
                state.workflow_outcome = "running"

            state.additional_metadata["triage"] = {
                "request_id": request_id,
                "model_name": model_name,
                "latency_ms": result.execution.latency_ms,
                "attempts": result.execution.attempts,
                "issue_category": parsed.issue_category,
                "intent": parsed.intent,
                "urgency": parsed.urgency,
                "requires_escalation": parsed.requires_escalation,
                "requires_human_approval": parsed.requires_human_approval,
            }

            logger.info(
                "triage.completed",
                extra=bind_log_context(
                    request_id=request_id,
                    node_name="triage",
                    model_name=model_name,
                    latency_ms=result.execution.latency_ms,
                    attempts=result.execution.attempts,
                    issue_category=parsed.issue_category,
                    intent=parsed.intent,
                    urgency=parsed.urgency,
                    requires_escalation=parsed.requires_escalation,
                    requires_human_approval=parsed.requires_human_approval,
                ),
            )
            return state

        except (ModelOutputParsingError, UpstreamServiceError) as exc:
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            state.workflow_outcome = "needs_human_review"
            state.additional_metadata["triage_error"] = {
                "request_id": request_id,
                "error_type": exc.__class__.__name__,
                "message": str(exc),
                "latency_ms": latency_ms,
            }

            logger.exception(
                "triage.recovered_error",
                extra=bind_log_context(
                    request_id=request_id,
                    node_name="triage",
                    error_type=exc.__class__.__name__,
                    latency_ms=latency_ms,
                ),
            )
            return state

    return triage_node
