"""Triage application operation."""

from __future__ import annotations

from dataclasses import dataclass

from app.application.ports.llm import LLMExecutionMetadata, LLMPort
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
    ) -> None:
        self._llm = llm
        self._prompt_repository = prompt_repository
        self._prompt_ref = prompt_ref

    async def execute(
        self,
        *,
        ticket: SupportTicket,
        shield_result: ShieldOutput,
    ) -> TriageOutcome:
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
        result = await self._llm.generate_structured(
            system_prompt=resolved.system_prompt,
            prompt=resolved.user_prompt,
            response_schema=TriageOutput,
        )
        return TriageOutcome(
            output=result.parsed,
            execution=result.execution,
            prompt_identity=resolved.identity,
        )
