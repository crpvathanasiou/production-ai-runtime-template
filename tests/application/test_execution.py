"""ExecutionContext / LLMInvocationId contract tests."""

from __future__ import annotations

import pytest

from app.application.execution import ExecutionContext, LLMInvocationId


def test_execution_context_rejects_blank_request_id() -> None:
    with pytest.raises(ValueError, match="request_id"):
        ExecutionContext(request_id="  ", run_id="run-1")


def test_execution_context_rejects_blank_run_id() -> None:
    with pytest.raises(ValueError, match="run_id"):
        ExecutionContext(request_id="req-1", run_id="")


def test_execution_context_rejects_blank_non_none_thread_id() -> None:
    with pytest.raises(ValueError, match="thread_id"):
        ExecutionContext(request_id="req-1", run_id="run-1", thread_id="   ")


def test_execution_context_accepts_valid_non_uuid_ids() -> None:
    context = ExecutionContext(
        request_id="req-not-a-uuid",
        run_id="run-not-a-uuid",
        thread_id="thread-not-a-uuid",
    )
    assert context.request_id == "req-not-a-uuid"
    assert context.run_id == "run-not-a-uuid"
    assert context.thread_id == "thread-not-a-uuid"


def test_execution_context_is_immutable() -> None:
    context = ExecutionContext(request_id="req-1", run_id="run-1")
    with pytest.raises(AttributeError):
        context.request_id = "other"  # type: ignore[misc]


def test_llm_invocation_id_rejects_blank() -> None:
    with pytest.raises(ValueError, match="value"):
        LLMInvocationId(value="")


def test_llm_invocation_id_is_immutable() -> None:
    invocation_id = LLMInvocationId(value="inv-1")
    with pytest.raises(AttributeError):
        invocation_id.value = "other"  # type: ignore[misc]


def test_llm_invocation_id_new_returns_unique_non_empty_values() -> None:
    first = LLMInvocationId.new()
    second = LLMInvocationId.new()
    assert first.value.strip()
    assert second.value.strip()
    assert first.value != second.value
