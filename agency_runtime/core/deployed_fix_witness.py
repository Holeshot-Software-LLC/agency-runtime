"""Attest that what each host runs carries the fixes main claims to ship (AR-363).

Version stamps prove what was installed, not that each documented fix's
load-bearing code is present in what runs.  Measured 2026-09-01: a live
session ran launcher projection ``e5e2e193`` while the last install had
published ``8698cca9`` -- stale hooks executing pre-fix code, noticed only
because a SessionStart notice happened to say so.

This module keeps a registry of documented fixes, each pinned to one file
and one load-bearing literal, and attests a host by reading those files out
of the projection the host is wired to.  The result is written as one
per-host witness manifest plus an append-only history, so drift can be
bisected to the attestation that introduced it.

Two projections identify a host.  The one the last install *published* is
the advisory per-host pointer (see ``runtime_staleness``).  The one the host
actually *invokes* comes from ``host_wiring``, and only Claude's wiring is
measured today: every other host is attested against its published pointer
and the manifest says so (``wired_source``) instead of implying a
measurement that was never taken.  The stale-hook shape -- wired digest
differing from published digest -- is therefore only provable where the
wiring is measured, and the manifest never hides that limitation.

Everything here is a bounded read of owner-private state.  The pointer is
advisory and the projection is content-addressed, so a tampered witness
input can at worst produce a wrong report; it can never redirect a hook.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from agency_runtime.core.bounded_io import atomic_write_text, read_bounded_regular_file
from agency_runtime.core.bounded_json import safe_load_bounded_json
from agency_runtime.core.configuration import restrict_private_file
from agency_runtime.core.filesystem_trust import metadata_is_link_or_reparse_point
from agency_runtime.core.host_wiring_drift import HostWiring, host_wiring
from agency_runtime.core.launcher_bootstrap import plan_private_package_runtime
from agency_runtime.core.private_paths import (
    private_runtime_directory,
    validate_private_directory,
)
from agency_runtime.core.runtime_staleness import installed_runtime_pointer

WITNESS_SCHEMA = "agency.deployed-fix-witness.v1"
WITNESS_STATUSES = frozenset({"attested", "drift", "missing_fix", "unavailable"})
# The two verdicts that fail a host: the code it runs is provably not the
# code that was published, or it provably lacks a documented fix.
WITNESS_FAILURE_STATUSES = frozenset({"drift", "missing_fix"})
WIRED_SOURCE_HOST_WIRING = "host-wiring"
WIRED_SOURCE_INSTALLED_POINTER = "installed-pointer"
MAX_WITNESS_HISTORY_ENTRIES = 1000

_WITNESS_DIRECTORY = "witness"
_LAUNCHERS_DIRECTORY = "launchers"
# Every launcher projection directory is named by its manifest digest; the
# prefix mirrors ``launcher_bootstrap`` without importing its private name.
_RUNTIME_DIRECTORY_PREFIX = "runtime-sha256-"
_MAX_FIX_FILE_BYTES = 4 * 1024 * 1024
_MAX_HISTORY_BYTES = 1024 * 1024
_MAX_HISTORY_LINE_BYTES = 8 * 1024
_HOST_PATTERN = re.compile(r"[a-z0-9][a-z0-9-]{0,31}")
_PRESENT = "present"
_NOT_CHECKED = "not_checked"


@dataclass(frozen=True, slots=True)
class DocumentedFix:
    """One documented fix pinned to a load-bearing literal in one file.

    ``relative_path`` is site-packages relative, exactly as the projection's
    ``runtime-manifest.json`` names it.  ``marker`` is the literal whose
    absence means the fix is not in the code that runs -- a regex name, a
    function definition, a reason string -- never a comment or docstring.
    """

    fix_id: str
    issue: str
    relative_path: str
    marker: str
    summary: str = ""


# Seeded with fixes whose markers exist on main today; a unit test asserts
# every marker against the working tree so the registry cannot rot.
FIX_REGISTRY: tuple[DocumentedFix, ...] = (
    DocumentedFix(
        fix_id="AR-345",
        issue="AR-345",
        relative_path="agency_runtime/core/workforce/plan_policy.py",
        marker="_VERIFICATION_CLAUSE_BOUNDARY",
        summary="planner verification-clause boundary matcher",
    ),
    DocumentedFix(
        fix_id="AR-346",
        issue="AR-346",
        relative_path="agency_runtime/core/rule8_evidence.py",
        marker="FAIL_OPEN_RUN_STATUSES",
        summary="shared fail-open run-status set",
    ),
    DocumentedFix(
        fix_id="AR-355",
        issue="AR-355",
        relative_path="agency_runtime/core/resident_managers.py",
        marker="A governed workforce of specialists exists",
        summary="kernel v5 resident-manager line",
    ),
    DocumentedFix(
        fix_id="AR-365",
        issue="AR-365",
        relative_path="agency_runtime/core/store/evidence.py",
        marker="def get_latest_run_for_session",
        summary="session-latest run fallback for the fail-open gate",
    ),
    DocumentedFix(
        fix_id="AR-366-gate",
        issue="AR-366",
        relative_path="agency_runtime/core/rule8_evidence.py",
        marker="turn_never_received_staffing_contract",
        summary="staffing-contract fail-open gate",
    ),
    DocumentedFix(
        fix_id="AR-366-stop-hook",
        issue="AR-366",
        relative_path="agency_runtime/adapters/hooks.py",
        marker="turn_closed_fail_open",
        summary="Stop-path fail-open pass-through",
    ),
)


@dataclass(frozen=True, slots=True)
class FixWitness:
    """One registered fix's verified presence in the invoked projection."""

    fix: DocumentedFix
    state: str
    file_sha256: str = ""

    @property
    def present(self) -> bool:
        return self.state == _PRESENT

    @property
    def checked(self) -> bool:
        return self.state != _NOT_CHECKED

    def as_dict(self) -> dict[str, Any]:
        return {
            "fix_id": self.fix.fix_id,
            "issue": self.fix.issue,
            "summary": self.fix.summary,
            "relative_path": self.fix.relative_path,
            "marker": self.fix.marker,
            "present": self.present,
            "state": self.state,
            "file_sha256": self.file_sha256,
        }


@dataclass(frozen=True, slots=True)
class HostWitness:
    """One host's attestation against the documented-fix registry."""

    host: str
    attested_at: str
    status: str
    reason_code: str
    published_digest: str
    wired_digest: str
    wired_source: str
    wiring_status: str
    wiring_reason_code: str
    staged_projection: str
    source_digest: str
    source_state: str
    projection_state: str
    projection_root: str
    fixes: tuple[FixWitness, ...]
    recorded: bool = False
    record_error: str = ""

    @property
    def drift(self) -> bool:
        """Whether the host provably invokes a projection other than the published one."""

        return bool(
            self.published_digest
            and self.wired_digest
            and self.published_digest != self.wired_digest
        )

    @property
    def source_drift(self) -> bool | None:
        """Whether the source package would stage something else; None when unknown."""

        if self.source_state != "planned" or not self.wired_digest:
            return None
        return self.source_digest != self.wired_digest

    @property
    def missing_fixes(self) -> tuple[str, ...]:
        return tuple(item.fix.fix_id for item in self.fixes if item.checked and not item.present)

    @property
    def reason(self) -> str:
        """One short human explanation, empty when the host is attested."""

        remedy = f"`agency install --agent {self.host}`"
        explanations = {
            "attested": "",
            "published_projection_mismatch": (
                "the host invokes a different projection than the last install "
                f"published; its hooks run stale code until {remedy}"
            ),
            "source_projection_mismatch": (
                "the source package would stage a different projection than the host "
                f"invokes; hooks keep running the older code until {remedy}"
            ),
            "fix_marker_absent": "the invoked projection lacks a registered fix marker",
            "no_installed_pointer": "no install has recorded a projection for this host",
            "projection_missing": "the recorded projection directory is absent",
            "projection_untrusted": "the recorded projection directory is not owner-private",
        }
        return explanations.get(self.reason_code, "")

    def history_entry(self) -> dict[str, Any]:
        """Return the compact per-attestation line the history keeps."""

        return {
            "attested_at": self.attested_at,
            "status": self.status,
            "reason_code": self.reason_code,
            "published_digest": self.published_digest,
            "wired_digest": self.wired_digest,
            "wired_source": self.wired_source,
            "source_digest": self.source_digest,
            "fixes": {item.fix.fix_id: item.present for item in self.fixes},
        }

    def as_dict(self) -> dict[str, Any]:
        """Return the manifest document, shared by the file, CLI and battery."""

        return {
            "schema": WITNESS_SCHEMA,
            "host": self.host,
            "attested_at": self.attested_at,
            "status": self.status,
            "reason_code": self.reason_code,
            "reason": self.reason,
            "published_digest": self.published_digest,
            "wired_digest": self.wired_digest,
            "wired_source": self.wired_source,
            "drift": self.drift,
            "source_drift": self.source_drift,
            "wiring_status": self.wiring_status,
            "wiring_reason_code": self.wiring_reason_code,
            "staged_projection": self.staged_projection,
            "source_digest": self.source_digest,
            "source_state": self.source_state,
            "projection_state": self.projection_state,
            "projection_root": self.projection_root,
            "fixes": [item.as_dict() for item in self.fixes],
            "missing_fixes": list(self.missing_fixes),
            "registry_size": len(self.fixes),
            "recorded": self.recorded,
            "record_error": self.record_error,
        }


def _validated_host(value: object) -> str:
    text = str(value or "").strip().casefold()
    if _HOST_PATTERN.fullmatch(text) is None:
        raise ValueError("deployed-fix witness requires a valid host name")
    return text


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _witness_paths(host: str) -> tuple[Path, Path]:
    """Return the manifest and history paths; ``host`` is already validated."""

    directory = private_runtime_directory(_WITNESS_DIRECTORY)
    return directory / f"{host}.json", directory / f"{host}.history.jsonl"


def _measured_wiring(
    host: str,
    *,
    agency_home: Path | None,
    claude_home: Path | None,
) -> HostWiring:
    """Read the host's wiring; a failed read is reported, never raised."""

    kwargs: dict[str, Path] = {}
    if agency_home is not None:
        kwargs["agency_home"] = Path(agency_home)
    if claude_home is not None:
        kwargs["claude_home"] = Path(claude_home)
    try:
        return host_wiring(host, **kwargs)
    except (OSError, ValueError):
        return HostWiring(
            host=host,
            measurement_status="measured",
            staged_state="unreadable",
            staged_projection="",
            staged_path="",
            wired_state="unreadable",
            wired_projection="",
            wired_path="",
        )


def _wired_identity(wiring: HostWiring, published: str) -> tuple[str, str]:
    """Return the digest the host invokes and where that knowledge came from.

    A measured wiring file is the only evidence of what runs.  Without one
    the published pointer stands in, and the returned source says so: a
    pointer cannot show the stale-hook shape, because it *is* the published
    side of that comparison.
    """

    if wiring.measurement_status == "measured" and wiring.wired_projection:
        return wiring.wired_projection, WIRED_SOURCE_HOST_WIRING
    return published, WIRED_SOURCE_INSTALLED_POINTER


def _source_identity(source_package: str | Path | None) -> tuple[str, str]:
    """Return the digest the source package would stage, if one was asked for.

    Planning hashes the whole distribution closure, so it only runs on
    request.  A digest from another environment never agrees with this one
    (see ``runtime_staleness``), which is why the caller opts in explicitly.
    """

    if source_package is None:
        return "", "not_requested"
    source = Path(source_package)
    if source.is_dir():
        source = source / "_bootstrap.py"
    try:
        return plan_private_package_runtime(source).manifest_sha256, "planned"
    except (OSError, ValueError):
        return "", "unplannable"


def _projection_root(digest: str) -> tuple[Path | None, str]:
    """Return the trusted projection directory for ``digest`` and its state."""

    if not digest:
        return None, "no_digest"
    candidate = private_runtime_directory(_LAUNCHERS_DIRECTORY) / (
        f"{_RUNTIME_DIRECTORY_PREFIX}{digest}"
    )
    try:
        metadata = os.lstat(candidate)
    except FileNotFoundError:
        return None, "missing"
    except OSError:
        return None, "untrusted"
    if metadata_is_link_or_reparse_point(metadata) or not stat.S_ISDIR(metadata.st_mode):
        return None, "untrusted"
    try:
        return validate_private_directory(candidate), "observed"
    except (OSError, ValueError):
        return None, "untrusted"


def _verify_fixes(root: Path | None) -> tuple[FixWitness, ...]:
    """Verify every registered marker inside one projection with bounded reads."""

    if root is None:
        return tuple(FixWitness(fix, _NOT_CHECKED) for fix in FIX_REGISTRY)
    site_packages = root / "site-packages"
    payloads: dict[str, bytes | str] = {}
    results: list[FixWitness] = []
    for fix in FIX_REGISTRY:
        payload = payloads.get(fix.relative_path)
        if payload is None:
            payload = _fix_file_payload(site_packages, fix.relative_path)
            payloads[fix.relative_path] = payload
        if isinstance(payload, str):
            results.append(FixWitness(fix, payload))
            continue
        state = _PRESENT if fix.marker.encode("utf-8") in payload else "absent"
        results.append(FixWitness(fix, state, hashlib.sha256(payload).hexdigest()))
    return tuple(results)


def _fix_file_payload(site_packages: Path, relative_path: str) -> bytes | str:
    """Read one registered file, or return the state naming why it could not be."""

    path = site_packages / Path(*PurePosixPath(relative_path).parts)
    try:
        return read_bounded_regular_file(
            path,
            limit=_MAX_FIX_FILE_BYTES,
            label=f"deployed fix file {relative_path}",
        )
    except FileNotFoundError:
        return "missing_file"
    except (OSError, ValueError):
        return "unreadable"


def _classify(
    *,
    published: str,
    wired: str,
    source_digest: str,
    source_state: str,
    projection_state: str,
    fixes: tuple[FixWitness, ...],
) -> tuple[str, str]:
    """Return ``(status, reason_code)`` with drift ranked above availability.

    A wired digest that differs from the published one is the headline even
    when the projection it names has since been removed: the host provably
    invokes something other than what was published, and that is the
    2026-09-01 shape this module exists to catch.
    """

    if not wired:
        return "unavailable", "no_installed_pointer"
    if published and wired != published:
        return "drift", "published_projection_mismatch"
    if projection_state == "missing":
        return "unavailable", "projection_missing"
    if projection_state != "observed":
        return "unavailable", "projection_untrusted"
    if source_state == "planned" and source_digest != wired:
        return "drift", "source_projection_mismatch"
    if any(not item.present for item in fixes):
        return "missing_fix", "fix_marker_absent"
    return "attested", "attested"


def attest_host(
    host: str,
    *,
    agency_home: str | Path | None = None,
    claude_home: str | Path | None = None,
    source_package: str | Path | None = None,
    record: bool = True,
) -> HostWitness:
    """Attest one host's invoked projection against the fix registry.

    ``agency_home`` and ``claude_home`` override the wiring measurement's
    roots exactly as ``claude_host_wiring`` accepts them.  ``source_package``
    is the package (or its ``_bootstrap.py``) whose planned projection should
    also match; it is optional because planning hashes the whole closure.
    With ``record`` the manifest is replaced and one history line appended;
    a recording failure is reported on the witness rather than raised, so an
    attestation is never lost to the bookkeeping around it.
    """

    normalized = _validated_host(host)
    published, _pointer_host = installed_runtime_pointer(normalized)
    wiring = _measured_wiring(
        normalized,
        agency_home=Path(agency_home) if agency_home is not None else None,
        claude_home=Path(claude_home) if claude_home is not None else None,
    )
    wired, wired_source = _wired_identity(wiring, published)
    source_digest, source_state = _source_identity(source_package)
    root, projection_state = _projection_root(wired)
    fixes = _verify_fixes(root)
    status, reason_code = _classify(
        published=published,
        wired=wired,
        source_digest=source_digest,
        source_state=source_state,
        projection_state=projection_state,
        fixes=fixes,
    )
    witness = HostWitness(
        host=normalized,
        attested_at=_now(),
        status=status,
        reason_code=reason_code,
        published_digest=published,
        wired_digest=wired,
        wired_source=wired_source,
        wiring_status=wiring.status,
        wiring_reason_code=wiring.reason_code,
        staged_projection=wiring.staged_projection,
        source_digest=source_digest,
        source_state=source_state,
        projection_state=projection_state,
        projection_root=str(root) if root is not None else "",
        fixes=fixes,
    )
    return _record(witness) if record else witness


def _record(witness: HostWitness) -> HostWitness:
    """Replace the manifest atomically and append one history line."""

    try:
        manifest_path, history_path = _witness_paths(witness.host)
        atomic_write_text(
            manifest_path,
            json.dumps(witness.as_dict(), indent=1, sort_keys=True) + "\n",
        )
        restrict_private_file(manifest_path)
        _append_history(history_path, witness)
    except (OSError, ValueError) as error:
        return replace(witness, recorded=False, record_error=type(error).__name__)
    return replace(witness, recorded=True)


def _rotate_full_history(path: Path) -> None:
    """Keep the newest window readable by rotating a full log aside once.

    Bisecting needs the most recent attestations, so a cap that refused new
    lines would discard exactly the evidence that matters; one rotated
    predecessor is kept and an older one is replaced.
    """

    try:
        size = os.lstat(path).st_size
    except FileNotFoundError:
        return
    if size < _MAX_HISTORY_BYTES:
        return
    os.replace(path, path.with_name(path.name.replace(".history.jsonl", ".history.1.jsonl")))


def _append_history(path: Path, witness: HostWitness) -> None:
    line = (
        json.dumps(
            witness.history_entry(),
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )
    _rotate_full_history(path)
    flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND
    flags |= int(getattr(os, "O_NOFOLLOW", 0)) | int(getattr(os, "O_BINARY", 0))
    descriptor = os.open(path, flags, stat.S_IRUSR | stat.S_IWUSR)
    try:
        opened = os.fstat(descriptor)
        if metadata_is_link_or_reparse_point(opened) or not stat.S_ISREG(opened.st_mode):
            raise PermissionError("witness history must be a regular file")
        os.write(descriptor, line.encode("utf-8"))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    restrict_private_file(path)


def witness_history(host: str, limit: int = 20) -> tuple[dict[str, Any], ...]:
    """Return up to ``limit`` recorded attestations for ``host``, newest last.

    Reads only the current history window.  Malformed lines are skipped
    rather than trusted: the log is advisory bisect evidence, not authority.
    """

    normalized = _validated_host(host)
    bounded = max(1, min(int(limit), MAX_WITNESS_HISTORY_ENTRIES))
    _manifest_path, history_path = _witness_paths(normalized)
    try:
        payload = read_bounded_regular_file(
            history_path,
            limit=_MAX_HISTORY_BYTES + _MAX_HISTORY_LINE_BYTES,
            label="witness history",
        )
    except (OSError, ValueError):
        return ()
    entries: list[dict[str, Any]] = []
    for raw in payload.splitlines()[-bounded:]:
        try:
            value = safe_load_bounded_json(
                raw,
                maximum_bytes=_MAX_HISTORY_LINE_BYTES,
                maximum_depth=4,
                maximum_nodes=256,
            )
        except (TypeError, ValueError):
            continue
        if isinstance(value, dict) and isinstance(value.get("attested_at"), str):
            entries.append(value)
    return tuple(entries)


__all__ = [
    "FIX_REGISTRY",
    "MAX_WITNESS_HISTORY_ENTRIES",
    "WIRED_SOURCE_HOST_WIRING",
    "WIRED_SOURCE_INSTALLED_POINTER",
    "WITNESS_FAILURE_STATUSES",
    "WITNESS_SCHEMA",
    "WITNESS_STATUSES",
    "DocumentedFix",
    "FixWitness",
    "HostWitness",
    "attest_host",
    "witness_history",
]
