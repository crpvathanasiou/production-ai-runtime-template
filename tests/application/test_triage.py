import pytest

from app.application.ports.llm import LLMExecutionMetadata, StructuredLLMResult
from app.application.triage import TriageOperation
from app.core.exceptions import ModelOutputParsingError, UpstreamServiceError
from app.prompts.triage_prompts import (
    build_triage_system_prompt,
    build_triage_user_prompt,
)
from app.schemas import ShieldOutput, SupportTicket, TriageOutput
from tests.application.fakes import FakeLLMPort


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


@pytest.mark.asyncio
async def test_triage_success_uses_prompt_builders_and_schema() -> None:
    ticket = _ticket()
    shield = _shield()
    triage = _triage()
    llm = FakeLLMPort(result=triage, latency_ms=8.0, attempts=1)
    operation = TriageOperation(llm=llm)

    result = await operation.execute(ticket=ticket, shield_result=shield)

    typed: StructuredLLMResult[TriageOutput] = result
    assert typed.parsed == triage
    assert typed.execution == LLMExecutionMetadata(latency_ms=8.0, attempts=1)
    assert llm.call_count == 1
    call = llm.calls[0]
    assert call["system_prompt"] == build_triage_system_prompt()
    assert call["prompt"] == build_triage_user_prompt(ticket=ticket, shield_result=shield)
    assert call["response_schema"] is TriageOutput


@pytest.mark.asyncio
async def test_triage_parsing_failure_propagates() -> None:
    llm = FakeLLMPort(error=ModelOutputParsingError("triage parse failed"))
    operation = TriageOperation(llm=llm)

    with pytest.raises(ModelOutputParsingError, match="triage parse failed"):
        await operation.execute(ticket=_ticket(), shield_result=_shield())


@pytest.mark.asyncio
async def test_triage_upstream_failure_propagates() -> None:
    llm = FakeLLMPort(error=UpstreamServiceError("triage upstream failed"))
    operation = TriageOperation(llm=llm)

    with pytest.raises(UpstreamServiceError, match="triage upstream failed"):
        await operation.execute(ticket=_ticket(), shield_result=_shield())
