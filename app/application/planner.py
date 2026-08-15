"""Planner application operation."""

from __future__ import annotations

import time
from dataclasses import dataclass

from app.application.execution import (
    OPERATION_PLANNER,
    ExecutionContext,
    LLMInvocationId,
    LLMInvocationStarted,
    OperationCompleted,
    OperationFailed,
    OperationFallback,
    OperationStarted,
    classify_operation_error,
)
from app.application.ports.llm import LLMExecutionMetadata, LLMPort
from app.application.ports.telemetry import TelemetryPort
from app.application.prompts import PromptIdentity, PromptRef, PromptRepository
from app.core.exceptions import ModelOutputParsingError, UpstreamServiceError
from app.schemas import PlanStep, ShieldOutput, SupportAgentState, SupportTicket, TriageOutput


@dataclass(frozen=True)
class PlannerOutcome:
    agent_state: SupportAgentState
    execution: LLMExecutionMetadata | None
    fallback_used: bool
    error_type: str | None
    error_message: str | None
    prompt_identity: PromptIdentity


def _normalize_planner_output(agent_state: SupportAgentState) -> SupportAgentState:
    normalized_steps: list[PlanStep] = []

    for step in agent_state.plan:
        normalized_steps.append(
            PlanStep(
                step_id=step.step_id,
                title=step.title,
                description=step.description,
                owner=step.owner,
                status="pending",
                requires_human_approval=step.requires_human_approval,
                result=None,
                error=None,
            )
        )

    current_step_id = agent_state.current_step_id
    if normalized_steps and not current_step_id:
        current_step_id = normalized_steps[0].step_id

    return SupportAgentState(
        plan=normalized_steps,
        current_step_id=current_step_id,
    )


def _build_fallback_plan() -> SupportAgentState:
    steps = [
        PlanStep(
            step_id="step_draft_response",
            title="Draft cautious response",
            description=(
                "Draft a cautious customer response using only ticket and triage "
                "context. Do not assume external policy/FAQ corpus grounding."
            ),
            owner="response_agent",
            status="pending",
        ),
        PlanStep(
            step_id="step_human_review",
            title="Human review",
            description=(
                "Review the case and cautious draft before any final "
                "customer-facing response."
            ),
            owner="human",
            status="pending",
            requires_human_approval=True,
        ),
    ]

    return SupportAgentState(
        plan=steps,
        current_step_id=steps[0].step_id if steps else None,
    )


class PlannerOperation:
    def __init__(
        self,
        llm: LLMPort,
        prompt_repository: PromptRepository,
        prompt_ref: PromptRef,
        telemetry: TelemetryPort,
    ) -> None:
        self._llm = llm
        self._prompt_repository = prompt_repository
        self._prompt_ref = prompt_ref
        self._telemetry = telemetry

    async def execute(
        self,
        *,
        context: ExecutionContext,
        ticket: SupportTicket,
        shield_result: ShieldOutput,
        triage_result: TriageOutput,
    ) -> PlannerOutcome:
        started = time.perf_counter()
        self._telemetry.emit(
            OperationStarted(context=context, operation_name=OPERATION_PLANNER)
        )

        try:
            resolved = self._prompt_repository.resolve(
                self._prompt_ref,
                variables={
                    "customer_message": ticket.customer_message,
                    "customer_metadata": ticket.customer_metadata or {},
                    "order_account_metadata": ticket.order_account_metadata or {},
                    "shield_decision": shield_result.decision,
                    "shield_risk_level": shield_result.risk_level,
                    "shield_categories": shield_result.categories,
                    "shield_should_route_to_human": shield_result.should_route_to_human,
                    "shield_reasoning": shield_result.reasoning,
                    "triage_issue_category": triage_result.issue_category,
                    "triage_intent": triage_result.intent,
                    "triage_urgency": triage_result.urgency,
                    "triage_customer_tone": triage_result.customer_tone,
                    "triage_requires_escalation": triage_result.requires_escalation,
                    "triage_requires_human_approval": triage_result.requires_human_approval,
                    "triage_reasoning_summary": triage_result.reasoning_summary,
                },
            )
        except Exception as exc:
            self._telemetry.emit(
                OperationFailed(
                    context=context,
                    operation_name=OPERATION_PLANNER,
                    duration_ms=(time.perf_counter() - started) * 1000,
                    error_category=classify_operation_error(exc),
                    error_type=exc.__class__.__name__,
                    invocation_id=None,
                )
            )
            raise

        invocation_id = LLMInvocationId.new()
        self._telemetry.emit(
            LLMInvocationStarted(
                context=context,
                operation_name=OPERATION_PLANNER,
                invocation_id=invocation_id,
                prompt_identity=resolved.identity,
            )
        )

        try:
            result = await self._llm.generate_structured(
                context=context,
                invocation_id=invocation_id,
                system_prompt=resolved.system_prompt,
                prompt=resolved.user_prompt,
                response_schema=SupportAgentState,
            )
            normalized = _normalize_planner_output(result.parsed)
            if not normalized.plan:
                raise ModelOutputParsingError("Planner returned an empty plan.")

            self._telemetry.emit(
                OperationCompleted(
                    context=context,
                    operation_name=OPERATION_PLANNER,
                    duration_ms=(time.perf_counter() - started) * 1000,
                )
            )
            return PlannerOutcome(
                agent_state=normalized,
                execution=result.execution,
                fallback_used=False,
                error_type=None,
                error_message=None,
                prompt_identity=resolved.identity,
            )
        except (ModelOutputParsingError, UpstreamServiceError) as exc:
            self._telemetry.emit(
                OperationFallback(
                    context=context,
                    operation_name=OPERATION_PLANNER,
                    invocation_id=invocation_id,
                    duration_ms=(time.perf_counter() - started) * 1000,
                    error_category=classify_operation_error(exc),
                    error_type=exc.__class__.__name__,
                )
            )
            return PlannerOutcome(
                agent_state=_build_fallback_plan(),
                execution=None,
                fallback_used=True,
                error_type=exc.__class__.__name__,
                error_message=str(exc),
                prompt_identity=resolved.identity,
            )
        except Exception as exc:
            self._telemetry.emit(
                OperationFallback(
                    context=context,
                    operation_name=OPERATION_PLANNER,
                    invocation_id=invocation_id,
                    duration_ms=(time.perf_counter() - started) * 1000,
                    error_category=classify_operation_error(exc),
                    error_type=exc.__class__.__name__,
                )
            )
            return PlannerOutcome(
                agent_state=_build_fallback_plan(),
                execution=None,
                fallback_used=True,
                error_type=exc.__class__.__name__,
                error_message=str(exc),
                prompt_identity=resolved.identity,
            )
