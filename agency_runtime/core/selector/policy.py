"""Companion policy — deterministic action→agent mapping."""

from __future__ import annotations

import logging
import os
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


_COMPANION_POLICY: dict[str, Any] | None = None
_POLICY_MTIME: float = 0.0


def load_policy(policy_path: Path | None = None) -> dict[str, Any]:
    """Load companion policy YAML, auto-reloading on file change."""
    global _COMPANION_POLICY, _POLICY_MTIME

    path = policy_path or _resolve_policy_path()
    try:
        mtime = path.stat().st_mtime
    except OSError:
        logger.debug("companion policy not found at %s", path)
        return _COMPANION_POLICY or _load_bundled_policy()

    if _COMPANION_POLICY is None or mtime != _POLICY_MTIME:
        try:
            loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            _COMPANION_POLICY = loaded if isinstance(loaded, dict) else {}
            _POLICY_MTIME = mtime
            actions = _COMPANION_POLICY.get("actions", {})
            logger.info("companion policy loaded (%d actions)", len(actions))
        except Exception as exc:
            logger.warning("could not load companion policy: %s", exc)
            if _COMPANION_POLICY is None:
                _COMPANION_POLICY = {}
    return _COMPANION_POLICY or _load_bundled_policy()


def detect_actions(message: str) -> tuple[list[str], list[str]]:
    """Detect which actions match the user message.

    Returns (action_names, companion_ids) where companion_ids is the union
    of all always_include slugs from matched actions, PLUS DEFAULT companions.
    """
    policy = load_policy()
    if not policy:
        return [], []

    actions_def = policy.get("actions", {})
    if not actions_def:
        return [], []

    msg_lower = message.lower()
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

        if any(t in msg_lower for t in triggers if t != "_fallback_"):
            matched_actions.append(action_name)
            for companion in action_def.get("always_include", []):
                slug = companion.get("slug", "")
                if slug and slug not in companion_ids:
                    companion_ids.append(slug)

            for cond in action_def.get("conditional", []):
                cond_slug = cond.get("slug", "")
                cond_when = cond.get("when", "")
                if cond_slug and cond_when:
                    when_tokens = cond_when.lower().split()
                    if any(tok in msg_lower for tok in when_tokens if len(tok) > 3):
                        if cond_slug not in companion_ids:
                            companion_ids.append(cond_slug)

    division_anchors = policy.get("division_anchors", {})
    for div_name, div_def in division_anchors.items():
        anchor_keywords = div_def.get("keywords", [])
        if any(kw in msg_lower for kw in anchor_keywords):
            anchor = div_def.get("anchor", "")
            if anchor and anchor not in companion_ids:
                companion_ids.append(anchor)
            for cond_entry in div_def.get("conditional", []):
                if len(cond_entry) >= 2:
                    cond_slug, cond_kw = cond_entry[0], cond_entry[1]
                    if cond_kw in msg_lower and cond_slug not in companion_ids:
                        companion_ids.append(cond_slug)

    return matched_actions, companion_ids
