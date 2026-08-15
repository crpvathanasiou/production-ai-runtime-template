import pytest

from app.application.planner import PlannerOperation
from app.application.ports.llm import LLMExecutionMetadata
from app.application.prompts import (
    PromptIdentity,
    PromptNotFoundError,
    PromptRef,
    PromptRenderError,
    ResolvedPrompt,
)
from app.core.exceptions import ModelOutputParsingError, UpstreamServiceError
from app.schemas import (
    PlanStep,
    ShieldOutput,
    SupportAgentState,
    SupportTicket,
    TriageOutput,
)
from tests.application.fakes import FakeLLMPort, FakePromptRepository

_PROMPT_REF = PromptRef(prompt_id="planner", revision=1)
_EXPECTED_IDENTITY = PromptIdentity(ref=_PROMPT_REF, content_hash="planner-hash")


def _ticket() -> SupportTicket:
    return SupportTicket(
        customer_message="I was charged twice for my order and need a refund.",
        customer_metadata={"customer_id": "cust_123"},
        order_account_metadata={"order_id": "ord_456"},
    )


def _shield() -> ShieldOutput:
    return ShieldOutput(
        decision="allow",
        risk_level="low",
        categories=["valid_support_request"],
        sanitized_message="I was charged twice for my order and need a refund.",
        should_route_to_human=False,
        clarification_question=None,
        reasoning="Valid support request.",
    )


def _triage() -> TriageOutput:
    return TriageOutput(
        issue_category="billing",
        intent="problem_report",
        urgency="medium",
        customer_tone="frustrated",
        requires_escalation=False,
        requires_human_approval=True,
        reasoning_summary="Billing dispute needs careful handling.",
    )


def _resolved() -> ResolvedPrompt:
    return ResolvedPrompt(
        ref=_PROMPT_REF,
        system_prompt="planner-system",
        user_prompt="planner-user",
        content_hash="planner-hash",
    )


def _operation(*, llm: FakeLLMPort, prompts: FakePromptRepository) -> PlannerOperation:
    return PlannerOperation(
        llm=llm,
        prompt_repository=prompts,
        prompt_ref=_PROMPT_REF,
    )


@pytest.mark.asyncio
async def test_planner_success_returns_normalized_agent_state() -> None:
    plan = SupportAgentState(
        plan=[
            PlanStep(
                step_id="step_1",
                title="Draft response",
                description="Draft a cautious reply.",
                owner="response_agent",
                status="completed",
                requires_human_approval=False,
                result="stale",
                error="stale-error",
            ),
            PlanStep(
                step_id="step_2",
                title="Human review",
                description="Review draft.",
                owner="human",
                status="failed",
                requires_human_approval=True,
                result="also-stale",
                error="also-stale-error",
            ),
        ],
        current_step_id="step_1",
    )
    llm = FakeLLMPort(result=plan, latency_ms=9.0, attempts=1)
    resolved = _resolved()
    prompts = FakePromptRepository(resolved=resolved)
    operation = _operation(llm=llm, prompts=prompts)
    ticket = _ticket()
    shield = _shield()
    triage = _triage()

    outcome = await operation.execute(
        ticket=ticket,
        shield_result=shield,
        triage_result=triage,
    )

    assert outcome.fallback_used is False
    assert outcome.execution == LLMExecutionMetadata(latency_ms=9.0, attempts=1)
    assert outcome.error_type is None
    assert outcome.prompt_identity == _EXPECTED_IDENTITY
    assert len(outcome.agent_state.plan) == 2
    assert all(step.status == "pending" for step in outcome.agent_state.plan)
    assert all(step.result is None for step in outcome.agent_state.plan)
    assert all(step.error is None for step in outcome.agent_state.plan)
    assert outcome.agent_state.plan[1].requires_human_approval is True
    assert prompts.call_count == 1
    assert prompts.calls[0]["ref"] == _PROMPT_REF
    assert prompts.calls[0]["variables"] == {
        "customer_message": ticket.customer_message,
        "customer_metadata": {"customer_id": "cust_123"},
        "order_account_metadata": {"order_id": "ord_456"},
        "shield_decision": shield.decision,
        "shield_risk_level": shield.risk_level,
        "shield_categories": shield.categories,
        "shield_should_route_to_human": shield.should_route_to_human,
        "shield_reasoning": shield.reasoning,
        "triage_issue_category": triage.issue_category,
        "triage_intent": triage.intent,
        "triage_urgency": triage.urgency,
        "triage_customer_tone": triage.customer_tone,
        "triage_requires_escalation": triage.requires_escalation,
        "triage_requires_human_approval": triage.requires_human_approval,
        "triage_reasoning_summary": triage.reasoning_summary,
    }
    assert llm.call_count == 1
    call = llm.calls[0]
    assert call["system_prompt"] == resolved.system_prompt
    assert call["prompt"] == resolved.user_prompt
    assert call["response_schema"] is SupportAgentState


@pytest.mark.asyncio
async def test_planner_missing_current_step_id_defaults_to_first() -> None:
    plan = SupportAgentState(
        plan=[
            PlanStep(
                step_id="first",
                title="Draft",
                description="Draft",
                owner="response_agent",
                status="pending",
            ),
            PlanStep(
                step_id="second",
                title="Review",
                description="Review",
                owner="human",
                status="pending",
                requires_human_approval=True,
            ),
        ],
        current_step_id=None,
    )
    llm = FakeLLMPort(result=plan)
    prompts = FakePromptRepository(resolved=_resolved())
    operation = _operation(llm=llm, prompts=prompts)

    outcome = await operation.execute(
        ticket=_ticket(),
        shield_result=_shield(),
        triage_result=_triage(),
    )

    assert outcome.agent_state.current_step_id == "first"


@pytest.mark.asyncio
async def test_planner_empty_plan_uses_safe_fallback() -> None:
    llm = FakeLLMPort(result=SupportAgentState(plan=[], current_step_id=None))
    prompts = FakePromptRepository(resolved=_resolved())
    operation = _operation(llm=llm, prompts=prompts)

    outcome = await operation.execute(
        ticket=_ticket(),
        shield_result=_shield(),
        triage_result=_triage(),
    )

    assert outcome.fallback_used is True
    assert outcome.execution is None
    assert outcome.error_type == "ModelOutputParsingError"
    assert outcome.prompt_identity == _EXPECTED_IDENTITY
    assert [step.owner for step in outcome.agent_state.plan] == [
        "response_agent",
        "human",
    ]
    assert "retrieval_agent" not in [step.owner for step in outcome.agent_state.plan]


@pytest.mark.asyncio
async def test_planner_prompt_not_found_propagates_without_fallback() -> None:
    llm = FakeLLMPort(result=SupportAgentState(plan=[], current_step_id=None))
    prompts = FakePromptRepository(error=PromptNotFoundError("missing planner"))
    operation = _operation(llm=llm, prompts=prompts)

    with pytest.raises(PromptNotFoundError, match="missing planner"):
        await operation.execute(
            ticket=_ticket(),
            shield_result=_shield(),
            triage_result=_triage(),
        )
    assert llm.call_count == 0


@pytest.mark.asyncio
async def test_planner_prompt_render_error_propagates_without_fallback() -> None:
    llm = FakeLLMPort(result=SupportAgentState(plan=[], current_step_id=None))
    prompts = FakePromptRepository(error=PromptRenderError("bad planner vars"))
    operation = _operation(llm=llm, prompts=prompts)

    with pytest.raises(PromptRenderError, match="bad planner vars"):
        await operation.execute(
            ticket=_ticket(),
            shield_result=_shield(),
            triage_result=_triage(),
        )
    assert llm.call_count == 0


@pytest.mark.asyncio
async def test_planner_parsing_failure_uses_safe_fallback() -> None:
    llm = FakeLLMPort(error=ModelOutputParsingError("planner parse failed"))
    prompts = FakePromptRepository(resolved=_resolved())
    operation = _operation(llm=llm, prompts=prompts)

    outcome = await operation.execute(
        ticket=_ticket(),
        shield_result=_shield(),
        triage_result=_triage(),
    )

    assert outcome.fallback_used is True
    assert outcome.error_type == "ModelOutputParsingError"
    assert outcome.error_message == "planner parse failed"
    assert outcome.prompt_identity == _EXPECTED_IDENTITY
    assert outcome.agent_state.plan[0].owner == "response_agent"
    assert outcome.agent_state.plan[1].owner == "human"
    assert outcome.agent_state.plan[1].requires_human_approval is True


@pytest.mark.asyncio
async def test_planner_upstream_failure_uses_safe_fallback() -> None:
    llm = FakeLLMPort(error=UpstreamServiceError("planner upstream failed"))
    prompts = FakePromptRepository(resolved=_resolved())
    operation = _operation(llm=llm, prompts=prompts)

    outcome = await operation.execute(
        ticket=_ticket(),
        shield_result=_shield(),
        triage_result=_triage(),
    )

    assert outcome.fallback_used is True
    assert outcome.error_type == "UpstreamServiceError"
    assert outcome.prompt_identity == _EXPECTED_IDENTITY


@pytest.mark.asyncio
async def test_planner_unexpected_exception_uses_safe_fallback() -> None:
    llm = FakeLLMPort(error=RuntimeError("unexpected boom"))
    prompts = FakePromptRepository(resolved=_resolved())
    operation = _operation(llm=llm, prompts=prompts)

    outcome = await operation.execute(
        ticket=_ticket(),
        shield_result=_shield(),
        triage_result=_triage(),
    )

    assert outcome.fallback_used is True
    assert outcome.error_type == "RuntimeError"
    assert outcome.error_message == "unexpected boom"
    assert outcome.prompt_identity == _EXPECTED_IDENTITY
    assert [step.owner for step in outcome.agent_state.plan] == [
        "response_agent",
        "human",
    ]
    assert "retrieval_agent" not in {step.owner for step in outcome.agent_state.plan}
