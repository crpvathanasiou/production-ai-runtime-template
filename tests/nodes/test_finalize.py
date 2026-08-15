import logging

import pytest

from app.graph_state import GraphState
from app.nodes.finalize import finalize_node
from app.schemas import ResponseDrafting, RetrievedDocument, SupportTicket
from tests.test_logging import assert_visible_correlation


@pytest.mark.asyncio
async def test_finalize_node_marks_completed_for_safe_response():
    state = GraphState(
        request_id="req-finalize-001",
        run_id="run-finalize-001",
        initial_ticket=SupportTicket(
            customer_message="How long does shipping take?",
            customer_metadata={},
            order_account_metadata={},
        ),
        response_draft=ResponseDrafting(
            ticket_response="Shipping usually takes 3-5 business days.",
            related_documents=[
                RetrievedDocument(
                    source="faq.md",
                    content="Shipping usually takes 3-5 business days.",
                )
            ],
            unsupported_promises=False,
        ),
        is_safe=True,
        workflow_outcome="running",
    )

    updated_state = await finalize_node(state)

    assert updated_state.workflow_outcome == "completed"
    assert "finalize" in updated_state.additional_metadata
    assert updated_state.additional_metadata["finalize"]["final_workflow_outcome"] == "completed"


@pytest.mark.asyncio
async def test_finalize_node_keeps_needs_human_review_when_pending():
    state = GraphState(
        request_id="req-finalize-002",
        run_id="run-finalize-002",
        initial_ticket=SupportTicket(
            customer_message="I want a refund.",
            customer_metadata={},
            order_account_metadata={"order_id": "ORD-002"},
        ),
        is_safe=False,
        workflow_outcome="needs_human_review",
        human_approved=None,
    )

    updated_state = await finalize_node(state)

    assert updated_state.workflow_outcome == "needs_human_review"
    assert "finalize" in updated_state.additional_metadata
    assert updated_state.additional_metadata["finalize"]["final_workflow_outcome"] == "needs_human_review"


@pytest.mark.asyncio
async def test_finalize_node_marks_blocked_when_human_rejects():
    state = GraphState(
        request_id="req-finalize-003",
        run_id="run-finalize-003",
        initial_ticket=SupportTicket(
            customer_message="My account was hacked.",
            customer_metadata={},
            order_account_metadata={"account_id": "ACC-003"},
        ),
        workflow_outcome="running",
        human_approved=False,
        human_comments="Do not send draft. Needs manual handling.",
    )

    updated_state = await finalize_node(state)

    assert updated_state.workflow_outcome == "blocked"
    assert "finalize" in updated_state.additional_metadata
    assert updated_state.additional_metadata["finalize"]["final_workflow_outcome"] == "blocked"


@pytest.mark.asyncio
async def test_finalize_operational_logs_visible_correlation(caplog):
    secret_response = "SECRET_MODEL_OUTPUT_SENTINEL"
    state = GraphState(
        request_id="req-finalize-log-001",
        run_id="run-finalize-log-001",
        thread_id="thread-finalize-log-001",
        initial_ticket=SupportTicket(
            customer_message="How long does shipping take?",
            customer_metadata={},
            order_account_metadata={},
        ),
        response_draft=ResponseDrafting(
            ticket_response=secret_response,
            related_documents=[
                RetrievedDocument(
                    source="faq.md",
                    content="Shipping usually takes 3-5 business days.",
                )
            ],
            unsupported_promises=False,
        ),
        is_safe=True,
        workflow_outcome="running",
    )

    with caplog.at_level(logging.INFO, logger="app.nodes.finalize"):
        updated = await finalize_node(state)

    assert updated.workflow_outcome == "completed"
    messages = [record.getMessage() for record in caplog.records]
    completed = [m for m in messages if "finalize.completed" in m]
    assert completed
    assert_visible_correlation(
        completed[0],
        request_id="req-finalize-log-001",
        run_id="run-finalize-log-001",
        node_name="finalize",
        event="finalize.completed",
        thread_id="thread-finalize-log-001",
    )
    assert secret_response not in "\n".join(messages)


def test_node_runtime_files_have_no_explicit_langsmith_tracing():
    from pathlib import Path

    nodes_dir = Path(__file__).resolve().parents[2] / "app" / "nodes"
    for path in sorted(nodes_dir.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        assert "@traceable" not in source, path.name
        assert "from langsmith" not in source, path.name
        assert "import langsmith" not in source, path.name
