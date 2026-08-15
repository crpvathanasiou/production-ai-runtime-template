import time
from typing import Literal, Protocol

from app.application.input_shield import InputShieldOutcome
from app.core.logging import bind_log_context, get_logger
from app.graph_state import GraphState
from app.schemas import ShieldOutput, SupportTicket

logger = get_logger(__name__)

WorkflowOutcome = Literal["running", "blocked", "needs_human_review", "completed"]


class SupportsInputShieldExecute(Protocol):
    async def execute(self, ticket: SupportTicket) -> InputShieldOutcome: ...


def _workflow_outcome_from_shield(output: ShieldOutput) -> WorkflowOutcome:
    if output.decision == "block":
        return "blocked"
    if output.decision == "needs_clarification":
        return "blocked"
    if output.should_route_to_human:
        return "needs_human_review"
    return "running"


def make_input_shield_node(
    operation: SupportsInputShieldExecute,
    *,
    model_name: str,
):
    async def input_shield_node(state: GraphState) -> GraphState:
        started = time.perf_counter()
        request_id = state.request_id

        logger.info(
            "input_shield.started",
            extra=bind_log_context(
                request_id=request_id,
                node_name="input_shield",
            ),
        )

        outcome = await operation.execute(state.initial_ticket)
        state.shield_result = outcome.output

        if outcome.source == "heuristic_fail_fast":
            state.workflow_outcome = _workflow_outcome_from_shield(outcome.output)

            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            state.additional_metadata["input_shield"] = {
                "request_id": request_id,
                "source": "heuristic_fail_fast",
                "latency_ms": latency_ms,
                "decision": outcome.output.decision,
                "risk_level": outcome.output.risk_level,
            }

            logger.info(
                "input_shield.completed_fail_fast",
                extra=bind_log_context(
                    request_id=request_id,
                    node_name="input_shield",
                    decision=outcome.output.decision,
                    risk_level=outcome.output.risk_level,
                    latency_ms=latency_ms,
                ),
            )
            return state

        if outcome.source == "prompt_length_block":
            state.workflow_outcome = "blocked"

            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            state.additional_metadata["input_shield_error"] = {
                "request_id": request_id,
                "error_type": outcome.error_type or "GuardrailBlockedError",
                "message": outcome.error_message or "",
                "latency_ms": latency_ms,
            }

            logger.warning(
                "input_shield.guardrail_blocked",
                extra=bind_log_context(
                    request_id=request_id,
                    node_name="input_shield",
                    error_type=outcome.error_type or "GuardrailBlockedError",
                    latency_ms=latency_ms,
                ),
            )
            return state

        if outcome.source == "llm_failure_fallback":
            state.workflow_outcome = "needs_human_review"

            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            state.additional_metadata["input_shield_error"] = {
                "request_id": request_id,
                "error_type": outcome.error_type or "UpstreamServiceError",
                "message": outcome.error_message or "",
                "latency_ms": latency_ms,
            }

            logger.error(
                "input_shield.recovered_error",
                extra=bind_log_context(
                    request_id=request_id,
                    node_name="input_shield",
                    error_type=outcome.error_type or "UpstreamServiceError",
                    latency_ms=latency_ms,
                ),
            )
            return state

        # source == "llm"
        state.workflow_outcome = _workflow_outcome_from_shield(outcome.output)

        execution = outcome.execution
        latency_ms = execution.latency_ms if execution is not None else 0.0
        attempts = execution.attempts if execution is not None else 0

        state.additional_metadata["input_shield"] = {
            "request_id": request_id,
            "model_name": model_name,
            "latency_ms": latency_ms,
            "attempts": attempts,
            "decision": outcome.output.decision,
            "risk_level": outcome.output.risk_level,
        }

        logger.info(
            "input_shield.completed",
            extra=bind_log_context(
                request_id=request_id,
                node_name="input_shield",
                model_name=model_name,
                latency_ms=latency_ms,
                attempts=attempts,
                decision=outcome.output.decision,
                risk_level=outcome.output.risk_level,
            ),
        )
        return state

    return input_shield_node
