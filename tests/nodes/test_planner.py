"""Planner node adapter tests — fake Application Operations only."""

from __future__ import annotations

import inspect
import logging

import pytest

import app.nodes.planner as planner_module
from app.application.execution import ExecutionContext
from app.application.planner import PlannerOutcome
from app.application.ports.llm import LLMExecutionMetadata
from app.application.prompts import PromptIdentity, PromptRef
from app.graph_state import GraphState
from app.nodes.planner import make_planner_node
from app.schemas import (
    PlanStep,
    ShieldOutput,
    SupportAgentState,
    SupportTicket,
    TriageOutput,
)
from tests.test_logging import assert_visible_correlation

_PROMPT_IDENTITY = PromptIdentity(
    ref=PromptRef(prompt_id="planner", revision=1),
    content_hash="planner-hash",
)


class FakePlannerOperation:
    def __init__(self, outcome: PlannerOutcome) -> None:
        self._outcome = outcome
        self.calls: list[dict] = []

    async def execute(
        self,
        *,
        context: ExecutionContext,
        ticket: SupportTicket,
        shield_result: ShieldOutput,
        triage_result: TriageOutput,
    ) -> PlannerOutcome:
        self.calls.append(
            {
                "context": context,
                "ticket": ticket,
                "shield_result": shield_result,
                "triage_result": triage_result,
            }
        )
        return self._outcome


def _ticket() -> SupportTicket:
    return SupportTicket(
        customer_message="Can you tell me how long shipping usually takes?",
        customer_metadata={},
        order_account_metadata={},
    )


def _shield() -> ShieldOutput:
    return ShieldOutput(
        decision="allow",
        risk_level="low",
        categories=["valid_support_request"],
        sanitized_message="Can you tell me how long shipping usually takes?",
        should_route_to_human=False,
        clarification_question=None,
        reasoning="Valid support request.",
    )


def _triage() -> TriageOutput:
    return TriageOutput(
        issue_category="other",
        intent="information_request",
        urgency="low",
        customer_tone="calm",
        requires_escalation=False,
        requires_human_approval=False,
        reasoning_summary="Customer is asking for general shipping information.",
    )


def _simple_plan() -> SupportAgentState:
    return SupportAgentState(
        plan=[
            PlanStep(
                step_id="step_draft_info_response",
                title="Draft informational response",
                description="Draft a cautious informational response.",
                owner="response_agent",
                status="pending",
            ),
        ],
        current_step_id="step_draft_info_response",
    )


def _fallback_plan() -> SupportAgentState:
    return SupportAgentState(
        plan=[
            PlanStep(
                step_id="step_draft_response",
                title="Draft cautious response",
                description="Draft a cautious customer response.",
                owner="response_agent",
                status="pending",
            ),
            PlanStep(
                step_id="step_human_review",
                title="Human review",
                description="Review before final response.",
                owner="human",
                status="pending",
                requires_human_approval=True,
            ),
        ],
        current_step_id="step_draft_response",
    )


def _outcome(
    *,
    agent_state: SupportAgentState,
    fallback_used: bool = False,
    execution: LLMExecutionMetadata | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
) -> PlannerOutcome:
    return PlannerOutcome(
        agent_state=agent_state,
        execution=execution,
        fallback_used=fallback_used,
        error_type=error_type,
        error_message=error_message,
        prompt_identity=_PROMPT_IDENTITY,
    )


@pytest.mark.asyncio
async def test_planner_node_missing_shield_blocked():
    operation = FakePlannerOperation(_outcome(agent_state=_simple_plan()))
    node = make_planner_node(operation, model_name="gpt-planner-test")
    state = GraphState(
        request_id="req-planner-001",
        run_id="run-planner-001",
        initial_ticket=_ticket(),
        triage_result=_triage(),
    )

    updated = await node(state)

    assert updated.workflow_outcome == "blocked"
    assert updated.additional_metadata["planner_error"]["error_type"] == "MissingShieldResult"
    assert len(operation.calls) == 0


@pytest.mark.asyncio
async def test_planner_node_missing_triage_blocked():
    operation = FakePlannerOperation(_outcome(agent_state=_simple_plan()))
    node = make_planner_node(operation, model_name="gpt-planner-test")
    state = GraphState(
        request_id="req-planner-002",
        run_id="run-planner-002",
        initial_ticket=_ticket(),
        shield_result=_shield(),
    )

    updated = await node(state)

    assert updated.workflow_outcome == "blocked"
    assert updated.additional_metadata["planner_error"]["error_type"] == "MissingTriageResult"
    assert len(operation.calls) == 0


@pytest.mark.asyncio
async def test_planner_node_normal_outcome_running():
    plan = _simple_plan()
    operation = FakePlannerOperation(
        _outcome(
            agent_state=plan,
            execution=LLMExecutionMetadata(latency_ms=55.0, attempts=1),
        )
    )
    node = make_planner_node(operation, model_name="gpt-planner-test")
    state = GraphState(
        request_id="req-planner-003",
        run_id="run-planner-003",
        initial_ticket=_ticket(),
        shield_result=_shield(),
        triage_result=_triage(),
    )

    updated = await node(state)

    assert updated.agent_state == plan
    assert updated.workflow_outcome == "running"
    meta = updated.additional_metadata["planner"]
    assert meta["model_name"] == "gpt-planner-test"
    assert meta["latency_ms"] == 55.0
    assert meta["attempts"] == 1
    assert meta["plan_length"] == 1
    assert meta["current_step_id"] == "step_draft_info_response"
    assert meta["step_titles"] == ["Draft informational response"]
    assert meta["prompt_id"] == "planner"
    assert meta["prompt_revision"] == 1
    assert meta["prompt_content_hash"] == "planner-hash"
    assert "system_prompt" not in meta
    assert "user_prompt" not in meta
    assert len(operation.calls) == 1
    assert operation.calls[0]["context"] == ExecutionContext(
        request_id="req-planner-003",
        run_id="run-planner-003",
        thread_id=None,
    )


@pytest.mark.asyncio
async def test_planner_node_can_carry_retrieval_capable_plan_shape():
    plan = SupportAgentState(
        plan=[
            PlanStep(
                step_id="step_retrieve_refund_policy",
                title="Retrieve refund policy",
                description="Retrieve refund policy.",
                owner="retrieval_agent",
                status="pending",
            ),
            PlanStep(
                step_id="step_draft_refund_response",
                title="Draft refund response",
                description="Draft refund response.",
                owner="response_agent",
                status="pending",
            ),
            PlanStep(
                step_id="step_human_review",
                title="Human review",
                description="Review refund case.",
                owner="human",
                status="pending",
                requires_human_approval=True,
            ),
        ],
        current_step_id="step_retrieve_refund_policy",
    )
    operation = FakePlannerOperation(
        _outcome(
            agent_state=plan,
            execution=LLMExecutionMetadata(latency_ms=10.0, attempts=1),
        )
    )
    node = make_planner_node(operation, model_name="gpt-planner-test")
    state = GraphState(
        request_id="req-planner-004",
        run_id="run-planner-004",
        initial_ticket=_ticket(),
        shield_result=_shield(),
        triage_result=_triage(),
    )

    updated = await node(state)

    assert updated.workflow_outcome == "running"
    owners = [step.owner for step in updated.agent_state.plan]  # type: ignore[union-attr]
    assert "retrieval_agent" in owners
    meta = updated.additional_metadata["planner"]
    assert meta["prompt_id"] == "planner"
    assert meta["prompt_revision"] == 1
    assert meta["prompt_content_hash"] == "planner-hash"


@pytest.mark.asyncio
async def test_planner_node_fallback_outcome_needs_human_review():
    operation = FakePlannerOperation(
        _outcome(
            agent_state=_fallback_plan(),
            fallback_used=True,
            error_type="UpstreamServiceError",
            error_message="Simulated planner failure",
        )
    )
    node = make_planner_node(operation, model_name="gpt-planner-test")
    state = GraphState(
        request_id="req-planner-005",
        run_id="run-planner-005",
        initial_ticket=_ticket(),
        shield_result=_shield(),
        triage_result=_triage(),
    )

    updated = await node(state)

    assert updated.workflow_outcome == "needs_human_review"
    assert updated.agent_state is not None
    assert len(updated.agent_state.plan) == 2
    owners = [step.owner for step in updated.agent_state.plan]
    assert "retrieval_agent" not in owners
    err = updated.additional_metadata["planner_error"]
    assert err["fallback_plan_used"] is True
    assert err["error_type"] == "UpstreamServiceError"
    assert err["message"] == "Simulated planner failure"
    assert "latency_ms" in err
    assert err["prompt_id"] == "planner"
    assert err["prompt_revision"] == 1
    assert err["prompt_content_hash"] == "planner-hash"
    assert "system_prompt" not in err
    assert "user_prompt" not in err


@pytest.mark.asyncio
async def test_planner_node_has_no_local_normalization_or_fallback():
    source = inspect.getsource(planner_module)
    assert "_normalize_planner_output" not in source
    assert "_build_fallback_plan" not in source
    assert "AsyncOpenAIWrapper" not in source


@pytest.mark.asyncio
async def test_planner_operational_logs_visible_correlation(caplog):
    operation = FakePlannerOperation(
        _outcome(
            agent_state=_simple_plan(),
            execution=LLMExecutionMetadata(latency_ms=5.0, attempts=1),
        )
    )
    node = make_planner_node(operation, model_name="gpt-planner-test")
    state = GraphState(
        request_id="req-planner-log-001",
        run_id="run-planner-log-001",
        thread_id="thread-planner-log-001",
        initial_ticket=_ticket(),
        shield_result=_shield(),
        triage_result=_triage(),
    )

    with caplog.at_level(logging.INFO, logger="app.nodes.planner"):
        updated = await node(state)

    assert updated.workflow_outcome == "running"
    messages = [record.getMessage() for record in caplog.records]
    completed = [m for m in messages if "planner.completed" in m]
    assert completed
    assert_visible_correlation(
        completed[0],
        request_id="req-planner-log-001",
        run_id="run-planner-log-001",
        node_name="planner",
        event="planner.completed",
        thread_id="thread-planner-log-001",
    )
