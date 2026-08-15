"""Composition-root wiring tests — no live provider calls."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import app.composition as composition_module
from app.application.input_shield import InputShieldOperation
from app.application.planner import PlannerOperation
from app.application.response_drafting import ResponseDraftingOperation
from app.application.triage import TriageOperation
from app.prompts.input_shield_prompts import INPUT_SHIELD_PROMPT_V1
from app.prompts.local_repository import LocalPromptRepository
from app.prompts.planner_prompts import PLANNER_PROMPT_V1
from app.prompts.response_drafting_prompts import RESPONSE_DRAFTING_PROMPT_V1
from app.prompts.triage_prompts import TRIAGE_PROMPT_V1
from app.telemetry import StdlibTelemetry


class FakeWrapper:
    instances: list[FakeWrapper] = []

    def __init__(
        self,
        *,
        default_model: str | None = None,
        default_temperature: float = 0.0,
        **_: Any,
    ) -> None:
        self.default_model = default_model
        self.default_temperature = default_temperature
        FakeWrapper.instances.append(self)


def test_build_runtime_graph_wires_four_configured_adapters(monkeypatch):
    FakeWrapper.instances = []
    captured: dict[str, Any] = {}

    settings = SimpleNamespace(
        openai_model_input_shield="model-input-shield",
        openai_model_planner="model-planner",
        openai_model_response_drafting="model-response-drafting",
        input_shield_temperature=0.3,
        input_shield_max_prompt_chars=9000,
    )

    monkeypatch.setattr(composition_module, "get_settings", lambda: settings)
    monkeypatch.setattr(composition_module, "AsyncOpenAIWrapper", FakeWrapper)

    def fake_build_graph(**kwargs: Any):
        captured.update(kwargs)
        return "compiled-graph"

    monkeypatch.setattr(composition_module, "build_graph", fake_build_graph)

    result = composition_module.build_runtime_graph()

    assert result == "compiled-graph"
    assert len(FakeWrapper.instances) == 4

    input_shield_llm, triage_llm, planner_llm, drafting_llm = FakeWrapper.instances

    assert input_shield_llm.default_model == "model-input-shield"
    assert input_shield_llm.default_temperature == 0.3

    assert triage_llm.default_model == "model-input-shield"
    assert triage_llm.default_temperature == 0.0

    assert planner_llm.default_model == "model-planner"
    assert planner_llm.default_temperature == 0.0

    assert drafting_llm.default_model == "model-response-drafting"
    assert drafting_llm.default_temperature == 0.0

    assert isinstance(captured["input_shield_operation"], InputShieldOperation)
    assert isinstance(captured["triage_operation"], TriageOperation)
    assert isinstance(captured["planner_operation"], PlannerOperation)
    assert isinstance(captured["response_drafting_operation"], ResponseDraftingOperation)

    assert captured["input_shield_operation"]._llm is input_shield_llm
    assert captured["triage_operation"]._llm is triage_llm
    assert captured["planner_operation"]._llm is planner_llm
    assert captured["response_drafting_operation"]._llm is drafting_llm

    assert captured["input_shield_operation"]._max_prompt_chars == 9000

    assert captured["input_shield_model_name"] == "model-input-shield"
    assert captured["triage_model_name"] == "model-input-shield"
    assert captured["planner_model_name"] == "model-planner"
    assert captured["response_drafting_model_name"] == "model-response-drafting"

    repos = [
        captured["input_shield_operation"]._prompt_repository,
        captured["triage_operation"]._prompt_repository,
        captured["planner_operation"]._prompt_repository,
        captured["response_drafting_operation"]._prompt_repository,
    ]
    assert all(isinstance(repo, LocalPromptRepository) for repo in repos)
    assert repos[0] is repos[1] is repos[2] is repos[3]

    shared_repo = repos[0]
    assert isinstance(shared_repo, LocalPromptRepository)
    assert set(shared_repo._definitions.keys()) == {
        INPUT_SHIELD_PROMPT_V1.ref,
        TRIAGE_PROMPT_V1.ref,
        PLANNER_PROMPT_V1.ref,
        RESPONSE_DRAFTING_PROMPT_V1.ref,
    }

    assert captured["input_shield_operation"]._prompt_ref == INPUT_SHIELD_PROMPT_V1.ref
    assert captured["triage_operation"]._prompt_ref == TRIAGE_PROMPT_V1.ref
    assert captured["planner_operation"]._prompt_ref == PLANNER_PROMPT_V1.ref
    assert (
        captured["response_drafting_operation"]._prompt_ref
        == RESPONSE_DRAFTING_PROMPT_V1.ref
    )

    telemetries = [
        captured["input_shield_operation"]._telemetry,
        captured["triage_operation"]._telemetry,
        captured["planner_operation"]._telemetry,
        captured["response_drafting_operation"]._telemetry,
    ]
    assert all(isinstance(item, StdlibTelemetry) for item in telemetries)
    assert telemetries[0] is telemetries[1] is telemetries[2] is telemetries[3]


def test_build_runtime_graph_planner_fallback_to_input_shield(monkeypatch):
    FakeWrapper.instances = []
    captured: dict[str, Any] = {}

    # No openai_model_planner → getattr falls back to input-shield model.
    # openai_model_planner is still present for response-drafting getattr default
    # evaluation parity with the previous node-local resolution.
    settings = SimpleNamespace(
        openai_model_input_shield="model-input-shield",
        openai_model_response_drafting="model-response-drafting",
        input_shield_temperature=0.0,
        input_shield_max_prompt_chars=12000,
    )

    monkeypatch.setattr(composition_module, "get_settings", lambda: settings)
    monkeypatch.setattr(composition_module, "AsyncOpenAIWrapper", FakeWrapper)
    monkeypatch.setattr(
        composition_module,
        "build_graph",
        lambda **kwargs: captured.update(kwargs) or "graph",
    )

    composition_module.build_runtime_graph()

    assert FakeWrapper.instances[2].default_model == "model-input-shield"
    assert captured["planner_model_name"] == "model-input-shield"


def test_build_runtime_graph_response_drafting_fallback_to_planner(monkeypatch):
    FakeWrapper.instances = []
    captured: dict[str, Any] = {}

    settings = SimpleNamespace(
        openai_model_input_shield="model-input-shield",
        openai_model_planner="model-planner",
        input_shield_temperature=0.0,
        input_shield_max_prompt_chars=12000,
    )

    monkeypatch.setattr(composition_module, "get_settings", lambda: settings)
    monkeypatch.setattr(composition_module, "AsyncOpenAIWrapper", FakeWrapper)
    monkeypatch.setattr(
        composition_module,
        "build_graph",
        lambda **kwargs: captured.update(kwargs) or "graph",
    )

    composition_module.build_runtime_graph()

    assert FakeWrapper.instances[3].default_model == "model-planner"
    assert captured["response_drafting_model_name"] == "model-planner"
