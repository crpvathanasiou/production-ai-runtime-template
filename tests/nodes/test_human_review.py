import logging

import pytest

from app.graph import route_after_guardrails
from app.graph_state import GraphState
from app.nodes.human_review import human_review_node
from app.schemas import ShieldOutput, SupportTicket, TriageOutput
from tests.test_logging import assert_visible_correlation


@pytest.mark.asyncio
async def test_human_review_node_stays_pending_when_decision_not_provided():
    state = GraphState(
        request_id="req-human-001",
        run_id="run-human-001",
        initial_ticket=SupportTicket(
            customer_message="I want a refund for a double charge.",
            customer_metadata={},
            order_account_metadata={"order_id": "ORD-001"},
        ),
        shield_result=ShieldOutput(
            decision="allow_with_flag",
            risk_level="medium",
            categories=["valid_support_request"],
            sanitized_message="I want a refund for a double charge.",
            should_route_to_human=False,
            clarification_question=None,
            reasoning="Valid request with some risk.",
        ),
        triage_result=TriageOutput(
            issue_category="refund",
            intent="complaint",
            urgency="high",
            customer_tone="frustrated",
            requires_escalation=False,
            requires_human_approval=True,
            reasoning_summary="Refund case requires human approval.",
        ),
        is_safe=True,
        human_approved=None,
        human_comments=None,
    )

    updated_state = await human_review_node(state)

    assert updated_state.workflow_outcome == "needs_human_review"
    assert "human_review" in updated_state.additional_metadata
    assert updated_state.additional_metadata["human_review"]["review_status"] == "pending"


@pytest.mark.asyncio
async def test_human_review_preserves_upstream_needs_human_review_signal():
    """Upstream execution unmet-retrieval/review signal must not be erased."""
    state = GraphState(
        request_id="req-human-upstream-signal",
        run_id="run-human-upstream-signal",
        initial_ticket=SupportTicket(
            customer_message="What is the refund policy?",
            customer_metadata={},
            order_account_metadata={},
        ),
        shield_result=ShieldOutput(
            decision="allow",
            risk_level="low",
            categories=["valid_support_request"],
            sanitized_message="What is the refund policy?",
            should_route_to_human=False,
            clarification_question=None,
            reasoning="Valid support request.",
        ),
        triage_result=TriageOutput(
            issue_category="refund",
            intent="information_request",
            urgency="low",
            customer_tone="calm",
            requires_escalation=False,
            requires_human_approval=False,
            reasoning_summary="Customer asks for refund policy information.",
        ),
        is_safe=True,
        workflow_outcome="needs_human_review",
        human_approved=None,
        human_comments=None,
    )

    updated_state = await human_review_node(state)

    assert updated_state.additional_metadata["human_review"]["review_required"] is True
    assert updated_state.workflow_outcome == "needs_human_review"
    assert updated_state.additional_metadata["human_review"]["review_status"] == "pending"


def test_route_after_guardrails_preserves_needs_human_review():
    state = GraphState(
        request_id="req-route-needs-human",
        run_id="run-route-needs-human",
        initial_ticket=SupportTicket(
            customer_message="What is the refund policy?",
            customer_metadata={},
            order_account_metadata={},
        ),
        is_safe=True,
        workflow_outcome="needs_human_review",
    )

    assert route_after_guardrails(state) == "human_review"


@pytest.mark.asyncio
async def test_human_review_node_marks_completed_when_approved():
    state = GraphState(
        request_id="req-human-002",
        run_id="run-human-002",
        initial_ticket=SupportTicket(
            customer_message="I was charged twice.",
            customer_metadata={},
            order_account_metadata={"order_id": "ORD-002"},
        ),
        triage_result=TriageOutput(
            issue_category="refund",
            intent="complaint",
            urgency="high",
            customer_tone="frustrated",
            requires_escalation=False,
            requires_human_approval=True,
            reasoning_summary="Refund case requires review.",
        ),
        is_safe=True,
        human_approved=True,
        human_comments="Approved after reviewing billing context.",
    )

    updated_state = await human_review_node(state)

    assert updated_state.workflow_outcome == "completed"
    assert "human_review" in updated_state.additional_metadata
    assert updated_state.additional_metadata["human_review"]["review_status"] == "approved"
    assert updated_state.additional_metadata["human_review"][
        "human_comments"
    ] == "Approved after reviewing billing context."


@pytest.mark.asyncio
async def test_human_review_node_blocks_when_rejected():
    state = GraphState(
        request_id="req-human-003",
        run_id="run-human-003",
        initial_ticket=SupportTicket(
            customer_message="My account was hacked.",
            customer_metadata={},
            order_account_metadata={"account_id": "ACC-003"},
        ),
        triage_result=TriageOutput(
            issue_category="account_security",
            intent="problem_report",
            urgency="high",
            customer_tone="frustrated",
            requires_escalation=True,
            requires_human_approval=True,
            reasoning_summary="Security case requires human decision.",
        ),
        is_safe=False,
        safety_feedback="Security-related draft contains risky account-action language.",
        human_approved=False,
        human_comments="Do not send this draft. Needs manual handling.",
    )

    updated_state = await human_review_node(state)

    assert updated_state.workflow_outcome == "blocked"
    assert "human_review" in updated_state.additional_metadata
    assert updated_state.additional_metadata["human_review"]["review_status"] == "rejected"
    assert updated_state.additional_metadata["human_review"][
        "human_comments"
    ] == "Do not send this draft. Needs manual handling."


@pytest.mark.asyncio
async def test_human_review_operational_logs_visible_correlation(caplog):
    secret_comment = "SECRET_HUMAN_COMMENT_SENTINEL"
    state = GraphState(
        request_id="req-human-log-001",
        run_id="run-human-log-001",
        thread_id="thread-human-log-001",
        initial_ticket=SupportTicket(
            customer_message="I want a refund for a double charge.",
            customer_metadata={},
            order_account_metadata={"order_id": "ORD-001"},
        ),
        triage_result=TriageOutput(
            issue_category="refund",
            intent="complaint",
            urgency="high",
            customer_tone="frustrated",
            requires_escalation=False,
            requires_human_approval=True,
            reasoning_summary="Refund case requires human approval.",
        ),
        is_safe=True,
        human_approved=None,
        human_comments=secret_comment,
        workflow_outcome="needs_human_review",
    )

    with caplog.at_level(logging.INFO, logger="app.nodes.human_review"):
        updated = await human_review_node(state)

    assert updated.workflow_outcome == "needs_human_review"
    messages = [record.getMessage() for record in caplog.records]
    pending = [m for m in messages if "human_review.pending" in m]
    assert pending
    assert_visible_correlation(
        pending[0],
        request_id="req-human-log-001",
        run_id="run-human-log-001",
        node_name="human_review",
        event="human_review.pending",
        thread_id="thread-human-log-001",
    )
    assert secret_comment not in "\n".join(messages)
