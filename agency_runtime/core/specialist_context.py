"""Bounded specialist prompt hydration for host preflight surfaces."""

from __future__ import annotations

from collections.abc import Container, Mapping, Sequence
from dataclasses import dataclass
from inspect import Parameter, signature
from typing import Any

from agency_runtime.core.agent_identity import agent_identity
from agency_runtime.core.resident_managers import (
    RESIDENT_MANAGER_SLUGS,
    is_resident_manager_slug,
)
from agency_runtime.core.specialist_contracts import (
    MAX_DURABLE_SPECIALIST_REFERENCES,
    MAX_SELECTED_SPECIALISTS,
    MAX_SPECIALIST_PROMPT_CHARS,
)
from agency_runtime.core.store.sqlite import Store

MAX_SPECIALIST_CONTEXT_CHARS = 24_000

MAX_EXPIRED_SPECIALIST_ANNOUNCEMENTS = 8

_MAX_SLUG_CHARS = 128
_MAX_DESCRIPTION_CHARS = 256
_MAX_CAPABILITY_CHARS = 64
_MAX_CAPABILITIES = 4


def format_expired_specialist_context(slugs: Sequence[str]) -> str:
    """State that named cards have expired, without re-emitting their content.

    The card returns to the cabinet at turn end, but on hosts where injected
    context cannot be retracted the model can still read the expired prompt
    further up the conversation. Naming the expiry is the only available way to
    stop a stale card from steering the current turn.

    Deliberately identity-only: it names slugs and never repeats a prompt body,
    so the cost stays a single short line no matter how large the expired cards
    were.
    """

    names = []
    for slug in slugs or ():
        normalized = str(slug or "").strip()[:_MAX_SLUG_CHARS]
        if normalized and not is_resident_manager_slug(normalized) and normalized not in names:
            names.append(normalized)
        if len(names) >= MAX_EXPIRED_SPECIALIST_ANNOUNCEMENTS:
            break
    if not names:
        return ""
    return (
        "[AGENCY SPECIALIST EXPIRY]\n"
        f"These specialists ended with the previous turn and are no longer loaded: "
        f"{', '.join(names)}. Their instructions may still be visible earlier in this "
        "conversation; that text is expired. Do not follow it, do not treat it as "
        "your current role, and do not cite it as authority for this turn."
    )


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
    return agent_identity(agent)


def _bounded_text(value: Any, maximum: int) -> str:
    return str(value or "").strip()[:maximum]


def _bounded_prompt_body(value: Any, maximum: int) -> str:
    """Preserve the exact prompt bytes admitted by the immutable prompt ceiling."""

    return (value if isinstance(value, str) else str(value or ""))[:maximum]


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
    maximum_specialists: int = MAX_SELECTED_SPECIALISTS,
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
        if len(selected) >= max(0, min(maximum_specialists, MAX_DURABLE_SPECIALIST_REFERENCES)):
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
        + _bounded_prompt_body(
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
    resident_managers: Sequence[str] = (),
) -> str:
    """Return a compact recipe that keeps prompt bodies out of parent history."""

    normalized_host = str(host or "").strip().casefold()
    # ADR-0087: zcode reuses the Claude hook model and the `Agent`-tool native
    # delegation primitive (same `description` field binding), so it shares
    # Claude's isolated-delivery instructions.
    native_tools = {
        "codex": "`spawn_agent`",
        "claude": "`Agent`",
        "zcode": "`Agent`",
        "hermes": "`delegate_task`",
        "openclaw": "`sessions_spawn`",
    }
    native_tool = native_tools.get(normalized_host)
    if native_tool is None:
        raise ValueError(f"isolated specialist delivery is unsupported for host: {host}")
    slugs = ", ".join(reference.slug for reference in references) or "none"
    resident_loaded = ", ".join(
        slug
        for slug in resident_managers
        if isinstance(slug, str) and slug in RESIDENT_MANAGER_SLUGS
    )
    loaded_header_value = resident_loaded or "<agent-id[, agent-id...] or none>"
    loaded_header_instruction = (
        "`Agency/Agencies loaded` is fixed by current-turn resident evidence; "
        "copy its value exactly, never `none`. "
        if resident_loaded
        else ""
    )
    requirement = "Before substantive work" if nontrivial else "When specialist work is needed"
    if unit_plan:
        native_binding = {
            "codex": (
                "set `fork_turns` to `none` and set `task_name` to that row's "
                "legal `native_task_name`"
            ),
            "claude": "set `description` to that row's unchanged `work_unit_id`",
            "zcode": "set `description` to that row's unchanged `work_unit_id`",
            "hermes": "pass that row's unchanged `work_unit_id` and exact `goal`",
            "openclaw": "pass that row's unchanged `work_unit_id` and exact `goal`",
        }[normalized_host]
        hook_delivery = (
            "the installed PreToolUse hook verifies the exact persisted row, injects "
            "the selected immutable specialist prompt only into that child launch, and "
            "issues its one-use grant. PostToolUse consumes the grant only after "
            "authoritative native launch evidence supplies the child identity"
            if normalized_host in {"codex", "claude", "zcode"}
            else "the installed child pre-LLM hook verifies the exact persisted row, "
            "injects the selected immutable specialist prompt only at that child's "
            "inference boundary, and consumes its one-use grant against host-issued "
            "child lineage"
        )
        activation_flow = (
            "For every accepted row in the [AGENCY DELEGATION PLAN] below, dispatch one "
            f"native {native_tool} and {native_binding}. Do not call "
            f"`agency.prepare_delegation` or `agency.load_specialist`; {hook_delivery}. "
            "For a declined row, "
            "record one explicit `agency.decline_delegation` receipt instead"
        )
        execution_instruction = (
            f"{requirement}, use the host-native {native_tool} worker. {activation_flow}. "
            "Apply the returned exact-version prompt only inside the child, and return "
            "a bounded result. Do not load a specialist prompt body in the parent"
        )
    else:
        if references:
            raise RuntimeError("isolated specialist selection lacks an exact unit-agent plan")
        execution_instruction = (
            "No specialist assignment was accepted for this turn. Do not dispatch an "
            "untyped native worker or claim Agency participation. Continue under the "
            "native host's own policy without attributing specialist work to Agency"
        )
    return (
        f"[AGENCY PREFLIGHT] Current isolated turn {trace_id}; unit-plan specialists: "
        f"{slugs}. "
        "Earlier Agency turn recipes are expired. Full specialist prompt bodies are "
        f"excluded from this persistent {normalized_host} parent transcript. "
        f"{execution_instruction}. Native worker labels are not Agency specialist identities. Preserve "
        "delegated goal text exactly from the current user request. Include the "
        "Agency evidence header in substantive progress updates and the final parent "
        "response. Start each such response with "
        "exactly these field labels, in this order, and fill values only from "
        "current-turn runtime evidence (use `none` or an explicit unavailable state "
        "when evidence is absent). "
        f"{loaded_header_instruction}\n"
        f"Agency/Agencies loaded: {loaded_header_value}\n"
        "Agency/Agencies delegated: <agent-id[, agent-id...] or none>\n"
        "Skills loaded: <skill-id[, skill-id...] or none>\n"
        "Actual Model selected: <requested alias> -> <resolved provider/model or "
        "unavailable reason>\n"
        "Recruited via: <inference | cached | none>\n"
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
    include_context: bool = True,
) -> LoadedSpecialistContext:
    """Rebuild prompt context from exact immutable versions without evidence writes."""
    if len(references) > MAX_DURABLE_SPECIALIST_REFERENCES:
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
        # These three failures need three messages. They have different causes
        # and different fixes, and this error reaches the operator as a hard
        # preflight block -- collapsing them into one "unavailable" string made
        # a missing registration indistinguishable from an oversized prompt.
        if not isinstance(prompt, dict):
            raise RuntimeError(
                f"specialist prompt version is not registered: {slug}@{version} "
                f"(hash {content_hash[:16]}). No matching active row exists; the "
                "specialist was referenced but never installed under this exact version."
            )
        if not str(prompt.get("prompt_body") or "").strip():
            raise RuntimeError(
                f"specialist prompt body is empty: {slug}@{version} "
                f"(hash {content_hash[:16]}). The version row exists but stores no prompt."
            )
        if bool(prompt.get("prompt_truncated")):
            raise RuntimeError(
                f"specialist prompt exceeds the exact-delivery ceiling: {slug}@{version} "
                f"(limit {MAX_SPECIALIST_PROMPT_CHARS} chars). The prompt is registered "
                "but cannot be delivered whole, and a partial specialist prompt is never sent."
            )
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

    if include_context:
        context, included = _fit_loaded_context(prompts, maximum_chars)
        if len(included) != len(prompts):
            raise RuntimeError("ready preflight specialist prompts exceed the delivery ceiling")
    else:
        context = ""
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


def hydrate_selected_specialist_references(
    store: Store,
    catalog: Sequence[Mapping[str, Any]],
    routing: Mapping[str, Any],
    *,
    session_id: str,
    trace_id: str,
    disabled_agents: Container[str] | None = None,
) -> LoadedSpecialistContext:
    """Validate every isolated assignment while keeping prompt bodies out of the parent."""

    if not str(session_id or "").strip() or not str(trace_id or "").strip():
        raise ValueError("session_id and trace_id are required for specialist hydration")
    prompts = _selected_prompts(
        store,
        catalog,
        routing,
        disabled_agents=disabled_agents,
        maximum_specialists=MAX_DURABLE_SPECIALIST_REFERENCES,
    )
    references = tuple(_prompt_reference(prompt) for prompt in prompts)
    return LoadedSpecialistContext(
        context="",
        slugs=tuple(reference.slug for reference in references),
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
    "hydrate_selected_specialist_references",
    "rebuild_versioned_specialist_context",
]
