"""Planner application operation."""

from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.llm import LLMExecutionMetadata, LLMPort
from app.core.exceptions import ModelOutputParsingError, UpstreamServiceError
from app.prompts.planner_prompts import (
    build_planner_system_prompt,
    build_planner_user_prompt,
)
from app.schemas import PlanStep, ShieldOutput, SupportAgentState, SupportTicket, TriageOutput


@dataclass(frozen=True)
class PlannerOutcome:
    agent_state: SupportAgentState
    execution: LLMExecutionMetadata | None
    fallback_used: bool
    error_type: str | None
    error_message: str | None


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
    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    async def execute(
        self,
        *,
        ticket: SupportTicket,
        shield_result: ShieldOutput,
        triage_result: TriageOutput,
    ) -> PlannerOutcome:
        system_prompt = build_planner_system_prompt()
        user_prompt = build_planner_user_prompt(
            ticket=ticket,
            shield_result=shield_result,
            triage_result=triage_result,
        )

        try:
            result = await self._llm.generate_structured(
                system_prompt=system_prompt,
                prompt=user_prompt,
                response_schema=SupportAgentState,
            )
            normalized = _normalize_planner_output(result.parsed)
            if not normalized.plan:
                raise ModelOutputParsingError("Planner returned an empty plan.")

            return PlannerOutcome(
                agent_state=normalized,
                execution=result.execution,
                fallback_used=False,
                error_type=None,
                error_message=None,
            )
        except (ModelOutputParsingError, UpstreamServiceError) as exc:
            return PlannerOutcome(
                agent_state=_build_fallback_plan(),
                execution=None,
                fallback_used=True,
                error_type=exc.__class__.__name__,
                error_message=str(exc),
            )
        except Exception as exc:
            return PlannerOutcome(
                agent_state=_build_fallback_plan(),
                execution=None,
                fallback_used=True,
                error_type=exc.__class__.__name__,
                error_message=str(exc),
            )
