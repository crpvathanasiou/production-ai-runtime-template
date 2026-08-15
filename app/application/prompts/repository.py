"""Application-owned prompt repository port and resolution failures."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from app.application.prompts.models import PromptRef, ResolvedPrompt


class PromptNotFoundError(LookupError):
    """Raised when the requested PromptRef is not present in the repository."""


class PromptRenderError(ValueError):
    """Raised when a prompt cannot be rendered deterministically from variables."""


class PromptRepository(Protocol):
    def resolve(
        self,
        ref: PromptRef,
        *,
        variables: Mapping[str, object],
    ) -> ResolvedPrompt: ...
