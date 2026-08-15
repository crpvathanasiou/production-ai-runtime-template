"""Triage application operation."""

from __future__ import annotations

from app.application.ports.llm import LLMPort, StructuredLLMResult
from app.prompts.triage_prompts import (
    build_triage_system_prompt,
    build_triage_user_prompt,
)
from app.schemas import ShieldOutput, SupportTicket, TriageOutput


class TriageOperation:
    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    async def execute(
        self,
        *,
        ticket: SupportTicket,
        shield_result: ShieldOutput,
    ) -> StructuredLLMResult[TriageOutput]:
        system_prompt = build_triage_system_prompt()
        user_prompt = build_triage_user_prompt(
            ticket=ticket,
            shield_result=shield_result,
        )
        return await self._llm.generate_structured(
            system_prompt=system_prompt,
            prompt=user_prompt,
            response_schema=TriageOutput,
        )
