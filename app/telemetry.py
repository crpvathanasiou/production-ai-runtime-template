"""Concrete telemetry exporters for Application Operations."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.application.execution import (
    EVENT_LLM_INVOCATION_STARTED,
    EVENT_OPERATION_COMPLETED,
    EVENT_OPERATION_FAILED,
    EVENT_OPERATION_FALLBACK,
    EVENT_OPERATION_STARTED,
    ApplicationTelemetryEvent,
    LLMInvocationStarted,
    OperationCompleted,
    OperationFailed,
    OperationFallback,
    OperationStarted,
)
from app.core.logging import get_logger


class NoOpTelemetry:
    """Synchronous no-op exporter for direct callers and tests."""

    def emit(self, event: ApplicationTelemetryEvent) -> None:
        return None


class StdlibTelemetry:
    """Minimal stdlib-logging exporter with safe compact JSON payloads."""

    def __init__(self, *, logger: logging.Logger | None = None) -> None:
        self._logger = logger or get_logger("app.telemetry")

    def emit(self, event: ApplicationTelemetryEvent) -> None:
        try:
            payload = self._render(event)
            message = json.dumps(payload, separators=(",", ":"), sort_keys=True)
            if isinstance(event, OperationFailed):
                self._logger.error(message)
            elif isinstance(event, OperationFallback):
                self._logger.warning(message)
            else:
                self._logger.info(message)
        except Exception:
            return None

    def _render(self, event: ApplicationTelemetryEvent) -> dict[str, Any]:
        context = event.context
        payload: dict[str, Any] = {
            "event": self._event_name(event),
            "request_id": context.request_id,
            "run_id": context.run_id,
            "operation": event.operation_name,
        }
        if context.thread_id is not None:
            payload["thread_id"] = context.thread_id

        if isinstance(event, LLMInvocationStarted):
            payload["invocation_id"] = event.invocation_id.value
            payload["prompt_id"] = event.prompt_identity.ref.prompt_id
            payload["prompt_revision"] = event.prompt_identity.ref.revision
            payload["prompt_content_hash"] = event.prompt_identity.content_hash
        elif isinstance(event, OperationCompleted):
            payload["duration_ms"] = event.duration_ms
        elif isinstance(event, OperationFallback):
            payload["invocation_id"] = event.invocation_id.value
            payload["duration_ms"] = event.duration_ms
            payload["error_category"] = event.error_category
            payload["error_type"] = event.error_type
        elif isinstance(event, OperationFailed):
            payload["duration_ms"] = event.duration_ms
            payload["error_category"] = event.error_category
            payload["error_type"] = event.error_type
            if event.invocation_id is not None:
                payload["invocation_id"] = event.invocation_id.value

        return payload

    @staticmethod
    def _event_name(event: ApplicationTelemetryEvent) -> str:
        if isinstance(event, OperationStarted):
            return EVENT_OPERATION_STARTED
        if isinstance(event, LLMInvocationStarted):
            return EVENT_LLM_INVOCATION_STARTED
        if isinstance(event, OperationCompleted):
            return EVENT_OPERATION_COMPLETED
        if isinstance(event, OperationFallback):
            return EVENT_OPERATION_FALLBACK
        if isinstance(event, OperationFailed):
            return EVENT_OPERATION_FAILED
        raise TypeError(f"Unsupported telemetry event type: {type(event)!r}")
