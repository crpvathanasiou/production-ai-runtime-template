"""Static typing proof that LocalPromptRepository satisfies PromptRepository."""

from __future__ import annotations

from app.application.prompts import PromptRepository
from app.application.prompts.models import PromptRef
from app.prompts.local_repository import LocalPromptRepository, PromptDefinition


def _as_prompt_repository(repo: LocalPromptRepository) -> PromptRepository:
    """Pyright-verified structural compatibility with PromptRepository."""
    return repo


def test_local_prompt_repository_satisfies_prompt_repository_protocol() -> None:
    repo = LocalPromptRepository(
        [
            PromptDefinition(
                ref=PromptRef(prompt_id="demo", revision=1),
                system_template=None,
                user_template="hello",
            )
        ]
    )
    typed: PromptRepository = _as_prompt_repository(repo)
    resolved = typed.resolve(
        PromptRef(prompt_id="demo", revision=1),
        variables={},
    )
    assert resolved.user_prompt == "hello"
