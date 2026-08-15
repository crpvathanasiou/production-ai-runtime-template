"""Application-owned execution correlation and telemetry events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

from app.application.prompts import PromptIdentity, PromptNotFoundError, PromptRenderError
from app.core.exceptions import ModelOutputParsingError, UpstreamServiceError

OperationName = Literal[
    "input_shield",
    "triage",
    "planner",
    "response_drafting",
]

OPERATION_INPUT_SHIELD: OperationName = "input_shield"
OPERATION_TRIAGE: OperationName = "triage"
OPERATION_PLANNER: OperationName = "planner"
OPERATION_RESPONSE_DRAFTING: OperationName = "response_drafting"

OperationErrorCategory = Literal[
    "prompt_resolution",
    "provider",
    "model_output",
    "unexpected",
]

EVENT_OPERATION_STARTED = "operation_started"
EVENT_LLM_INVOCATION_STARTED = "llm_invocation_started"
EVENT_OPERATION_COMPLETED = "operation_completed"
EVENT_OPERATION_FALLBACK = "operation_fallback"
EVENT_OPERATION_FAILED = "operation_failed"


def _require_non_blank(name: str, value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty, non-whitespace string")


@dataclass(frozen=True)
class ExecutionContext:
    """Immutable correlation for one top-level application execution."""

    request_id: str
    run_id: str
    thread_id: str | None = None

    def __post_init__(self) -> None:
        _require_non_blank("request_id", self.request_id)
        _require_non_blank("run_id", self.run_id)
        if self.thread_id is not None:
            _require_non_blank("thread_id", self.thread_id)


@dataclass(frozen=True)
class LLMInvocationId:
    """Opaque identity for one LLMPort invocation including its retries."""

    value: str

    def __post_init__(self) -> None:
        _require_non_blank("value", self.value)

    @classmethod
    def new(cls) -> LLMInvocationId:
        return cls(value=str(uuid4()))


@dataclass(frozen=True)
class OperationStarted:
    context: ExecutionContext
    operation_name: OperationName


@dataclass(frozen=True)
class LLMInvocationStarted:
    context: ExecutionContext
    operation_name: OperationName
    invocation_id: LLMInvocationId
    prompt_identity: PromptIdentity


@dataclass(frozen=True)
class OperationCompleted:
    context: ExecutionContext
    operation_name: OperationName
    duration_ms: float


@dataclass(frozen=True)
class OperationFallback:
    context: ExecutionContext
    operation_name: OperationName
    invocation_id: LLMInvocationId
    duration_ms: float
    error_category: OperationErrorCategory
    error_type: str


@dataclass(frozen=True)
class OperationFailed:
    context: ExecutionContext
    operation_name: OperationName
    duration_ms: float
    error_category: OperationErrorCategory
    error_type: str
    invocation_id: LLMInvocationId | None


ApplicationTelemetryEvent = (
    OperationStarted
    | LLMInvocationStarted
    | OperationCompleted
    | OperationFallback
    | OperationFailed
)


def classify_operation_error(exc: BaseException) -> OperationErrorCategory:
    """Map known application failures to the locked error categories."""
    if isinstance(exc, PromptNotFoundError | PromptRenderError):
        return "prompt_resolution"
    if isinstance(exc, UpstreamServiceError):
        return "provider"
    if isinstance(exc, ModelOutputParsingError):
        return "model_output"
    return "unexpected"
