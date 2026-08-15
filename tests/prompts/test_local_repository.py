"""Tests for LocalPromptRepository resolution semantics."""

from __future__ import annotations

import pytest

from app.application.prompts import (
    PromptNotFoundError,
    PromptRef,
    PromptRenderError,
)
from app.prompts.local_repository import LocalPromptRepository, PromptDefinition


def _def(
    *,
    prompt_id: str = "triage",
    revision: int = 1,
    system_template: str | None = "You are the {role}.",
    user_template: str = "Customer message:\n{customer_message}",
) -> PromptDefinition:
    return PromptDefinition(
        ref=PromptRef(prompt_id=prompt_id, revision=revision),
        system_template=system_template,
        user_template=user_template,
    )


def test_resolve_system_and_user_success() -> None:
    repo = LocalPromptRepository([_def()])
    resolved = repo.resolve(
        PromptRef(prompt_id="triage", revision=1),
        variables={
            "role": "triage analyzer",
            "customer_message": "I need help",
        },
    )
    assert resolved.ref == PromptRef(prompt_id="triage", revision=1)
    assert resolved.system_prompt == "You are the triage analyzer."
    assert resolved.user_prompt == "Customer message:\nI need help"
    assert len(resolved.content_hash) == 64


def test_resolve_user_only_when_system_template_none() -> None:
    repo = LocalPromptRepository(
        [_def(system_template=None, user_template="Only {msg}")]
    )
    resolved = repo.resolve(
        PromptRef(prompt_id="triage", revision=1),
        variables={"msg": "hello"},
    )
    assert resolved.system_prompt is None
    assert resolved.user_prompt == "Only hello"


def test_missing_prompt_ref_raises_not_found() -> None:
    repo = LocalPromptRepository([_def()])
    with pytest.raises(PromptNotFoundError, match="prompt not found"):
        repo.resolve(
            PromptRef(prompt_id="triage", revision=99),
            variables={"role": "x", "customer_message": "y"},
        )


def test_missing_required_variable_raises_render_error() -> None:
    repo = LocalPromptRepository([_def()])
    with pytest.raises(PromptRenderError, match="missing required"):
        repo.resolve(
            PromptRef(prompt_id="triage", revision=1),
            variables={"role": "triage analyzer"},
        )


def test_unexpected_extra_variable_raises_render_error() -> None:
    repo = LocalPromptRepository([_def()])
    with pytest.raises(PromptRenderError, match="unexpected template variables"):
        repo.resolve(
            PromptRef(prompt_id="triage", revision=1),
            variables={
                "role": "triage analyzer",
                "customer_message": "help",
                "unused": "nope",
            },
        )


def test_runtime_braces_are_inserted_literally_not_recursively() -> None:
    repo = LocalPromptRepository(
        [_def(system_template=None, user_template="Value: {payload}")]
    )
    resolved = repo.resolve(
        PromptRef(prompt_id="triage", revision=1),
        variables={"payload": "contains {another_placeholder} braces"},
    )
    assert resolved.user_prompt == "Value: contains {another_placeholder} braces"


def test_caller_mutation_of_input_collection_does_not_affect_repository() -> None:
    definitions = [_def()]
    repo = LocalPromptRepository(definitions)
    definitions.clear()
    definitions.append(
        _def(
            system_template=None,
            user_template="mutated {x}",
        )
    )
    resolved = repo.resolve(
        PromptRef(prompt_id="triage", revision=1),
        variables={
            "role": "triage analyzer",
            "customer_message": "stable",
        },
    )
    assert resolved.system_prompt == "You are the triage analyzer."
    assert resolved.user_prompt == "Customer message:\nstable"


def test_duplicate_prompt_ref_definitions_fail_construction() -> None:
    with pytest.raises(ValueError, match="duplicate PromptRef"):
        LocalPromptRepository([_def(), _def()])


def test_same_static_definition_different_variables_same_content_hash() -> None:
    repo = LocalPromptRepository([_def()])
    first = repo.resolve(
        PromptRef(prompt_id="triage", revision=1),
        variables={"role": "a", "customer_message": "one"},
    )
    second = repo.resolve(
        PromptRef(prompt_id="triage", revision=1),
        variables={"role": "b", "customer_message": "two"},
    )
    assert first.content_hash == second.content_hash
    assert first.user_prompt != second.user_prompt


def test_different_user_template_changes_content_hash() -> None:
    repo_a = LocalPromptRepository([_def(user_template="A {customer_message}")])
    repo_b = LocalPromptRepository([_def(user_template="B {customer_message}")])
    hash_a = repo_a.resolve(
        PromptRef(prompt_id="triage", revision=1),
        variables={"role": "x", "customer_message": "y"},
    ).content_hash
    hash_b = repo_b.resolve(
        PromptRef(prompt_id="triage", revision=1),
        variables={"role": "x", "customer_message": "y"},
    ).content_hash
    assert hash_a != hash_b


def test_different_system_template_changes_content_hash() -> None:
    repo_a = LocalPromptRepository([_def(system_template="System A {role}")])
    repo_b = LocalPromptRepository([_def(system_template="System B {role}")])
    hash_a = repo_a.resolve(
        PromptRef(prompt_id="triage", revision=1),
        variables={"role": "x", "customer_message": "y"},
    ).content_hash
    hash_b = repo_b.resolve(
        PromptRef(prompt_id="triage", revision=1),
        variables={"role": "x", "customer_message": "y"},
    ).content_hash
    assert hash_a != hash_b


def test_malformed_unmatched_opening_brace_raises_prompt_render_error() -> None:
    repo = LocalPromptRepository(
        [_def(system_template=None, user_template="broken {placeholder")]
    )
    with pytest.raises(PromptRenderError, match="malformed template syntax") as exc_info:
        repo.resolve(
            PromptRef(prompt_id="triage", revision=1),
            variables={},
        )
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_malformed_unmatched_closing_brace_raises_prompt_render_error() -> None:
    repo = LocalPromptRepository(
        [_def(system_template=None, user_template="broken } placeholder")]
    )
    with pytest.raises(PromptRenderError, match="malformed template syntax") as exc_info:
        repo.resolve(
            PromptRef(prompt_id="triage", revision=1),
            variables={},
        )
    assert isinstance(exc_info.value.__cause__, ValueError)


def test_same_static_content_under_different_prompt_ref_same_hash() -> None:
    system = "You are the {role}."
    user = "Customer message:\n{customer_message}"
    repo = LocalPromptRepository(
        [
            _def(prompt_id="triage", revision=1, system_template=system, user_template=user),
            _def(prompt_id="other", revision=2, system_template=system, user_template=user),
        ]
    )
    hash_a = repo.resolve(
        PromptRef(prompt_id="triage", revision=1),
        variables={"role": "x", "customer_message": "y"},
    ).content_hash
    hash_b = repo.resolve(
        PromptRef(prompt_id="other", revision=2),
        variables={"role": "x", "customer_message": "y"},
    ).content_hash
    assert hash_a == hash_b
