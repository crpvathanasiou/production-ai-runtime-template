"""Tests for PromptRef, PromptIdentity, and ResolvedPrompt value objects."""

from __future__ import annotations

import dataclasses

import pytest

from app.application.prompts import PromptIdentity, PromptRef, ResolvedPrompt


def test_prompt_ref_valid() -> None:
    ref = PromptRef(prompt_id="triage", revision=1)
    assert ref.prompt_id == "triage"
    assert ref.revision == 1


@pytest.mark.parametrize("prompt_id", ["", "   ", "\t", "\n"])
def test_prompt_ref_rejects_empty_or_whitespace_prompt_id(prompt_id: str) -> None:
    with pytest.raises(ValueError, match="prompt_id"):
        PromptRef(prompt_id=prompt_id, revision=1)


@pytest.mark.parametrize("revision", [0, -1, -100])
def test_prompt_ref_rejects_non_positive_revision(revision: int) -> None:
    with pytest.raises(ValueError, match="revision"):
        PromptRef(prompt_id="triage", revision=revision)


def test_prompt_ref_rejects_bool_revision() -> None:
    with pytest.raises(ValueError, match="revision"):
        PromptRef(prompt_id="triage", revision=True)  # type: ignore[arg-type]


def test_prompt_ref_is_immutable() -> None:
    ref = PromptRef(prompt_id="triage", revision=1)
    with pytest.raises(AttributeError):
        ref.prompt_id = "other"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        ref.revision = 2  # type: ignore[misc]


def test_resolved_prompt_is_immutable() -> None:
    resolved = ResolvedPrompt(
        ref=PromptRef(prompt_id="triage", revision=1),
        system_prompt="system",
        user_prompt="user",
        content_hash="abc",
    )
    with pytest.raises(AttributeError):
        resolved.user_prompt = "changed"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        resolved.content_hash = "changed"  # type: ignore[misc]


def test_resolved_prompt_identity_projection() -> None:
    ref = PromptRef(prompt_id="triage", revision=1)
    resolved = ResolvedPrompt(
        ref=ref,
        system_prompt="system text with {{variables}}",
        user_prompt="rendered user prompt with runtime values",
        content_hash="content-hash-abc",
    )

    identity = resolved.identity

    assert identity == PromptIdentity(ref=ref, content_hash="content-hash-abc")
    assert identity.ref is ref
    assert identity.content_hash == resolved.content_hash
    assert dataclasses.is_dataclass(identity)
    field_names = {f.name for f in dataclasses.fields(identity)}
    assert field_names == {"ref", "content_hash"}
    assert "system_prompt" not in field_names
    assert "user_prompt" not in field_names
    assert not hasattr(identity, "system_prompt")
    assert not hasattr(identity, "user_prompt")
    assert "rendered user prompt" not in repr(identity)
    assert "{{variables}}" not in repr(identity)

    with pytest.raises(AttributeError):
        identity.content_hash = "mutated"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        identity.ref = PromptRef(prompt_id="other", revision=2)  # type: ignore[misc]
