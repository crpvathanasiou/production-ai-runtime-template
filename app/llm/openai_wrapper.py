from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Generic, List, Optional, Protocol, Sequence, Type

from openai import APIError, APITimeoutError, AsyncOpenAI
from openai.types.chat import (
    ChatCompletionMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
)
from pydantic import BaseModel

from app.application.execution import ExecutionContext, LLMInvocationId
from app.application.ports.llm import LLMExecutionMetadata, StructuredLLMResult, T
from app.core.exceptions import (
    GuardrailBlockedError,
    ModelOutputParsingError,
    UpstreamServiceError,
)
from app.core.logging import format_operational_log, get_logger
from app.core.settings import get_settings

logger = get_logger(__name__)

# -----------------------------------------------------------------------------
# Protocols
# -----------------------------------------------------------------------------
# Τα Protocols εδώ υπάρχουν για type-safety και testability.
# Μας επιτρέπουν να περνάμε είτε τον πραγματικό AsyncOpenAI client,
# είτε fake/mock client στα tests, χωρίς να δένουμε σφιχτά τον wrapper
# πάνω στην concrete υλοποίηση του SDK.


class ChatCompletionsCreateProtocol(Protocol):
    async def create(self, **kwargs: Any) -> Any: ...


class ChatCompletionsParseProtocol(Protocol):
    async def parse(self, **kwargs: Any) -> Any: ...


class ChatCompletionsProtocol(Protocol):
    @property
    def completions(self) -> ChatCompletionsCreateProtocol: ...


class BetaChatCompletionsProtocol(Protocol):
    @property
    def completions(self) -> ChatCompletionsParseProtocol: ...


class BetaProtocol(Protocol):
    @property
    def chat(self) -> BetaChatCompletionsProtocol: ...


class AsyncOpenAIClientProtocol(Protocol):
    @property
    def chat(self) -> ChatCompletionsProtocol: ...

    @property
    def beta(self) -> BetaProtocol: ...


# T is imported from the application LLM port so LLMCallResult[T] shares the
# same TypeVar as StructuredLLMResult[T] for static assignability.


# -----------------------------------------------------------------------------
# Guardrail models
# -----------------------------------------------------------------------------
# Το αποτέλεσμα ενός guardrail check.
# Κρατάμε:
# - αν πέρασε
# - γιατί απέτυχε (αν απέτυχε)
# - extra metadata για observability / logging


@dataclass
class GuardrailResult:
    passed: bool
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# Base class για guardrails.
# Τα guardrails μπορούν να ελέγχουν:
# - το input prompt πριν φύγει προς το model
# - το output text αφού επιστρέψει το model
#
# Από default δεν μπλοκάρουν τίποτα.


class BaseGuardrail:
    name: str = "base_guardrail"

    def check_input(
        self,
        *,
        prompt: str,
        model_name: str,
        temperature: float,
    ) -> GuardrailResult:
        return GuardrailResult(passed=True)

    def check_output(
        self,
        *,
        prompt: str,
        output_text: str,
        model_name: str,
        temperature: float,
    ) -> GuardrailResult:
        return GuardrailResult(passed=True)


# Απλό deterministic guardrail:
# κόβει request αν το prompt είναι υπερβολικά μεγάλο.
# Αυτό βοηθά:
# - economy
# - predictability
# - protection από accidental huge payloads


class MaxPromptLengthGuardrail(BaseGuardrail):
    name = "max_prompt_length"

    def __init__(self, max_chars: int) -> None:
        self.max_chars = max_chars

    def check_input(
        self,
        *,
        prompt: str,
        model_name: str,
        temperature: float,
    ) -> GuardrailResult:
        if len(prompt) > self.max_chars:
            return GuardrailResult(
                passed=False,
                reason=f"Prompt exceeds max allowed length ({self.max_chars} chars).",
                metadata={"actual_length": len(prompt)},
            )
        return GuardrailResult(passed=True)


# -----------------------------------------------------------------------------
# Wrapper result models
# -----------------------------------------------------------------------------
# LLMCallResult: legacy/general adapter result for text generation.
# parsed may be None.
#
# OpenAIStructuredResult: structured-generation adapter result.
# Structurally compatible with StructuredLLMResult[T] (parsed: T is mandatory)
# while preserving the live adapter surface used by nodes.


@dataclass
class LLMCallResult(Generic[T]):
    model_name: str
    raw_text: str
    parsed: T | None = None
    guardrail_notes: List[Dict[str, Any]] = field(default_factory=list)
    raw_response: Any = None
    latency_ms: float = 0.0
    attempts: int = 1


@dataclass(frozen=True)
class OpenAIStructuredResult(StructuredLLMResult[T], Generic[T]):
    model_name: str
    raw_text: str
    guardrail_notes: list[dict[str, Any]] = field(default_factory=list)
    raw_response: Any = None

    @property
    def latency_ms(self) -> float:
        return self.execution.latency_ms

    @property
    def attempts(self) -> int:
        return self.execution.attempts


# -----------------------------------------------------------------------------
# Async OpenAI Wrapper
# -----------------------------------------------------------------------------
# Αυτός είναι ο βασικός async wrapper που θα χρησιμοποιούν τα nodes.
#
# Στόχοι:
# - async I/O
# - central config
# - retries / timeout handling
# - guardrails
# - structured output support
# - observability-friendly result object


class AsyncOpenAIWrapper:
    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        client: Optional[AsyncOpenAIClientProtocol] = None,
        default_model: Optional[str] = None,
        default_temperature: float = 0.0,
    ) -> None:
        settings = get_settings()

        # Αν δοθεί custom client (π.χ. στα tests), τον χρησιμοποιούμε.
        # Αλλιώς φτιάχνουμε πραγματικό AsyncOpenAI client.
        self.client = client or AsyncOpenAI(
            api_key=api_key or os.getenv("OPENAI_API_KEY") or settings.openai_api_key,
            timeout=settings.openai_timeout_seconds,
            max_retries=0,  # retries τα χειριζόμαστε εμείς, όχι το SDK
        )

        # Default model/temperature για να μη χρειάζεται κάθε node
        # να τα περνά πάντα χειροκίνητα.
        self.default_model = default_model or settings.openai_model_input_shield
        self.default_temperature = default_temperature

        # Centralized timeout / retry policy από settings.
        self.timeout_seconds = settings.openai_timeout_seconds
        self.max_retries = settings.openai_max_retries


    # -------------------------------------------------------------------------
    # Plain text generation
    # -------------------------------------------------------------------------
    # Χρήση όταν θες ελεύθερο text output.
    # Δεν κάνει parsing σε schema, μόνο raw text extraction.
    async def generate_text(
        self,
        *,
        prompt: str,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        enforced_guardrails: Optional[Sequence[BaseGuardrail]] = None,
        system_prompt: Optional[str] = None,
        ) -> LLMCallResult[BaseModel]:
        model = model_name or self.default_model
        temp = self.default_temperature if temperature is None else temperature
        guardrails = list(enforced_guardrails or [])

        # Input guardrails τρέχουν πριν γίνει το API call.
        guardrail_notes = self._run_input_guardrails(
            prompt=prompt,
            model_name=model,
            temperature=temp,
            guardrails=guardrails,
        )

        start = time.perf_counter()
        last_error: Optional[Exception] = None

        # Μετατρέπουμε system/user prompts στο format που θέλει το Chat Completions API.
        messages = self._build_messages(
            system_prompt=system_prompt,
            user_prompt=prompt,
            )

        # Retry loop.
        # Αν max_retries=2, θα έχουμε attempts: 1, 2, 3 συνολικά.
        for attempt in range(1, self.max_retries + 2):
            try:
                # Το asyncio.wait_for βάζει explicit timeout πάνω από το await.
                # Έτσι κρατάμε deterministic timeout behavior.
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=temp,
                    ),
                    timeout=self.timeout_seconds,
                )

                # Extract το text από το SDK response.
                raw_text = self._extract_chat_text(response)

                # Output guardrails τρέχουν αφού επιστρέψει το model.
                guardrail_notes.extend(
                    self._run_output_guardrails(
                        prompt=prompt,
                        output_text=raw_text,
                        model_name=model,
                        temperature=temp,
                        guardrails=guardrails,
                    )
                )

                latency_ms = round((time.perf_counter() - start) * 1000, 2)

                return LLMCallResult(
                    model_name=model,
                    raw_text=raw_text,
                    parsed=None,
                    guardrail_notes=guardrail_notes,
                    raw_response=response,
                    latency_ms=latency_ms,
                    attempts=attempt,
                )

            # Αυτά θεωρούνται upstream / transport failures:
            # timeout, API timeout, generic API error.
            # Είναι retryable μέχρι να εξαντληθούν τα attempts.
            except (asyncio.TimeoutError, APITimeoutError, APIError) as exc:
                last_error = exc
                if attempt > self.max_retries:
                    raise UpstreamServiceError(
                        f"OpenAI text request failed after {attempt} attempt(s): {exc}"
                    ) from exc

                # Απλό linear backoff.
                await asyncio.sleep(0.5 * attempt)

            # Οτιδήποτε άλλο εδώ θεωρείται upstream/transport failure.
            # Το κρατάμε ξεχωριστό από parsing/schema/logic failures.
            except Exception as exc:
                raise UpstreamServiceError(
                    f"OpenAI text request failed with unexpected upstream error: {exc}"
                ) from exc

        raise UpstreamServiceError(f"OpenAI text request failed: {last_error}")

    # -------------------------------------------------------------------------
    # Structured generation
    # -------------------------------------------------------------------------
    # Χρήση όταν θες typed structured output σε Pydantic schema.
    #
    # Εδώ χρησιμοποιούμε SDK-native structured parsing:
    # client.beta.chat.completions.parse(...)
    #
    # Άρα ΔΕΝ βασιζόμαστε κυρίως σε:
    # - prompt-only "return JSON"
    # - manual json.loads()
    # - manual schema parsing σαν primary mechanism
    #
    # Public method stays thin so TypeVar inference / LLMPort assignability
    # are preserved; provider attempt work lives on the private impl below.
    async def generate_structured(
        self,
        *,
        context: ExecutionContext,
        invocation_id: LLMInvocationId,
        prompt: str,
        response_schema: Type[T],
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        enforced_guardrails: Optional[Sequence[BaseGuardrail]] = None,
        system_prompt: Optional[str] = None,
    ) -> OpenAIStructuredResult[T]:
        """
        Strict structured path.

        Uses SDK-native structured parsing instead of:
        - prompt-only JSON instructions
        - manual json.loads()
        - manual schema enforcement as the primary mechanism
        """
        return await self._generate_structured_impl(
            context=context,
            invocation_id=invocation_id,
            prompt=prompt,
            response_schema=response_schema,
            model_name=model_name,
            temperature=temperature,
            enforced_guardrails=enforced_guardrails,
            system_prompt=system_prompt,
        )

    async def _generate_structured_impl(
        self,
        *,
        context: ExecutionContext,
        invocation_id: LLMInvocationId,
        prompt: str,
        response_schema: Type[T],
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        enforced_guardrails: Optional[Sequence[BaseGuardrail]] = None,
        system_prompt: Optional[str] = None,
    ) -> OpenAIStructuredResult[T]:
        model = model_name or self.default_model
        temp = self.default_temperature if temperature is None else temperature
        guardrails = list(enforced_guardrails or [])
        max_attempts = self.max_retries + 1

        # Αυτό είναι ένα "λογικό prompt" για purposes guardrails/logging.
        # Δηλαδή συνδυάζουμε system + user prompt σε ένα ενιαίο string
        # ώστε τα guardrails να βλέπουν όλο το semantic input.
        logical_prompt = self._compose_logical_prompt(
            system_prompt=system_prompt,
            user_prompt=prompt,
        )

        guardrail_notes = self._run_input_guardrails(
            prompt=logical_prompt,
            model_name=model,
            temperature=temp,
            guardrails=guardrails,
        )

        start = time.perf_counter()
        last_error: Optional[Exception] = None

        messages = self._build_messages(
            system_prompt=system_prompt,
            user_prompt=prompt,
        )

        for attempt in range(1, self.max_retries + 2):
            self._log_provider_event(
                "llm_provider.attempt_started",
                context=context,
                invocation_id=invocation_id,
                model_name=model,
                attempt=attempt,
                max_attempts=max_attempts,
            )
            try:
                # SDK-native structured parsing.
                # Το SDK επιστρέφει parsed object με βάση το response_schema.
                completion = await asyncio.wait_for(
                    self.client.beta.chat.completions.parse(
                        model=model,
                        messages=messages,
                        temperature=temp,
                        response_format=response_schema,
                    ),
                    timeout=self.timeout_seconds,
                )

                # Provider/SDK request succeeded. Later parsing/application
                # failures must not be labeled as llm_provider.failed.
                self._log_provider_event(
                    "llm_provider.attempt_succeeded",
                    context=context,
                    invocation_id=invocation_id,
                    model_name=model,
                    attempt=attempt,
                    max_attempts=max_attempts,
                )

                message = completion.choices[0].message
                parsed = message.parsed
                raw_text = message.content or ""

                # Αν το SDK δεν μπόρεσε να παράξει parsed object,
                # το θεωρούμε schema/parsing failure.
                if parsed is None:
                    raise ModelOutputParsingError(
                        f"Structured response parsing returned None for schema '{response_schema.__name__}'."
                    )

                # Output guardrails τρέχουν και στο structured path.
                # Μπορεί να θες semantic validation και εδώ.
                guardrail_notes.extend(
                    self._run_output_guardrails(
                        prompt=logical_prompt,
                        output_text=raw_text,
                        model_name=model,
                        temperature=temp,
                        guardrails=guardrails,
                    )
                )

                latency_ms = round((time.perf_counter() - start) * 1000, 2)

                return OpenAIStructuredResult[T](
                    parsed=parsed,
                    execution=LLMExecutionMetadata(
                        latency_ms=latency_ms,
                        attempts=attempt,
                    ),
                    model_name=model,
                    raw_text=raw_text,
                    guardrail_notes=guardrail_notes,
                    raw_response=completion,
                )

            # Upstream/transport failures => retryable
            except (asyncio.TimeoutError, APITimeoutError, APIError) as exc:
                last_error = exc
                failure_category = self._provider_failure_category(exc)
                error_type = type(exc).__name__
                if attempt > self.max_retries:
                    self._log_provider_event(
                        "llm_provider.failed",
                        context=context,
                        invocation_id=invocation_id,
                        model_name=model,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        provider_failure_category=failure_category,
                        error_type=error_type,
                    )
                    raise UpstreamServiceError(
                        f"OpenAI structured request failed after {attempt} attempt(s): {exc}"
                    ) from exc

                retry_delay_seconds = 0.5 * attempt
                self._log_provider_event(
                    "llm_provider.retry_scheduled",
                    context=context,
                    invocation_id=invocation_id,
                    model_name=model,
                    attempt=attempt,
                    max_attempts=max_attempts,
                    next_attempt=attempt + 1,
                    retry_delay_seconds=retry_delay_seconds,
                    provider_failure_category=failure_category,
                    error_type=error_type,
                )
                await asyncio.sleep(retry_delay_seconds)

            # Οτιδήποτε άλλο εδώ θεωρείται parsing/schema/logic failure.
            # Το κρατάμε ξεχωριστό από transport failures.
            except Exception as exc:
                if isinstance(exc, (GuardrailBlockedError, ModelOutputParsingError)):
                    raise

                raise ModelOutputParsingError(
                    f"Structured parsing failed for schema '{response_schema.__name__}': {exc}"
                ) from exc

        raise UpstreamServiceError(f"OpenAI structured request failed: {last_error}")

    @staticmethod
    def _provider_failure_category(exc: Exception) -> str:
        if isinstance(exc, APITimeoutError):
            return "timeout"
        if isinstance(exc, asyncio.TimeoutError):
            return "timeout"
        if isinstance(exc, APIError):
            return "api_error"
        raise TypeError(f"Unsupported provider failure type: {type(exc).__name__}")

    @staticmethod
    def _log_provider_event(
        event: str,
        *,
        context: ExecutionContext,
        invocation_id: LLMInvocationId,
        model_name: str,
        attempt: int,
        max_attempts: int,
        **fields: Any,
    ) -> None:
        logger.info(
            format_operational_log(
                event,
                request_id=context.request_id,
                run_id=context.run_id,
                thread_id=context.thread_id,
                invocation_id=invocation_id.value,
                provider="openai",
                model_name=model_name,
                attempt=attempt,
                max_attempts=max_attempts,
                **fields,
            ),
        )

    # -------------------------------------------------------------------------
    # Guardrail execution
    # -------------------------------------------------------------------------
    # Τρέχει όλα τα input guardrails και επιστρέφει notes για observability.
    # Αν κάποιο guardrail αποτύχει, σηκώνει GuardrailBlockedError.
    def _run_input_guardrails(
        self,
        *,
        prompt: str,
        model_name: str,
        temperature: float,
        guardrails: Sequence[BaseGuardrail],
    ) -> List[Dict[str, Any]]:
        notes: List[Dict[str, Any]] = []

        for guardrail in guardrails:
            result = guardrail.check_input(
                prompt=prompt,
                model_name=model_name,
                temperature=temperature,
            )
            notes.append(
                {
                    "guardrail": guardrail.name,
                    "stage": "input",
                    "passed": result.passed,
                    "reason": result.reason,
                    "metadata": result.metadata,
                }
            )
            if not result.passed:
                raise GuardrailBlockedError(
                    f"Input guardrail '{guardrail.name}' blocked the request: {result.reason}"
                )

        return notes

    # Αντίστοιχα για output guardrails.
    def _run_output_guardrails(
        self,
        *,
        prompt: str,
        output_text: str,
        model_name: str,
        temperature: float,
        guardrails: Sequence[BaseGuardrail],
    ) -> List[Dict[str, Any]]:
        notes: List[Dict[str, Any]] = []

        for guardrail in guardrails:
            result = guardrail.check_output(
                prompt=prompt,
                output_text=output_text,
                model_name=model_name,
                temperature=temperature,
            )
            notes.append(
                {
                    "guardrail": guardrail.name,
                    "stage": "output",
                    "passed": result.passed,
                    "reason": result.reason,
                    "metadata": result.metadata,
                }
            )
            if not result.passed:
                raise GuardrailBlockedError(
                    f"Output guardrail '{guardrail.name}' blocked the response: {result.reason}"
                )

        return notes

    # -------------------------------------------------------------------------
    # Prompt/message helpers
    # -------------------------------------------------------------------------
    # Μετατρέπει system/user prompts στη δομή messages που περιμένει το SDK.
    @staticmethod
    def _build_messages(
        *,
        system_prompt: Optional[str],
        user_prompt: str,
    ) -> list[ChatCompletionMessageParam]:
        messages: list[ChatCompletionMessageParam] = []

        if system_prompt and system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": user_prompt})
        return messages

    # Χρήσιμο για logging / guardrails / semantic inspection.
    # Δεν στέλνεται αυτούσιο στο API· είναι λογική αναπαράσταση του πλήρους prompt.
    @staticmethod
    def _compose_logical_prompt(
        *,
        system_prompt: Optional[str],
        user_prompt: str,
    ) -> str:
        if system_prompt and system_prompt.strip():
            return f"[SYSTEM]\n{system_prompt}\n\n[USER]\n{user_prompt}"
        return user_prompt

    # -------------------------------------------------------------------------
    # Response extraction helper
    # -------------------------------------------------------------------------
    # Προσπαθεί να εξάγει plain text από standard chat completion response.
    # Το κρατάμε defensive γιατί το SDK shape μπορεί να έχει μικρές διαφορές.
    @staticmethod
    def _extract_chat_text(response: Any) -> str:
        try:
            message = response.choices[0].message
            content = getattr(message, "content", None)

            # Συνήθης περίπτωση: string content
            if isinstance(content, str) and content.strip():
                return content

            # Εναλλακτική περίπτωση: list of content parts
            if isinstance(content, list):
                chunks: List[str] = []
                for item in content:
                    text = getattr(item, "text", None)
                    if isinstance(text, str):
                        chunks.append(text)
                joined = "\n".join(c for c in chunks if c).strip()
                if joined:
                    return joined
        except Exception:
            pass

        raise UpstreamServiceError("Could not extract text from chat completion response.")
