"""Response drafting application operation."""

from __future__ import annotations

from app.application.ports.llm import LLMPort, StructuredLLMResult
from app.prompts.response_drafting_prompts import (
    build_response_drafting_system_prompt,
    build_response_drafting_user_prompt,
)
from app.schemas import ResponseDrafting, RetrievedDocument, SupportTicket, TriageOutput


class ResponseDraftingOperation:
    def __init__(self, llm: LLMPort) -> None:
        self._llm = llm

    async def execute(
        self,
        *,
        ticket: SupportTicket,
        triage_result: TriageOutput,
        retrieved_documents: list[RetrievedDocument],
    ) -> StructuredLLMResult[ResponseDrafting]:
        system_prompt = build_response_drafting_system_prompt()
        user_prompt = build_response_drafting_user_prompt(
            ticket=ticket,
            triage_result=triage_result,
            retrieved_documents=retrieved_documents,
        )
        return await self._llm.generate_structured(
            system_prompt=system_prompt,
            prompt=user_prompt,
            response_schema=ResponseDrafting,
        )
