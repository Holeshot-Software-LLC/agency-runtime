"""Companion policy — deterministic action→agent mapping."""

from __future__ import annotations

import logging
import os
import re
import time
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


def detect_actions(
    message: str,
    policy: dict[str, Any] | None = None,
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

    for action_name, action_def in actions_def.items():
        triggers = action_def.get("triggers", [])
        if not triggers:
            continue

        if action_name == "DEFAULT":
            for companion in action_def.get("always_include", []):
                slug = companion.get("slug", "")
                if slug and slug not in companion_ids:
                    companion_ids.append(slug)
            continue

        if any(_matches(message, trigger) for trigger in triggers):
            matched_actions.append(action_name)
            for companion in action_def.get("always_include", []):
                slug = companion.get("slug", "")
                if slug and slug not in companion_ids:
                    companion_ids.append(slug)

            for cond in action_def.get("conditional", []):
                cond_slug = cond.get("slug", "")
                cond_when = cond.get("when", "")
                if cond_slug and cond_when:
                    if _matches_condition(message, cond_when):
                        if cond_slug not in companion_ids:
                            companion_ids.append(cond_slug)

    division_anchors = policy.get("division_anchors", {})
    for _div_name, div_def in division_anchors.items():
        anchor_keywords = div_def.get("keywords", [])
        if any(_matches(message, keyword) for keyword in anchor_keywords):
            anchor = div_def.get("anchor", "")
            if anchor and anchor not in companion_ids:
                companion_ids.append(anchor)
            for cond_entry in div_def.get("conditional", []):
                if len(cond_entry) >= 2:
                    cond_slug, cond_kw = cond_entry[0], cond_entry[1]
                    if _matches(message, cond_kw) and cond_slug not in companion_ids:
                        companion_ids.append(cond_slug)

    return matched_actions, companion_ids
