"""Response drafting application operation."""

from __future__ import annotations

import time
from dataclasses import dataclass

from app.application.execution import (
    OPERATION_RESPONSE_DRAFTING,
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
from app.schemas import ResponseDrafting, RetrievedDocument, SupportTicket, TriageOutput


@dataclass(frozen=True)
class ResponseDraftingOutcome:
    output: ResponseDrafting
    execution: LLMExecutionMetadata
    prompt_identity: PromptIdentity


class ResponseDraftingOperation:
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
        triage_result: TriageOutput,
        retrieved_documents: list[RetrievedDocument],
    ) -> ResponseDraftingOutcome:
        started = time.perf_counter()
        self._telemetry.emit(
            OperationStarted(
                context=context,
                operation_name=OPERATION_RESPONSE_DRAFTING,
            )
        )

        if retrieved_documents:
            docs_text = "\n\n".join(
                [
                    f"[Source: {doc.source}]\n{doc.content}"
                    for doc in retrieved_documents
                ]
            )
            retrieval_mode = (
                "Retrieved support context is available below. "
                "Use it for external/policy grounding. "
                "Populate related_documents only from these exact documents."
            )
        else:
            docs_text = "No retrieved documents available."
            retrieval_mode = (
                "No retrieved documents are available for this run. "
                "Return related_documents as an empty list. "
                "Do not invent documents or claim corpus grounding. "
                "Draft a cautious response from ticket and triage context only."
            )

        try:
            resolved = self._prompt_repository.resolve(
                self._prompt_ref,
                variables={
                    "retrieval_mode": retrieval_mode,
                    "customer_message": ticket.customer_message,
                    "triage_issue_category": triage_result.issue_category,
                    "triage_intent": triage_result.intent,
                    "triage_urgency": triage_result.urgency,
                    "triage_customer_tone": triage_result.customer_tone,
                    "triage_requires_escalation": triage_result.requires_escalation,
                    "triage_requires_human_approval": triage_result.requires_human_approval,
                    "triage_reasoning_summary": triage_result.reasoning_summary,
                    "docs_text": docs_text,
                },
            )
        except Exception as exc:
            self._telemetry.emit(
                OperationFailed(
                    context=context,
                    operation_name=OPERATION_RESPONSE_DRAFTING,
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
                operation_name=OPERATION_RESPONSE_DRAFTING,
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
                response_schema=ResponseDrafting,
            )
            self._telemetry.emit(
                OperationCompleted(
                    context=context,
                    operation_name=OPERATION_RESPONSE_DRAFTING,
                    duration_ms=(time.perf_counter() - started) * 1000,
                )
            )
            return ResponseDraftingOutcome(
                output=result.parsed,
                execution=result.execution,
                prompt_identity=resolved.identity,
            )
        except Exception as exc:
            self._telemetry.emit(
                OperationFailed(
                    context=context,
                    operation_name=OPERATION_RESPONSE_DRAFTING,
                    duration_ms=(time.perf_counter() - started) * 1000,
                    error_category=classify_operation_error(exc),
                    error_type=exc.__class__.__name__,
                    invocation_id=invocation_id,
                )
            )
            raise
