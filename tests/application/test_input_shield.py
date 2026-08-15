import pytest

from app.application.input_shield import InputShieldOperation
from app.application.ports.llm import LLMExecutionMetadata
from app.core.exceptions import ModelOutputParsingError, UpstreamServiceError
from app.prompts.input_shield_prompts import (
    build_input_shield_system_prompt,
    build_input_shield_user_prompt,
)
from app.schemas import ShieldOutput, SupportTicket
from tests.application.fakes import FakeLLMPort


def _ticket(message: str = "I was charged twice for my order and need a refund.") -> SupportTicket:
    return SupportTicket(
        customer_message=message,
        customer_metadata={"customer_id": "cust_123"},
        order_account_metadata={"order_id": "ord_456"},
    )


def _logical_prompt(system_prompt: str, user_prompt: str) -> str:
    if system_prompt and system_prompt.strip():
        return f"[SYSTEM]\n{system_prompt}\n\n[USER]\n{user_prompt}"
    return user_prompt


@pytest.mark.asyncio
async def test_input_shield_fail_fast_skips_llm() -> None:
    llm = FakeLLMPort(
        result=ShieldOutput(
            decision="allow",
            risk_level="low",
            categories=["valid_support_request"],
            sanitized_message="unused",
            should_route_to_human=False,
            clarification_question=None,
            reasoning="unused",
        )
    )
    operation = InputShieldOperation(llm=llm, max_prompt_chars=12000)

    outcome = await operation.execute(_ticket("issue"))

    assert outcome.source == "heuristic_fail_fast"
    assert outcome.output.decision == "needs_clarification"
    assert outcome.output.categories == ["non_actionable"]
    assert outcome.execution is None
    assert outcome.error_type is None
    assert llm.call_count == 0


@pytest.mark.asyncio
async def test_input_shield_llm_path_uses_prompt_builders_and_propagates_execution() -> None:
    llm_output = ShieldOutput(
        decision="allow",
        risk_level="low",
        categories=["valid_support_request"],
        sanitized_message="I was charged twice for my order and need a refund.",
        should_route_to_human=False,
        clarification_question=None,
        reasoning="Valid support request.",
    )
    llm = FakeLLMPort(
        result=llm_output,
        latency_ms=12.5,
        attempts=2,
    )
    operation = InputShieldOperation(llm=llm, max_prompt_chars=12000)
    ticket = _ticket()

    outcome = await operation.execute(ticket)

    assert outcome.source == "llm"
    assert outcome.output.decision == "allow"
    assert outcome.execution == LLMExecutionMetadata(latency_ms=12.5, attempts=2)
    assert llm.call_count == 1
    call = llm.calls[0]
    assert call["system_prompt"] == build_input_shield_system_prompt()
    assert call["prompt"] == build_input_shield_user_prompt(ticket)
    assert call["response_schema"] is ShieldOutput


@pytest.mark.asyncio
async def test_input_shield_privacy_risk_normalization() -> None:
    llm = FakeLLMPort(
        result=ShieldOutput(
            decision="allow",
            risk_level="low",
            categories=["privacy_risk"],
            sanitized_message="I need help with my billing charge today.",
            should_route_to_human=False,
            clarification_question=None,
            reasoning="LLM under-classified privacy risk.",
        )
    )
    operation = InputShieldOperation(llm=llm, max_prompt_chars=12000)

    outcome = await operation.execute(_ticket("I need help with my billing charge today."))

    assert outcome.source == "llm"
    assert outcome.output.decision == "block"
    assert outcome.output.risk_level == "high"
    assert outcome.output.should_route_to_human is True


@pytest.mark.asyncio
async def test_input_shield_prompt_injection_normalization() -> None:
    llm = FakeLLMPort(
        result=ShieldOutput(
            decision="allow",
            risk_level="low",
            categories=["prompt_injection"],
            sanitized_message="I need help with my billing charge today.",
            should_route_to_human=False,
            clarification_question=None,
            reasoning="LLM under-classified injection.",
        )
    )
    operation = InputShieldOperation(llm=llm, max_prompt_chars=12000)

    outcome = await operation.execute(_ticket("I need help with my billing charge today."))

    assert outcome.output.decision == "allow_with_flag"
    assert outcome.output.risk_level == "high"


@pytest.mark.asyncio
async def test_input_shield_non_actionable_normalization() -> None:
    llm = FakeLLMPort(
        result=ShieldOutput(
            decision="allow",
            risk_level="low",
            categories=["non_actionable"],
            sanitized_message="I need help with my billing charge today.",
            should_route_to_human=False,
            clarification_question=None,
            reasoning="LLM under-classified non-actionable.",
        )
    )
    operation = InputShieldOperation(llm=llm, max_prompt_chars=12000)

    outcome = await operation.execute(_ticket("I need help with my billing charge today."))

    assert outcome.output.decision == "needs_clarification"


@pytest.mark.asyncio
async def test_input_shield_max_prompt_boundary_allows_equal_length() -> None:
    ticket = _ticket()
    system_prompt = build_input_shield_system_prompt()
    user_prompt = build_input_shield_user_prompt(ticket)
    logical = _logical_prompt(system_prompt, user_prompt)
    llm = FakeLLMPort(
        result=ShieldOutput(
            decision="allow",
            risk_level="low",
            categories=["valid_support_request"],
            sanitized_message=ticket.customer_message,
            should_route_to_human=False,
            clarification_question=None,
            reasoning="ok",
        )
    )
    operation = InputShieldOperation(llm=llm, max_prompt_chars=len(logical))

    outcome = await operation.execute(ticket)

    assert outcome.source == "llm"
    assert llm.call_count == 1


@pytest.mark.asyncio
async def test_input_shield_max_prompt_boundary_blocks_when_over_limit() -> None:
    ticket = _ticket()
    system_prompt = build_input_shield_system_prompt()
    user_prompt = build_input_shield_user_prompt(ticket)
    logical = _logical_prompt(system_prompt, user_prompt)
    llm = FakeLLMPort(
        result=ShieldOutput(
            decision="allow",
            risk_level="low",
            categories=["valid_support_request"],
            sanitized_message=ticket.customer_message,
            should_route_to_human=False,
            clarification_question=None,
            reasoning="ok",
        )
    )
    max_chars = len(logical) - 1
    operation = InputShieldOperation(llm=llm, max_prompt_chars=max_chars)

    outcome = await operation.execute(ticket)

    assert outcome.source == "prompt_length_block"
    assert outcome.execution is None
    assert outcome.error_type == "GuardrailBlockedError"
    assert outcome.output.decision == "block"
    assert outcome.output.risk_level == "high"
    assert outcome.output.categories == ["suspicious_input"]
    assert outcome.output.should_route_to_human is True
    assert f"({max_chars} chars)" in (outcome.error_message or "")
    assert "max_prompt_length" in (outcome.error_message or "")
    assert llm.call_count == 0


@pytest.mark.asyncio
async def test_input_shield_parsing_failure_fallback() -> None:
    llm = FakeLLMPort(error=ModelOutputParsingError("bad parse"))
    operation = InputShieldOperation(llm=llm, max_prompt_chars=12000)

    outcome = await operation.execute(_ticket())

    assert outcome.source == "llm_failure_fallback"
    assert outcome.output.decision == "allow_with_flag"
    assert outcome.output.risk_level == "medium"
    assert outcome.output.should_route_to_human is True
    assert outcome.error_type == "ModelOutputParsingError"
    assert outcome.error_message == "bad parse"
    assert outcome.execution is None


@pytest.mark.asyncio
async def test_input_shield_upstream_failure_fallback() -> None:
    llm = FakeLLMPort(error=UpstreamServiceError("upstream down"))
    operation = InputShieldOperation(llm=llm, max_prompt_chars=12000)

    outcome = await operation.execute(_ticket())

    assert outcome.source == "llm_failure_fallback"
    assert outcome.output.decision == "allow_with_flag"
    assert outcome.error_type == "UpstreamServiceError"
    assert outcome.error_message == "upstream down"


@pytest.mark.asyncio
async def test_input_shield_unexpected_exception_propagates() -> None:
    llm = FakeLLMPort(error=RuntimeError("boom"))
    operation = InputShieldOperation(llm=llm, max_prompt_chars=12000)

    with pytest.raises(RuntimeError, match="boom"):
        await operation.execute(_ticket())
