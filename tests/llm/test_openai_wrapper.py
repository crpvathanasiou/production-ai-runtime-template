import asyncio
import json
import logging
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
from openai import APIError, APITimeoutError
from pydantic import BaseModel, ConfigDict

from app.application.execution import ExecutionContext, LLMInvocationId
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


class FakeApiErrorStructuredChatCompletions:
    def __init__(self, *, message: str) -> None:
        self.call_count = 0
        self._message = message

    async def parse(self, **kwargs: Any) -> None:
        self.call_count += 1
        raise APIError(
            message=self._message,
            request=MagicMock(),
            body=None,
        )


class FakeApiErrorBetaChat:
    def __init__(self, *, message: str) -> None:
        self.completions = FakeApiErrorStructuredChatCompletions(message=message)


class FakeApiErrorBeta:
    def __init__(self, *, message: str) -> None:
        self.chat = FakeApiErrorBetaChat(message=message)


class FakeApiErrorAsyncOpenAIClient:
    def __init__(self, *, message: str) -> None:
        self.chat = FakeChat()
        self.beta = FakeApiErrorBeta(message=message)


def _exec_context(*, thread_id: str | None = "thread-llm-test") -> ExecutionContext:
    return ExecutionContext(
        request_id="req-llm-test",
        run_id="run-llm-test",
        thread_id=thread_id,
    )


def _invocation_id() -> LLMInvocationId:
    return LLMInvocationId(value="inv-llm-test")


def _provider_log_payloads(caplog: pytest.LogCaptureFixture) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for record in caplog.records:
        if record.name != "app.llm.openai_wrapper":
            continue
        message = record.getMessage()
        if "llm_provider." not in message:
            continue
        payloads.append(json.loads(message))
    return payloads


def _assert_common_provider_fields(
    payload: dict[str, Any],
    *,
    event: str,
    context: ExecutionContext,
    invocation_id: LLMInvocationId,
    model_name: str,
    attempt: int,
    max_attempts: int,
) -> None:
    assert payload["event"] == event
    assert payload["request_id"] == context.request_id
    assert payload["run_id"] == context.run_id
    assert payload["invocation_id"] == invocation_id.value
    assert payload["provider"] == "openai"
    assert payload["model_name"] == model_name
    assert payload["attempt"] == attempt
    assert payload["max_attempts"] == max_attempts
    if context.thread_id is None:
        assert "thread_id" not in payload
    else:
        assert payload["thread_id"] == context.thread_id


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
            context=_exec_context(),
            invocation_id=_invocation_id(),
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
            context=_exec_context(),
            invocation_id=_invocation_id(),
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
            context=_exec_context(),
            invocation_id=_invocation_id(),
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
            context=_exec_context(),
            invocation_id=_invocation_id(),
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
            context=_exec_context(),
            invocation_id=_invocation_id(),
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
            context=_exec_context(),
            invocation_id=_invocation_id(),
            prompt="Classify",
            response_schema=DummyStructuredResponse,
        )

    assert client.beta.chat.completions.call_count == 3
    assert sleeps == [0.5, 1.0]


@pytest.mark.asyncio
async def test_generate_structured_logs_successful_provider_attempt(
    caplog: pytest.LogCaptureFixture,
) -> None:
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
    context = _exec_context(thread_id="thread-success")
    invocation_id = _invocation_id()

    with caplog.at_level(logging.INFO, logger="app.llm.openai_wrapper"):
        result = await wrapper.generate_structured(
            context=context,
            invocation_id=invocation_id,
            prompt="Classify this message",
            response_schema=DummyStructuredResponse,
        )

    payloads = _provider_log_payloads(caplog)
    assert [p["event"] for p in payloads] == [
        "llm_provider.attempt_started",
        "llm_provider.attempt_succeeded",
    ]
    for payload, event in zip(
        payloads,
        ("llm_provider.attempt_started", "llm_provider.attempt_succeeded"),
        strict=True,
    ):
        _assert_common_provider_fields(
            payload,
            event=event,
            context=context,
            invocation_id=invocation_id,
            model_name="gpt-test",
            attempt=1,
            max_attempts=wrapper.max_retries + 1,
        )

    assert isinstance(result.parsed, DummyStructuredResponse)
    assert result.parsed.decision == "allow"
    assert result.attempts == 1
    assert client.beta.chat.completions.call_count == 1


@pytest.mark.asyncio
async def test_generate_structured_retry_logs_preserve_correlation(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
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
    context = _exec_context(thread_id="thread-retry")
    invocation_id = LLMInvocationId(value="inv-retry-continuity")

    with caplog.at_level(logging.INFO, logger="app.llm.openai_wrapper"):
        with pytest.raises(UpstreamServiceError):
            await wrapper.generate_structured(
                context=context,
                invocation_id=invocation_id,
                prompt="Classify",
                response_schema=DummyStructuredResponse,
            )

    assert client.beta.chat.completions.call_count == 3
    assert sleeps == [0.5, 1.0]

    payloads = _provider_log_payloads(caplog)
    assert [p["event"] for p in payloads] == [
        "llm_provider.attempt_started",
        "llm_provider.retry_scheduled",
        "llm_provider.attempt_started",
        "llm_provider.retry_scheduled",
        "llm_provider.attempt_started",
        "llm_provider.failed",
    ]

    for payload in payloads:
        assert payload["request_id"] == context.request_id
        assert payload["run_id"] == context.run_id
        assert payload["thread_id"] == context.thread_id
        assert payload["invocation_id"] == invocation_id.value
        assert payload["provider"] == "openai"
        assert payload["model_name"] == "gpt-test"
        assert payload["max_attempts"] == 3

    assert payloads[0]["attempt"] == 1
    assert payloads[1]["attempt"] == 1
    assert payloads[1]["next_attempt"] == 2
    assert payloads[1]["retry_delay_seconds"] == 0.5
    assert payloads[1]["provider_failure_category"] == "timeout"
    assert payloads[2]["attempt"] == 2
    assert payloads[3]["attempt"] == 2
    assert payloads[3]["next_attempt"] == 3
    assert payloads[3]["retry_delay_seconds"] == 1.0
    assert payloads[4]["attempt"] == 3
    assert payloads[5]["attempt"] == 3
    assert payloads[5]["provider_failure_category"] == "timeout"


@pytest.mark.asyncio
async def test_generate_structured_terminal_timeout_logs_failed(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def fake_sleep(delay: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    client = FakeTimeoutAsyncOpenAIClient()
    wrapper = AsyncOpenAIWrapper(
        client=client,
        default_model="gpt-test",
        default_temperature=0.0,
    )
    wrapper.max_retries = 0
    context = _exec_context(thread_id="thread-timeout")
    invocation_id = _invocation_id()

    with caplog.at_level(logging.INFO, logger="app.llm.openai_wrapper"):
        with pytest.raises(UpstreamServiceError):
            await wrapper.generate_structured(
                context=context,
                invocation_id=invocation_id,
                prompt="Classify",
                response_schema=DummyStructuredResponse,
            )

    payloads = _provider_log_payloads(caplog)
    failed = [p for p in payloads if p["event"] == "llm_provider.failed"]
    assert len(failed) == 1
    _assert_common_provider_fields(
        failed[0],
        event="llm_provider.failed",
        context=context,
        invocation_id=invocation_id,
        model_name="gpt-test",
        attempt=1,
        max_attempts=1,
    )
    assert failed[0]["provider_failure_category"] == "timeout"
    assert failed[0]["error_type"] == "APITimeoutError"
    for payload in payloads:
        assert "Request timed out." not in json.dumps(payload)
        assert "message" not in payload


@pytest.mark.asyncio
async def test_generate_structured_api_error_classification(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def fake_sleep(delay: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    sentinel = "SECRET_PROVIDER_EXCEPTION_SENTINEL"
    client = FakeApiErrorAsyncOpenAIClient(message=sentinel)
    wrapper = AsyncOpenAIWrapper(
        client=client,
        default_model="gpt-test",
        default_temperature=0.0,
    )
    wrapper.max_retries = 0
    context = _exec_context(thread_id="thread-api-error")
    invocation_id = _invocation_id()

    with caplog.at_level(logging.INFO, logger="app.llm.openai_wrapper"):
        with pytest.raises(UpstreamServiceError):
            await wrapper.generate_structured(
                context=context,
                invocation_id=invocation_id,
                prompt="Classify",
                response_schema=DummyStructuredResponse,
            )

    payloads = _provider_log_payloads(caplog)
    assert any(p["event"] == "llm_provider.failed" for p in payloads)
    for payload in payloads:
        if payload["event"] in {"llm_provider.retry_scheduled", "llm_provider.failed"}:
            assert payload["provider_failure_category"] == "api_error"
            assert payload["error_type"] == "APIError"
        assert sentinel not in json.dumps(payload)


@pytest.mark.asyncio
async def test_generate_structured_provider_success_vs_model_output_failure(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = FakeAsyncOpenAIClient(
        parsed_response=None,
        structured_content="SECRET_MODEL_OUTPUT_SENTINEL",
    )
    wrapper = AsyncOpenAIWrapper(
        client=client,
        default_model="gpt-test",
        default_temperature=0.0,
    )
    context = _exec_context()
    invocation_id = _invocation_id()

    with caplog.at_level(logging.INFO, logger="app.llm.openai_wrapper"):
        with pytest.raises(ModelOutputParsingError):
            await wrapper.generate_structured(
                context=context,
                invocation_id=invocation_id,
                prompt="Return structured output",
                response_schema=DummyStructuredResponse,
            )

    payloads = _provider_log_payloads(caplog)
    assert [p["event"] for p in payloads] == [
        "llm_provider.attempt_started",
        "llm_provider.attempt_succeeded",
    ]
    assert not any(p["event"] == "llm_provider.failed" for p in payloads)
    assert client.beta.chat.completions.call_count == 1

    provider_messages = [
        record.getMessage()
        for record in caplog.records
        if record.name == "app.llm.openai_wrapper" and "llm_provider." in record.getMessage()
    ]
    assert provider_messages
    for message in provider_messages:
        assert "SECRET_MODEL_OUTPUT_SENTINEL" not in message


@pytest.mark.asyncio
async def test_generate_structured_provider_logs_data_minimization(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    async def fake_sleep(delay: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", fake_sleep)

    system_sentinel = "SECRET_SYSTEM_PROMPT_SENTINEL"
    prompt_sentinel = "SECRET_PROMPT_SENTINEL"
    exception_sentinel = "SECRET_PROVIDER_EXCEPTION_SENTINEL"
    client = FakeApiErrorAsyncOpenAIClient(message=exception_sentinel)
    wrapper = AsyncOpenAIWrapper(
        client=client,
        default_model="gpt-test",
        default_temperature=0.0,
    )
    wrapper.max_retries = 1
    context = _exec_context(thread_id="thread-minimize")
    invocation_id = LLMInvocationId(value="inv-minimize")

    with caplog.at_level(logging.INFO, logger="app.llm.openai_wrapper"):
        with pytest.raises(UpstreamServiceError):
            await wrapper.generate_structured(
                context=context,
                invocation_id=invocation_id,
                system_prompt=system_sentinel,
                prompt=prompt_sentinel,
                response_schema=DummyStructuredResponse,
            )

    messages = [
        record.getMessage()
        for record in caplog.records
        if record.name == "app.llm.openai_wrapper"
    ]
    joined = "\n".join(messages)
    assert system_sentinel not in joined
    assert prompt_sentinel not in joined
    assert exception_sentinel not in joined
    assert context.request_id in joined
    assert context.run_id in joined
    assert context.thread_id is not None and context.thread_id in joined
    assert invocation_id.value in joined


@pytest.mark.asyncio
async def test_generate_structured_provider_logs_omit_none_thread_id(
    caplog: pytest.LogCaptureFixture,
) -> None:
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
    context = _exec_context(thread_id=None)
    invocation_id = _invocation_id()

    with caplog.at_level(logging.INFO, logger="app.llm.openai_wrapper"):
        await wrapper.generate_structured(
            context=context,
            invocation_id=invocation_id,
            prompt="Classify this message",
            response_schema=DummyStructuredResponse,
        )

    payloads = _provider_log_payloads(caplog)
    assert payloads
    for payload in payloads:
        _assert_common_provider_fields(
            payload,
            event=payload["event"],
            context=context,
            invocation_id=invocation_id,
            model_name="gpt-test",
            attempt=payload["attempt"],
            max_attempts=payload["max_attempts"],
        )
        assert "thread_id" not in payload


def test_openai_wrapper_has_no_direct_langsmith_tracing() -> None:
    source = Path("app/llm/openai_wrapper.py").read_text(encoding="utf-8")
    assert "@traceable" not in source
    assert "from langsmith" not in source
    assert "import langsmith" not in source
