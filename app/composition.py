"""Explicit composition root for the live LangGraph runtime."""

from __future__ import annotations

from app.application.input_shield import InputShieldOperation
from app.application.planner import PlannerOperation
from app.application.response_drafting import ResponseDraftingOperation
from app.application.triage import TriageOperation
from app.core.settings import get_settings
from app.graph import build_graph
from app.llm.openai_wrapper import AsyncOpenAIWrapper
from app.prompts.input_shield_prompts import INPUT_SHIELD_PROMPT_V1
from app.prompts.local_repository import LocalPromptRepository
from app.prompts.planner_prompts import PLANNER_PROMPT_V1
from app.prompts.response_drafting_prompts import RESPONSE_DRAFTING_PROMPT_V1
from app.prompts.triage_prompts import TRIAGE_PROMPT_V1


def build_runtime_graph():
    """
    Construct configured provider adapters, Application Operations, and the
    compiled graph. Provider clients are created once here and reused across
    graph invocations.
    """
    settings = get_settings()

    input_shield_model = settings.openai_model_input_shield
    triage_model = settings.openai_model_input_shield
    planner_model = getattr(
        settings,
        "openai_model_planner",
        settings.openai_model_input_shield,
    )
    response_drafting_model = getattr(
        settings,
        "openai_model_response_drafting",
        planner_model,
    )

    input_shield_llm = AsyncOpenAIWrapper(
        default_model=input_shield_model,
        default_temperature=settings.input_shield_temperature,
    )
    triage_llm = AsyncOpenAIWrapper(
        default_model=triage_model,
        default_temperature=0.0,
    )
    planner_llm = AsyncOpenAIWrapper(
        default_model=planner_model,
        default_temperature=0.0,
    )
    response_drafting_llm = AsyncOpenAIWrapper(
        default_model=response_drafting_model,
        default_temperature=0.0,
    )

    prompt_repository = LocalPromptRepository(
        [
            INPUT_SHIELD_PROMPT_V1,
            TRIAGE_PROMPT_V1,
            PLANNER_PROMPT_V1,
            RESPONSE_DRAFTING_PROMPT_V1,
        ]
    )

    input_shield_operation = InputShieldOperation(
        llm=input_shield_llm,
        prompt_repository=prompt_repository,
        prompt_ref=INPUT_SHIELD_PROMPT_V1.ref,
        max_prompt_chars=settings.input_shield_max_prompt_chars,
    )
    triage_operation = TriageOperation(
        llm=triage_llm,
        prompt_repository=prompt_repository,
        prompt_ref=TRIAGE_PROMPT_V1.ref,
    )
    planner_operation = PlannerOperation(
        llm=planner_llm,
        prompt_repository=prompt_repository,
        prompt_ref=PLANNER_PROMPT_V1.ref,
    )
    response_drafting_operation = ResponseDraftingOperation(
        llm=response_drafting_llm,
        prompt_repository=prompt_repository,
        prompt_ref=RESPONSE_DRAFTING_PROMPT_V1.ref,
    )

    return build_graph(
        input_shield_operation=input_shield_operation,
        triage_operation=triage_operation,
        planner_operation=planner_operation,
        response_drafting_operation=response_drafting_operation,
        input_shield_model_name=input_shield_model,
        triage_model_name=triage_model,
        planner_model_name=planner_model,
        response_drafting_model_name=response_drafting_model,
    )
