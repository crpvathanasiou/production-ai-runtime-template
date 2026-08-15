import time
from typing import Protocol

from app.application.execution import ExecutionContext
from app.application.planner import PlannerOutcome
from app.core.logging import format_operational_log, get_logger
from app.graph_state import GraphState
from app.schemas import ShieldOutput, SupportTicket, TriageOutput

logger = get_logger(__name__)

_RECOVERED_ERROR_TYPES = frozenset(
    {
        "ModelOutputParsingError",
        "UpstreamServiceError",
    }
)


class SupportsPlannerExecute(Protocol):
    async def execute(
        self,
        *,
        context: ExecutionContext,
        ticket: SupportTicket,
        shield_result: ShieldOutput,
        triage_result: TriageOutput,
    ) -> PlannerOutcome: ...


def make_planner_node(
    operation: SupportsPlannerExecute,
    *,
    model_name: str,
):
    async def planner_node(state: GraphState) -> GraphState:
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
                "planner.started",
                request_id=request_id,
                run_id=run_id,
                thread_id=thread_id,
                node_name="planner",
            ),
        )

        if state.shield_result is None:
            state.workflow_outcome = "blocked"
            state.additional_metadata["planner_error"] = {
                "request_id": request_id,
                "error_type": "MissingShieldResult",
                "message": "planner_node called without shield_result",
            }
            return state

        if state.triage_result is None:
            state.workflow_outcome = "blocked"
            state.additional_metadata["planner_error"] = {
                "request_id": request_id,
                "error_type": "MissingTriageResult",
                "message": "planner_node called without triage_result",
            }
            return state

        outcome = await operation.execute(
            context=context,
            ticket=state.initial_ticket,
            shield_result=state.shield_result,
            triage_result=state.triage_result,
        )

        state.agent_state = outcome.agent_state

        if not outcome.fallback_used:
            state.workflow_outcome = "running"

            execution = outcome.execution
            latency_ms = execution.latency_ms if execution is not None else 0.0
            attempts = execution.attempts if execution is not None else 0

            state.additional_metadata["planner"] = {
                "request_id": request_id,
                "model_name": model_name,
                "latency_ms": latency_ms,
                "attempts": attempts,
                "plan_length": len(outcome.agent_state.plan),
                "current_step_id": outcome.agent_state.current_step_id,
                "step_titles": [step.title for step in outcome.agent_state.plan],
                "prompt_id": outcome.prompt_identity.ref.prompt_id,
                "prompt_revision": outcome.prompt_identity.ref.revision,
                "prompt_content_hash": outcome.prompt_identity.content_hash,
            }

            logger.info(
                format_operational_log(
                    "planner.completed",
                    request_id=request_id,
                    run_id=run_id,
                    thread_id=thread_id,
                    node_name="planner",
                    model_name=model_name,
                    latency_ms=latency_ms,
                    attempts=attempts,
                    plan_length=len(outcome.agent_state.plan),
                    current_step_id=outcome.agent_state.current_step_id,
                ),
            )
            return state

        # fallback_used == True
        latency_ms = round((time.perf_counter() - started) * 1000, 2)
        state.workflow_outcome = "needs_human_review"
        state.additional_metadata["planner_error"] = {
            "request_id": request_id,
            "error_type": outcome.error_type or "Exception",
            "message": outcome.error_message or "",
            "latency_ms": latency_ms,
            "fallback_plan_used": True,
            "prompt_id": outcome.prompt_identity.ref.prompt_id,
            "prompt_revision": outcome.prompt_identity.ref.revision,
            "prompt_content_hash": outcome.prompt_identity.content_hash,
        }

        error_type = outcome.error_type or "Exception"
        if error_type in _RECOVERED_ERROR_TYPES:
            logger.error(
                format_operational_log(
                    "planner.recovered_error",
                    request_id=request_id,
                    run_id=run_id,
                    thread_id=thread_id,
                    node_name="planner",
                    error_type=error_type,
                    latency_ms=latency_ms,
                ),
            )
        else:
            logger.error(
                format_operational_log(
                    "planner.unexpected_error",
                    request_id=request_id,
                    run_id=run_id,
                    thread_id=thread_id,
                    node_name="planner",
                    error_type=error_type,
                    latency_ms=latency_ms,
                ),
            )
        return state

    return planner_node
