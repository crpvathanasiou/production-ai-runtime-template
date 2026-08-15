"""Application-owned LLM port and structured-generation result contract."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Protocol, TypeVar

from pydantic import BaseModel

from app.application.execution import ExecutionContext, LLMInvocationId

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class LLMExecutionMetadata:
    latency_ms: float
    attempts: int


@dataclass(frozen=True)
class StructuredLLMResult(Generic[T]):
    parsed: T
    execution: LLMExecutionMetadata


class LLMPort(Protocol):
    async def generate_structured(
        self,
        *,
        context: ExecutionContext,
        invocation_id: LLMInvocationId,
        system_prompt: str | None,
        prompt: str,
        response_schema: type[T],
    ) -> StructuredLLMResult[T]: ...
