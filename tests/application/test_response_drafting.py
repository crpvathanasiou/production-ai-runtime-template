import pytest

from app.application.ports.llm import LLMExecutionMetadata, StructuredLLMResult
from app.application.response_drafting import ResponseDraftingOperation
from app.core.exceptions import ModelOutputParsingError, UpstreamServiceError
from app.prompts.response_drafting_prompts import (
    build_response_drafting_system_prompt,
    build_response_drafting_user_prompt,
)
from app.schemas import ResponseDrafting, RetrievedDocument, SupportTicket, TriageOutput
from tests.application.fakes import FakeLLMPort


def _ticket() -> SupportTicket:
    return SupportTicket(
        customer_message="I was charged twice for my order and need a refund.",
        customer_metadata={"customer_id": "cust_123"},
        order_account_metadata={"order_id": "ord_456"},
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


def _draft() -> ResponseDrafting:
    return ResponseDrafting(
        ticket_response="We are reviewing your billing concern.",
        related_documents=[],
        unsupported_promises=False,
    )


@pytest.mark.asyncio
async def test_response_drafting_with_no_retrieved_documents() -> None:
    ticket = _ticket()
    triage = _triage()
    draft = _draft()
    llm = FakeLLMPort(result=draft, latency_ms=5.0, attempts=1)
    operation = ResponseDraftingOperation(llm=llm)

    result = await operation.execute(
        ticket=ticket,
        triage_result=triage,
        retrieved_documents=[],
    )

    typed: StructuredLLMResult[ResponseDrafting] = result
    assert typed.parsed == draft
    assert typed.execution == LLMExecutionMetadata(latency_ms=5.0, attempts=1)
    assert llm.call_count == 1
    call = llm.calls[0]
    assert call["system_prompt"] == build_response_drafting_system_prompt()
    assert call["prompt"] == build_response_drafting_user_prompt(
        ticket=ticket,
        triage_result=triage,
        retrieved_documents=[],
    )
    assert "No retrieved documents available." in call["prompt"]
    assert call["response_schema"] is ResponseDrafting


@pytest.mark.asyncio
async def test_response_drafting_with_retrieved_documents() -> None:
    ticket = _ticket()
    triage = _triage()
    documents = [
        RetrievedDocument(source="billing_policy.md", content="Double charges are reviewed."),
        RetrievedDocument(source="refund_policy.md", content="Refunds require verification."),
    ]
    draft = ResponseDrafting(
        ticket_response="Based on policy, we will review the double charge.",
        related_documents=documents,
        unsupported_promises=False,
    )
    llm = FakeLLMPort(result=draft)
    operation = ResponseDraftingOperation(llm=llm)

    result = await operation.execute(
        ticket=ticket,
        triage_result=triage,
        retrieved_documents=documents,
    )

    assert result.parsed == draft
    call = llm.calls[0]
    assert call["prompt"] == build_response_drafting_user_prompt(
        ticket=ticket,
        triage_result=triage,
        retrieved_documents=documents,
    )
    assert "[Source: billing_policy.md]" in call["prompt"]
    assert "Double charges are reviewed." in call["prompt"]
    assert "[Source: refund_policy.md]" in call["prompt"]
    assert call["response_schema"] is ResponseDrafting


@pytest.mark.asyncio
async def test_response_drafting_parsing_failure_propagates() -> None:
    llm = FakeLLMPort(error=ModelOutputParsingError("draft parse failed"))
    operation = ResponseDraftingOperation(llm=llm)

    with pytest.raises(ModelOutputParsingError, match="draft parse failed"):
        await operation.execute(
            ticket=_ticket(),
            triage_result=_triage(),
            retrieved_documents=[],
        )


@pytest.mark.asyncio
async def test_response_drafting_upstream_failure_propagates() -> None:
    llm = FakeLLMPort(error=UpstreamServiceError("draft upstream failed"))
    operation = ResponseDraftingOperation(llm=llm)

    with pytest.raises(UpstreamServiceError, match="draft upstream failed"):
        await operation.execute(
            ticket=_ticket(),
            triage_result=_triage(),
            retrieved_documents=[],
        )
