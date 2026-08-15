"""Input Shield application operation."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

from app.application.execution import (
    OPERATION_INPUT_SHIELD,
    ExecutionContext,
    LLMInvocationId,
    LLMInvocationStarted,
    OperationCompleted,
    OperationFailed,
    OperationFallback,
    OperationStarted,
    classify_operation_error,
)
from app.application.ports.llm import LLMExecutionMetadata, LLMPort
from app.application.ports.telemetry import TelemetryPort
from app.application.prompts import PromptIdentity, PromptRef, PromptRepository
from app.core.exceptions import ModelOutputParsingError, UpstreamServiceError
from app.guardrails.input_guardrails import (
    build_fail_fast_shield_output,
    sanitize_message,
)
from app.schemas import ShieldOutput, SupportTicket

InputShieldSource = Literal[
    "heuristic_fail_fast",
    "llm",
    "prompt_length_block",
    "llm_failure_fallback",
]


@dataclass(frozen=True)
class InputShieldOutcome:
    output: ShieldOutput
    source: InputShieldSource
    execution: LLMExecutionMetadata | None
    error_type: str | None
    error_message: str | None
    prompt_identity: PromptIdentity | None


def _compose_logical_prompt(*, system_prompt: str | None, user_prompt: str) -> str:
    if system_prompt and system_prompt.strip():
        return f"[SYSTEM]\n{system_prompt}\n\n[USER]\n{user_prompt}"
    return user_prompt


def _normalize_llm_shield_output(output: ShieldOutput, ticket: SupportTicket) -> ShieldOutput:
    sanitized = sanitize_message(output.sanitized_message or ticket.customer_message)

    if not sanitized:
        sanitized = sanitize_message(ticket.customer_message)

    categories = output.categories or []
    decision = output.decision
    risk_level = output.risk_level
    should_route_to_human = output.should_route_to_human

    if "privacy_risk" in categories and decision != "block":
        decision = "block"
        risk_level = "high"
        should_route_to_human = True

    if "prompt_injection" in categories and decision == "allow":
        decision = "allow_with_flag"
        if risk_level in {"low", "medium"}:
            risk_level = "high"

    if "non_actionable" in categories and decision == "allow":
        decision = "needs_clarification"

    return ShieldOutput(
        decision=decision,
        risk_level=risk_level,
        categories=categories,
        sanitized_message=sanitized,
        should_route_to_human=should_route_to_human,
        clarification_question=output.clarification_question,
        reasoning=output.reasoning,
    )


class InputShieldOperation:
    def __init__(
        self,
        llm: LLMPort,
        prompt_repository: PromptRepository,
        prompt_ref: PromptRef,
        telemetry: TelemetryPort,
        max_prompt_chars: int,
    ) -> None:
        self._llm = llm
        self._prompt_repository = prompt_repository
        self._prompt_ref = prompt_ref
        self._telemetry = telemetry
        self._max_prompt_chars = max_prompt_chars

    async def execute(
        self,
        *,
        context: ExecutionContext,
        ticket: SupportTicket,
    ) -> InputShieldOutcome:
        started = time.perf_counter()
        self._telemetry.emit(
            OperationStarted(context=context, operation_name=OPERATION_INPUT_SHIELD)
        )

        fail_fast_result = build_fail_fast_shield_output(ticket)
        if fail_fast_result is not None:
            self._telemetry.emit(
                OperationCompleted(
                    context=context,
                    operation_name=OPERATION_INPUT_SHIELD,
                    duration_ms=(time.perf_counter() - started) * 1000,
                )
            )
            return InputShieldOutcome(
                output=fail_fast_result,
                source="heuristic_fail_fast",
                execution=None,
                error_type=None,
                error_message=None,
                prompt_identity=None,
            )

        try:
            resolved = self._prompt_repository.resolve(
                self._prompt_ref,
                variables={
                    "customer_message": ticket.customer_message,
                    "customer_metadata": ticket.customer_metadata or {},
                    "order_account_metadata": ticket.order_account_metadata or {},
                },
            )
        except Exception as exc:
            self._telemetry.emit(
                OperationFailed(
                    context=context,
                    operation_name=OPERATION_INPUT_SHIELD,
                    duration_ms=(time.perf_counter() - started) * 1000,
                    error_category=classify_operation_error(exc),
                    error_type=exc.__class__.__name__,
                    invocation_id=None,
                )
            )
            raise

        logical_prompt = _compose_logical_prompt(
            system_prompt=resolved.system_prompt,
            user_prompt=resolved.user_prompt,
        )

        if len(logical_prompt) > self._max_prompt_chars:
            guardrail_message = (
                "Input guardrail 'max_prompt_length' blocked the request: "
                f"Prompt exceeds max allowed length ({self._max_prompt_chars} chars)."
            )
            self._telemetry.emit(
                OperationCompleted(
                    context=context,
                    operation_name=OPERATION_INPUT_SHIELD,
                    duration_ms=(time.perf_counter() - started) * 1000,
                )
            )
            return InputShieldOutcome(
                output=ShieldOutput(
                    decision="block",
                    risk_level="high",
                    categories=["suspicious_input"],
                    sanitized_message=sanitize_message(ticket.customer_message),
                    should_route_to_human=True,
                    clarification_question=None,
                    reasoning=f"Shield guardrail blocked the input: {guardrail_message}",
                ),
                source="prompt_length_block",
                execution=None,
                error_type="GuardrailBlockedError",
                error_message=guardrail_message,
                prompt_identity=resolved.identity,
            )

        invocation_id = LLMInvocationId.new()
        self._telemetry.emit(
            LLMInvocationStarted(
                context=context,
                operation_name=OPERATION_INPUT_SHIELD,
                invocation_id=invocation_id,
                prompt_identity=resolved.identity,
            )
        )

        try:
            result = await self._llm.generate_structured(
                context=context,
                invocation_id=invocation_id,
                system_prompt=resolved.system_prompt,
                prompt=resolved.user_prompt,
                response_schema=ShieldOutput,
            )
            normalized = _normalize_llm_shield_output(result.parsed, ticket)
            self._telemetry.emit(
                OperationCompleted(
                    context=context,
                    operation_name=OPERATION_INPUT_SHIELD,
                    duration_ms=(time.perf_counter() - started) * 1000,
                )
            )
            return InputShieldOutcome(
                output=normalized,
                source="llm",
                execution=result.execution,
                error_type=None,
                error_message=None,
                prompt_identity=resolved.identity,
            )
        except (ModelOutputParsingError, UpstreamServiceError) as exc:
            self._telemetry.emit(
                OperationFallback(
                    context=context,
                    operation_name=OPERATION_INPUT_SHIELD,
                    invocation_id=invocation_id,
                    duration_ms=(time.perf_counter() - started) * 1000,
                    error_category=classify_operation_error(exc),
                    error_type=exc.__class__.__name__,
                )
            )
            return InputShieldOutcome(
                output=ShieldOutput(
                    decision="allow_with_flag",
                    risk_level="medium",
                    categories=["suspicious_input"],
                    sanitized_message=sanitize_message(ticket.customer_message),
                    should_route_to_human=True,
                    clarification_question=None,
                    reasoning=(
                        "Shield model classification failed, so the message is being "
                        "forwarded with caution."
                    ),
                ),
                source="llm_failure_fallback",
                execution=None,
                error_type=exc.__class__.__name__,
                error_message=str(exc),
                prompt_identity=resolved.identity,
            )
        except Exception as exc:
            self._telemetry.emit(
                OperationFailed(
                    context=context,
                    operation_name=OPERATION_INPUT_SHIELD,
                    duration_ms=(time.perf_counter() - started) * 1000,
                    error_category=classify_operation_error(exc),
                    error_type=exc.__class__.__name__,
                    invocation_id=invocation_id,
                )
            )
            raise
