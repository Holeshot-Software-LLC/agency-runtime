"""What Agency's always-present frame costs per turn, in characters and tokens (AR-355).

AR-355 added one line to the resident-steward kernel (v4 -> v5) and put the
owner's working agreements on every ready turn through the operator-policy
block. Both are paid on every turn on every host, so their price is a product
number, not an implementation detail. This renders each component with the
same code that renders it for a host, sizes it, and separates the AR-355 delta
from the frame that was already there.

Token counts are estimates. The heuristic is four characters per token, which
is close for English prose and fixed-width identifiers and pessimistic for hex
digests. When ``tiktoken`` happens to be importable its ``cl100k_base``
encoding is used instead and the report says which. It is never a dependency,
and no host model's exact tokenizer is known here.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Final

from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.fail_open_disclosure import render_fail_open_disclosure
from agency_runtime.core.header.contract import format_header
from agency_runtime.core.header.snapshot import (
    HEADER_SNAPSHOT_INSTRUCTIONS,
    format_header_snapshot,
)
from agency_runtime.core.operator_policy import (
    MAX_OPERATOR_POLICY_CHARS,
    normalized_operator_policy,
    render_operator_policy,
)
from agency_runtime.core.preflight_recipe import MAX_PREFLIGHT_CONTEXT_CHARS
from agency_runtime.core.resident_manager_binding import (
    MAX_RESIDENT_MANAGER_TURN_REFERENCE_CHARS,
    build_resident_control_epoch,
    build_resident_manager_binding,
    resident_manager_host_mode,
    resident_manager_turn_reference_context,
)
from agency_runtime.core.resident_managers import (
    MAX_RESIDENT_MANAGER_KERNEL_CHARS,
    RESIDENT_MANAGER_KERNEL,
    RESIDENT_MANAGER_KERNEL_VERSION,
    RESIDENT_MANAGER_SLUGS,
)
from agency_runtime.core.routing_latency import nearest_rank_percentile
from agency_runtime.core.specialist_context import MAX_SPECIALIST_CONTEXT_CHARS

CHARS_PER_TOKEN_HEURISTIC: Final[int] = 4
TOKEN_ESTIMATOR_HEURISTIC: Final[str] = "chars/4"
TOKEN_ESTIMATOR_TIKTOKEN: Final[str] = "tiktoken:cl100k_base"
TOKEN_ESTIMATOR_METHODS: Final[tuple[str, ...]] = ("auto", "chars", "tiktoken")
_TIKTOKEN_ENCODING: Final[str] = "cl100k_base"

# The exact text kernel v5 added over v4 (AR-355), pinned so the delta is
# measured rather than remembered. tests/test_context_budget.py asserts it is
# still in the shipped kernel; a later trim must update both together.
RESIDENT_KERNEL_V5_ADDITION: Final[str] = (
    "A governed workforce of specialists exists. When this turn's capsule names specialists,\n"
    "treat them as present expertise; when it names none, the turn is honestly unstaffed."
)

# Hosts whose hook bridge appends a header snapshot to the UserPromptSubmit
# context (adapters/hooks.py, _header_snapshot_context). Mirrored, not imported:
# core does not depend on adapters.
HEADER_SNAPSHOT_HOSTS: Final[tuple[str, ...]] = ("claude", "codex", "zcode")
DEFAULT_CAPSULE_SAMPLE: Final[int] = 100
# The context segments a hook delivers are joined the way _combine_context and
# the bridge join them.
_SEGMENT_SEPARATOR: Final[str] = "\n\n"
_REPRESENTATIVE_SESSION_ID: Final[str] = "00000000-0000-4000-8000-00000000a355"
_REPRESENTATIVE_TRACE_ID: Final[str] = "00000000-0000-4000-8000-00000000b355"
REPRESENTATIVE_SPECIALISTS: Final[tuple[str, ...]] = ("specialist-one", "specialist-two")

Tokenizer = Callable[[str], int]


def heuristic_token_count(text: str) -> int:
    """Estimate tokens as ceil(chars / 4)."""

    return -(-len(text) // CHARS_PER_TOKEN_HEURISTIC)


def _tiktoken_counter() -> Tokenizer | None:
    """Return a cl100k_base counter when tiktoken and its cached encoding are available."""

    try:
        import tiktoken
    except ImportError:
        return None
    try:
        encoding = tiktoken.get_encoding(_TIKTOKEN_ENCODING)
    except Exception:
        # An uncached encoding tries the network; failing that is not an error
        # in a read-only audit, it is the heuristic's turn.
        return None
    return lambda text: len(encoding.encode(text, disallowed_special=()))


@dataclass(frozen=True, slots=True)
class TokenEstimator:
    """One labelled way of turning text into a token estimate."""

    method: str
    note: str
    count: Tokenizer

    def estimate(self, text: str) -> int:
        return int(self.count(text)) if text else 0


def token_estimator(method: str = "auto", *, tokenizer: Tokenizer | None = None) -> TokenEstimator:
    """Build the estimator the report labels itself with.

    ``auto`` prefers tiktoken and falls back to the heuristic; ``tiktoken``
    insists and raises when it is unavailable; ``chars`` never imports it. An
    injected ``tokenizer`` is for tests and callers that know their model.
    """

    if tokenizer is not None:
        return TokenEstimator(method="injected", note="caller-supplied tokenizer", count=tokenizer)
    if method not in TOKEN_ESTIMATOR_METHODS:
        raise ValueError("token estimator method must be auto, chars, or tiktoken")
    if method in {"auto", "tiktoken"}:
        counter = _tiktoken_counter()
        if counter is not None:
            return TokenEstimator(
                method=TOKEN_ESTIMATOR_TIKTOKEN,
                note="tiktoken cl100k_base encoding; a proxy, not the host model's tokenizer",
                count=counter,
            )
        if method == "tiktoken":
            raise RuntimeError("tiktoken is not importable here; use the chars or auto estimator")
    return TokenEstimator(
        method=TOKEN_ESTIMATOR_HEURISTIC,
        note="heuristic ceil(chars / 4): close for prose, pessimistic for hex digests",
        count=heuristic_token_count,
    )


@dataclass(frozen=True, slots=True)
class ContextComponent:
    """One sized piece of the per-turn frame."""

    name: str
    chars: int
    lines: int
    estimated_tokens: int
    note: str = ""

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "chars": self.chars,
            "lines": self.lines,
            "estimated_tokens": self.estimated_tokens,
            "note": self.note,
        }


def measure_component(
    name: str,
    text: str,
    estimator: TokenEstimator,
    *,
    note: str = "",
) -> ContextComponent:
    """Size one rendered text exactly as delivered."""

    return ContextComponent(
        name=name,
        chars=len(text),
        lines=text.count("\n") + 1 if text else 0,
        estimated_tokens=estimator.estimate(text),
        note=note,
    )


def representative_binding_reference(host: str) -> str:
    """Render the binding line for a representative session on ``host``.

    The line's length is fixed by its format (hashes and generations are
    fixed-width), so a synthetic binding with a zero control epoch sizes it
    exactly without touching live control state.
    """

    delivery_mode = "injected" if resident_manager_host_mode(host) == "persistent" else "request"
    binding = build_resident_manager_binding(
        session_id=_REPRESENTATIVE_SESSION_ID,
        host=host,
        delivery_mode=delivery_mode,
        control_epoch=build_resident_control_epoch(),
    )
    return resident_manager_turn_reference_context(
        binding,
        session_id=_REPRESENTATIVE_SESSION_ID,
        trace_id=_REPRESENTATIVE_TRACE_ID,
    )


def representative_header(specialists: Sequence[str] = REPRESENTATIVE_SPECIALISTS) -> str:
    """Render the five header lines with representative values.

    Marker and instruction are exact; the five values vary per turn with the
    roster names and the model receipt, so these stand in for a typical
    staffed turn rather than any recorded one.
    """

    return format_header(
        {
            "agencies_loaded": ", ".join((*RESIDENT_MANAGER_SLUGS, *specialists)),
            "agencies_delegated": "none",
            "skills_loaded": "none",
            "actual_model_selected": (
                "host-model (parent turn; specialist launches inherit the host model)"
            ),
            "recruited_via": "inference (planner, recruiter, critic; confidence 1.0)",
        }
    )


def representative_header_snapshot(marker: str) -> str:
    """Render one header snapshot exactly as the hook bridge frames it."""

    return format_header_snapshot(
        marker, HEADER_SNAPSHOT_INSTRUCTIONS[marker], representative_header()
    )


def representative_routing_context(
    config: AgencyConfig,
    specialists: Sequence[str] = REPRESENTATIVE_SPECIALISTS,
) -> str:
    """Render the [AGENCY PREFLIGHT] block a staffed turn receives."""

    from agency_runtime.core.selector.pipeline import build_routing_context

    return build_routing_context(
        {
            "selected_ids": list(specialists),
            "confidence": 1.0,
            "status": "applied",
            "source": "workforce_inference",
        },
        config,
    )


def _joined(*segments: str) -> str:
    return _SEGMENT_SEPARATOR.join(segment for segment in segments if segment)


def _summary(values: Sequence[int]) -> dict[str, int]:
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "min": ordered[0] if ordered else 0,
        "p50": nearest_rank_percentile(ordered, 50),
        "p95": nearest_rank_percentile(ordered, 95),
        "max": ordered[-1] if ordered else 0,
    }


def measure_staffed_capsules(
    store: Any,
    config: AgencyConfig,
    *,
    host: str = "",
    limit: int = DEFAULT_CAPSULE_SAMPLE,
    estimator: TokenEstimator | None = None,
) -> dict[str, Any]:
    """Replay the newest ready turns' capsules from their exact immutable versions.

    A ready recipe is content-free, so the delivered specialist capsule is
    rebuilt the way a replay does it -- from the referenced prompt versions --
    and sized. A turn whose versions are no longer registered is counted, not
    guessed. Unstaffed ready turns (zero references) are counted separately so
    they do not pull the staffed median toward zero.
    """

    from agency_runtime.core.selector.pipeline import build_routing_context
    from agency_runtime.core.specialist_context import rebuild_versioned_specialist_context

    counter = estimator or token_estimator()
    rows = store.get_recent_ready_recipes(host=host, limit=limit)
    disabled = frozenset(config.agents.disabled)
    capsule_chars: list[int] = []
    capsule_tokens: list[int] = []
    routing_chars: list[int] = []
    specialists: list[int] = []
    recipe_chars = [int(row.get("recipe_chars") or 0) for row in rows]
    undecodable = unreplayable = unstaffed = 0
    for row in rows:
        recipe = row.get("recipe")
        if not isinstance(recipe, Mapping):
            undecodable += 1
            continue
        raw_refs = recipe.get("specialist_refs")
        refs = (
            [ref for ref in raw_refs if isinstance(ref, Mapping)]
            if isinstance(raw_refs, list)
            else []
        )
        if not refs:
            unstaffed += 1
            continue
        try:
            loaded = rebuild_versioned_specialist_context(
                store,
                refs,
                maximum_chars=int(recipe.get("context_limit") or MAX_PREFLIGHT_CONTEXT_CHARS),
                disabled_agents=disabled,
            )
        except (RuntimeError, ValueError):
            unreplayable += 1
            continue
        routing = recipe.get("routing")
        routing_context = build_routing_context(
            dict(routing) if isinstance(routing, Mapping) else {},
            config,
        )
        capsule_chars.append(len(loaded.context))
        capsule_tokens.append(counter.estimate(loaded.context))
        routing_chars.append(len(routing_context))
        specialists.append(len(loaded.slugs))
    measured = bool(capsule_chars)
    if measured:
        reason = ""
    elif not rows:
        reason = "no ready turn in the store"
    else:
        reason = "no staffed ready turn could be replayed from its immutable versions"
    return {
        "measured": measured,
        "host": host or None,
        "ready_runs_read": len(rows),
        "staffed_replayed": len(capsule_chars),
        "unstaffed_ready": unstaffed,
        "undecodable": undecodable,
        "unreplayable": unreplayable,
        "specialist_capsule_chars": _summary(capsule_chars),
        "specialist_capsule_estimated_tokens": _summary(capsule_tokens),
        "routing_context_chars": _summary(routing_chars),
        "specialists_per_staffed_turn": _summary(specialists),
        "recipe_json_chars": _summary(recipe_chars),
        "reason": reason,
    }


def _turn(
    estimator: TokenEstimator,
    *,
    components: Sequence[str],
    text: str,
    snapshot: str,
    carries_operator_policy: bool,
    capsule: Mapping[str, Any] | None,
    note: str,
) -> dict[str, Any]:
    delivered = _joined(text, snapshot)
    fixed_chars = len(delivered)
    fixed_tokens = estimator.estimate(delivered)
    result: dict[str, Any] = {
        "components": list(components),
        "carries_operator_policy": carries_operator_policy,
        "fixed_chars": fixed_chars,
        "fixed_estimated_tokens": fixed_tokens,
        "note": note,
    }
    if capsule is None:
        result["chars"] = fixed_chars
        result["estimated_tokens"] = fixed_tokens
        return result
    if capsule.get("measured"):
        capsule_p50 = int(capsule["specialist_capsule_chars"]["p50"])
        capsule_tokens_p50 = int(capsule["specialist_capsule_estimated_tokens"]["p50"])
        result["capsule_p50_chars"] = capsule_p50
        result["capsule_p50_estimated_tokens"] = capsule_tokens_p50
        result["chars"] = fixed_chars + len(_SEGMENT_SEPARATOR) + capsule_p50
        result["estimated_tokens"] = fixed_tokens + capsule_tokens_p50
    else:
        result["chars"] = None
        result["estimated_tokens"] = None
        result["bound_chars"] = MAX_PREFLIGHT_CONTEXT_CHARS + len(_joined("x", snapshot)) - 1
        result["bound_estimated_tokens"] = estimator.estimate("x" * int(result["bound_chars"]))
    return result


def context_budget_report(
    config: AgencyConfig,
    *,
    kernel: str = RESIDENT_MANAGER_KERNEL,
    policy: str | None = None,
    host: str = "claude",
    estimator: TokenEstimator | None = None,
    capsules: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Size every per-turn component and isolate what AR-355 added.

    ``policy`` defaults to the configured operator policy; passing text sizes a
    candidate before it is set. ``capsules`` is the output of
    :func:`measure_staffed_capsules`; without it the staffed total is a bound.
    """

    counter = estimator or token_estimator()
    policy_text = config.operator_policy if policy is None else normalized_operator_policy(policy)
    policy_block = render_operator_policy(policy_text)
    reference = representative_binding_reference(host)
    routing = representative_routing_context(config)
    snapshots = {
        marker: representative_header_snapshot(marker) for marker in HEADER_SNAPSHOT_INSTRUCTIONS
    }
    snapshot = snapshots["INITIAL"] if host in HEADER_SNAPSHOT_HOSTS else ""
    components = {
        "resident_kernel": measure_component(
            "resident_kernel",
            kernel,
            counter,
            note=(
                f"steward kernel v{RESIDENT_MANAGER_KERNEL_VERSION}; every request-scoped turn, "
                "and once per persistent binding on claude"
            ),
        ),
        "resident_binding_reference": measure_component(
            "resident_binding_reference",
            reference,
            counter,
            note=f"content-free binding line for host {host}; every turn",
        ),
        "operator_policy_block": measure_component(
            "operator_policy_block",
            policy_block,
            counter,
            note="owner policy text inside Agency's header/footer; ready turns only",
        ),
        "routing_context_staffed": measure_component(
            "routing_context_staffed",
            routing,
            counter,
            note="[AGENCY PREFLIGHT] line and header instruction for two specialists; ready turns",
        ),
        "header_snapshot_initial": measure_component(
            "header_snapshot_initial",
            snapshots["INITIAL"],
            counter,
            note=(
                f"UserPromptSubmit on {', '.join(HEADER_SNAPSHOT_HOSTS)}; "
                "five header lines use representative values"
            ),
        ),
        "header_snapshot_updated": measure_component(
            "header_snapshot_updated",
            snapshots["UPDATED"],
            counter,
            note="codex only, once per tool call; not counted in the per-turn totals",
        ),
        "header_snapshot_final": measure_component(
            "header_snapshot_final",
            snapshots["FINAL"],
            counter,
            note="codex only, after a native wait; not counted in the per-turn totals",
        ),
    }
    # A fail-open turn's capsule: kernel + binding reference, the operator
    # policy (AR-356 restored it on this path), and one bounded disclosure line
    # naming the persisted reason class; the representative reason is the
    # window's dominant shape (AR-353).
    disclosure = render_fail_open_disclosure(
        "workforce_inference_failed", ["staffing_critic_rejected"]
    )
    components["fail_open_disclosure"] = measure_component(
        "fail_open_disclosure",
        disclosure,
        counter,
        note="AR-356 disclosure line; fail-open turns only, representative reason class",
    )
    addition = f"{RESIDENT_KERNEL_V5_ADDITION}\n"
    addition_component = measure_component(
        "kernel_v5_addition",
        addition,
        counter,
        note="the roster-awareness sentence (two physical lines) and its joining newline",
    )
    policy_component = components["operator_policy_block"]
    separator = len(_SEGMENT_SEPARATOR) if policy_block else 0
    ready_delta_text = _joined(addition.rstrip("\n"), policy_block) if policy_block else addition
    fail_open_note = (
        "a fail-open turn delivers kernel + binding reference, the operator-policy "
        "block, and the AR-356 disclosure line (core/preflight.py "
        "_fail_open_preflight_result); after AR-367 its binding is claimed and "
        "acknowledged like a ready turn's, so later fail-open turns reuse the kernel"
    )
    return {
        "estimator": {"method": counter.method, "note": counter.note},
        "host": host,
        "header_snapshot_hosts": list(HEADER_SNAPSHOT_HOSTS),
        "kernel": {
            "version": RESIDENT_MANAGER_KERNEL_VERSION,
            "chars": len(kernel),
            "budget_chars": MAX_RESIDENT_MANAGER_KERNEL_CHARS,
        },
        "components": {name: component.as_dict() for name, component in components.items()},
        "ar355_delta": {
            "kernel_v5_addition": addition_component.as_dict(),
            "operator_policy_block": {
                **policy_component.as_dict(),
                "policy_text_chars": len(policy_text),
                "framing_chars": max(0, len(policy_block) - len(policy_text)),
                "separator_chars": separator,
            },
            "per_ready_turn": {
                "chars": len(addition) + separator + len(policy_block),
                "estimated_tokens": counter.estimate(ready_delta_text),
            },
            "per_fail_open_turn": {
                "chars": len(addition) + separator + len(policy_block),
                "estimated_tokens": counter.estimate(ready_delta_text),
            },
            "note": fail_open_note,
        },
        "per_turn": {
            "fail_open_turn": _turn(
                counter,
                components=[
                    "resident_kernel",
                    "resident_binding_reference",
                    "operator_policy_block",
                    "fail_open_disclosure",
                    "header_snapshot_initial",
                ],
                text=_joined(kernel, reference, policy_block, disclosure),
                snapshot=snapshot,
                carries_operator_policy=True,
                capsule=None,
                note=fail_open_note,
            ),
            "fail_open_turn_reused_binding": _turn(
                counter,
                components=[
                    "resident_binding_reference",
                    "operator_policy_block",
                    "fail_open_disclosure",
                    "header_snapshot_initial",
                ],
                text=_joined(reference, policy_block, disclosure),
                snapshot=snapshot,
                carries_operator_policy=True,
                capsule=None,
                note=(
                    "persistent hosts after an acknowledged binding (delivery=reused); "
                    "reachable on fail-open turns since AR-367"
                ),
            ),
            "staffed_turn": _turn(
                counter,
                components=[
                    "resident_kernel",
                    "resident_binding_reference",
                    "operator_policy_block",
                    "routing_context_staffed",
                    "specialist_capsule",
                    "header_snapshot_initial",
                ],
                text=_joined(kernel, reference, policy_block, routing),
                snapshot=snapshot,
                carries_operator_policy=True,
                capsule=capsules if capsules is not None else {"measured": False},
                note=(
                    "kernel + binding reference + operator policy + routing context + the "
                    "replayed specialist capsule (p50 when measured, else the delivery bound)"
                ),
            ),
        },
        "staffed_capsule": (
            dict(capsules)
            if capsules is not None
            else {"measured": False, "reason": "no store sample supplied"}
        ),
        "bounds": {
            "context_limit_chars": MAX_PREFLIGHT_CONTEXT_CHARS,
            "specialist_capsule_ceiling_chars": MAX_SPECIALIST_CONTEXT_CHARS,
            "kernel_budget_chars": MAX_RESIDENT_MANAGER_KERNEL_CHARS,
            "operator_policy_budget_chars": MAX_OPERATOR_POLICY_CHARS,
            "binding_reference_ceiling_chars": MAX_RESIDENT_MANAGER_TURN_REFERENCE_CHARS,
        },
    }


__all__ = [
    "CHARS_PER_TOKEN_HEURISTIC",
    "DEFAULT_CAPSULE_SAMPLE",
    "HEADER_SNAPSHOT_HOSTS",
    "RESIDENT_KERNEL_V5_ADDITION",
    "TOKEN_ESTIMATOR_HEURISTIC",
    "TOKEN_ESTIMATOR_METHODS",
    "TOKEN_ESTIMATOR_TIKTOKEN",
    "ContextComponent",
    "TokenEstimator",
    "context_budget_report",
    "heuristic_token_count",
    "measure_component",
    "measure_staffed_capsules",
    "representative_binding_reference",
    "representative_header_snapshot",
    "representative_routing_context",
    "token_estimator",
]
