"""Companion policy — deterministic action→agent mapping."""

from __future__ import annotations

import logging
import os
import re
import stat
import threading
import time
from collections.abc import Collection
from functools import lru_cache
from pathlib import Path
from typing import Any

from agency_runtime.core.bounded_io import (
    FileSizeLimitError,
    UnsafeFileError,
    read_bounded_regular_file,
)
from agency_runtime.core.bounded_yaml import safe_load_bounded
from agency_runtime.core.configuration_contracts import ConfigurationError
from agency_runtime.core.configuration_persistence import assert_config_namespace
from agency_runtime.core.selector.intent_text import affirmative_intent
from agency_runtime.core.windows_acl import (
    current_process_user_sid,
    read_windows_sddl,
    windows_file_prevents_untrusted_mutation,
    windows_sddl_owner_matches_sid,
)

logger = logging.getLogger("agency_runtime.selector.policy")

_DEFAULT_POLICY_PATH = Path.home() / ".agency-runtime" / "companion_policy.yaml"
_BUNDLED_POLICY_PATH = Path(__file__).resolve().parents[1] / "companion_policy.yaml"
_BUNDLED_COMPANION_POLICY: dict[str, Any] | None = None
_MAX_CUSTOM_POLICY_BYTES = 1024 * 1024
_MAX_NO_MATCH_FALLBACKS = 2
_POLICY_LOCK = threading.RLock()


class PolicyIdentityError(ValueError):
    """A configured policy path is linked, special, or changed during read."""


def default_policy_path() -> Path:
    """Return the conventional user policy path without loading configuration."""

    return _DEFAULT_POLICY_PATH


def policy_path_for_config(config: Any) -> Path:
    """Resolve policy identity solely from an already materialized config."""

    configured = getattr(config, "companion_policy_path", None)
    if configured:
        return Path(os.path.expanduser(str(configured)))
    return default_policy_path()


def _read_bounded_policy(
    path: Path,
    *,
    maximum_bytes: int | None = None,
    trusted_custom: bool = False,
) -> Any:
    """Read and strictly parse a policy without unbounded custom-file reads."""
    limit = _MAX_CUSTOM_POLICY_BYTES if maximum_bytes is None else maximum_bytes
    if trusted_custom:
        payload = _read_trusted_custom_policy(path, limit=limit)
    else:
        payload = read_bounded_regular_file(
            path,
            limit=limit,
            label="companion policy",
        )
    return safe_load_bounded(payload)


def _platform_is_windows() -> bool:
    """Return the active filesystem security model through a patchable seam."""

    return os.name == "nt"


def _metadata_identity(
    metadata: Any,
    *,
    is_windows: bool | None = None,
) -> tuple[int, ...]:
    """Capture every stable field used to reject replacement and mutation."""

    windows = _platform_is_windows() if is_windows is None else is_windows
    return (
        int(metadata.st_dev),
        int(getattr(metadata, "st_ino", 0) or 0),
        int(metadata.st_mode),
        int(metadata.st_size),
        int(metadata.st_mtime_ns),
        # CPython's Windows path stat and descriptor stat can report different
        # creation-time precision for the same file. Device/inode plus the
        # remaining mutation fields and a fresh DACL probe provide the stable
        # Windows binding; POSIX ctime remains a valuable in-place-write guard.
        0 if windows else int(metadata.st_ctime_ns),
        int(getattr(metadata, "st_nlink", 0) or 0),
        int(getattr(metadata, "st_uid", -1)),
    )


def _metadata_is_link_or_reparse(metadata: Any) -> bool:
    attributes = int(getattr(metadata, "st_file_attributes", 0) or 0)
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return stat.S_ISLNK(metadata.st_mode) or bool(attributes & reparse_flag)


def _assert_trusted_policy_metadata(
    metadata: Any,
    *,
    is_windows: bool,
    effective_uid: int | None = None,
) -> None:
    """Require one immutable-by-other-accounts custom-policy file shape."""

    if _metadata_is_link_or_reparse(metadata) or not stat.S_ISREG(metadata.st_mode):
        raise PolicyIdentityError("companion policy must be a regular non-link file")
    if int(getattr(metadata, "st_ino", 0) or 0) <= 0:
        raise PolicyIdentityError("companion policy identity is unavailable")
    if int(getattr(metadata, "st_nlink", 0) or 0) != 1:
        raise PolicyIdentityError("companion policy must have exactly one hard link")
    if is_windows:
        return

    uid_getter = getattr(os, "geteuid", None)
    uid = int(uid_getter()) if effective_uid is None and callable(uid_getter) else effective_uid
    if uid is None or int(getattr(metadata, "st_uid", -1)) != int(uid):
        raise PolicyIdentityError("companion policy must be owned by the current user")
    mode = stat.S_IMODE(metadata.st_mode)
    if not mode & stat.S_IRUSR or mode & (stat.S_IWGRP | stat.S_IWOTH):
        raise PolicyIdentityError(
            "companion policy must be owner-readable and not group or other writable"
        )


def _windows_policy_file_is_trusted(path: Path) -> bool:
    """Require the exact current-user owner and one mutation-safe DACL snapshot.

    Executables may legitimately be OS-owned, so the shared DACL predicate
    accepts a narrow SYSTEM/Administrators/TrustedInstaller owner set. Custom
    user policy is different: its owner must exactly match the effective user.
    The shared predicate still supplies the restricted/logon-SID handling for
    the captured DACL; only its broader executable-owner allowance is narrowed.
    """

    try:
        sddl = read_windows_sddl(path)
        current_sid = str(current_process_user_sid(is_windows=True) or "")
    except Exception:
        return False
    owner = ""
    if sddl.startswith("O:"):
        remainder = sddl[2:]
        boundaries = [index for marker in ("G:", "D:") if (index := remainder.find(marker)) >= 0]
        owner = remainder[: min(boundaries) if boundaries else len(remainder)]
    owner_matches_current = bool(
        current_sid
        and owner
        and (
            owner == current_sid
            or windows_sddl_owner_matches_sid(sddl, current_sid, is_windows=True)
        )
    )
    if not owner_matches_current:
        return False
    return windows_file_prevents_untrusted_mutation(
        path,
        is_windows=True,
        sddl_reader=lambda _path: sddl,
        current_sid_reader=lambda: current_sid,
        owner_sid_matcher=lambda captured, expected: (
            captured == sddl and expected == current_sid and owner_matches_current
        ),
    )


def _read_trusted_custom_policy(path: Path, *, limit: int) -> bytes:
    """Read one custom policy through a stable, privacy-checked descriptor."""

    expected = _policy_file_identity(path)
    if expected is None:
        raise PolicyIdentityError("companion policy disappeared before read")
    flags = os.O_RDONLY | int(getattr(os, "O_BINARY", 0))
    flags |= int(getattr(os, "O_CLOEXEC", 0))
    flags |= int(getattr(os, "O_NOFOLLOW", 0))
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise PolicyIdentityError("companion policy could not be opened safely") from exc
    try:
        opened = os.fstat(descriptor)
        _assert_trusted_policy_metadata(opened, is_windows=_platform_is_windows())
        opened_identity = _metadata_identity(opened)
        if opened_identity != expected or _policy_file_identity(path) != opened_identity:
            raise PolicyIdentityError("companion policy changed during open")
        if opened.st_size > limit:
            raise FileSizeLimitError("companion policy exceeds the size limit")

        chunks: list[bytes] = []
        remaining = limit + 1
        while remaining:
            chunk = os.read(descriptor, min(remaining, 64 * 1024))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        payload = b"".join(chunks)
        if len(payload) > limit:
            raise FileSizeLimitError("companion policy exceeds the size limit")

        after = os.fstat(descriptor)
        _assert_trusted_policy_metadata(after, is_windows=_platform_is_windows())
        after_identity = _metadata_identity(after)
        if after_identity != opened_identity or _policy_file_identity(path) != after_identity:
            raise PolicyIdentityError("companion policy changed during read")
        return payload
    finally:
        os.close(descriptor)


def _resolve_policy_path() -> Path:
    """Resolve policy path from centralized config, env, or default."""
    from agency_runtime.core.config import load_config

    cfg = load_config()
    if cfg.companion_policy_path:
        return Path(os.path.expanduser(cfg.companion_policy_path))
    return _DEFAULT_POLICY_PATH


def _load_bundled_policy() -> dict[str, Any]:
    """Load the packaged broad-action companion policy."""
    global _BUNDLED_COMPANION_POLICY
    with _POLICY_LOCK:
        if _BUNDLED_COMPANION_POLICY is None:
            try:
                loaded = _read_bounded_policy(_BUNDLED_POLICY_PATH) or {}
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
_POLICY_FILE_IDENTITY: tuple[int, ...] | None = None
_POLICY_PATH: Path | None = None
_POLICY_REQUEST_KEY = ""
_POLICY_CHECKED_AT = 0.0
_POLICY_RECHECK_SECONDS = 1.0

# The bundled policy historically used a handful of intentionally truncated
# stems.  Keep those compatible, but constrain them to the start of a complete
# lexical token.  All other triggers are exact words or contiguous phrases.
_PREFIX_TRIGGERS = frozenset(
    {
        "orchestrat",
        "profil",
        "scalab",
        "tokeni",
        "vulnerab",
    }
)
_LEXEME_RE = re.compile(r"[a-z0-9]+(?:\+\+|#)?", re.IGNORECASE)
_CONDITION_STOPWORDS = frozenset(
    {
        "and",
        "are",
        "for",
        "from",
        "in",
        "into",
        "new",
        "of",
        "on",
        "or",
        "the",
        "to",
        "when",
        "with",
        "work",
        "needed",
        "involved",
    }
)


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
    use_prefix = normalized.endswith("*") or (len(words) == 1 and words[0] in _PREFIX_TRIGGERS)
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
        variants_by_word: list[set[str]] = []
        for word in words:
            variants = {word}
            if len(word) > 4 and word.endswith("ies"):
                variants.add(f"{word[:-3]}y")
            elif len(word) > 4 and word.endswith("s") and not word.endswith("ss"):
                variants.add(word[:-1])
            elif len(word) > 4:
                variants.add(f"{word}s")
            variants_by_word.append(variants)
        matched_words = sum(
            any(_matches(text, variant) for variant in variants if len(variant) >= 3)
            for variants in variants_by_word
        )
        # A single generic token from a multi-word condition is not evidence
        # for that specialist. For example, "test agent selection" must not
        # satisfy "test result analysis" and activate a results analyst. Exact
        # phrases still win above; otherwise require two independent terms.
        required_words = 1 if len(words) == 1 else 2
        if matched_words >= required_words:
            return True
    return False


def load_policy(policy_path: Path | None = None) -> dict[str, Any]:
    """Load one policy atomically so concurrent identities cannot cross-talk."""

    with _POLICY_LOCK:
        return _load_policy_locked(policy_path)


def _load_policy_locked(policy_path: Path | None = None) -> dict[str, Any]:
    """Load companion policy YAML while the module cache lock is held."""
    global _COMPANION_POLICY, _POLICY_FILE_IDENTITY, _POLICY_MTIME, _POLICY_PATH
    global _POLICY_REQUEST_KEY, _POLICY_CHECKED_AT

    requested = policy_path or _resolve_policy_path()
    path = Path(os.path.abspath(requested.expanduser()))
    identity = _policy_file_identity(path)
    request_key = str(path)
    now = time.monotonic()
    if identity is None:
        # No caller-controlled content exists to trust or read.  Keep probing
        # the no-follow file identity on every call so a policy created by
        # another process is visible immediately; only then is the namespace
        # ACL gate required before consuming it.
        _COMPANION_POLICY = None
        _POLICY_FILE_IDENTITY = None
        _POLICY_PATH = path
        _POLICY_MTIME = -1
        _POLICY_REQUEST_KEY = request_key
        _POLICY_CHECKED_AT = now
        logger.debug("companion policy not found at %s", path)
        return _load_bundled_policy()
    try:
        assert_config_namespace(path)
    except ConfigurationError as exc:
        raise PolicyIdentityError(
            "companion policy parent permits cross-account path substitution"
        ) from exc
    if (
        policy_path is None
        and request_key == _POLICY_REQUEST_KEY
        and path == _POLICY_PATH
        and identity == _POLICY_FILE_IDENTITY
        and now - _POLICY_CHECKED_AT < _POLICY_RECHECK_SECONDS
    ):
        return _COMPANION_POLICY or _load_bundled_policy()
    mtime = identity[4]

    if (
        _COMPANION_POLICY is None
        or path != _POLICY_PATH
        or mtime != _POLICY_MTIME
        or identity != _POLICY_FILE_IDENTITY
    ):
        try:
            loaded = (
                _read_bounded_policy(
                    path,
                    maximum_bytes=_MAX_CUSTOM_POLICY_BYTES,
                    trusted_custom=True,
                )
                or {}
            )
            confirmed_identity = _policy_file_identity(path)
            if confirmed_identity != identity:
                raise PolicyIdentityError("companion policy changed during load")
            _COMPANION_POLICY = loaded if isinstance(loaded, dict) else {}
            _POLICY_FILE_IDENTITY = identity
            _POLICY_MTIME = mtime
            _POLICY_PATH = path
            _POLICY_REQUEST_KEY = request_key
            _POLICY_CHECKED_AT = now
            actions = _COMPANION_POLICY.get("actions", {})
            logger.info("companion policy loaded (%d actions)", len(actions))
        except UnsafeFileError as exc:
            raise PolicyIdentityError("companion policy must be a regular non-link file") from exc
        except PolicyIdentityError:
            raise
        except Exception as exc:
            logger.warning("could not load companion policy: %s", exc)
            if path != _POLICY_PATH:
                _COMPANION_POLICY = None
                _POLICY_FILE_IDENTITY = None
                _POLICY_PATH = path
                _POLICY_MTIME = -1
                _POLICY_REQUEST_KEY = request_key
                _POLICY_CHECKED_AT = now
                return _load_bundled_policy()
    else:
        _POLICY_REQUEST_KEY = request_key
        _POLICY_CHECKED_AT = now
    return _COMPANION_POLICY or _load_bundled_policy()


def _policy_file_identity(path: Path) -> tuple[int, ...] | None:
    """Return one privacy-checked no-follow identity for a custom policy."""

    candidates = (*reversed(path.parents), path)
    for index, candidate in enumerate(candidates):  # pragma: no branch
        try:
            metadata = os.lstat(candidate)
        except FileNotFoundError:
            return None
        except OSError as exc:
            raise PolicyIdentityError("companion policy identity is unavailable") from exc
        if _metadata_is_link_or_reparse(metadata):
            raise PolicyIdentityError(
                "companion policy path must not contain a symlink or reparse point"
            )
        if index < len(candidates) - 1:
            if not stat.S_ISDIR(metadata.st_mode):
                raise PolicyIdentityError("companion policy parent must be a directory")
            continue
        is_windows = _platform_is_windows()
        _assert_trusted_policy_metadata(metadata, is_windows=is_windows)
        identity = _metadata_identity(metadata)
        if is_windows and not _windows_policy_file_is_trusted(path):
            raise PolicyIdentityError(
                "companion policy owner or Windows DACL permits untrusted mutation"
            )
        try:
            confirmed = os.lstat(path)
        except OSError as exc:
            raise PolicyIdentityError(
                "companion policy changed during security validation"
            ) from exc
        _assert_trusted_policy_metadata(confirmed, is_windows=is_windows)
        if _metadata_identity(confirmed) != identity:
            raise PolicyIdentityError("companion policy changed during security validation")
        return identity


def _append_action_routes(
    actions: dict[Any, Any],
    routes: list[dict[str, str]],
    errors: list[str],
) -> None:
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


def _division_condition(
    entry: Any,
    *,
    path: str,
    errors: list[str],
) -> tuple[Any, Any] | None:
    if isinstance(entry, dict):
        return entry.get("slug"), entry.get("when")
    if isinstance(entry, (list, tuple)) and len(entry) >= 2:
        return entry[0], entry[1]
    errors.append(f"{path} must contain a slug and condition")
    return None


def _append_division_routes(
    divisions: dict[Any, Any],
    routes: list[dict[str, str]],
    errors: list[str],
) -> None:
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
            values = _division_condition(entry, path=path, errors=errors)
            if values is None:
                continue
            slug, condition = values
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
    _append_action_routes(actions, routes, errors)
    divisions = policy.get("division_anchors", {})
    if not isinstance(divisions, dict):
        errors.append("division_anchors must be a mapping")
        divisions = {}
    _append_division_routes(divisions, routes, errors)
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
                    "specialist_availability.roster_gated.reason must be a non-empty string"
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
            "availability slugs cannot be both enabled and roster-gated: " + ", ".join(overlap)
        )
    undeclared = sorted(referenced - enabled - gated)
    if undeclared:
        errors.append("policy routes have no availability declaration: " + ", ".join(undeclared))
    unreferenced = sorted((enabled | gated) - referenced)
    if unreferenced:
        errors.append("availability declares unreferenced specialists: " + ", ".join(unreferenced))

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


def _eligible_companions(
    policy: dict[str, Any],
    active_slugs: Collection[str] | None,
) -> set[str] | None:
    if active_slugs is not None:
        availability = validate_policy(policy, active_slugs)
        return set(availability["enabled_slugs"])
    declared_availability = policy.get("specialist_availability")
    if not isinstance(declared_availability, dict):
        return None
    declared = declared_availability.get("enabled", [])
    return {item.strip() for item in declared if isinstance(item, str) and item.strip()}


def _append_eligible_companion(
    companion_ids: list[str],
    slug: Any,
    eligible: set[str] | None,
) -> None:
    if not isinstance(slug, str) or not slug:
        return
    if eligible is not None and slug not in eligible:
        return
    if slug not in companion_ids:
        companion_ids.append(slug)


def _append_action_companions(
    message: str,
    actions: dict[Any, Any],
    eligible: set[str] | None,
    companion_ids: list[str],
) -> list[str]:
    matched_actions: list[str] = []
    for action_name, action_def in actions.items():
        triggers = action_def.get("triggers", [])
        if not triggers:
            continue
        if action_name == "DEFAULT":
            # DEFAULT is a post-selection fallback, not an ordinary action.
            # Applying it here would make its agents accompany every request.
            continue
        if not any(_matches(message, trigger) for trigger in triggers):
            continue
        matched_actions.append(action_name)
        for companion in action_def.get("always_include", []):
            _append_eligible_companion(companion_ids, companion.get("slug", ""), eligible)
        for condition in action_def.get("conditional", []):
            slug = condition.get("slug", "")
            when = condition.get("when", "")
            if slug and when and _matches_condition(message, when):
                _append_eligible_companion(companion_ids, slug, eligible)
    return matched_actions


def detect_fallback_companions(
    policy: dict[str, Any] | None = None,
    *,
    active_slugs: Collection[str] | None = None,
) -> list[str]:
    """Return at most two eligible DEFAULT companions in policy order.

    DEFAULT is intentionally resolved separately from action matching so the
    selector can prove that semantic and deterministic policy routing both
    produced no active selection before applying it.
    """
    policy = policy if policy is not None else load_policy()
    actions = policy.get("actions", {}) if isinstance(policy, dict) else {}
    default = actions.get("DEFAULT", {}) if isinstance(actions, dict) else {}
    entries = default.get("always_include", []) if isinstance(default, dict) else []
    if not isinstance(entries, list):
        return []

    eligible = _eligible_companions(policy, active_slugs)
    companions: list[str] = []
    for entry in entries:
        if len(companions) >= _MAX_NO_MATCH_FALLBACKS:
            break
        if not isinstance(entry, dict):
            continue
        _append_eligible_companion(companions, entry.get("slug", ""), eligible)
    return companions


def _division_companion_values(entry: Any) -> tuple[Any, Any] | None:
    if isinstance(entry, dict):
        return entry.get("slug", ""), entry.get("when", "")
    if isinstance(entry, (list, tuple)) and len(entry) >= 2:
        return entry[0], entry[1]
    return None


def _append_division_companions(
    message: str,
    divisions: dict[Any, Any],
    eligible: set[str] | None,
    companion_ids: list[str],
) -> None:
    for division in divisions.values():
        keywords = division.get("keywords", [])
        if not any(_matches(message, keyword) for keyword in keywords):
            continue
        _append_eligible_companion(companion_ids, division.get("anchor", ""), eligible)
        for entry in division.get("conditional", []):
            values = _division_companion_values(entry)
            if values is None:
                continue
            slug, condition = values
            if _matches(message, condition):
                _append_eligible_companion(companion_ids, slug, eligible)


def detect_actions(
    message: str,
    policy: dict[str, Any] | None = None,
    *,
    active_slugs: Collection[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Detect which actions match the user message.

    Returns (action_names, companion_ids) where companion_ids is the union
    of companions from matched actions and division anchors. DEFAULT companions
    are resolved separately by :func:`detect_fallback_companions`.
    """
    policy = policy if policy is not None else load_policy()
    if not policy:
        return [], []

    actions_def = policy.get("actions", {})
    if not actions_def:
        return [], []

    affirmative_message = affirmative_intent(message)
    companion_ids: list[str] = []
    eligible = _eligible_companions(policy, active_slugs)
    matched_actions = _append_action_companions(
        affirmative_message,
        actions_def,
        eligible,
        companion_ids,
    )
    _append_division_companions(
        affirmative_message,
        policy.get("division_anchors", {}),
        eligible,
        companion_ids,
    )
    fallback_ids = set(
        detect_fallback_companions(
            policy,
            active_slugs=active_slugs,
        )
    )
    return matched_actions, [slug for slug in companion_ids if slug not in fallback_ids]
