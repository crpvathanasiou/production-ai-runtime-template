"""Stdlib/NoOp telemetry exporter tests."""

from __future__ import annotations

import json
import logging
from typing import Any

import pytest

from app.application.execution import (
    EVENT_LLM_INVOCATION_STARTED,
    EVENT_OPERATION_COMPLETED,
    EVENT_OPERATION_FAILED,
    EVENT_OPERATION_FALLBACK,
    EVENT_OPERATION_STARTED,
    OPERATION_INPUT_SHIELD,
    OPERATION_PLANNER,
    OPERATION_RESPONSE_DRAFTING,
    OPERATION_TRIAGE,
    ExecutionContext,
    LLMInvocationId,
    LLMInvocationStarted,
    OperationCompleted,
    OperationFailed,
    OperationFallback,
    OperationStarted,
)
from app.application.prompts import PromptIdentity, PromptRef
from app.telemetry import NoOpTelemetry, StdlibTelemetry


def _context() -> ExecutionContext:
    return ExecutionContext(
        request_id="req-1",
        run_id="run-1",
        thread_id="thread-1",
    )


def test_stable_operation_and_event_identifiers() -> None:
    assert OPERATION_INPUT_SHIELD == "input_shield"
    assert OPERATION_TRIAGE == "triage"
    assert OPERATION_PLANNER == "planner"
    assert OPERATION_RESPONSE_DRAFTING == "response_drafting"
    assert EVENT_OPERATION_STARTED == "operation_started"
    assert EVENT_LLM_INVOCATION_STARTED == "llm_invocation_started"
    assert EVENT_OPERATION_COMPLETED == "operation_completed"
    assert EVENT_OPERATION_FALLBACK == "operation_fallback"
    assert EVENT_OPERATION_FAILED == "operation_failed"


def test_noop_telemetry_emit_returns_normally() -> None:
    NoOpTelemetry().emit(
        OperationStarted(context=_context(), operation_name=OPERATION_TRIAGE)
    )


def test_stdlib_telemetry_renders_safe_fields(caplog: pytest.LogCaptureFixture) -> None:
    telemetry = StdlibTelemetry(logger=logging.getLogger("test.stdlib.telemetry"))
    identity = PromptIdentity(
        ref=PromptRef(prompt_id="triage", revision=1),
        content_hash="hash-1",
    )
    invocation_id = LLMInvocationId(value="inv-1")
    context = _context()

    with caplog.at_level(logging.INFO, logger="test.stdlib.telemetry"):
        telemetry.emit(
            OperationStarted(context=context, operation_name=OPERATION_TRIAGE)
        )
        telemetry.emit(
            LLMInvocationStarted(
                context=context,
                operation_name=OPERATION_TRIAGE,
                invocation_id=invocation_id,
                prompt_identity=identity,
            )
        )
        telemetry.emit(
            OperationCompleted(
                context=context,
                operation_name=OPERATION_TRIAGE,
                duration_ms=12.5,
            )
        )

    with caplog.at_level(logging.WARNING, logger="test.stdlib.telemetry"):
        telemetry.emit(
            OperationFallback(
                context=context,
                operation_name=OPERATION_INPUT_SHIELD,
                invocation_id=invocation_id,
                duration_ms=3.0,
                error_category="provider",
                error_type="UpstreamServiceError",
            )
        )

    with caplog.at_level(logging.ERROR, logger="test.stdlib.telemetry"):
        telemetry.emit(
            OperationFailed(
                context=context,
                operation_name=OPERATION_PLANNER,
                duration_ms=4.0,
                error_category="prompt_resolution",
                error_type="PromptNotFoundError",
                invocation_id=None,
            )
        )

    payloads = [json.loads(record.getMessage()) for record in caplog.records]
    assert payloads[0]["event"] == "operation_started"
    assert payloads[0]["request_id"] == "req-1"
    assert payloads[0]["run_id"] == "run-1"
    assert payloads[0]["thread_id"] == "thread-1"
    assert payloads[0]["operation"] == "triage"

    assert payloads[1]["event"] == "llm_invocation_started"
    assert payloads[1]["invocation_id"] == "inv-1"
    assert payloads[1]["prompt_id"] == "triage"
    assert payloads[1]["prompt_revision"] == 1
    assert payloads[1]["prompt_content_hash"] == "hash-1"

    assert payloads[2]["event"] == "operation_completed"
    assert payloads[2]["duration_ms"] == 12.5

    assert payloads[3]["event"] == "operation_fallback"
    assert payloads[3]["error_category"] == "provider"
    assert payloads[3]["error_type"] == "UpstreamServiceError"

    assert payloads[4]["event"] == "operation_failed"
    assert payloads[4]["error_category"] == "prompt_resolution"
    assert "invocation_id" not in payloads[4]

    forbidden = {
        "system_prompt",
        "user_prompt",
        "prompt",
        "customer_message",
        "docs_text",
        "exception_message",
        "secret",
        "raw_text",
    }
    for payload in payloads:
        assert forbidden.isdisjoint(payload.keys())


def test_stdlib_telemetry_contains_logging_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class BrokenLogger:
        def info(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("logger boom")

        def warning(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("logger boom")

        def error(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("logger boom")

    telemetry = StdlibTelemetry(logger=BrokenLogger())  # type: ignore[arg-type]
    telemetry.emit(
        OperationStarted(context=_context(), operation_name=OPERATION_RESPONSE_DRAFTING)
    )
