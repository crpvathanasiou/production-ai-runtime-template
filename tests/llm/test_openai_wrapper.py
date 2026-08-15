import asyncio
from typing import Any
from unittest.mock import MagicMock

import pytest
from openai import APITimeoutError
from pydantic import BaseModel, ConfigDict

from app.application.ports.llm import LLMPort, StructuredLLMResult
from app.core.exceptions import (
    GuardrailBlockedError,
    ModelOutputParsingError,
    UpstreamServiceError,
)
from app.llm.openai_wrapper import (
    AsyncOpenAIWrapper,
    BaseGuardrail,
    GuardrailResult,
    LLMCallResult,
    MaxPromptLengthGuardrail,
    OpenAIStructuredResult,
)

"""
Καλύπτει βασικά cases:

generate_text επιστρέφει plain text σωστά
generate_structured επιστρέφει parsed Pydantic object
input guardrail μπλοκάρει request
max prompt length guardrail δουλεύει
structured parsing αποτυγχάνει όταν parsed is None
text upstream failure γίνεται UpstreamServiceError
structured unexpected failure γίνεται ModelOutputParsingError
LLMPort static compatibility
application execution metadata + live adapter surface
retry/backoff → UpstreamServiceError
blocking guardrail prevents provider call
"""


class DummyStructuredResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: str
    risk_level: str


class RejectAllGuardrail(BaseGuardrail):
    name = "reject_all"

    def check_input(self, *, prompt: str, model_name: str, temperature: float) -> GuardrailResult:
        return GuardrailResult(
            passed=False,
            reason="Rejected by test guardrail.",
        )


class FakeTextMessage:
    def __init__(self, content: str) -> None:
        self.content = content


class FakeTextChoice:
    def __init__(self, content: str) -> None:
        self.message = FakeTextMessage(content)


class FakeTextCompletion:
    def __init__(self, content: str) -> None:
        self.choices = [FakeTextChoice(content)]


class FakeStructuredMessage:
    def __init__(self, parsed: Any = None, content: str = "") -> None:
        self.parsed = parsed
        self.content = content


class FakeStructuredChoice:
    def __init__(self, parsed: Any = None, content: str = "") -> None:
        self.message = FakeStructuredMessage(parsed=parsed, content=content)


class FakeStructuredCompletion:
    def __init__(self, parsed: Any = None, content: str = "") -> None:
        self.choices = [FakeStructuredChoice(parsed=parsed, content=content)]


class FakeChatCompletions:
    def __init__(self, text_response: str = "ok") -> None:
        self._text_response = text_response
        self.call_count = 0

    async def create(self, **kwargs: Any) -> FakeTextCompletion:
        self.call_count += 1
        return FakeTextCompletion(self._text_response)


class FakeBetaChatCompletions:
    def __init__(self, parsed_response: Any = None, content: str = "") -> None:
        self._parsed_response = parsed_response
        self._content = content
        self.call_count = 0

    async def parse(self, **kwargs: Any) -> FakeStructuredCompletion:
        self.call_count += 1
        return FakeStructuredCompletion(
            parsed=self._parsed_response,
            content=self._content,
        )


class FakeChat:
    def __init__(self, text_response: str = "ok") -> None:
        self.completions = FakeChatCompletions(text_response=text_response)


class FakeBetaChat:
    def __init__(self, parsed_response: Any = None, content: str = "") -> None:
        self.completions = FakeBetaChatCompletions(
            parsed_response=parsed_response,
            content=content,
        )


class FakeBeta:
    def __init__(self, parsed_response: Any = None, content: str = "") -> None:
        self.chat = FakeBetaChat(
            parsed_response=parsed_response,
            content=content,
        )


class FakeAsyncOpenAIClient:
    def __init__(
        self,
        *,
        text_response: str = "plain text response",
        parsed_response: Any = None,
        structured_content: str = '{"decision":"allow","risk_level":"low"}',
    ) -> None:
        self.chat = FakeChat(text_response=text_response)
        self.beta = FakeBeta(
            parsed_response=parsed_response,
            content=structured_content,
        )


class FakeFailingTextChatCompletions:
    call_count = 0

    async def create(self, **kwargs: Any) -> None:
        type(self).call_count += 1
        raise RuntimeError("text call failed")


class FakeFailingStructuredChatCompletions:
    call_count = 0

    async def parse(self, **kwargs: Any) -> None:
        type(self).call_count += 1
        raise RuntimeError("structured parse failed")


class FakeFailingChat:
    def __init__(self) -> None:
        self.completions = FakeFailingTextChatCompletions()


class FakeFailingBetaChat:
    def __init__(self) -> None:
        self.completions = FakeFailingStructuredChatCompletions()


class FakeFailingBeta:
    def __init__(self) -> None:
        self.chat = FakeFailingBetaChat()


class FakeFailingAsyncOpenAIClient:
    def __init__(self) -> None:
        self.chat = FakeFailingChat()
        self.beta = FakeFailingBeta()


class FakeTimeoutStructuredChatCompletions:
    def __init__(self) -> None:
        self.call_count = 0

    async def parse(self, **kwargs: Any) -> None:
        self.call_count += 1
        raise APITimeoutError(request=MagicMock())


class FakeTimeoutBetaChat:
    def __init__(self) -> None:
        self.completions = FakeTimeoutStructuredChatCompletions()


class FakeTimeoutBeta:
    def __init__(self) -> None:
        self.chat = FakeTimeoutBetaChat()


class FakeTimeoutAsyncOpenAIClient:
    def __init__(self) -> None:
        self.chat = FakeChat()
        self.beta = FakeTimeoutBeta()


def test_async_openai_wrapper_satisfies_llm_port_statically() -> None:
    """Pyright verifies AsyncOpenAIWrapper is assignable to LLMPort."""

    def require_llm_port(port: LLMPort) -> LLMPort:
        return port

    client = FakeAsyncOpenAIClient(
        parsed_response=DummyStructuredResponse(decision="allow", risk_level="low"),
    )
    wrapper = AsyncOpenAIWrapper(
        client=client,
        default_model="gpt-test",
        default_temperature=0.0,
    )
    bound: LLMPort = require_llm_port(wrapper)
    assert bound is wrapper


@pytest.mark.asyncio
async def test_generate_text_returns_plain_text_result():
    client = FakeAsyncOpenAIClient(text_response="hello from model")

    wrapper = AsyncOpenAIWrapper(
        client=client,
        default_model="gpt-test",
        default_temperature=0.0,
    )

    result = await wrapper.generate_text(
        prompt="Say hello",
    )

    assert result.model_name == "gpt-test"
    assert result.raw_text == "hello from model"
    assert result.parsed is None
    assert isinstance(result, LLMCallResult)
    assert not isinstance(result, OpenAIStructuredResult)
    assert result.attempts == 1
    assert result.latency_ms >= 0.0
    assert client.chat.completions.call_count == 1


@pytest.mark.asyncio
async def test_generate_structured_returns_parsed_pydantic_object():
    parsed = DummyStructuredResponse(
        decision="allow",
        risk_level="low",
    )
    client = FakeAsyncOpenAIClient(
        parsed_response=parsed,
        structured_content='{"decision":"allow","risk_level":"low"}',
    )

    wrapper = AsyncOpenAIWrapper(
        client=client,
        default_model="gpt-test",
        default_temperature=0.0,
    )

    result = await wrapper.generate_structured(
        prompt="Classify this message",
        response_schema=DummyStructuredResponse,
    )

    assert isinstance(result, OpenAIStructuredResult)
    assert result.model_name == "gpt-test"
    assert result.parsed is not None
    assert isinstance(result.parsed, DummyStructuredResponse)
    assert result.parsed.decision == "allow"
    assert result.parsed.risk_level == "low"
    assert result.attempts == 1
    assert result.latency_ms >= 0.0
    assert result.execution.latency_ms == result.latency_ms
    assert result.execution.attempts == result.attempts
    assert client.beta.chat.completions.call_count == 1


@pytest.mark.asyncio
async def test_generate_structured_matches_application_structured_result_contract():
    parsed = DummyStructuredResponse(decision="allow", risk_level="low")
    client = FakeAsyncOpenAIClient(
        parsed_response=parsed,
        structured_content='{"decision":"allow","risk_level":"low"}',
    )
    wrapper = AsyncOpenAIWrapper(
        client=client,
        default_model="gpt-test",
        default_temperature=0.0,
    )

    result = await wrapper.generate_structured(
        system_prompt="system",
        prompt="Classify this message",
        response_schema=DummyStructuredResponse,
    )

    structured: OpenAIStructuredResult[DummyStructuredResponse] = result
    application_view: StructuredLLMResult[DummyStructuredResponse] = structured
    assert application_view.parsed.decision == "allow"
    assert application_view.parsed.risk_level == "low"
    assert application_view.execution.attempts == 1
    assert application_view.execution.latency_ms >= 0.0
    # Live adapter surface remains available alongside the application contract.
    assert structured.model_name == "gpt-test"
    assert structured.latency_ms == application_view.execution.latency_ms
    assert structured.attempts == application_view.execution.attempts
    assert client.beta.chat.completions.call_count == 1


@pytest.mark.asyncio
async def test_generate_text_blocks_when_input_guardrail_fails():
    client = FakeAsyncOpenAIClient()

    wrapper = AsyncOpenAIWrapper(
        client=client,
        default_model="gpt-test",
        default_temperature=0.0,
    )

    with pytest.raises(GuardrailBlockedError):
        await wrapper.generate_text(
            prompt="This should be blocked",
            enforced_guardrails=[RejectAllGuardrail()],
        )

    assert client.chat.completions.call_count == 0


@pytest.mark.asyncio
async def test_generate_structured_blocks_when_prompt_too_long():
    client = FakeAsyncOpenAIClient(
        parsed_response=DummyStructuredResponse(decision="allow", risk_level="low")
    )

    wrapper = AsyncOpenAIWrapper(
        client=client,
        default_model="gpt-test",
        default_temperature=0.0,
    )

    with pytest.raises(GuardrailBlockedError):
        await wrapper.generate_structured(
            prompt="x" * 100,
            response_schema=DummyStructuredResponse,
            enforced_guardrails=[MaxPromptLengthGuardrail(max_chars=10)],
        )

    assert client.beta.chat.completions.call_count == 0


@pytest.mark.asyncio
async def test_generate_structured_raises_parsing_error_when_parsed_is_none():
    client = FakeAsyncOpenAIClient(
        parsed_response=None,
        structured_content="",
    )

    wrapper = AsyncOpenAIWrapper(
        client=client,
        default_model="gpt-test",
        default_temperature=0.0,
    )

    with pytest.raises(ModelOutputParsingError):
        await wrapper.generate_structured(
            prompt="Return structured output",
            response_schema=DummyStructuredResponse,
        )

    assert client.beta.chat.completions.call_count == 1


@pytest.mark.asyncio
async def test_generate_text_raises_upstream_error_on_transport_failure():
    FakeFailingTextChatCompletions.call_count = 0
    client = FakeFailingAsyncOpenAIClient()

    wrapper = AsyncOpenAIWrapper(
        client=client,
        default_model="gpt-test",
        default_temperature=0.0,
    )
    wrapper.max_retries = 0

    with pytest.raises(UpstreamServiceError):
        await wrapper.generate_text(
            prompt="Hello",
        )


@pytest.mark.asyncio
async def test_generate_structured_raises_parsing_error_on_unexpected_failure():
    FakeFailingStructuredChatCompletions.call_count = 0
    client = FakeFailingAsyncOpenAIClient()

    wrapper = AsyncOpenAIWrapper(
        client=client,
        default_model="gpt-test",
        default_temperature=0.0,
    )
    wrapper.max_retries = 0

    with pytest.raises(ModelOutputParsingError):
        await wrapper.generate_structured(
            prompt="Classify",
            response_schema=DummyStructuredResponse,
        )


@pytest.mark.asyncio
async def test_generate_structured_retries_timeout_then_raises_upstream(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sleeps: list[float] = []

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    client = FakeTimeoutAsyncOpenAIClient()
    wrapper = AsyncOpenAIWrapper(
        client=client,
        default_model="gpt-test",
        default_temperature=0.0,
    )
    wrapper.max_retries = 2

    with pytest.raises(UpstreamServiceError):
        await wrapper.generate_structured(
            prompt="Classify",
            response_schema=DummyStructuredResponse,
        )

    assert client.beta.chat.completions.call_count == 3
    assert sleeps == [0.5, 1.0]
