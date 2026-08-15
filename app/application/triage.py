"""Triage application operation."""

from __future__ import annotations

import time
from dataclasses import dataclass

from app.application.execution import (
    OPERATION_TRIAGE,
    ExecutionContext,
    LLMInvocationId,
    LLMInvocationStarted,
    OperationCompleted,
    OperationFailed,
    OperationStarted,
    classify_operation_error,
)
from app.application.ports.llm import LLMExecutionMetadata, LLMPort
from app.application.ports.telemetry import TelemetryPort
from app.application.prompts import PromptIdentity, PromptRef, PromptRepository
from app.schemas import ShieldOutput, SupportTicket, TriageOutput


@dataclass(frozen=True)
class TriageOutcome:
    output: TriageOutput
    execution: LLMExecutionMetadata
    prompt_identity: PromptIdentity


class TriageOperation:
    def __init__(
        self,
        llm: LLMPort,
        prompt_repository: PromptRepository,
        prompt_ref: PromptRef,
        telemetry: TelemetryPort,
    ) -> None:
        self._llm = llm
        self._prompt_repository = prompt_repository
        self._prompt_ref = prompt_ref
        self._telemetry = telemetry

    async def execute(
        self,
        *,
        context: ExecutionContext,
        ticket: SupportTicket,
        shield_result: ShieldOutput,
    ) -> TriageOutcome:
        started = time.perf_counter()
        self._telemetry.emit(
            OperationStarted(context=context, operation_name=OPERATION_TRIAGE)
        )

        try:
            resolved = self._prompt_repository.resolve(
                self._prompt_ref,
                variables={
                    "sanitized_message": shield_result.sanitized_message,
                    "shield_decision": shield_result.decision,
                    "shield_risk_level": shield_result.risk_level,
                    "shield_categories": shield_result.categories,
                    "shield_should_route_to_human": shield_result.should_route_to_human,
                    "customer_metadata": ticket.customer_metadata or {},
                    "order_account_metadata": ticket.order_account_metadata or {},
                },
            )
        except Exception as exc:
            self._telemetry.emit(
                OperationFailed(
                    context=context,
                    operation_name=OPERATION_TRIAGE,
                    duration_ms=(time.perf_counter() - started) * 1000,
                    error_category=classify_operation_error(exc),
                    error_type=exc.__class__.__name__,
                    invocation_id=None,
                )
            )
            raise

        invocation_id = LLMInvocationId.new()
        self._telemetry.emit(
            LLMInvocationStarted(
                context=context,
                operation_name=OPERATION_TRIAGE,
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
                response_schema=TriageOutput,
            )
            self._telemetry.emit(
                OperationCompleted(
                    context=context,
                    operation_name=OPERATION_TRIAGE,
                    duration_ms=(time.perf_counter() - started) * 1000,
                )
            )
            return TriageOutcome(
                output=result.parsed,
                execution=result.execution,
                prompt_identity=resolved.identity,
            )
        except Exception as exc:
            self._telemetry.emit(
                OperationFailed(
                    context=context,
                    operation_name=OPERATION_TRIAGE,
                    duration_ms=(time.perf_counter() - started) * 1000,
                    error_category=classify_operation_error(exc),
                    error_type=exc.__class__.__name__,
                    invocation_id=invocation_id,
                )
            )
            raise
