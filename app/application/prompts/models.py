"""Application-owned prompt identity and resolved-prompt value objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptRef:
    """Immutable identity of one behavioural prompt bundle revision."""

    prompt_id: str
    revision: int

    def __post_init__(self) -> None:
        if not isinstance(self.prompt_id, str) or not self.prompt_id.strip():
            raise ValueError("prompt_id must be a non-empty, non-whitespace string")
        if not isinstance(self.revision, int) or isinstance(self.revision, bool):
            raise ValueError("revision must be an integer >= 1")
        if self.revision < 1:
            raise ValueError("revision must be an integer >= 1")


@dataclass(frozen=True)
class PromptIdentity:
    """Safe immutable prompt-definition identity for operation evidence."""

    ref: PromptRef
    content_hash: str


@dataclass(frozen=True)
class ResolvedPrompt:
    """Immutable rendered prompt ready for LLM execution."""

    ref: PromptRef
    system_prompt: str | None
    user_prompt: str
    content_hash: str

    @property
    def identity(self) -> PromptIdentity:
        return PromptIdentity(
            ref=self.ref,
            content_hash=self.content_hash,
        )
