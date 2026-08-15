import inspect

import pytest

from app.application.execution import (
    ExecutionContext,
    LLMInvocationStarted,
    OperationFailed,
    OperationStarted,
)
from app.application.ports.llm import LLMExecutionMetadata
from app.application.prompts import (
    PromptIdentity,
    PromptNotFoundError,
    PromptRef,
    PromptRenderError,
    ResolvedPrompt,
)
from app.application.response_drafting import (
    ResponseDraftingOperation,
    ResponseDraftingOutcome,
)
from app.core.exceptions import ModelOutputParsingError, UpstreamServiceError
from app.schemas import ResponseDrafting, RetrievedDocument, SupportTicket, TriageOutput
from app.telemetry import NoOpTelemetry
from tests.application.fakes import FakeLLMPort, FakePromptRepository, RecordingTelemetry

_PROMPT_REF = PromptRef(prompt_id="response-drafting", revision=1)
_EXPECTED_IDENTITY = PromptIdentity(ref=_PROMPT_REF, content_hash="draft-hash")


def _context() -> ExecutionContext:
    return ExecutionContext(request_id="req-draft-app", run_id="run-draft-app")


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


def _resolved(*, user_prompt: str = "draft-user") -> ResolvedPrompt:
    return ResolvedPrompt(
        ref=_PROMPT_REF,
        system_prompt="draft-system",
        user_prompt=user_prompt,
        content_hash="draft-hash",
    )


def _operation(
    *,
    llm: FakeLLMPort,
    prompts: FakePromptRepository,
    telemetry: RecordingTelemetry | NoOpTelemetry | None = None,
) -> ResponseDraftingOperation:
    return ResponseDraftingOperation(
        llm=llm,
        prompt_repository=prompts,
        prompt_ref=_PROMPT_REF,
        telemetry=telemetry if telemetry is not None else NoOpTelemetry(),
    )


def test_response_drafting_requires_explicit_telemetry() -> None:
    params = inspect.signature(ResponseDraftingOperation.__init__).parameters
    assert "telemetry" in params
    assert params["telemetry"].default is inspect.Parameter.empty


@pytest.mark.asyncio
async def test_response_drafting_with_no_retrieved_documents() -> None:
    ticket = _ticket()
    triage = _triage()
    draft = _draft()
    llm = FakeLLMPort(result=draft, latency_ms=5.0, attempts=1)
    resolved = _resolved(user_prompt="no-docs-user")
    prompts = FakePromptRepository(resolved=resolved)
    operation = _operation(llm=llm, prompts=prompts)

    outcome = await operation.execute(
        context=_context(),
        ticket=ticket,
        triage_result=triage,
        retrieved_documents=[],
    )

    typed: ResponseDraftingOutcome = outcome
    assert typed.output == draft
    assert typed.execution == LLMExecutionMetadata(latency_ms=5.0, attempts=1)
    assert typed.prompt_identity == _EXPECTED_IDENTITY
    assert prompts.call_count == 1
    assert prompts.calls[0]["ref"] == _PROMPT_REF
    variables = prompts.calls[0]["variables"]
    assert variables["docs_text"] == "No retrieved documents available."
    assert variables["retrieval_mode"] == (
        "No retrieved documents are available for this run. "
        "Return related_documents as an empty list. "
        "Do not invent documents or claim corpus grounding. "
        "Draft a cautious response from ticket and triage context only."
    )
    assert variables["customer_message"] == ticket.customer_message
    assert variables["triage_issue_category"] == triage.issue_category
    assert variables["triage_intent"] == triage.intent
    assert variables["triage_urgency"] == triage.urgency
    assert variables["triage_customer_tone"] == triage.customer_tone
    assert variables["triage_requires_escalation"] == triage.requires_escalation
    assert variables["triage_requires_human_approval"] == triage.requires_human_approval
    assert variables["triage_reasoning_summary"] == triage.reasoning_summary
    assert llm.call_count == 1
    call = llm.calls[0]
    assert call["system_prompt"] == resolved.system_prompt
    assert call["prompt"] == resolved.user_prompt
    assert call["response_schema"] is ResponseDrafting


@pytest.mark.asyncio
async def test_response_drafting_direct_caller_receives_prompt_identity() -> None:
    """Direct Application Operation callers get identity without LangGraph."""
    llm = FakeLLMPort(result=_draft(), latency_ms=1.0, attempts=1)
    prompts = FakePromptRepository(resolved=_resolved())
    operation = _operation(llm=llm, prompts=prompts)

    outcome = await operation.execute(
        context=_context(),
        ticket=_ticket(),
        triage_result=_triage(),
        retrieved_documents=[],
    )

    assert isinstance(outcome, ResponseDraftingOutcome)
    assert outcome.prompt_identity == _EXPECTED_IDENTITY
    assert outcome.prompt_identity.ref.prompt_id == "response-drafting"
    assert outcome.prompt_identity.ref.revision == 1
    assert outcome.prompt_identity.content_hash == "draft-hash"


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
    resolved = _resolved(user_prompt="with-docs-user")
    prompts = FakePromptRepository(resolved=resolved)
    operation = _operation(llm=llm, prompts=prompts)

    outcome = await operation.execute(
        context=_context(),
        ticket=ticket,
        triage_result=triage,
        retrieved_documents=documents,
    )

    assert outcome.output == draft
    assert outcome.prompt_identity == _EXPECTED_IDENTITY
    variables = prompts.calls[0]["variables"]
    assert variables["docs_text"] == (
        "[Source: billing_policy.md]\nDouble charges are reviewed.\n\n"
        "[Source: refund_policy.md]\nRefunds require verification."
    )
    assert variables["retrieval_mode"] == (
        "Retrieved support context is available below. "
        "Use it for external/policy grounding. "
        "Populate related_documents only from these exact documents."
    )
    call = llm.calls[0]
    assert call["prompt"] == resolved.user_prompt
    assert call["response_schema"] is ResponseDrafting


@pytest.mark.asyncio
async def test_response_drafting_prompt_not_found_propagates() -> None:
    llm = FakeLLMPort(result=_draft())
    prompts = FakePromptRepository(error=PromptNotFoundError("missing draft"))
    operation = _operation(llm=llm, prompts=prompts)

    with pytest.raises(PromptNotFoundError, match="missing draft"):
        await operation.execute(
            context=_context(),
            ticket=_ticket(),
            triage_result=_triage(),
            retrieved_documents=[],
        )
    assert llm.call_count == 0


@pytest.mark.asyncio
async def test_response_drafting_prompt_render_error_propagates() -> None:
    llm = FakeLLMPort(result=_draft())
    prompts = FakePromptRepository(error=PromptRenderError("bad draft vars"))
    operation = _operation(llm=llm, prompts=prompts)

    with pytest.raises(PromptRenderError, match="bad draft vars"):
        await operation.execute(
            context=_context(),
            ticket=_ticket(),
            triage_result=_triage(),
            retrieved_documents=[],
        )
    assert llm.call_count == 0


@pytest.mark.asyncio
async def test_response_drafting_parsing_failure_propagates() -> None:
    llm = FakeLLMPort(error=ModelOutputParsingError("draft parse failed"))
    prompts = FakePromptRepository(resolved=_resolved())
    operation = _operation(llm=llm, prompts=prompts)

    with pytest.raises(ModelOutputParsingError, match="draft parse failed"):
        await operation.execute(
            context=_context(),
            ticket=_ticket(),
            triage_result=_triage(),
            retrieved_documents=[],
        )


@pytest.mark.asyncio
async def test_response_drafting_upstream_failure_propagates() -> None:
    llm = FakeLLMPort(error=UpstreamServiceError("draft upstream failed"))
    prompts = FakePromptRepository(resolved=_resolved())
    operation = _operation(llm=llm, prompts=prompts)

    with pytest.raises(UpstreamServiceError, match="draft upstream failed"):
        await operation.execute(
            context=_context(),
            ticket=_ticket(),
            triage_result=_triage(),
            retrieved_documents=[],
        )


@pytest.mark.asyncio
async def test_response_drafting_emits_prompt_identity_before_llm_failure() -> None:
    telemetry = RecordingTelemetry()
    llm = FakeLLMPort(error=ModelOutputParsingError("draft parse failed"))
    operation = _operation(
        llm=llm,
        prompts=FakePromptRepository(resolved=_resolved()),
        telemetry=telemetry,
    )

    with pytest.raises(ModelOutputParsingError):
        await operation.execute(
            context=_context(),
            ticket=_ticket(),
            triage_result=_triage(),
            retrieved_documents=[],
        )

    assert isinstance(telemetry.events[1], LLMInvocationStarted)
    assert telemetry.events[1].prompt_identity == _EXPECTED_IDENTITY
    assert isinstance(telemetry.events[-1], OperationFailed)
    assert telemetry.events[-1].error_category == "model_output"
    assert telemetry.events[-1].invocation_id == llm.calls[0]["invocation_id"]
    assert telemetry.events[-1].duration_ms >= 0


@pytest.mark.asyncio
async def test_response_drafting_unexpected_failure_emits_failed_with_invocation_id() -> None:
    telemetry = RecordingTelemetry()
    llm = FakeLLMPort(error=RuntimeError("draft boom"))
    operation = _operation(
        llm=llm,
        prompts=FakePromptRepository(resolved=_resolved()),
        telemetry=telemetry,
    )

    with pytest.raises(RuntimeError, match="draft boom"):
        await operation.execute(
            context=_context(),
            ticket=_ticket(),
            triage_result=_triage(),
            retrieved_documents=[],
        )

    assert [type(e) for e in telemetry.events] == [
        OperationStarted,
        LLMInvocationStarted,
        OperationFailed,
    ]
    invocation_started = telemetry.events[1]
    failed = telemetry.events[2]
    assert isinstance(invocation_started, LLMInvocationStarted)
    assert invocation_started.operation_name == "response_drafting"
    assert invocation_started.prompt_identity == _EXPECTED_IDENTITY
    assert isinstance(failed, OperationFailed)
    assert failed.operation_name == "response_drafting"
    assert failed.error_category == "unexpected"
    assert failed.error_type == "RuntimeError"
    assert failed.invocation_id == invocation_started.invocation_id
    assert failed.invocation_id == llm.calls[0]["invocation_id"]
    assert failed.duration_ms >= 0
    assert llm.call_count == 1
