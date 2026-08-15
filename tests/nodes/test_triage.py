"""Triage node adapter tests — fake Application Operations only."""

from __future__ import annotations

import pytest

from app.application.ports.llm import LLMExecutionMetadata, StructuredLLMResult
from app.core.exceptions import ModelOutputParsingError, UpstreamServiceError
from app.graph_state import GraphState
from app.nodes.triage import make_triage_node
from app.schemas import ShieldOutput, SupportTicket, TriageOutput


class FakeTriageOperation:
    def __init__(
        self,
        *,
        result: StructuredLLMResult[TriageOutput] | None = None,
        error: Exception | None = None,
    ) -> None:
        self._result = result
        self._error = error
        self.calls: list[dict] = []

    async def execute(
        self,
        *,
        ticket: SupportTicket,
        shield_result: ShieldOutput,
    ) -> StructuredLLMResult[TriageOutput]:
        self.calls.append({"ticket": ticket, "shield_result": shield_result})
        if self._error is not None:
            raise self._error
        if self._result is None:
            raise AssertionError("FakeTriageOperation requires result or error")
        return self._result


def _ticket() -> SupportTicket:
    return SupportTicket(
        customer_message="I was charged twice and want a refund.",
        customer_metadata={},
        order_account_metadata={},
    )


def _allow_shield() -> ShieldOutput:
    return ShieldOutput(
        decision="allow",
        risk_level="low",
        categories=["valid_support_request"],
        sanitized_message="I was charged twice and want a refund.",
        should_route_to_human=False,
        clarification_question=None,
        reasoning="ok",
    )


def _triage(
    *,
    requires_escalation: bool = False,
    requires_human_approval: bool = False,
) -> TriageOutput:
    return TriageOutput(
        issue_category="refund",
        intent="complaint",
        urgency="medium",
        customer_tone="frustrated",
        requires_escalation=requires_escalation,
        requires_human_approval=requires_human_approval,
        reasoning_summary="Refund complaint.",
    )


@pytest.mark.asyncio
async def test_triage_node_missing_shield_blocked():
    operation = FakeTriageOperation(
        result=StructuredLLMResult(
            parsed=_triage(),
            execution=LLMExecutionMetadata(latency_ms=1.0, attempts=1),
        )
    )
    node = make_triage_node(operation, model_name="gpt-triage-test")
    state = GraphState(request_id="req-triage-001", initial_ticket=_ticket())

    updated = await node(state)

    assert updated.workflow_outcome == "blocked"
    assert updated.additional_metadata["triage_error"]["error_type"] == "MissingShieldResult"
    assert len(operation.calls) == 0


@pytest.mark.asyncio
async def test_triage_node_skipped_when_shield_blocked():
    operation = FakeTriageOperation(
        result=StructuredLLMResult(
            parsed=_triage(),
            execution=LLMExecutionMetadata(latency_ms=1.0, attempts=1),
        )
    )
    node = make_triage_node(operation, model_name="gpt-triage-test")
    state = GraphState(
        request_id="req-triage-002",
        initial_ticket=_ticket(),
        shield_result=ShieldOutput(
            decision="block",
            risk_level="high",
            categories=["prompt_injection"],
            sanitized_message="x",
            should_route_to_human=True,
            clarification_question=None,
            reasoning="blocked",
        ),
    )

    updated = await node(state)

    assert updated.workflow_outcome == "blocked"
    assert updated.additional_metadata["triage"]["skipped"] is True
    assert len(operation.calls) == 0


@pytest.mark.asyncio
async def test_triage_node_success_running():
    parsed = _triage()
    operation = FakeTriageOperation(
        result=StructuredLLMResult(
            parsed=parsed,
            execution=LLMExecutionMetadata(latency_ms=33.0, attempts=1),
        )
    )
    node = make_triage_node(operation, model_name="gpt-triage-test")
    state = GraphState(
        request_id="req-triage-003",
        initial_ticket=_ticket(),
        shield_result=_allow_shield(),
    )

    updated = await node(state)

    assert updated.triage_result == parsed
    assert updated.workflow_outcome == "running"
    meta = updated.additional_metadata["triage"]
    assert meta["model_name"] == "gpt-triage-test"
    assert meta["latency_ms"] == 33.0
    assert meta["attempts"] == 1
    assert meta["issue_category"] == "refund"
    assert meta["requires_escalation"] is False
    assert len(operation.calls) == 1


@pytest.mark.asyncio
async def test_triage_node_success_needs_human_review():
    parsed = _triage(requires_escalation=True)
    operation = FakeTriageOperation(
        result=StructuredLLMResult(
            parsed=parsed,
            execution=LLMExecutionMetadata(latency_ms=10.0, attempts=1),
        )
    )
    node = make_triage_node(operation, model_name="gpt-triage-test")
    state = GraphState(
        request_id="req-triage-004",
        initial_ticket=_ticket(),
        shield_result=_allow_shield(),
    )

    updated = await node(state)

    assert updated.workflow_outcome == "needs_human_review"
    assert updated.triage_result is not None
    assert updated.triage_result.requires_escalation is True


@pytest.mark.asyncio
async def test_triage_node_parsing_failure_needs_human_review():
    operation = FakeTriageOperation(error=ModelOutputParsingError("bad parse"))
    node = make_triage_node(operation, model_name="gpt-triage-test")
    state = GraphState(
        request_id="req-triage-005",
        initial_ticket=_ticket(),
        shield_result=_allow_shield(),
    )

    updated = await node(state)

    assert updated.workflow_outcome == "needs_human_review"
    err = updated.additional_metadata["triage_error"]
    assert err["error_type"] == "ModelOutputParsingError"
    assert err["message"] == "bad parse"
    assert "latency_ms" in err


@pytest.mark.asyncio
async def test_triage_node_upstream_failure_needs_human_review():
    operation = FakeTriageOperation(error=UpstreamServiceError("down"))
    node = make_triage_node(operation, model_name="gpt-triage-test")
    state = GraphState(
        request_id="req-triage-006",
        initial_ticket=_ticket(),
        shield_result=_allow_shield(),
    )

    updated = await node(state)

    assert updated.workflow_outcome == "needs_human_review"
    assert updated.additional_metadata["triage_error"]["error_type"] == "UpstreamServiceError"
