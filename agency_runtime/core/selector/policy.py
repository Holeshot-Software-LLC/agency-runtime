"""Companion policy — deterministic action→agent mapping."""

from __future__ import annotations

import logging
import os
import re
import time
from collections.abc import Collection
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("agency_runtime.selector.policy")

_DEFAULT_POLICY_PATH = Path.home() / ".agency-runtime" / "companion_policy.yaml"
_BUNDLED_POLICY_PATH = Path(__file__).resolve().parents[1] / "companion_policy.yaml"
_BUNDLED_COMPANION_POLICY: dict[str, Any] | None = None


def _resolve_policy_path() -> Path:
    """Resolve policy path from centralized config, env, or default."""
    env_path = os.environ.get("AGENCY_POLICY_PATH")
    if env_path:
        return Path(env_path)
    try:
        from agency_runtime.core.config import load_config
        cfg = load_config()
        if cfg.companion_policy_path:
            return Path(os.path.expanduser(cfg.companion_policy_path))
    except Exception:
        pass
    return _DEFAULT_POLICY_PATH

def _load_bundled_policy() -> dict[str, Any]:
    """Load the packaged broad-action companion policy."""
    global _BUNDLED_COMPANION_POLICY
    if _BUNDLED_COMPANION_POLICY is None:
        try:
            loaded = yaml.safe_load(_BUNDLED_POLICY_PATH.read_text(encoding="utf-8")) or {}
            _BUNDLED_COMPANION_POLICY = loaded if isinstance(loaded, dict) else {}
        except Exception as exc:
            logger.warning("could not load bundled companion policy: %s", exc)
            _BUNDLED_COMPANION_POLICY = {}
    return _BUNDLED_COMPANION_POLICY


def load_bundled_policy() -> dict[str, Any]:
    """Return the packaged policy, independent of per-user configuration."""
    return _load_bundled_policy()


_COMPANION_POLICY: dict[str, Any] | None = None
_POLICY_MTIME: int | float = 0.0
_POLICY_PATH: Path | None = None
_POLICY_REQUEST_KEY = ""
_POLICY_CHECKED_AT = 0.0
_POLICY_RECHECK_SECONDS = 1.0

# The bundled policy historically used a handful of intentionally truncated
# stems.  Keep those compatible, but constrain them to the start of a complete
# lexical token.  All other triggers are exact words or contiguous phrases.
_PREFIX_TRIGGERS = frozenset({
    "orchestrat", "profil", "scalab", "tokeni", "vulnerab",
})
_LEXEME_RE = re.compile(r"[a-z0-9]+(?:\+\+|#)?", re.IGNORECASE)
_CONDITION_STOPWORDS = frozenset({
    "and", "are", "for", "from", "in", "into", "new", "of", "on", "or",
    "the", "to", "when", "with", "work", "needed", "involved",
})


def _lexemes(text: str) -> tuple[str, ...]:
    return tuple(_LEXEME_RE.findall(text.lower()))


@lru_cache(maxsize=512)
def _compiled_trigger(trigger: str) -> re.Pattern[str] | None:
    """Compile an exact token/phrase trigger, or an explicit token prefix."""
    normalized = trigger.strip().lower()
    if not normalized or normalized == "_fallback_":
        return None

    words = _lexemes(normalized.rstrip("*"))
    if not words:
        return None
    separator = r"(?:[^a-z0-9+#]+)"
    phrase = separator.join(re.escape(word) for word in words)
    use_prefix = normalized.endswith("*") or (
        len(words) == 1 and words[0] in _PREFIX_TRIGGERS
    )
    suffix = r"[a-z0-9+#]*" if use_prefix else ""
    return re.compile(rf"(?<![a-z0-9+#]){phrase}{suffix}(?![a-z0-9+#])", re.IGNORECASE)


def _matches(text: str, trigger: Any) -> bool:
    if not isinstance(trigger, str):
        return False
    pattern = _compiled_trigger(trigger)
    return bool(pattern and pattern.search(text))


def _matches_condition(text: str, condition: Any) -> bool:
    """Match a conditional description without substring false positives."""
    if not isinstance(condition, str):
        return False
    # Preserve explicit comma-delimited phrases, then fall back to meaningful
    # exact tokens.  Conditions are inclusive hints rather than full parsers.
    clauses = [part.strip() for part in re.split(r",|\bor\b", condition.lower())]
    for clause in clauses:
        words = [word for word in _lexemes(clause) if word not in _CONDITION_STOPWORDS]
        if not words:
            continue
        if _matches(text, " ".join(words)):
            return True
        variants: set[str] = set(words)
        for word in words:
            if len(word) > 4 and word.endswith("ies"):
                variants.add(f"{word[:-3]}y")
            elif len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
                variants.add(word[:-1])
        if any(_matches(text, word) for word in variants if len(word) >= 3):
            return True
    return False


def load_policy(policy_path: Path | None = None) -> dict[str, Any]:
    """Load companion policy YAML, auto-reloading on file change."""
    global _COMPANION_POLICY, _POLICY_MTIME, _POLICY_PATH
    global _POLICY_REQUEST_KEY, _POLICY_CHECKED_AT

    requested = policy_path or _resolve_policy_path()
    request_key = str(requested.expanduser())
    now = time.monotonic()
    if (
        policy_path is None
        and request_key == _POLICY_REQUEST_KEY
        and now - _POLICY_CHECKED_AT < _POLICY_RECHECK_SECONDS
    ):
        return _COMPANION_POLICY or _load_bundled_policy()

    path = requested.expanduser().resolve()
    try:
        mtime = path.stat().st_mtime_ns
    except OSError:
        _POLICY_PATH = path
        _POLICY_MTIME = -1
        _POLICY_REQUEST_KEY = request_key
        _POLICY_CHECKED_AT = now
        logger.debug("companion policy not found at %s", path)
        return _load_bundled_policy()

    if _COMPANION_POLICY is None or path != _POLICY_PATH or mtime != _POLICY_MTIME:
        try:
            loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            _COMPANION_POLICY = loaded if isinstance(loaded, dict) else {}
            _POLICY_MTIME = mtime
            _POLICY_PATH = path
            _POLICY_REQUEST_KEY = request_key
            _POLICY_CHECKED_AT = now
            actions = _COMPANION_POLICY.get("actions", {})
            logger.info("companion policy loaded (%d actions)", len(actions))
        except Exception as exc:
            logger.warning("could not load companion policy: %s", exc)
            if _POLICY_PATH != path:
                return _load_bundled_policy()
    else:
        _POLICY_REQUEST_KEY = request_key
        _POLICY_CHECKED_AT = now
    return _COMPANION_POLICY or _load_bundled_policy()


def _policy_routes(
    policy: dict[str, Any],
) -> tuple[list[dict[str, str]], list[str]]:
    """Collect every action and division route with precise validation paths."""
    routes: list[dict[str, str]] = []
    errors: list[str] = []
    actions = policy.get("actions")
    if not isinstance(actions, dict):
        errors.append("actions must be a mapping")
        actions = {}
    for action_name, action in actions.items():
        action_path = f"actions.{action_name}"
        if not isinstance(action, dict):
            errors.append(f"{action_path} must be a mapping")
            continue
        for kind in ("always_include", "conditional"):
            entries = action.get(kind, [])
            if not isinstance(entries, list):
                errors.append(f"{action_path}.{kind} must be a list")
                continue
            for index, entry in enumerate(entries):
                path = f"{action_path}.{kind}[{index}]"
                if not isinstance(entry, dict):
                    errors.append(f"{path} must be a mapping")
                    continue
                slug = entry.get("slug")
                if not isinstance(slug, str) or not slug.strip():
                    errors.append(f"{path}.slug must be a non-empty string")
                    continue
                if kind == "conditional":
                    condition = entry.get("when")
                    if not isinstance(condition, str) or not condition.strip():
                        errors.append(f"{path}.when must be a non-empty string")
                routes.append(
                    {
                        "path": path,
                        "slug": slug.strip(),
                        "source": "action",
                        "group": str(action_name),
                        "kind": kind,
                    }
                )

    divisions = policy.get("division_anchors", {})
    if not isinstance(divisions, dict):
        errors.append("division_anchors must be a mapping")
        divisions = {}
    for division_name, division in divisions.items():
        division_path = f"division_anchors.{division_name}"
        if not isinstance(division, dict):
            errors.append(f"{division_path} must be a mapping")
            continue
        anchor = division.get("anchor")
        if anchor is not None:
            if not isinstance(anchor, str) or not anchor.strip():
                errors.append(f"{division_path}.anchor must be a non-empty string")
            else:
                routes.append(
                    {
                        "path": f"{division_path}.anchor",
                        "slug": anchor.strip(),
                        "source": "division",
                        "group": str(division_name),
                        "kind": "anchor",
                    }
                )
        conditional = division.get("conditional", [])
        if not isinstance(conditional, list):
            errors.append(f"{division_path}.conditional must be a list")
            continue
        for index, entry in enumerate(conditional):
            path = f"{division_path}.conditional[{index}]"
            if isinstance(entry, dict):
                slug = entry.get("slug")
                condition = entry.get("when")
            elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
                slug, condition = entry[0], entry[1]
            else:
                errors.append(f"{path} must contain a slug and condition")
                continue
            if not isinstance(slug, str) or not slug.strip():
                errors.append(f"{path}.slug must be a non-empty string")
                continue
            if not isinstance(condition, str) or not condition.strip():
                errors.append(f"{path}.when must be a non-empty string")
            routes.append(
                {
                    "path": path,
                    "slug": slug.strip(),
                    "source": "division",
                    "group": str(division_name),
                    "kind": "conditional",
                }
            )
    return routes, errors


def _slug_list(value: Any, *, path: str, errors: list[str]) -> list[str]:
    if not isinstance(value, list):
        errors.append(f"{path} must be a list")
        return []
    result: list[str] = []
    for index, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{path}[{index}] must be a non-empty string")
            continue
        result.append(item.strip())
    if len(result) != len(set(result)):
        errors.append(f"{path} must not contain duplicate slugs")
    return result


def validate_policy(
    policy: dict[str, Any],
    active_slugs: Collection[str],
) -> dict[str, Any]:
    """Validate policy structure and resolve governed route availability.

    Policies predating the availability registry remain loadable: their routes
    are treated as enabled and therefore validate only when every referenced
    specialist is active. The bundled policy uses the explicit v1 registry.
    """
    routes, errors = _policy_routes(policy)
    referenced = {route["slug"] for route in routes}
    active = {str(slug) for slug in active_slugs if str(slug)}
    availability = policy.get("specialist_availability")
    gated_reason = ""
    mode = "explicit"
    if availability is None:
        mode = "legacy-all-enabled"
        enabled = set(referenced)
        gated: set[str] = set()
    elif not isinstance(availability, dict):
        errors.append("specialist_availability must be a mapping")
        enabled = set()
        gated = set()
    else:
        if availability.get("schema_version") != 1:
            errors.append("specialist_availability.schema_version must be 1")
        enabled_items = _slug_list(
            availability.get("enabled"),
            path="specialist_availability.enabled",
            errors=errors,
        )
        gated_config = availability.get("roster_gated")
        if not isinstance(gated_config, dict):
            errors.append("specialist_availability.roster_gated must be a mapping")
            gated_items: list[str] = []
        else:
            reason = gated_config.get("reason")
            if not isinstance(reason, str) or not reason.strip():
                errors.append(
                    "specialist_availability.roster_gated.reason "
                    "must be a non-empty string"
                )
            else:
                gated_reason = reason.strip()
            gated_items = _slug_list(
                gated_config.get("slugs"),
                path="specialist_availability.roster_gated.slugs",
                errors=errors,
            )
        enabled = set(enabled_items)
        gated = set(gated_items)

    overlap = sorted(enabled & gated)
    if overlap:
        errors.append(
            "availability slugs cannot be both enabled and roster-gated: "
            + ", ".join(overlap)
        )
    undeclared = sorted(referenced - enabled - gated)
    if undeclared:
        errors.append(
            "policy routes have no availability declaration: "
            + ", ".join(undeclared)
        )
    unreferenced = sorted((enabled | gated) - referenced)
    if unreferenced:
        errors.append(
            "availability declares unreferenced specialists: "
            + ", ".join(unreferenced)
        )

    missing_enabled = sorted((enabled & referenced) - active)
    for slug in missing_enabled:
        errors.append(f"enabled specialist is not active: {slug}")
    active_gated = gated & referenced & active
    enabled_slugs = sorted((enabled & referenced & active) | active_gated)
    disabled_slugs = sorted((gated & referenced) - active)
    disabled_routes = [
        {
            "slug": slug,
            "reason": gated_reason,
        }
        for slug in disabled_slugs
    ]
    return {
        "valid": not errors,
        "mode": mode,
        "errors": errors,
        "route_count": len(routes),
        "unique_policy_slugs": len(referenced),
        "enabled_declared": sorted(enabled & referenced),
        "enabled_slugs": enabled_slugs,
        "roster_gated_slugs": sorted(gated & referenced),
        "roster_gated_enabled": sorted(active_gated),
        "missing_enabled": missing_enabled,
        "disabled_count": len(disabled_slugs),
        "disabled_routes": disabled_routes,
        "routes": routes,
    }


def detect_actions(
    message: str,
    policy: dict[str, Any] | None = None,
    *,
    active_slugs: Collection[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Detect which actions match the user message.

    Returns (action_names, companion_ids) where companion_ids is the union
    of all always_include slugs from matched actions, PLUS DEFAULT companions.
    """
    policy = policy if policy is not None else load_policy()
    if not policy:
        return [], []

    actions_def = policy.get("actions", {})
    if not actions_def:
        return [], []

    matched_actions: list[str] = []
    companion_ids: list[str] = []
    eligible: set[str] | None = None
    if active_slugs is not None:
        availability = validate_policy(policy, active_slugs)
        eligible = set(availability["enabled_slugs"])
    elif isinstance(policy.get("specialist_availability"), dict):
        # Explicit policies default to their required bundled set. Roster-gated
        # routes need an active roster supplied by the caller before they can
        # become eligible. Legacy custom policies retain their prior behavior.
        declared = policy["specialist_availability"].get("enabled", [])
        eligible = {
            item.strip()
            for item in declared
            if isinstance(item, str) and item.strip()
        }

    def add_companion(slug: Any) -> None:
        if not isinstance(slug, str) or not slug:
            return
        if eligible is not None and slug not in eligible:
            return
        if slug not in companion_ids:
            companion_ids.append(slug)

    for action_name, action_def in actions_def.items():
        triggers = action_def.get("triggers", [])
        if not triggers:
            continue

        if action_name == "DEFAULT":
            for companion in action_def.get("always_include", []):
                add_companion(companion.get("slug", ""))
            continue

        if any(_matches(message, trigger) for trigger in triggers):
            matched_actions.append(action_name)
            for companion in action_def.get("always_include", []):
                add_companion(companion.get("slug", ""))

            for cond in action_def.get("conditional", []):
                cond_slug = cond.get("slug", "")
                cond_when = cond.get("when", "")
                if cond_slug and cond_when:
                    if _matches_condition(message, cond_when):
                        add_companion(cond_slug)

    division_anchors = policy.get("division_anchors", {})
    for _div_name, div_def in division_anchors.items():
        anchor_keywords = div_def.get("keywords", [])
        if any(_matches(message, keyword) for keyword in anchor_keywords):
            anchor = div_def.get("anchor", "")
            add_companion(anchor)
            for cond_entry in div_def.get("conditional", []):
                if isinstance(cond_entry, dict):
                    cond_slug = cond_entry.get("slug", "")
                    cond_kw = cond_entry.get("when", "")
                elif isinstance(cond_entry, (list, tuple)) and len(cond_entry) >= 2:
                    cond_slug, cond_kw = cond_entry[0], cond_entry[1]
                else:
                    continue
                if _matches(message, cond_kw):
                    add_companion(cond_slug)

    return matched_actions, companion_ids
