"""Install the bounded Agency delegation request in Codex global guidance."""

from __future__ import annotations

import hashlib
import os
import stat
from pathlib import Path
from typing import Any

from agency_runtime.core.bounded_io import atomic_write_text, read_bounded_regular_file
from agency_runtime.core.filesystem_trust import metadata_is_link_or_reparse_point

CODEX_GUIDANCE_BEGIN = "<!-- agency-runtime:codex-delegation:begin -->"
CODEX_GUIDANCE_END = "<!-- agency-runtime:codex-delegation:end -->"

_SCHEMA_VERSION = "agency.codex-global-guidance.v1"
_MAX_GLOBAL_AGENTS_BYTES = 32 * 1024


class CodexGlobalGuidanceError(RuntimeError):
    """Codex global guidance could not be changed without crossing its boundary."""


def render_codex_global_guidance() -> str:
    """Return the one canonical, inference-bound Codex delegation request."""

    return (
        f"{CODEX_GUIDANCE_BEGIN}\n"
        "# Agency Runtime native delegation\n\n"
        "This block applies only when the current turn contains `[AGENCY DELEGATION PLAN]`. "
        "This installed "
        "owner configuration explicitly requests Codex native subagent delegation. "
        "Treat the accepted persisted rows in that current-turn plan as the complete "
        "staffing decision.\n\n"
        "Inference remains the only staffing authority. This instruction does not choose, "
        "name, or replace any specialist. For every accepted persisted plan row exactly "
        "once, use Codex's native collaboration tools with that row's exact task name and "
        "goal. The selected specialist executes that exact goal in its initial spawn turn. "
        "Wait for that exact child to become terminal before starting another row. Respect "
        "dependency order and required waits. Do not send a follow-up execution message, "
        "merge, omit, "
        "broaden, decline, duplicate, or retry an accepted "
        "row. The parent must not perform the specialist work or substitute a generalist; "
        "it only schedules, waits, and consolidates recorded outcomes.\n\n"
        "When no current-turn Agency delegation plan exists, this block requests no "
        "delegation and does not alter ordinary Codex behavior.\n"
        f"{CODEX_GUIDANCE_END}\n"
    )


def _real_codex_home(codex_home: Path) -> Path:
    candidate = Path(os.path.abspath(codex_home.expanduser()))
    try:
        metadata = os.lstat(candidate)
    except OSError as exc:
        raise CodexGlobalGuidanceError("Codex home is unavailable") from exc
    if metadata_is_link_or_reparse_point(metadata) or not stat.S_ISDIR(metadata.st_mode):
        raise CodexGlobalGuidanceError("Codex home must be a real directory")
    return candidate


def _ensure_real_codex_home(codex_home: Path) -> tuple[Path, bool]:
    candidate = Path(os.path.abspath(codex_home.expanduser()))
    try:
        return _real_codex_home(candidate), False
    except CodexGlobalGuidanceError:
        try:
            os.lstat(candidate)
        except FileNotFoundError:
            pass
        except OSError:
            raise
        else:
            raise

    parent = candidate.parent
    try:
        parent_metadata = os.lstat(parent)
    except OSError as exc:
        raise CodexGlobalGuidanceError("Codex home parent is unavailable") from exc
    if metadata_is_link_or_reparse_point(parent_metadata) or not stat.S_ISDIR(
        parent_metadata.st_mode
    ):
        raise CodexGlobalGuidanceError("Codex home parent must be a real directory")
    try:
        os.mkdir(candidate, mode=0o700)
        created = True
    except FileExistsError:
        created = False
    except OSError as exc:
        raise CodexGlobalGuidanceError("Codex home could not be created safely") from exc
    return _real_codex_home(candidate), created


def _read_document(path: Path) -> str | None:
    try:
        payload = read_bounded_regular_file(
            path,
            limit=_MAX_GLOBAL_AGENTS_BYTES,
            label="Codex global guidance",
        )
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise CodexGlobalGuidanceError("Codex global guidance is not safely readable") from exc
    try:
        return payload.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise CodexGlobalGuidanceError("Codex global guidance must be UTF-8") from exc


def _managed_span(document: str) -> tuple[int, int] | None:
    begin_count = document.count(CODEX_GUIDANCE_BEGIN)
    end_count = document.count(CODEX_GUIDANCE_END)
    if begin_count == end_count == 0:
        return None
    if begin_count != 1 or end_count != 1:
        raise CodexGlobalGuidanceError("Codex global guidance has a malformed managed boundary")
    begin = document.index(CODEX_GUIDANCE_BEGIN)
    end = document.index(CODEX_GUIDANCE_END)
    if end < begin:
        raise CodexGlobalGuidanceError("Codex global guidance has a malformed managed boundary")
    stop = end + len(CODEX_GUIDANCE_END)
    if document[stop : stop + 2] == "\r\n":
        stop += 2
    elif document[stop : stop + 1] == "\n":
        stop += 1
    return begin, stop


def _bounded_document(document: str) -> bytes:
    payload = document.encode("utf-8")
    if len(payload) > _MAX_GLOBAL_AGENTS_BYTES:
        raise CodexGlobalGuidanceError("Codex global guidance would exceed the size limit")
    return payload


def _write_verified(path: Path, document: str) -> str:
    expected = _bounded_document(document)
    try:
        atomic_write_text(path, document)
        observed = read_bounded_regular_file(
            path,
            limit=_MAX_GLOBAL_AGENTS_BYTES,
            label="Codex global guidance",
        )
    except OSError as exc:
        raise CodexGlobalGuidanceError("Codex global guidance could not be written safely") from exc
    if observed != expected:
        raise CodexGlobalGuidanceError("Codex global guidance verification failed")
    return hashlib.sha256(observed).hexdigest()


def _active_document(codex_home: Path) -> tuple[Path, str]:
    override = codex_home / "AGENTS.override.md"
    override_document = _read_document(override)
    if override_document:
        return override, override_document
    base = codex_home / "AGENTS.md"
    return base, _read_document(base) or ""


def install_codex_global_guidance(codex_home: Path) -> dict[str, Any]:
    """Idempotently install the managed block in Codex's active global file."""

    root, root_created = _ensure_real_codex_home(codex_home)
    path, before = _active_document(root)
    span = _managed_span(before)
    rendered = render_codex_global_guidance()
    after = before + rendered if span is None else before[: span[0]] + rendered + before[span[1] :]
    _bounded_document(after)
    changed = after != before
    digest = (
        _write_verified(path, after)
        if changed
        else hashlib.sha256(after.encode("utf-8")).hexdigest()
    )
    return {
        "schema_version": _SCHEMA_VERSION,
        "status": "installed",
        "path": str(path.resolve(strict=True)),
        "changed": changed,
        "root_created": root_created,
        "document_sha256": digest,
    }


def plan_codex_global_guidance(codex_home: Path) -> dict[str, Any]:
    """Return the content-free guidance mutation plan without writing."""

    candidate = Path(os.path.abspath(codex_home.expanduser()))
    try:
        root = _real_codex_home(candidate)
    except CodexGlobalGuidanceError:
        try:
            os.lstat(candidate)
        except FileNotFoundError:
            pass
        except OSError:
            raise
        else:
            raise
        path = candidate / "AGENTS.md"
        before = ""
        root_exists = False
    else:
        path, before = _active_document(root)
        root_exists = True
    span = _managed_span(before)
    rendered = render_codex_global_guidance()
    after = before + rendered if span is None else before[: span[0]] + rendered + before[span[1] :]
    digest = hashlib.sha256(_bounded_document(after)).hexdigest()
    return {
        "schema_version": _SCHEMA_VERSION,
        "status": "planned",
        "path": str(path),
        "changed": after != before,
        "root_exists": root_exists,
        "document_sha256": digest,
    }


def remove_codex_global_guidance(codex_home: Path) -> dict[str, Any]:
    """Remove only Agency's managed block while preserving all owner content."""

    candidate = Path(os.path.abspath(codex_home.expanduser()))
    try:
        root = _real_codex_home(candidate)
    except CodexGlobalGuidanceError:
        try:
            os.lstat(candidate)
        except FileNotFoundError:
            return {
                "schema_version": _SCHEMA_VERSION,
                "status": "absent",
                "changed": False,
                "paths": [],
                "document_sha256": {},
            }
        except OSError:
            raise
        raise
    plans: list[tuple[Path, str, str]] = []
    for path in (root / "AGENTS.override.md", root / "AGENTS.md"):
        before = _read_document(path)
        if before is None:
            continue
        span = _managed_span(before)
        if span is None:
            continue
        after = before[: span[0]] + before[span[1] :]
        _bounded_document(after)
        plans.append((path, before, after))

    changed_paths: list[str] = []
    digests: dict[str, str] = {}
    for path, _before, after in plans:
        digest = _write_verified(path, after)
        resolved = str(path.resolve(strict=True))
        changed_paths.append(resolved)
        digests[resolved] = digest
    return {
        "schema_version": _SCHEMA_VERSION,
        "status": "removed" if changed_paths else "absent",
        "changed": bool(changed_paths),
        "paths": changed_paths,
        "document_sha256": digests,
    }


__all__ = [
    "CODEX_GUIDANCE_BEGIN",
    "CODEX_GUIDANCE_END",
    "CodexGlobalGuidanceError",
    "install_codex_global_guidance",
    "plan_codex_global_guidance",
    "remove_codex_global_guidance",
    "render_codex_global_guidance",
]
