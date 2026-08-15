"""Input Shield application operation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.application.ports.llm import LLMExecutionMetadata, LLMPort
from app.core.exceptions import ModelOutputParsingError, UpstreamServiceError
from app.guardrails.input_guardrails import (
    build_fail_fast_shield_output,
    sanitize_message,
)
from app.prompts.input_shield_prompts import (
    build_input_shield_system_prompt,
    build_input_shield_user_prompt,
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
    def __init__(self, llm: LLMPort, max_prompt_chars: int) -> None:
        self._llm = llm
        self._max_prompt_chars = max_prompt_chars

    async def execute(self, ticket: SupportTicket) -> InputShieldOutcome:
        fail_fast_result = build_fail_fast_shield_output(ticket)
        if fail_fast_result is not None:
            return InputShieldOutcome(
                output=fail_fast_result,
                source="heuristic_fail_fast",
                execution=None,
                error_type=None,
                error_message=None,
            )

        system_prompt = build_input_shield_system_prompt()
        user_prompt = build_input_shield_user_prompt(ticket)
        logical_prompt = _compose_logical_prompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        if len(logical_prompt) > self._max_prompt_chars:
            guardrail_message = (
                "Input guardrail 'max_prompt_length' blocked the request: "
                f"Prompt exceeds max allowed length ({self._max_prompt_chars} chars)."
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
            )

        try:
            result = await self._llm.generate_structured(
                system_prompt=system_prompt,
                prompt=user_prompt,
                response_schema=ShieldOutput,
            )
            normalized = _normalize_llm_shield_output(result.parsed, ticket)
            return InputShieldOutcome(
                output=normalized,
                source="llm",
                execution=result.execution,
                error_type=None,
                error_message=None,
            )
        except (ModelOutputParsingError, UpstreamServiceError) as exc:
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
            )
