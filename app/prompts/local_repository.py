"""Local, code-backed, deterministic PromptRepository implementation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from string import Formatter

from app.application.prompts.models import PromptRef, ResolvedPrompt
from app.application.prompts.repository import (
    PromptNotFoundError,
    PromptRenderError,
)

_FORMATTER = Formatter()


@dataclass(frozen=True)
class PromptDefinition:
    """Immutable code-backed prompt bundle (system + user templates)."""

    ref: PromptRef
    system_template: str | None
    user_template: str


def _content_hash(*, system_template: str | None, user_template: str) -> str:
    canonical = json.dumps(
        {
            "system_template": system_template,
            "user_template": user_template,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _named_placeholders(template: str) -> set[str]:
    names: set[str] = set()
    try:
        parsed = list(_FORMATTER.parse(template))
    except ValueError as exc:
        raise PromptRenderError(f"malformed template syntax: {exc}") from exc
    for _, field_name, format_spec, conversion in parsed:
        if field_name is None:
            continue
        if field_name == "":
            raise PromptRenderError("positional placeholders are not supported")
        if "." in field_name or "[" in field_name:
            raise PromptRenderError(
                f"unsupported placeholder expression: {{{field_name}}}"
            )
        if format_spec or conversion:
            raise PromptRenderError(
                f"unsupported placeholder formatting: {{{field_name}}}"
            )
        names.add(field_name)
    return names


def _render(template: str, variables: Mapping[str, object]) -> str:
    # Build values once; str.format does not recursively format inserted values.
    values = {name: variables[name] for name in _named_placeholders(template)}
    try:
        return template.format(**values)
    except (KeyError, ValueError, IndexError) as exc:
        raise PromptRenderError(f"failed to render template: {exc}") from exc


class LocalPromptRepository:
    """Synchronous in-memory repository over immutable code-backed definitions."""

    def __init__(self, definitions: Iterable[PromptDefinition]) -> None:
        lookup: dict[PromptRef, PromptDefinition] = {}
        for definition in definitions:
            if definition.ref in lookup:
                raise ValueError(
                    "duplicate PromptRef definition: "
                    f"prompt_id={definition.ref.prompt_id!r}, "
                    f"revision={definition.ref.revision}"
                )
            lookup[definition.ref] = definition
        self._definitions = lookup

    def resolve(
        self,
        ref: PromptRef,
        *,
        variables: Mapping[str, object],
    ) -> ResolvedPrompt:
        definition = self._definitions.get(ref)
        if definition is None:
            raise PromptNotFoundError(
                f"prompt not found: prompt_id={ref.prompt_id!r}, revision={ref.revision}"
            )

        required: set[str] = set()
        if definition.system_template is not None:
            required |= _named_placeholders(definition.system_template)
        required |= _named_placeholders(definition.user_template)

        provided = set(variables.keys())
        missing = required - provided
        if missing:
            raise PromptRenderError(
                f"missing required template variables: {sorted(missing)}"
            )
        extra = provided - required
        if extra:
            raise PromptRenderError(
                f"unexpected template variables: {sorted(extra)}"
            )

        system_prompt = (
            None
            if definition.system_template is None
            else _render(definition.system_template, variables)
        )
        user_prompt = _render(definition.user_template, variables)
        return ResolvedPrompt(
            ref=ref,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            content_hash=_content_hash(
                system_template=definition.system_template,
                user_template=definition.user_template,
            ),
        )
