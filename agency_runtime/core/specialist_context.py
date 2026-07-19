"""Bounded specialist prompt hydration for host preflight surfaces."""

from __future__ import annotations

from collections.abc import Container, Mapping, Sequence
from dataclasses import dataclass
from inspect import Parameter, signature
from typing import Any

from agency_runtime.core.resident_managers import is_resident_manager_slug
from agency_runtime.core.specialist_contracts import (
    MAX_SELECTED_SPECIALISTS,
    MAX_SPECIALIST_PROMPT_CHARS,
)
from agency_runtime.core.store.sqlite import Store

MAX_SPECIALIST_CONTEXT_CHARS = 24_000

_MAX_SLUG_CHARS = 128
_MAX_DESCRIPTION_CHARS = 256
_MAX_CAPABILITY_CHARS = 64
_MAX_CAPABILITIES = 4


@dataclass(frozen=True, slots=True)
class LoadedSpecialistContext:
    """Prompt context and authoritative load evidence created for one turn."""

    context: str
    slugs: tuple[str, ...]
    references: tuple[SpecialistPromptReference, ...] = ()


@dataclass(frozen=True, slots=True)
class SpecialistPromptReference:
    """Content-free identity for one immutable specialist prompt version."""

    slug: str
    version: str
    content_hash: str
    description: str
    capabilities: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        """Return the bounded persistence projection used by preflight replay."""
        return {
            "slug": self.slug,
            "version": self.version,
            "hash": self.content_hash,
            "description": self.description,
            "capabilities": list(self.capabilities),
        }


def _slug(agent: Mapping[str, Any]) -> str:
    return str(agent.get("agent_slug") or agent.get("slug") or "").strip()


def _bounded_text(value: Any, maximum: int) -> str:
    return str(value or "").strip()[:maximum]


class SpecialistPromptDeliveryError(RuntimeError):
    """Raised when a selected prompt cannot be delivered exactly within policy."""

    def __init__(self, slug: str) -> None:
        self.slug = _bounded_text(slug, _MAX_SLUG_CHARS)
        super().__init__(f"specialist prompt exceeds the exact-delivery ceiling: {self.slug}")


def _supports_disabled_snapshot(getter: Any) -> bool:
    """Return whether one Store-compatible getter accepts the new policy seam."""

    try:
        parameters = signature(getter).parameters.values()
    except (TypeError, ValueError):
        return False
    return any(
        parameter.name == "disabled_agents" or parameter.kind == Parameter.VAR_KEYWORD
        for parameter in parameters
    )


def _selected_prompts(
    store: Store,
    catalog: Sequence[Mapping[str, Any]],
    routing: Mapping[str, Any],
    *,
    disabled_agents: Container[str] | None = None,
) -> list[dict[str, Any]]:
    active_slugs = {_slug(agent) for agent in catalog if _slug(agent)}
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_slug in routing.get("selected_ids", []):
        slug = str(raw_slug or "").strip()
        if not slug or is_resident_manager_slug(slug) or slug in seen or slug not in active_slugs:
            continue
        prompt_kwargs: dict[str, Any] = {"max_chars": MAX_SPECIALIST_PROMPT_CHARS}
        if disabled_agents is not None and _supports_disabled_snapshot(store.get_specialist_prompt):
            prompt_kwargs["disabled_agents"] = disabled_agents
        prompt = store.get_specialist_prompt(slug, **prompt_kwargs)
        if prompt and bool(prompt.get("prompt_truncated")):
            raise SpecialistPromptDeliveryError(slug)
        if (
            not prompt
            or not str(prompt.get("prompt_body") or "").strip()
            or not str(prompt.get("version") or "").strip()
            or not str(prompt.get("prompt_hash") or prompt.get("hash") or "").strip()
        ):
            continue
        selected.append(prompt)
        seen.add(slug)
        if len(selected) >= MAX_SELECTED_SPECIALISTS:
            break
    return selected


def _prompt_context_lines(prompt: Mapping[str, Any]) -> list[str]:
    """Render one specialist as an indivisible, bounded instruction block."""

    slug = _bounded_text(_slug(prompt), _MAX_SLUG_CHARS)
    description = _bounded_text(
        prompt.get("description") or prompt.get("name"),
        _MAX_DESCRIPTION_CHARS,
    )
    raw_capabilities = prompt.get("capabilities")
    capabilities = (
        [
            _bounded_text(capability, _MAX_CAPABILITY_CHARS)
            for capability in raw_capabilities[:_MAX_CAPABILITIES]
            if _bounded_text(capability, _MAX_CAPABILITY_CHARS)
        ]
        if isinstance(raw_capabilities, list)
        else []
    )
    capability_text = f" Capabilities: {', '.join(capabilities)}." if capabilities else ""
    return [
        f"- {slug}: {description}{capability_text}",
        "  Instructions: "
        + _bounded_text(
            prompt.get("prompt_body"),
            MAX_SPECIALIST_PROMPT_CHARS,
        ),
    ]


def _fit_loaded_context(
    prompts: Sequence[Mapping[str, Any]],
    maximum_chars: int,
) -> tuple[str, list[Mapping[str, Any]]]:
    """Fit only whole specialist blocks under the host delivery ceiling."""

    if not prompts:
        return "", []
    maximum = max(0, int(maximum_chars))
    lines = [
        "[AGENCY LOADED] Complete current-turn specialist instruction capsule:",
        "Earlier Agency specialist capsules are expired and are not applied "
        "unless the specialist is repeated below.",
    ]
    if len("\n".join(lines)) > maximum:
        return "", []
    included: list[Mapping[str, Any]] = []
    for prompt in prompts:
        block = _prompt_context_lines(prompt)
        if len("\n".join([*lines, *block])) > maximum:
            break
        lines.extend(block)
        included.append(prompt)
    return ("\n".join(lines), included) if included else ("", [])


def _format_loaded_context(
    prompts: Sequence[Mapping[str, Any]],
    maximum_chars: int = MAX_SPECIALIST_CONTEXT_CHARS,
) -> str:
    context, _included = _fit_loaded_context(prompts, maximum_chars)
    return context


def format_isolated_specialist_context(
    references: Sequence[SpecialistPromptReference],
    *,
    host: str,
    session_id: str,
    trace_id: str,
    nontrivial: bool,
    unit_plan: Sequence[Mapping[str, Any]] = (),
) -> str:
    """Return a compact recipe that keeps prompt bodies out of parent history."""

    slugs = ", ".join(reference.slug for reference in references) or "none"
    native_tool = "`spawn_agent`" if host == "codex" else "`Agent`"
    requirement = "Before substantive work" if nontrivial else "When specialist work is needed"
    if unit_plan:
        if host == "claude":
            activation_flow = (
                "For every accepted row in the [AGENCY DELEGATION PLAN] below, dispatch one "
                "native `Agent` with its `description` set to that row's unchanged "
                "`work_unit_id`. Do not call `agency.prepare_delegation` in the "
                "parent and do not place an activation token in the Agent prompt. "
                "The installed PreToolUse and SubagentStart hooks verify the exact "
                f"plan row for `session_id={session_id}` and `trace_id={trace_id}`, "
                "then add a content-free child recipe and that child's native identity. "
                "Inside the child only, follow that recipe to call "
                "`agency.prepare_delegation` and immediately consume its one-use result "
                "with `agency.load_specialist`. For a declined row, record one explicit "
                "`agency.decline_delegation` receipt instead"
            )
        else:
            activation_flow = (
                "For every accepted row in the [AGENCY DELEGATION PLAN] below, call "
                "`agency.prepare_delegation` exactly once in the parent with that row's "
                "`recommended_agent` as the slug and its unchanged `work_unit_id`, "
                f"`session_id={session_id}`, and `trace_id={trace_id}`; pass each "
                "returned `activation_token` only to its isolated child and set the "
                "native `task_name` to that row's legal `native_task_name` so the "
                "post-tool receipt can reconcile. Prefix the child's task with a "
                "bounded `[AGENCY CHILD PREFLIGHT v1]` recipe containing only the "
                "parent session ID, parent trace ID, unchanged work-unit ID, selected "
                "slug, and that one-use activation token. The installed SubagentStart "
                "hook supplies the native child identity separately. Inside that child, call "
                "`agency.load_specialist` with the same slug, correlation, work-unit "
                "ID, activation token, and injected native identity. For a declined row, "
                "record one explicit `agency.decline_delegation` receipt instead"
            )
    else:
        from agency_runtime.core.delegation.native_labels import (
            codex_task_name_for_work_unit,
        )

        grants = "; ".join(
            (
                f"{reference.slug} => work_unit_id=specialist:{reference.slug}, "
                "native_task_name="
                f"{codex_task_name_for_work_unit(f'specialist:{reference.slug}')}"
                if host == "codex"
                else f"{reference.slug} => work_unit_id=specialist:{reference.slug}"
            )
            for reference in references
        )
        if host == "claude":
            activation_flow = (
                "For every selected slug, dispatch one native `Agent` and set its "
                f"`description` to the exact work-unit binding ({grants or 'none'}). "
                "Do not call `agency.prepare_delegation` in the parent and do not "
                "place an activation token in the Agent prompt. The installed "
                "PreToolUse and SubagentStart hooks verify that binding for "
                f"`session_id={session_id}` and `trace_id={trace_id}`, then add a "
                "content-free child recipe and that child's native identity. Inside "
                "the child only, follow that recipe to call `agency.prepare_delegation` "
                "and immediately consume its one-use result with "
                "`agency.load_specialist`"
            )
        else:
            activation_flow = (
                "In the parent, call `agency.prepare_delegation` once for every "
                f"selected slug with its exact work-unit binding ({grants or 'none'}), "
                f"`session_id={session_id}`, and `trace_id={trace_id}`; pass each "
                "returned `activation_token` only to its isolated child and set the "
                "native `task_name` to that binding's legal `native_task_name` so the "
                "post-tool receipt can reconcile. Prefix the child's task with a "
                "bounded `[AGENCY CHILD PREFLIGHT v1]` recipe containing only the "
                "parent session ID, parent trace ID, exact work-unit binding, selected "
                "slug, and that one-use activation token. The installed SubagentStart "
                "hook supplies the native child identity separately. Inside that child, call "
                "`agency.load_specialist` with the same slug, correlation, work-unit "
                "ID, activation token, and injected native identity"
            )
    return (
        f"[AGENCY PREFLIGHT] Current isolated turn {trace_id}; unit-plan specialists: "
        f"{slugs}. "
        "Earlier Agency turn recipes are expired. Full specialist prompt bodies are "
        f"excluded from this persistent {host} parent transcript. {requirement}, use "
        f"the host-native {native_tool} worker. {activation_flow}. Apply the "
        "returned exact-version prompt only inside the child, "
        "and return a bounded result. Do not load a specialist prompt body in the "
        "parent. Native worker labels are not Agency specialist identities. Preserve "
        "delegated goal text exactly from the current user request. Include the six-line "
        "Agency evidence header in the final parent response. Start the response with "
        "exactly these six field labels, in this order, and fill values only from "
        "current-turn runtime evidence (use `none` or an explicit unavailable state "
        "when evidence is absent):\n"
        "Agency/Agencies loaded: <agent-id[, agent-id...] or none>\n"
        "Agency/Agencies delegated: <agent-id[, agent-id...] or none>\n"
        "Skills loaded: <skill-id[, skill-id...] or none>\n"
        "Actual Model selected: <requested alias> -> <resolved provider/model or "
        "unavailable reason>\n"
        "Why: <one evidence-grounded line>\n"
        "How it shaped outcome: <one evidence-grounded line>"
    )


def _prompt_reference(prompt: Mapping[str, Any]) -> SpecialistPromptReference:
    raw_capabilities = prompt.get("capabilities")
    capabilities = (
        tuple(
            _bounded_text(capability, _MAX_CAPABILITY_CHARS)
            for capability in raw_capabilities[:_MAX_CAPABILITIES]
            if _bounded_text(capability, _MAX_CAPABILITY_CHARS)
        )
        if isinstance(raw_capabilities, list)
        else ()
    )
    return SpecialistPromptReference(
        slug=_slug(prompt),
        version=str(prompt.get("version") or "").strip(),
        content_hash=str(prompt.get("prompt_hash") or prompt.get("hash") or "").strip(),
        description=_bounded_text(
            prompt.get("description") or prompt.get("name"),
            _MAX_DESCRIPTION_CHARS,
        ),
        capabilities=capabilities,
    )


def rebuild_versioned_specialist_context(
    store: Store,
    references: Sequence[Mapping[str, Any]],
    *,
    maximum_chars: int = MAX_SPECIALIST_CONTEXT_CHARS,
    disabled_agents: Container[str] | None = None,
) -> LoadedSpecialistContext:
    """Rebuild prompt context from exact immutable versions without evidence writes."""
    if len(references) > MAX_SELECTED_SPECIALISTS:
        raise RuntimeError("ready preflight references too many specialists")
    if not references:
        return LoadedSpecialistContext(context="", slugs=(), references=())
    getter = getattr(store, "get_versioned_specialist_prompt", None)
    if not callable(getter):
        raise RuntimeError("evidence store cannot replay versioned specialist prompts")

    prompts: list[dict[str, Any]] = []
    exact_references: list[SpecialistPromptReference] = []
    for raw_reference in references:
        slug = str(raw_reference.get("slug") or "").strip()
        version = str(raw_reference.get("version") or "").strip()
        content_hash = str(raw_reference.get("hash") or "").strip()
        if is_resident_manager_slug(slug):
            raise RuntimeError("ready preflight references a resident manager as a specialist")
        description = _bounded_text(
            raw_reference.get("description"),
            _MAX_DESCRIPTION_CHARS,
        )
        raw_capabilities = raw_reference.get("capabilities")
        capabilities = (
            tuple(
                _bounded_text(capability, _MAX_CAPABILITY_CHARS)
                for capability in raw_capabilities[:_MAX_CAPABILITIES]
                if _bounded_text(capability, _MAX_CAPABILITY_CHARS)
            )
            if isinstance(raw_capabilities, list)
            else ()
        )
        if not slug or not version or not content_hash:
            raise RuntimeError("ready preflight contains an invalid specialist reference")
        prompt_kwargs = {"max_chars": MAX_SPECIALIST_PROMPT_CHARS}
        if disabled_agents is not None and _supports_disabled_snapshot(getter):
            prompt_kwargs["disabled_agents"] = disabled_agents
        prompt = getter(slug, version, content_hash, **prompt_kwargs)
        if (
            not isinstance(prompt, dict)
            or not str(prompt.get("prompt_body") or "").strip()
            or bool(prompt.get("prompt_truncated"))
        ):
            raise RuntimeError(f"specialist prompt version is unavailable: {slug}@{version}")
        prompt_identity = (
            _slug(prompt),
            str(prompt.get("version") or "").strip(),
            str(prompt.get("prompt_hash") or prompt.get("hash") or "").strip(),
        )
        if prompt_identity != (slug, version, content_hash):
            raise RuntimeError(f"specialist prompt version does not match: {slug}@{version}")
        reference = SpecialistPromptReference(
            slug,
            version,
            content_hash,
            description,
            capabilities,
        )
        prompt["description"] = description
        prompt["capabilities"] = list(capabilities)
        prompts.append(prompt)
        exact_references.append(reference)

    context, included = _fit_loaded_context(prompts, maximum_chars)
    if len(included) != len(prompts):
        raise RuntimeError("ready preflight specialist prompts exceed the delivery ceiling")
    return LoadedSpecialistContext(
        context=context,
        slugs=tuple(reference.slug for reference in exact_references),
        references=tuple(exact_references),
    )


def hydrate_selected_specialist_context(
    store: Store,
    catalog: Sequence[Mapping[str, Any]],
    routing: Mapping[str, Any],
    *,
    session_id: str,
    trace_id: str,
    record_evidence: bool = True,
    maximum_chars: int = MAX_SPECIALIST_CONTEXT_CHARS,
    disabled_agents: Container[str] | None = None,
) -> LoadedSpecialistContext:
    """Load selected governed prompts and record exactly what shaped one turn.

    Selection is intersected with the active catalog, deduplicated in routing
    order, and capped before any prompt bodies are read. Correlation is required
    so callers cannot create session-only evidence that later looks current.
    """
    if not str(session_id or "").strip() or not str(trace_id or "").strip():
        raise ValueError("session_id and trace_id are required for specialist hydration")

    prompts = _selected_prompts(
        store,
        catalog,
        routing,
        disabled_agents=disabled_agents,
    )
    context, included = _fit_loaded_context(prompts, maximum_chars)
    references = tuple(_prompt_reference(prompt) for prompt in included)
    slugs = tuple(reference.slug for reference in references)
    if record_evidence:
        for slug in slugs:
            store.record_specialist_loaded(
                session_id,
                slug,
                trace_id=trace_id,
            )
    return LoadedSpecialistContext(
        context=context,
        slugs=slugs,
        references=references,
    )


__all__ = [
    "MAX_SELECTED_SPECIALISTS",
    "MAX_SPECIALIST_CONTEXT_CHARS",
    "MAX_SPECIALIST_PROMPT_CHARS",
    "LoadedSpecialistContext",
    "SpecialistPromptDeliveryError",
    "SpecialistPromptReference",
    "format_isolated_specialist_context",
    "hydrate_selected_specialist_context",
    "rebuild_versioned_specialist_context",
]
