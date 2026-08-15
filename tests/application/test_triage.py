import pytest

from app.application.ports.llm import LLMExecutionMetadata
from app.application.prompts import (
    PromptIdentity,
    PromptNotFoundError,
    PromptRef,
    PromptRenderError,
    ResolvedPrompt,
)
from app.application.triage import TriageOperation, TriageOutcome
from app.core.exceptions import ModelOutputParsingError, UpstreamServiceError
from app.schemas import ShieldOutput, SupportTicket, TriageOutput
from tests.application.fakes import FakeLLMPort, FakePromptRepository

_PROMPT_REF = PromptRef(prompt_id="triage", revision=1)
_EXPECTED_IDENTITY = PromptIdentity(ref=_PROMPT_REF, content_hash="triage-hash")


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
        system_prompt="triage-system",
        user_prompt="triage-user",
        content_hash="triage-hash",
    )


def _operation(*, llm: FakeLLMPort, prompts: FakePromptRepository) -> TriageOperation:
    return TriageOperation(
        llm=llm,
        prompt_repository=prompts,
        prompt_ref=_PROMPT_REF,
    )


@pytest.mark.asyncio
async def test_triage_success_uses_resolved_prompt_and_schema() -> None:
    ticket = _ticket()
    shield = _shield()
    triage = _triage()
    llm = FakeLLMPort(result=triage, latency_ms=8.0, attempts=1)
    resolved = _resolved()
    prompts = FakePromptRepository(resolved=resolved)
    operation = _operation(llm=llm, prompts=prompts)

    outcome = await operation.execute(ticket=ticket, shield_result=shield)

    typed: TriageOutcome = outcome
    assert typed.output == triage
    assert typed.execution == LLMExecutionMetadata(latency_ms=8.0, attempts=1)
    assert typed.prompt_identity == _EXPECTED_IDENTITY
    assert prompts.call_count == 1
    assert prompts.calls[0]["ref"] == _PROMPT_REF
    assert prompts.calls[0]["variables"] == {
        "sanitized_message": shield.sanitized_message,
        "shield_decision": shield.decision,
        "shield_risk_level": shield.risk_level,
        "shield_categories": shield.categories,
        "shield_should_route_to_human": shield.should_route_to_human,
        "customer_metadata": {"customer_id": "cust_123"},
        "order_account_metadata": {"order_id": "ord_456"},
    }
    assert llm.call_count == 1
    call = llm.calls[0]
    assert call["system_prompt"] == resolved.system_prompt
    assert call["prompt"] == resolved.user_prompt
    assert call["response_schema"] is TriageOutput


@pytest.mark.asyncio
async def test_triage_direct_caller_receives_prompt_identity() -> None:
    """Direct Application Operation callers get identity without LangGraph."""
    llm = FakeLLMPort(result=_triage(), latency_ms=2.0, attempts=1)
    prompts = FakePromptRepository(resolved=_resolved())
    operation = _operation(llm=llm, prompts=prompts)

    outcome = await operation.execute(ticket=_ticket(), shield_result=_shield())

    assert isinstance(outcome, TriageOutcome)
    assert outcome.prompt_identity == _EXPECTED_IDENTITY
    assert outcome.prompt_identity.ref.prompt_id == "triage"
    assert outcome.prompt_identity.ref.revision == 1
    assert outcome.prompt_identity.content_hash == "triage-hash"


@pytest.mark.asyncio
async def test_triage_prompt_not_found_propagates() -> None:
    llm = FakeLLMPort(result=_triage())
    prompts = FakePromptRepository(error=PromptNotFoundError("missing triage"))
    operation = _operation(llm=llm, prompts=prompts)

    with pytest.raises(PromptNotFoundError, match="missing triage"):
        await operation.execute(ticket=_ticket(), shield_result=_shield())
    assert llm.call_count == 0


@pytest.mark.asyncio
async def test_triage_prompt_render_error_propagates() -> None:
    llm = FakeLLMPort(result=_triage())
    prompts = FakePromptRepository(error=PromptRenderError("bad triage vars"))
    operation = _operation(llm=llm, prompts=prompts)

    with pytest.raises(PromptRenderError, match="bad triage vars"):
        await operation.execute(ticket=_ticket(), shield_result=_shield())
    assert llm.call_count == 0


@pytest.mark.asyncio
async def test_triage_parsing_failure_propagates() -> None:
    llm = FakeLLMPort(error=ModelOutputParsingError("triage parse failed"))
    prompts = FakePromptRepository(resolved=_resolved())
    operation = _operation(llm=llm, prompts=prompts)

    with pytest.raises(ModelOutputParsingError, match="triage parse failed"):
        await operation.execute(ticket=_ticket(), shield_result=_shield())


@pytest.mark.asyncio
async def test_triage_upstream_failure_propagates() -> None:
    llm = FakeLLMPort(error=UpstreamServiceError("triage upstream failed"))
    prompts = FakePromptRepository(resolved=_resolved())
    operation = _operation(llm=llm, prompts=prompts)

    with pytest.raises(UpstreamServiceError, match="triage upstream failed"):
        await operation.execute(ticket=_ticket(), shield_result=_shield())
