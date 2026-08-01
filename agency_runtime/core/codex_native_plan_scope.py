"""Private exact authority for opaque Codex native-child launches.

Codex deliberately keeps collaboration messages encrypted at ``PreToolUse``.
The preflight process is the last trusted boundary that still has the exact
plaintext work-unit resources, so it projects a bounded path capability for
later hook use.  This payload is private Store authority, not public turn
evidence, and is removed when its parent turn becomes terminal.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from hashlib import sha256
from typing import Any, Final

from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.native_child_activation import (
    MAX_NATIVE_CHILD_ACTIVATION_BYTES,
    MAX_NATIVE_CHILD_PATH_PREFIXES,
    NativeChildEvidenceContract,
    NativeChildMutationScope,
    NativeChildSpecialistIdentity,
    build_native_child_evidence_contract,
    build_native_child_mutation_scope,
    build_native_child_specialist_identity,
)

CODEX_NATIVE_PLAN_SCOPE_VERSION: Final[int] = 1
_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "version",
        "work_unit_id",
        "specialist",
        "goal_hash",
        "resource_hashes",
        "mutation_scope",
        "evidence_contract",
    }
)
_DIGEST_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")
_WORK_UNIT_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,159}$")


@dataclass(frozen=True, slots=True)
class CodexNativePlanScope:
    """One immutable preflight-derived capability for one persisted plan row."""

    work_unit_id: str
    specialist: NativeChildSpecialistIdentity
    goal_hash: str
    resource_hashes: tuple[str, ...]
    mutation_scope: NativeChildMutationScope
    evidence_contract: NativeChildEvidenceContract

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": CODEX_NATIVE_PLAN_SCOPE_VERSION,
            "work_unit_id": self.work_unit_id,
            "specialist": self.specialist.as_dict(),
            "goal_hash": self.goal_hash,
            "resource_hashes": list(self.resource_hashes),
            "mutation_scope": self.mutation_scope.as_dict(),
            "evidence_contract": self.evidence_contract.as_dict(),
        }


def _digest(value: object, *, field: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    normalized = value.strip().casefold()
    if _DIGEST_RE.fullmatch(normalized) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return normalized


def _resource_digests(value: object) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise ValueError("resource_hashes must be a list")
    if not 1 <= len(value) <= MAX_NATIVE_CHILD_PATH_PREFIXES:
        raise ValueError("resource_hashes exceed the native-child scope bound")
    result = tuple(_digest(item, field="resource hash") for item in value)
    if len(result) != len(set(result)):
        raise ValueError("resource_hashes must not contain duplicates")
    return result


def build_codex_native_plan_scope(
    *,
    work_unit_id: object,
    specialist_slug: object,
    specialist_version: object,
    specialist_prompt_hash: object,
    goal_hash: object,
    resource_hashes: object,
    mutation_mode: object,
    mutation_path_prefixes: object,
    evidence_contract_id: object,
    evidence_requirements: object,
) -> CodexNativePlanScope:
    """Build and cross-check one exact opaque-launch path capability."""

    unit = str(work_unit_id or "").strip()
    if _WORK_UNIT_RE.fullmatch(unit) is None:
        raise ValueError("work_unit_id is invalid")
    specialist = build_native_child_specialist_identity(
        slug=specialist_slug,
        version=specialist_version,
        content_hash=specialist_prompt_hash,
    )
    resources = _resource_digests(resource_hashes)
    mutation = build_native_child_mutation_scope(
        mode=mutation_mode,
        path_prefixes=mutation_path_prefixes,
    )
    evidence = build_native_child_evidence_contract(
        contract_id=evidence_contract_id,
        requirements=evidence_requirements,
    )
    if mutation.mode == "workspace_write":
        projected = tuple(
            sorted(
                sha256(
                    ("repository-workspace" if path == "." else path).encode(
                        "utf-8", errors="surrogatepass"
                    )
                ).hexdigest()
                for path in mutation.path_prefixes
            )
        )
        if projected != tuple(sorted(resources)):
            raise ValueError("mutation path prefixes do not match the planned resource hashes")
    return CodexNativePlanScope(
        work_unit_id=unit,
        specialist=specialist,
        goal_hash=_digest(goal_hash, field="goal_hash"),
        resource_hashes=resources,
        mutation_scope=mutation,
        evidence_contract=evidence,
    )


def validate_codex_native_plan_scope(value: object) -> CodexNativePlanScope:
    """Validate an exact mapping or return a rebuilt immutable scope."""

    raw = value.as_dict() if isinstance(value, CodexNativePlanScope) else value
    if not isinstance(raw, Mapping) or set(raw) != _FIELDS:
        raise ValueError("Codex native plan scope is malformed")
    if raw.get("version") != CODEX_NATIVE_PLAN_SCOPE_VERSION:
        raise ValueError("Codex native plan scope version is unsupported")
    specialist = raw.get("specialist")
    mutation = raw.get("mutation_scope")
    evidence = raw.get("evidence_contract")
    if not all(isinstance(item, Mapping) for item in (specialist, mutation, evidence)):
        raise ValueError("Codex native plan scope is malformed")
    return build_codex_native_plan_scope(
        work_unit_id=raw.get("work_unit_id"),
        specialist_slug=specialist.get("slug"),
        specialist_version=specialist.get("version"),
        specialist_prompt_hash=specialist.get("content_hash"),
        goal_hash=raw.get("goal_hash"),
        resource_hashes=raw.get("resource_hashes"),
        mutation_mode=mutation.get("mode"),
        mutation_path_prefixes=mutation.get("path_prefixes"),
        evidence_contract_id=evidence.get("contract_id"),
        evidence_requirements=evidence.get("requirements"),
    )


def serialize_codex_native_plan_scope(value: object) -> str:
    """Serialize one canonical bounded private Store payload."""

    scope = validate_codex_native_plan_scope(value)
    payload = json.dumps(
        scope.as_dict(),
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    if len(payload.encode("utf-8")) > MAX_NATIVE_CHILD_ACTIVATION_BYTES:
        raise ValueError("Codex native plan scope exceeds the Store payload bound")
    return payload


def deserialize_codex_native_plan_scope(payload: object) -> CodexNativePlanScope:
    """Read one canonical payload and reject malformed or noncanonical state."""

    if not isinstance(payload, str):
        raise ValueError("Codex native plan scope payload must be text")
    try:
        raw = safe_load_bounded_json(
            payload,
            maximum_bytes=MAX_NATIVE_CHILD_ACTIVATION_BYTES,
            maximum_depth=8,
            maximum_nodes=128,
        )
        scope = validate_codex_native_plan_scope(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("Codex native plan scope payload is invalid") from exc
    if serialize_codex_native_plan_scope(scope) != payload:
        raise ValueError("Codex native plan scope payload is not canonical")
    return scope


__all__ = [
    "CODEX_NATIVE_PLAN_SCOPE_VERSION",
    "CodexNativePlanScope",
    "build_codex_native_plan_scope",
    "deserialize_codex_native_plan_scope",
    "serialize_codex_native_plan_scope",
    "validate_codex_native_plan_scope",
]
