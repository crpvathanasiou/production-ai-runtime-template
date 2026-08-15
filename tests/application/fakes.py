"""Minimal FakeLLMPort for application-operation tests."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.application.ports.llm import LLMExecutionMetadata, StructuredLLMResult, T


class FakeLLMPort:
    def __init__(
        self,
        *,
        result: BaseModel | None = None,
        error: Exception | None = None,
        latency_ms: float = 1.0,
        attempts: int = 1,
    ) -> None:
        self._result = result
        self._error = error
        self._latency_ms = latency_ms
        self._attempts = attempts
        self.calls: list[dict[str, Any]] = []

    @property
    def call_count(self) -> int:
        return len(self.calls)

    async def generate_structured(
        self,
        *,
        system_prompt: str | None,
        prompt: str,
        response_schema: type[T],
    ) -> StructuredLLMResult[T]:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "prompt": prompt,
                "response_schema": response_schema,
            }
        )
        if self._error is not None:
            raise self._error
        if self._result is None:
            raise AssertionError("FakeLLMPort requires result or error")
        if not isinstance(self._result, response_schema):
            raise AssertionError(
                f"FakeLLMPort result type {type(self._result).__name__} "
                f"does not match schema {response_schema.__name__}"
            )
        return StructuredLLMResult(
            parsed=self._result,
            execution=LLMExecutionMetadata(
                latency_ms=self._latency_ms,
                attempts=self._attempts,
            ),
        )
