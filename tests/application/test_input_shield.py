import pytest

from app.application.input_shield import InputShieldOperation
from app.application.ports.llm import LLMExecutionMetadata
from app.application.prompts import (
    PromptIdentity,
    PromptNotFoundError,
    PromptRef,
    PromptRenderError,
    ResolvedPrompt,
)
from app.core.exceptions import ModelOutputParsingError, UpstreamServiceError
from app.schemas import ShieldOutput, SupportTicket
from tests.application.fakes import FakeLLMPort, FakePromptRepository

_PROMPT_REF = PromptRef(prompt_id="input-shield", revision=1)


def _ticket(message: str = "I was charged twice for my order and need a refund.") -> SupportTicket:
    return SupportTicket(
        customer_message=message,
        customer_metadata={"customer_id": "cust_123"},
        order_account_metadata={"order_id": "ord_456"},
    )


def _resolved_for(ticket: SupportTicket) -> ResolvedPrompt:
    system_prompt = "input-shield-system"
    user_prompt = (
        f"Customer message:\n{ticket.customer_message}\n"
        f"Customer metadata:\n{ticket.customer_metadata or {}}\n"
        f"Order/account metadata:\n{ticket.order_account_metadata or {}}"
    )
    return ResolvedPrompt(
        ref=_PROMPT_REF,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        content_hash="input-shield-hash",
    )


def _logical_prompt(system_prompt: str, user_prompt: str) -> str:
    if system_prompt and system_prompt.strip():
        return f"[SYSTEM]\n{system_prompt}\n\n[USER]\n{user_prompt}"
    return user_prompt


def _operation(
    *,
    llm: FakeLLMPort,
    prompts: FakePromptRepository,
    max_prompt_chars: int = 12000,
) -> InputShieldOperation:
    return InputShieldOperation(
        llm=llm,
        prompt_repository=prompts,
        prompt_ref=_PROMPT_REF,
        max_prompt_chars=max_prompt_chars,
    )


@pytest.mark.asyncio
async def test_input_shield_fail_fast_skips_llm_and_prompt_repository() -> None:
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
    prompts = FakePromptRepository(resolved=_resolved_for(_ticket()))
    operation = _operation(llm=llm, prompts=prompts)

    outcome = await operation.execute(_ticket("issue"))

    assert outcome.source == "heuristic_fail_fast"
    assert outcome.output.decision == "needs_clarification"
    assert outcome.output.categories == ["non_actionable"]
    assert outcome.execution is None
    assert outcome.error_type is None
    assert outcome.prompt_identity is None
    assert llm.call_count == 0
    assert prompts.call_count == 0


@pytest.mark.asyncio
async def test_input_shield_llm_path_uses_resolved_prompt_and_propagates_execution() -> None:
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
    ticket = _ticket()
    resolved = _resolved_for(ticket)
    prompts = FakePromptRepository(resolved=resolved)
    operation = _operation(llm=llm, prompts=prompts)

    outcome = await operation.execute(ticket)

    assert outcome.source == "llm"
    assert outcome.output.decision == "allow"
    assert outcome.execution == LLMExecutionMetadata(latency_ms=12.5, attempts=2)
    assert outcome.prompt_identity == PromptIdentity(
        ref=_PROMPT_REF,
        content_hash="input-shield-hash",
    )
    assert prompts.call_count == 1
    assert prompts.calls[0]["ref"] == _PROMPT_REF
    assert prompts.calls[0]["variables"] == {
        "customer_message": ticket.customer_message,
        "customer_metadata": {"customer_id": "cust_123"},
        "order_account_metadata": {"order_id": "ord_456"},
    }
    assert llm.call_count == 1
    call = llm.calls[0]
    assert call["system_prompt"] == resolved.system_prompt
    assert call["prompt"] == resolved.user_prompt
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
    ticket = _ticket("I need help with my billing charge today.")
    prompts = FakePromptRepository(resolved=_resolved_for(ticket))
    operation = _operation(llm=llm, prompts=prompts)

    outcome = await operation.execute(ticket)

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
    ticket = _ticket("I need help with my billing charge today.")
    prompts = FakePromptRepository(resolved=_resolved_for(ticket))
    operation = _operation(llm=llm, prompts=prompts)

    outcome = await operation.execute(ticket)

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
    ticket = _ticket("I need help with my billing charge today.")
    prompts = FakePromptRepository(resolved=_resolved_for(ticket))
    operation = _operation(llm=llm, prompts=prompts)

    outcome = await operation.execute(ticket)

    assert outcome.output.decision == "needs_clarification"


@pytest.mark.asyncio
async def test_input_shield_max_prompt_boundary_allows_equal_length() -> None:
    ticket = _ticket()
    resolved = _resolved_for(ticket)
    logical = _logical_prompt(resolved.system_prompt or "", resolved.user_prompt)
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
    prompts = FakePromptRepository(resolved=resolved)
    operation = _operation(llm=llm, prompts=prompts, max_prompt_chars=len(logical))

    outcome = await operation.execute(ticket)

    assert outcome.source == "llm"
    assert llm.call_count == 1
    assert prompts.call_count == 1


@pytest.mark.asyncio
async def test_input_shield_max_prompt_boundary_blocks_when_over_limit() -> None:
    ticket = _ticket()
    resolved = _resolved_for(ticket)
    logical = _logical_prompt(resolved.system_prompt or "", resolved.user_prompt)
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
    prompts = FakePromptRepository(resolved=resolved)
    operation = _operation(llm=llm, prompts=prompts, max_prompt_chars=max_chars)

    outcome = await operation.execute(ticket)

    assert outcome.source == "prompt_length_block"
    assert outcome.execution is None
    assert outcome.error_type == "GuardrailBlockedError"
    assert outcome.prompt_identity == PromptIdentity(
        ref=_PROMPT_REF,
        content_hash="input-shield-hash",
    )
    assert outcome.output.decision == "block"
    assert outcome.output.risk_level == "high"
    assert outcome.output.categories == ["suspicious_input"]
    assert outcome.output.should_route_to_human is True
    assert f"({max_chars} chars)" in (outcome.error_message or "")
    assert "max_prompt_length" in (outcome.error_message or "")
    assert llm.call_count == 0
    assert prompts.call_count == 1


@pytest.mark.asyncio
async def test_input_shield_prompt_not_found_propagates() -> None:
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
    prompts = FakePromptRepository(error=PromptNotFoundError("missing"))
    operation = _operation(llm=llm, prompts=prompts)

    with pytest.raises(PromptNotFoundError, match="missing"):
        await operation.execute(_ticket())
    assert llm.call_count == 0


@pytest.mark.asyncio
async def test_input_shield_prompt_render_error_propagates() -> None:
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
    prompts = FakePromptRepository(error=PromptRenderError("bad vars"))
    operation = _operation(llm=llm, prompts=prompts)

    with pytest.raises(PromptRenderError, match="bad vars"):
        await operation.execute(_ticket())
    assert llm.call_count == 0


@pytest.mark.asyncio
async def test_input_shield_parsing_failure_fallback() -> None:
    llm = FakeLLMPort(error=ModelOutputParsingError("bad parse"))
    ticket = _ticket()
    prompts = FakePromptRepository(resolved=_resolved_for(ticket))
    operation = _operation(llm=llm, prompts=prompts)

    outcome = await operation.execute(ticket)

    assert outcome.source == "llm_failure_fallback"
    assert outcome.output.decision == "allow_with_flag"
    assert outcome.output.risk_level == "medium"
    assert outcome.output.should_route_to_human is True
    assert outcome.error_type == "ModelOutputParsingError"
    assert outcome.error_message == "bad parse"
    assert outcome.execution is None
    assert outcome.prompt_identity == PromptIdentity(
        ref=_PROMPT_REF,
        content_hash="input-shield-hash",
    )


@pytest.mark.asyncio
async def test_input_shield_upstream_failure_fallback() -> None:
    llm = FakeLLMPort(error=UpstreamServiceError("upstream down"))
    ticket = _ticket()
    prompts = FakePromptRepository(resolved=_resolved_for(ticket))
    operation = _operation(llm=llm, prompts=prompts)

    outcome = await operation.execute(ticket)

    assert outcome.source == "llm_failure_fallback"
    assert outcome.output.decision == "allow_with_flag"
    assert outcome.error_type == "UpstreamServiceError"
    assert outcome.error_message == "upstream down"
    assert outcome.prompt_identity == PromptIdentity(
        ref=_PROMPT_REF,
        content_hash="input-shield-hash",
    )


@pytest.mark.asyncio
async def test_input_shield_unexpected_exception_propagates() -> None:
    llm = FakeLLMPort(error=RuntimeError("boom"))
    ticket = _ticket()
    prompts = FakePromptRepository(resolved=_resolved_for(ticket))
    operation = _operation(llm=llm, prompts=prompts)

    with pytest.raises(RuntimeError, match="boom"):
        await operation.execute(ticket)
