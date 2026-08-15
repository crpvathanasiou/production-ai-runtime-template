import time
from typing import Literal, Protocol

from app.application.execution import ExecutionContext
from app.application.input_shield import InputShieldOutcome
from app.core.logging import format_operational_log, get_logger
from app.graph_state import GraphState
from app.schemas import ShieldOutput, SupportTicket

logger = get_logger(__name__)

WorkflowOutcome = Literal["running", "blocked", "needs_human_review", "completed"]


class SupportsInputShieldExecute(Protocol):
    async def execute(
        self,
        *,
        context: ExecutionContext,
        ticket: SupportTicket,
    ) -> InputShieldOutcome: ...


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
        run_id = state.run_id
        thread_id = state.thread_id
        context = ExecutionContext(
            request_id=state.request_id,
            run_id=state.run_id,
            thread_id=state.thread_id,
        )

        logger.info(
            format_operational_log(
                "input_shield.started",
                request_id=request_id,
                run_id=run_id,
                thread_id=thread_id,
                node_name="input_shield",
            ),
        )

        outcome = await operation.execute(
            context=context,
            ticket=state.initial_ticket,
        )
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
                format_operational_log(
                    "input_shield.completed_fail_fast",
                    request_id=request_id,
                    run_id=run_id,
                    thread_id=thread_id,
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
            error_meta: dict = {
                "request_id": request_id,
                "error_type": outcome.error_type or "GuardrailBlockedError",
                "message": outcome.error_message or "",
                "latency_ms": latency_ms,
            }
            if outcome.prompt_identity is not None:
                error_meta["prompt_id"] = outcome.prompt_identity.ref.prompt_id
                error_meta["prompt_revision"] = outcome.prompt_identity.ref.revision
                error_meta["prompt_content_hash"] = outcome.prompt_identity.content_hash
            state.additional_metadata["input_shield_error"] = error_meta

            logger.warning(
                format_operational_log(
                    "input_shield.guardrail_blocked",
                    request_id=request_id,
                    run_id=run_id,
                    thread_id=thread_id,
                    node_name="input_shield",
                    error_type=outcome.error_type or "GuardrailBlockedError",
                    latency_ms=latency_ms,
                ),
            )
            return state

        if outcome.source == "llm_failure_fallback":
            state.workflow_outcome = "needs_human_review"

            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            fallback_meta: dict = {
                "request_id": request_id,
                "error_type": outcome.error_type or "UpstreamServiceError",
                "message": outcome.error_message or "",
                "latency_ms": latency_ms,
            }
            if outcome.prompt_identity is not None:
                fallback_meta["prompt_id"] = outcome.prompt_identity.ref.prompt_id
                fallback_meta["prompt_revision"] = outcome.prompt_identity.ref.revision
                fallback_meta["prompt_content_hash"] = (
                    outcome.prompt_identity.content_hash
                )
            state.additional_metadata["input_shield_error"] = fallback_meta

            logger.error(
                format_operational_log(
                    "input_shield.recovered_error",
                    request_id=request_id,
                    run_id=run_id,
                    thread_id=thread_id,
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

        success_meta: dict = {
            "request_id": request_id,
            "model_name": model_name,
            "latency_ms": latency_ms,
            "attempts": attempts,
            "decision": outcome.output.decision,
            "risk_level": outcome.output.risk_level,
        }
        if outcome.prompt_identity is not None:
            success_meta["prompt_id"] = outcome.prompt_identity.ref.prompt_id
            success_meta["prompt_revision"] = outcome.prompt_identity.ref.revision
            success_meta["prompt_content_hash"] = outcome.prompt_identity.content_hash
        state.additional_metadata["input_shield"] = success_meta

        logger.info(
            format_operational_log(
                "input_shield.completed",
                request_id=request_id,
                run_id=run_id,
                thread_id=thread_id,
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
