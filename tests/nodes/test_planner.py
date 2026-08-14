import pytest

from app.graph_state import GraphState
from app.nodes.planner import planner_node
from app.schemas import (
    PlanStep,
    ShieldOutput,
    SupportAgentState,
    SupportTicket,
    TriageOutput,
)


class FakeLLMResult:
    def __init__(self, parsed, model_name="gpt-4.1-mini", latency_ms=120.5, attempts=1):
        self.parsed = parsed
        self.model_name = model_name
        self.latency_ms = latency_ms
        self.attempts = attempts


@pytest.mark.asyncio
async def test_planner_node_simple_informational_ticket(monkeypatch):
    """
    Current-baseline happy path:
    ordinary low-risk informational request drafts without unnecessary retrieval.
    """

    async def fake_generate_structured(self, *, system_prompt, prompt, response_schema):
        return FakeLLMResult(
            parsed=SupportAgentState(
                plan=[
                    PlanStep(
                        step_id="step_draft_info_response",
                        title="Draft informational response",
                        description=(
                            "Draft a cautious informational response using ticket "
                            "and triage context only."
                        ),
                        owner="response_agent",
                        status="pending",
                    ),
                ],
                current_step_id="step_draft_info_response",
            )
        )

    monkeypatch.setattr(
        "app.nodes.planner.AsyncOpenAIWrapper.generate_structured",
        fake_generate_structured,
    )

    state = GraphState(
        request_id="req-test-001",
        initial_ticket=SupportTicket(
            customer_message="Can you tell me how long shipping usually takes?",
            customer_metadata={},
            order_account_metadata={},
        ),
        shield_result=ShieldOutput(
            decision="allow",
            risk_level="low",
            categories=["valid_support_request"],
            sanitized_message="Can you tell me how long shipping usually takes?",
            should_route_to_human=False,
            clarification_question=None,
            reasoning="Valid support request.",
        ),
        triage_result=TriageOutput(
            issue_category="other",
            intent="information_request",
            urgency="low",
            customer_tone="calm",
            requires_escalation=False,
            requires_human_approval=False,
            reasoning_summary="Customer is asking for general shipping information.",
        ),
    )

    updated_state = await planner_node(state)

    assert updated_state.agent_state is not None
    assert len(updated_state.agent_state.plan) == 1
    assert updated_state.agent_state.current_step_id == "step_draft_info_response"
    assert updated_state.workflow_outcome == "running"

    owners = [step.owner for step in updated_state.agent_state.plan]
    assert "retrieval_agent" not in owners
    assert "response_agent" in owners


@pytest.mark.asyncio
async def test_planner_node_can_carry_retrieval_capable_plan_shape(monkeypatch):
    """
    Proves the plan contract can still carry a retrieval_agent step.
    This does NOT prove an active retrieval backend exists.
    """

    async def fake_generate_structured(self, *, system_prompt, prompt, response_schema):
        return FakeLLMResult(
            parsed=SupportAgentState(
                plan=[
                    PlanStep(
                        step_id="step_retrieve_refund_policy",
                        title="Retrieve refund policy",
                        description="Retrieve refund and billing policy relevant to the ticket.",
                        owner="retrieval_agent",
                        status="pending",
                    ),
                    PlanStep(
                        step_id="step_draft_refund_response",
                        title="Draft refund response",
                        description="Draft a refund response grounded in the refund policy.",
                        owner="response_agent",
                        status="pending",
                    ),
                    PlanStep(
                        step_id="step_human_review",
                        title="Human review",
                        description="Review the refund case before any final response.",
                        owner="human",
                        status="pending",
                        requires_human_approval=True,
                    ),
                ],
                current_step_id="step_retrieve_refund_policy",
            )
        )

    monkeypatch.setattr(
        "app.nodes.planner.AsyncOpenAIWrapper.generate_structured",
        fake_generate_structured,
    )

    state = GraphState(
        request_id="req-test-002",
        initial_ticket=SupportTicket(
            customer_message="I was charged twice and I want a refund immediately.",
            customer_metadata={},
            order_account_metadata={"order_id": "ORD-123"},
        ),
        shield_result=ShieldOutput(
            decision="allow_with_flag",
            risk_level="medium",
            categories=["valid_support_request", "policy_bypass_attempt"],
            sanitized_message="I was charged twice and I want a refund immediately.",
            should_route_to_human=False,
            clarification_question=None,
            reasoning="Valid support request with elevated policy risk.",
        ),
        triage_result=TriageOutput(
            issue_category="refund",
            intent="complaint",
            urgency="high",
            customer_tone="frustrated",
            requires_escalation=False,
            requires_human_approval=True,
            reasoning_summary=(
                "Refund-related complaint that should be reviewed by a "
                "human before final response."
            ),
        ),
    )

    updated_state = await planner_node(state)

    assert updated_state.agent_state is not None
    assert len(updated_state.agent_state.plan) == 3
    assert updated_state.workflow_outcome == "running"

    owners = [step.owner for step in updated_state.agent_state.plan]
    assert "retrieval_agent" in owners

    human_steps = [
        step for step in updated_state.agent_state.plan
        if step.owner == "human" and step.requires_human_approval
    ]
    assert len(human_steps) == 1
    assert human_steps[0].step_id == "step_human_review"


@pytest.mark.asyncio
async def test_planner_node_uses_fallback_plan_on_model_failure(monkeypatch):
    """
    Planner failure fallback must not invent an unfulfillable retrieval dependency.
    """

    async def fake_generate_structured(self, *, system_prompt, prompt, response_schema):
        raise Exception("Simulated planner failure")

    monkeypatch.setattr(
        "app.nodes.planner.AsyncOpenAIWrapper.generate_structured",
        fake_generate_structured,
    )

    state = GraphState(
        request_id="req-test-003",
        initial_ticket=SupportTicket(
            customer_message="My account may have been accessed by someone else.",
            customer_metadata={},
            order_account_metadata={"account_id": "ACC-777"},
        ),
        shield_result=ShieldOutput(
            decision="allow_with_flag",
            risk_level="high",
            categories=["valid_support_request", "suspicious_input"],
            sanitized_message="My account may have been accessed by someone else.",
            should_route_to_human=True,
            clarification_question=None,
            reasoning="Potentially sensitive support request.",
        ),
        triage_result=TriageOutput(
            issue_category="account_security",
            intent="problem_report",
            urgency="high",
            customer_tone="frustrated",
            requires_escalation=True,
            requires_human_approval=True,
            reasoning_summary="Potential account security incident requiring human review.",
        ),
    )

    updated_state = await planner_node(state)

    assert updated_state.agent_state is not None
    assert updated_state.workflow_outcome == "needs_human_review"
    assert len(updated_state.agent_state.plan) == 2

    step_ids = [step.step_id for step in updated_state.agent_state.plan]
    assert "step_draft_response" in step_ids
    assert "step_human_review" in step_ids
    assert "step_retrieve_context" not in step_ids

    owners = [step.owner for step in updated_state.agent_state.plan]
    assert "retrieval_agent" not in owners

    human_steps = [step for step in updated_state.agent_state.plan if step.owner == "human"]
    assert len(human_steps) == 1

    assert "planner_error" in updated_state.additional_metadata
    assert updated_state.additional_metadata["planner_error"]["fallback_plan_used"] is True
