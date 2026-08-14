import pytest

from app.graph_state import GraphState
from app.nodes.execute_plan import execute_plan_node
from app.schemas import (
    PlanStep,
    ResponseDrafting,
    RetrievedDocument,
    SupportAgentState,
    SupportTicket,
    TriageOutput,
)


class FakeLLMResult:
    def __init__(self, parsed, model_name="gpt-4.1-mini", latency_ms=95.0, attempts=1):
        self.parsed = parsed
        self.model_name = model_name
        self.latency_ms = latency_ms
        self.attempts = attempts


@pytest.mark.asyncio
async def test_execute_plan_node_retrieval_step_populates_documents(monkeypatch):
    """RAG-ready seam: mocked successful retrieval still populates state and completes."""

    def fake_retrieve_relevant_documents(*, query, max_documents=3):
        return [
            RetrievedDocument(
                source="faq.md",
                content="Shipping usually takes 3-5 business days.",
            ),
            RetrievedDocument(
                source="shipping_policy.md",
                content="Orders are processed within 24 hours.",
            ),
        ]

    monkeypatch.setattr(
        "app.nodes.execute_plan.retrieve_relevant_documents",
        fake_retrieve_relevant_documents,
    )

    state = GraphState(
        request_id="req-execute-001",
        initial_ticket=SupportTicket(
            customer_message="How long does shipping take?",
            customer_metadata={},
            order_account_metadata={},
        ),
        triage_result=TriageOutput(
            issue_category="other",
            intent="information_request",
            urgency="low",
            customer_tone="calm",
            requires_escalation=False,
            requires_human_approval=False,
            reasoning_summary="Customer asks for general shipping information.",
        ),
        agent_state=SupportAgentState(
            plan=[
                PlanStep(
                    step_id="step_retrieve_shipping_info",
                    title="Retrieve shipping info",
                    description="Retrieve shipping FAQ and shipping policy context.",
                    owner="retrieval_agent",
                    status="pending",
                )
            ],
            current_step_id="step_retrieve_shipping_info",
        ),
    )

    updated_state = await execute_plan_node(state)

    assert updated_state.retrieved_documents is not None
    assert len(updated_state.retrieved_documents) == 2
    assert updated_state.retrieved_documents[0].source == "faq.md"

    assert updated_state.agent_state is not None
    assert updated_state.agent_state.plan[0].status == "completed"
    assert updated_state.agent_state.plan[0].result == "Retrieved 2 document(s)."
    assert updated_state.agent_state.current_step_id is None

    assert updated_state.workflow_outcome == "running"
    assert "execute_plan" in updated_state.additional_metadata


@pytest.mark.asyncio
async def test_execute_plan_node_explicit_retrieval_returning_empty_fails(monkeypatch):
    """
    Current baseline: inert retrieval entrypoint returns [].
    An explicitly requested retrieval step is unmet, not a false success.
    """

    async def fake_generate_structured(self, *, system_prompt, prompt, response_schema):
        return FakeLLMResult(
            parsed=ResponseDrafting(
                ticket_response=(
                    "Thanks for reaching out. I do not have verified policy "
                    "context available, so a human agent will review your request."
                ),
                related_documents=[],
                unsupported_promises=False,
            )
        )

    monkeypatch.setattr(
        "app.nodes.execute_plan.AsyncOpenAIWrapper.generate_structured",
        fake_generate_structured,
    )

    state = GraphState(
        request_id="req-execute-empty-retrieval",
        initial_ticket=SupportTicket(
            customer_message="What is the refund policy?",
            customer_metadata={},
            order_account_metadata={},
        ),
        triage_result=TriageOutput(
            issue_category="refund",
            intent="information_request",
            urgency="low",
            customer_tone="calm",
            requires_escalation=False,
            requires_human_approval=False,
            reasoning_summary="Customer asks about refund policy.",
        ),
        agent_state=SupportAgentState(
            plan=[
                PlanStep(
                    step_id="step_retrieve_refund_policy",
                    title="Retrieve refund policy",
                    description="Retrieve refund policy context.",
                    owner="retrieval_agent",
                    status="pending",
                ),
                PlanStep(
                    step_id="step_draft_response",
                    title="Draft cautious response",
                    description="Draft a cautious response for human review.",
                    owner="response_agent",
                    status="pending",
                ),
            ],
            current_step_id="step_retrieve_refund_policy",
        ),
    )

    updated_state = await execute_plan_node(state)

    assert updated_state.retrieved_documents == []
    assert updated_state.agent_state is not None

    retrieval_step = updated_state.agent_state.plan[0]
    assert retrieval_step.status == "failed"
    assert retrieval_step.result is None
    assert retrieval_step.error == "Retrieval returned no documents."

    draft_step = updated_state.agent_state.plan[1]
    assert draft_step.status == "completed"
    assert draft_step.result == "Drafted customer response without retrieved context."

    assert updated_state.workflow_outcome == "needs_human_review"


@pytest.mark.asyncio
async def test_execute_plan_node_response_step_populates_response_draft(monkeypatch):
    async def fake_generate_structured(self, *, system_prompt, prompt, response_schema):
        return FakeLLMResult(
            parsed=ResponseDrafting(
                ticket_response="Thanks for reaching out. Shipping usually takes 3-5 business days.",
                related_documents=[
                    RetrievedDocument(
                        source="faq.md",
                        content="Shipping usually takes 3-5 business days.",
                    )
                ],
                unsupported_promises=False,
            )
        )

    monkeypatch.setattr(
        "app.nodes.execute_plan.AsyncOpenAIWrapper.generate_structured",
        fake_generate_structured,
    )

    state = GraphState(
        request_id="req-execute-002",
        initial_ticket=SupportTicket(
            customer_message="How long does shipping take?",
            customer_metadata={},
            order_account_metadata={},
        ),
        triage_result=TriageOutput(
            issue_category="other",
            intent="information_request",
            urgency="low",
            customer_tone="calm",
            requires_escalation=False,
            requires_human_approval=False,
            reasoning_summary="Customer asks for general shipping information.",
        ),
        retrieved_documents=[
            RetrievedDocument(
                source="faq.md",
                content="Shipping usually takes 3-5 business days.",
            )
        ],
        agent_state=SupportAgentState(
            plan=[
                PlanStep(
                    step_id="step_draft_shipping_response",
                    title="Draft shipping response",
                    description="Draft a grounded response for the customer using shipping FAQ context.",
                    owner="response_agent",
                    status="pending",
                )
            ],
            current_step_id="step_draft_shipping_response",
        ),
    )

    updated_state = await execute_plan_node(state)

    assert updated_state.response_draft is not None
    assert "3-5 business days" in updated_state.response_draft.ticket_response
    assert updated_state.response_draft.unsupported_promises is False

    assert updated_state.agent_state is not None
    assert updated_state.agent_state.plan[0].status == "completed"
    assert (
        updated_state.agent_state.plan[0].result
        == "Drafted grounded customer response."
    )
    assert updated_state.agent_state.current_step_id is None

    assert updated_state.workflow_outcome == "running"
    assert "response_drafting" in updated_state.additional_metadata
    assert "execute_plan" in updated_state.additional_metadata


@pytest.mark.asyncio
async def test_execute_plan_node_response_without_retrieved_context(monkeypatch):
    """Drafting without retrieval evidence is non-grounded-by-corpus and valid."""

    async def fake_generate_structured(self, *, system_prompt, prompt, response_schema):
        return FakeLLMResult(
            parsed=ResponseDrafting(
                ticket_response=(
                    "Thanks for your message. Based on the available ticket details, "
                    "I can acknowledge your request and share next steps once verified."
                ),
                related_documents=[],
                unsupported_promises=False,
            )
        )

    monkeypatch.setattr(
        "app.nodes.execute_plan.AsyncOpenAIWrapper.generate_structured",
        fake_generate_structured,
    )

    state = GraphState(
        request_id="req-execute-no-retrieval-draft",
        initial_ticket=SupportTicket(
            customer_message="Can you tell me how long shipping usually takes?",
            customer_metadata={},
            order_account_metadata={},
        ),
        triage_result=TriageOutput(
            issue_category="other",
            intent="information_request",
            urgency="low",
            customer_tone="calm",
            requires_escalation=False,
            requires_human_approval=False,
            reasoning_summary="Customer asks for shipping information.",
        ),
        retrieved_documents=[],
        agent_state=SupportAgentState(
            plan=[
                PlanStep(
                    step_id="step_draft_response",
                    title="Draft cautious response",
                    description="Draft using ticket and triage context only.",
                    owner="response_agent",
                    status="pending",
                )
            ],
            current_step_id="step_draft_response",
        ),
    )

    updated_state = await execute_plan_node(state)

    assert updated_state.response_draft is not None
    assert updated_state.response_draft.related_documents == []
    assert updated_state.agent_state is not None
    assert updated_state.agent_state.plan[0].status == "completed"
    assert (
        updated_state.agent_state.plan[0].result
        == "Drafted customer response without retrieved context."
    )
    assert "grounded" not in (
        updated_state.agent_state.plan[0].result or ""
    ).lower()
    assert updated_state.workflow_outcome == "running"


@pytest.mark.asyncio
async def test_execute_plan_node_failed_response_step_routes_to_human_review(monkeypatch):
    async def fake_generate_structured(self, *, system_prompt, prompt, response_schema):
        raise Exception("Simulated response drafting failure")

    monkeypatch.setattr(
        "app.nodes.execute_plan.AsyncOpenAIWrapper.generate_structured",
        fake_generate_structured,
    )

    state = GraphState(
        request_id="req-execute-003",
        initial_ticket=SupportTicket(
            customer_message="I was charged twice and want a refund.",
            customer_metadata={},
            order_account_metadata={"order_id": "ORD-123"},
        ),
        triage_result=TriageOutput(
            issue_category="refund",
            intent="complaint",
            urgency="high",
            customer_tone="frustrated",
            requires_escalation=False,
            requires_human_approval=True,
            reasoning_summary="Refund-related complaint requiring careful handling.",
        ),
        retrieved_documents=[
            RetrievedDocument(
                source="refund_policy.md",
                content="Refunds are reviewed according to the billing policy.",
            )
        ],
        agent_state=SupportAgentState(
            plan=[
                PlanStep(
                    step_id="step_draft_refund_response",
                    title="Draft refund response",
                    description="Draft a grounded response using the refund policy.",
                    owner="response_agent",
                    status="pending",
                ),
                PlanStep(
                    step_id="step_human_review",
                    title="Human review",
                    description="Review the case before final response.",
                    owner="human",
                    status="pending",
                    requires_human_approval=True,
                ),
            ],
            current_step_id="step_draft_refund_response",
        ),
    )

    updated_state = await execute_plan_node(state)

    assert updated_state.agent_state is not None
    assert len(updated_state.agent_state.plan) == 2

    failed_step = updated_state.agent_state.plan[0]
    assert failed_step.step_id == "step_draft_refund_response"
    assert failed_step.status == "failed"
    assert failed_step.error is not None
    assert "Simulated response drafting failure" in failed_step.error

    human_step = updated_state.agent_state.plan[1]
    assert human_step.owner == "human"
    assert human_step.status == "pending"

    assert updated_state.agent_state.current_step_id == "step_human_review"
    assert updated_state.workflow_outcome == "needs_human_review"
    assert "execute_plan" in updated_state.additional_metadata


@pytest.mark.asyncio
async def test_execute_plan_node_pending_human_step_forces_needs_human_review(
    monkeypatch,
):
    """
    An explicit pending human PlanStep is a review gate.

    Even when triage/shield do not independently require human review and
    response drafting succeeds safely, workflow_outcome must become
    needs_human_review — not ordinary running.
    """

    async def fake_generate_structured(self, *, system_prompt, prompt, response_schema):
        return FakeLLMResult(
            parsed=ResponseDrafting(
                ticket_response=(
                    "Thanks for reaching out. Shipping usually takes 3-5 business days."
                ),
                related_documents=[
                    RetrievedDocument(
                        source="faq.md",
                        content="Shipping usually takes 3-5 business days.",
                    )
                ],
                unsupported_promises=False,
            )
        )

    monkeypatch.setattr(
        "app.nodes.execute_plan.AsyncOpenAIWrapper.generate_structured",
        fake_generate_structured,
    )

    state = GraphState(
        request_id="req-execute-pending-human",
        initial_ticket=SupportTicket(
            customer_message="How long does shipping take?",
            customer_metadata={},
            order_account_metadata={},
        ),
        triage_result=TriageOutput(
            issue_category="other",
            intent="information_request",
            urgency="low",
            customer_tone="calm",
            requires_escalation=False,
            requires_human_approval=False,
            reasoning_summary="Customer asks for general shipping information.",
        ),
        retrieved_documents=[
            RetrievedDocument(
                source="faq.md",
                content="Shipping usually takes 3-5 business days.",
            )
        ],
        agent_state=SupportAgentState(
            plan=[
                PlanStep(
                    step_id="step_draft_shipping_response",
                    title="Draft shipping response",
                    description="Draft a grounded response using shipping FAQ context.",
                    owner="response_agent",
                    status="pending",
                ),
                PlanStep(
                    step_id="step_human_review",
                    title="Human review",
                    description="Review the drafted response before send.",
                    owner="human",
                    status="pending",
                ),
            ],
            current_step_id="step_draft_shipping_response",
        ),
    )

    updated_state = await execute_plan_node(state)

    assert updated_state.agent_state is not None
    assert len(updated_state.agent_state.plan) == 2

    response_step = updated_state.agent_state.plan[0]
    assert response_step.step_id == "step_draft_shipping_response"
    assert response_step.status == "completed"

    human_step = updated_state.agent_state.plan[1]
    assert human_step.owner == "human"
    assert human_step.status == "pending"

    assert updated_state.agent_state.current_step_id == "step_human_review"
    assert updated_state.workflow_outcome == "needs_human_review"
    assert updated_state.response_draft is not None
    assert updated_state.response_draft.unsupported_promises is False
