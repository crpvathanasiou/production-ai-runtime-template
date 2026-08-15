"""Input shield node adapter tests — fake Application Operations only."""

from __future__ import annotations

import inspect
import logging

import pytest

import app.nodes.input_shield as input_shield_module
from app.application.execution import ExecutionContext
from app.application.input_shield import InputShieldOutcome
from app.application.ports.llm import LLMExecutionMetadata
from app.application.prompts import PromptIdentity, PromptRef
from app.graph_state import GraphState
from app.nodes.input_shield import make_input_shield_node
from app.schemas import ShieldOutput, SupportTicket
from tests.test_logging import assert_visible_correlation

_PROMPT_IDENTITY = PromptIdentity(
    ref=PromptRef(prompt_id="input-shield", revision=1),
    content_hash="input-shield-hash",
)
_IDENTITY_KEYS = ("prompt_id", "prompt_revision", "prompt_content_hash")


class FakeInputShieldOperation:
    def __init__(self, outcome: InputShieldOutcome) -> None:
        self._outcome = outcome
        self.calls: list[dict] = []

    async def execute(
        self,
        *,
        context: ExecutionContext,
        ticket: SupportTicket,
    ) -> InputShieldOutcome:
        self.calls.append({"context": context, "ticket": ticket})
        return self._outcome


def _ticket() -> SupportTicket:
    return SupportTicket(
        customer_message="I was charged twice for my order and I need help.",
        customer_metadata={"customer_id": "cust_123"},
        order_account_metadata={"order_id": "ord_456"},
    )


def _state() -> GraphState:
    return GraphState(
        request_id="req-shield-001",
        run_id="run-shield-001",
        thread_id="thread-shield-001",
        initial_ticket=_ticket(),
    )


def _assert_no_raw_prompt_content(meta: dict) -> None:
    assert "system_prompt" not in meta
    assert "user_prompt" not in meta


@pytest.mark.asyncio
async def test_input_shield_node_fail_fast_outcome():
    shield = ShieldOutput(
        decision="block",
        risk_level="high",
        categories=["non_actionable"],
        sanitized_message="",
        should_route_to_human=False,
        clarification_question=None,
        reasoning="Empty message.",
    )
    operation = FakeInputShieldOperation(
        InputShieldOutcome(
            output=shield,
            source="heuristic_fail_fast",
            execution=None,
            error_type=None,
            error_message=None,
            prompt_identity=None,
        )
    )
    node = make_input_shield_node(operation, model_name="unused-model")

    updated = await node(_state())

    assert len(operation.calls) == 1
    assert operation.calls[0]["ticket"].customer_message == _ticket().customer_message
    assert operation.calls[0]["context"] == ExecutionContext(
        request_id="req-shield-001",
        run_id="run-shield-001",
        thread_id="thread-shield-001",
    )
    assert updated.shield_result == shield
    assert updated.workflow_outcome == "blocked"
    meta = updated.additional_metadata["input_shield"]
    assert meta["request_id"] == "req-shield-001"
    assert meta["source"] == "heuristic_fail_fast"
    assert meta["decision"] == "block"
    assert meta["risk_level"] == "high"
    assert "latency_ms" in meta
    for key in _IDENTITY_KEYS:
        assert key not in meta
    _assert_no_raw_prompt_content(meta)


@pytest.mark.asyncio
async def test_input_shield_node_llm_success():
    shield = ShieldOutput(
        decision="allow",
        risk_level="low",
        categories=["valid_support_request"],
        sanitized_message="I was charged twice for my order and I need help.",
        should_route_to_human=False,
        clarification_question=None,
        reasoning="Valid request.",
    )
    operation = FakeInputShieldOperation(
        InputShieldOutcome(
            output=shield,
            source="llm",
            execution=LLMExecutionMetadata(latency_ms=42.5, attempts=2),
            error_type=None,
            error_message=None,
            prompt_identity=_PROMPT_IDENTITY,
        )
    )
    node = make_input_shield_node(operation, model_name="gpt-shield-test")

    updated = await node(_state())

    assert updated.shield_result == shield
    assert updated.workflow_outcome == "running"
    meta = updated.additional_metadata["input_shield"]
    assert meta["request_id"] == "req-shield-001"
    assert meta["model_name"] == "gpt-shield-test"
    assert meta["latency_ms"] == 42.5
    assert meta["attempts"] == 2
    assert meta["decision"] == "allow"
    assert meta["risk_level"] == "low"
    assert meta["prompt_id"] == "input-shield"
    assert meta["prompt_revision"] == 1
    assert meta["prompt_content_hash"] == "input-shield-hash"
    assert "guardrail_notes" not in meta
    _assert_no_raw_prompt_content(meta)


@pytest.mark.asyncio
async def test_input_shield_node_prompt_length_block():
    shield = ShieldOutput(
        decision="block",
        risk_level="high",
        categories=["suspicious_input"],
        sanitized_message="too long",
        should_route_to_human=True,
        clarification_question=None,
        reasoning="Prompt too long.",
    )
    operation = FakeInputShieldOperation(
        InputShieldOutcome(
            output=shield,
            source="prompt_length_block",
            execution=None,
            error_type="GuardrailBlockedError",
            error_message="Prompt exceeds max allowed length.",
            prompt_identity=_PROMPT_IDENTITY,
        )
    )
    node = make_input_shield_node(operation, model_name="gpt-shield-test")

    updated = await node(_state())

    assert updated.shield_result == shield
    assert updated.workflow_outcome == "blocked"
    err = updated.additional_metadata["input_shield_error"]
    assert err["request_id"] == "req-shield-001"
    assert err["error_type"] == "GuardrailBlockedError"
    assert err["message"] == "Prompt exceeds max allowed length."
    assert "latency_ms" in err
    assert err["prompt_id"] == "input-shield"
    assert err["prompt_revision"] == 1
    assert err["prompt_content_hash"] == "input-shield-hash"
    _assert_no_raw_prompt_content(err)

    source = inspect.getsource(input_shield_module)
    assert "build_fail_fast_shield_output" not in source
    assert "MaxPromptLengthGuardrail" not in source
    assert "AsyncOpenAIWrapper" not in source
    assert "build_input_shield_system_prompt" not in source


@pytest.mark.asyncio
async def test_input_shield_node_llm_failure_fallback():
    shield = ShieldOutput(
        decision="allow_with_flag",
        risk_level="medium",
        categories=["suspicious_input"],
        sanitized_message="I was charged twice for my order and I need help.",
        should_route_to_human=True,
        clarification_question=None,
        reasoning="Shield model classification failed.",
    )
    operation = FakeInputShieldOperation(
        InputShieldOutcome(
            output=shield,
            source="llm_failure_fallback",
            execution=None,
            error_type="UpstreamServiceError",
            error_message="provider down",
            prompt_identity=_PROMPT_IDENTITY,
        )
    )
    node = make_input_shield_node(operation, model_name="gpt-shield-test")

    updated = await node(_state())

    assert updated.shield_result == shield
    assert updated.workflow_outcome == "needs_human_review"
    err = updated.additional_metadata["input_shield_error"]
    assert err["request_id"] == "req-shield-001"
    assert err["error_type"] == "UpstreamServiceError"
    assert err["message"] == "provider down"
    assert "latency_ms" in err
    assert err["prompt_id"] == "input-shield"
    assert err["prompt_revision"] == 1
    assert err["prompt_content_hash"] == "input-shield-hash"
    _assert_no_raw_prompt_content(err)


@pytest.mark.asyncio
async def test_input_shield_operational_logs_visible_correlation(caplog):
    secret_message = "SECRET_CUSTOMER_MESSAGE_SENTINEL"
    shield = ShieldOutput(
        decision="allow",
        risk_level="low",
        categories=["valid_support_request"],
        sanitized_message=secret_message,
        should_route_to_human=False,
        clarification_question=None,
        reasoning="Valid request.",
    )
    operation = FakeInputShieldOperation(
        InputShieldOutcome(
            output=shield,
            source="llm",
            execution=LLMExecutionMetadata(latency_ms=1.0, attempts=1),
            error_type=None,
            error_message=None,
            prompt_identity=_PROMPT_IDENTITY,
        )
    )
    node = make_input_shield_node(operation, model_name="gpt-shield-test")
    state = GraphState(
        request_id="req-shield-log-001",
        run_id="run-shield-log-001",
        thread_id="thread-shield-log-001",
        initial_ticket=SupportTicket(
            customer_message=secret_message,
            customer_metadata={},
            order_account_metadata={},
        ),
    )

    with caplog.at_level(logging.INFO, logger="app.nodes.input_shield"):
        updated = await node(state)

    assert updated.workflow_outcome == "running"
    messages = [record.getMessage() for record in caplog.records]
    completed = [m for m in messages if "input_shield.completed" in m]
    assert completed
    assert_visible_correlation(
        completed[0],
        request_id="req-shield-log-001",
        run_id="run-shield-log-001",
        node_name="input_shield",
        event="input_shield.completed",
        thread_id="thread-shield-log-001",
    )
    assert secret_message not in "\n".join(messages)


@pytest.mark.asyncio
async def test_input_shield_operational_logs_omit_none_thread_id(caplog):
    shield = ShieldOutput(
        decision="block",
        risk_level="high",
        categories=["non_actionable"],
        sanitized_message="",
        should_route_to_human=False,
        clarification_question=None,
        reasoning="Empty message.",
    )
    operation = FakeInputShieldOperation(
        InputShieldOutcome(
            output=shield,
            source="heuristic_fail_fast",
            execution=None,
            error_type=None,
            error_message=None,
            prompt_identity=None,
        )
    )
    node = make_input_shield_node(operation, model_name="unused-model")
    state = GraphState(
        request_id="req-shield-log-002",
        run_id="run-shield-log-002",
        thread_id=None,
        initial_ticket=_ticket(),
    )

    with caplog.at_level(logging.INFO, logger="app.nodes.input_shield"):
        updated = await node(state)

    assert updated.thread_id is None
    messages = [record.getMessage() for record in caplog.records]
    assert messages
    for message in messages:
        assert '"thread_id"' not in message
        assert "req-shield-log-002" in message
        assert "run-shield-log-002" in message
        assert "input_shield" in message
