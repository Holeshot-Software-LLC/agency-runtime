"""Read-only release discovery and attended upgrade planning.

The runtime never installs code from this module.  It resolves a mutable
selector to one immutable commit, stores a bounded untrusted cache, and emits
the exact argv an operator may review and run outside the dashboard.  This
keeps hooks and model-facing surfaces free of package-mutation authority.
"""

from __future__ import annotations

import json
import math
import os
import re
import shlex
import stat
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from contextlib import suppress
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, distribution
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote, urlsplit

from agency_runtime import __version__
from agency_runtime.core.bounded_json import BoundedJSONError, safe_load_bounded_json
from agency_runtime.core.configuration import restrict_private_file
from agency_runtime.core.configuration_persistence import config_lock
from agency_runtime.core.http_safety import open_no_redirect
from agency_runtime.core.owned_process import BoundedProcessResult, run_bounded_process
from agency_runtime.core.private_paths import (
    bootstrap_private_directory,
    ensure_private_directory,
    private_runtime_directory,
    private_runtime_root_candidates,
    validate_private_directory,
)
from agency_runtime.core.process_argv import (
    freeze_process_argv,
    prepare_process_argv,
    repository_forbidden_roots,
)

UPDATE_SCHEMA_VERSION = "agency.update.v1"
DASHBOARD_UPDATE_SCHEMA_VERSION = "agency.dashboard.update.v1"
CACHE_SCHEMA_VERSION = 1
REPOSITORY = "Holeshot-Software-LLC/agency-runtime"
REPOSITORY_URL = f"https://github.com/{REPOSITORY}"
REPOSITORY_GIT_URL = f"{REPOSITORY_URL}.git"
GITHUB_API_ORIGIN = "https://api.github.com"
DEFAULT_CHANNEL = "release"
DEFAULT_CACHE_TTL_SECONDS = 24 * 60 * 60
FAILED_CACHE_TTL_SECONDS = 60 * 60
DEFAULT_TIMEOUT_SECONDS = 5.0
MAX_RESPONSE_BYTES = 256 * 1024
MAX_CACHE_BYTES = 512 * 1024
MAX_CACHE_ENTRIES = 16
DASHBOARD_IDENTITY_TTL_SECONDS = 10.0

_FULL_SHA = re.compile(r"[0-9a-f]{40}")
_VERSION = re.compile(
    r"v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:(a|b|rc)(0|[1-9]\d*))?"
)
_REF = re.compile(r"[0-9A-Za-z][0-9A-Za-z._+/-]{0,127}")
_CACHE_LOCK = threading.RLock()
_DASHBOARD_IDENTITY_LOCK = threading.Lock()
_DASHBOARD_IDENTITY_CACHE: tuple[float, dict[str, Any]] | None = None
_INFLIGHT_LOCK = threading.Lock()
_INFLIGHT: set[str] = set()

JsonFetcher = Callable[[str, float], Mapping[str, Any]]
Clock = Callable[[], float]


class UpdateCheckError(RuntimeError):
    """A bounded remote update probe could not establish a valid target."""


def _utc_iso(epoch: float) -> str:
    return datetime.fromtimestamp(epoch, tz=timezone.utc).isoformat()


def _bounded_text(value: object, *, label: str, limit: int = 512) -> str:
    if not isinstance(value, str):
        raise UpdateCheckError(f"{label} is invalid")
    text = value.strip()
    if (
        not text
        or text != value
        or len(text.encode("utf-8", errors="surrogatepass")) > limit
        or any(ord(character) < 32 or ord(character) == 127 for character in text)
    ):
        raise UpdateCheckError(f"{label} is invalid")
    return text


def _normalize_ref(value: object, *, label: str = "update ref") -> str:
    try:
        text = _bounded_text(value, label=label, limit=128)
    except UpdateCheckError as exc:
        raise ValueError(str(exc)) from exc
    if (
        _REF.fullmatch(text) is None
        or ".." in text
        or "//" in text
        or "@{" in text
        or text.endswith("/")
    ):
        raise ValueError(f"{label} is invalid")
    return text


def _normalize_version(value: object) -> str:
    try:
        text = _bounded_text(value, label="release version", limit=64)
    except UpdateCheckError as exc:
        raise ValueError(str(exc)) from exc
    if _VERSION.fullmatch(text) is None:
        raise ValueError("release version must look like 1.2.3 or v1.2.3")
    return text.removeprefix("v")


def normalize_update_selector(
    *,
    channel: str | None = None,
    version: str | None = None,
    ref: str | None = None,
) -> dict[str, str]:
    """Return one closed-world update selector."""

    supplied = sum(value is not None for value in (channel, version, ref))
    if supplied > 1:
        raise ValueError("choose exactly one of --channel, --version, or --ref")
    if version is not None:
        normalized = _normalize_version(version)
        tag = f"v{normalized}"
        return {"kind": "version", "value": normalized, "ref": tag, "key": f"version:{tag}"}
    if ref is not None:
        normalized = _normalize_ref(ref)
        return {"kind": "ref", "value": normalized, "ref": normalized, "key": f"ref:{normalized}"}
    selected = DEFAULT_CHANNEL if channel is None else str(channel).strip().casefold()
    if selected not in {"release", "main"}:
        raise ValueError("update channel must be release or main")
    if selected == "main":
        return {"kind": "channel", "value": "main", "ref": "main", "key": "channel:main"}
    return {
        "kind": "channel",
        "value": "release",
        "ref": "latest",
        "key": "channel:release",
    }


def _find_source_repository() -> Path | None:
    module = Path(__file__).resolve()
    package = module.parents[1]
    repository = package.parent
    marker = repository / ".git"
    if package.name != "agency_runtime" or not (marker.exists() or os.path.lexists(marker)):
        return None
    try:
        expected = (repository / "agency_runtime" / "core" / "update_service.py").resolve(
            strict=True
        )
    except OSError:
        return None
    return repository if expected == module else None


def _run_read_only_git(repository: Path, arguments: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        from agency_runtime.core.delegation.lifecycle_git import run_git

        return run_git(repository, arguments, timeout=5)
    except (OSError, PermissionError, RuntimeError, TypeError, ValueError) as exc:
        return subprocess.CompletedProcess(["git", *arguments], 1, "", type(exc).__name__)


def _git_value(repository: Path, arguments: list[str]) -> str:
    result = _run_read_only_git(repository, arguments)
    if result.returncode != 0:
        return ""
    value = str(result.stdout or "").strip()
    if len(value.encode("utf-8", errors="replace")) > 4096:
        return ""
    return value


def _official_remote(value: str) -> bool:
    candidate = value.strip().removesuffix("/").removesuffix(".git")
    return candidate.casefold() in {
        REPOSITORY_URL.casefold(),
        f"git@github.com:{REPOSITORY}".casefold(),
        f"ssh://git@github.com/{REPOSITORY}".casefold(),
    }


def installed_version_snapshot() -> dict[str, Any]:
    """Return bounded installed identity without claiming unavailable provenance."""

    install_kind = "package"
    direct_revision = ""
    direct_official = False
    with suppress(PackageNotFoundError, OSError, TypeError, ValueError):
        package = distribution("agency-runtime")
        files = tuple(str(item) for item in (package.files or ()))
        if any(Path(item).name.startswith("__editable__") for item in files):
            install_kind = "editable"
        direct = package.read_text("direct_url.json")
        if direct and len(direct.encode("utf-8", errors="replace")) <= 64 * 1024:
            value = safe_load_bounded_json(
                direct,
                maximum_bytes=64 * 1024,
                maximum_depth=16,
                maximum_nodes=1_000,
            )
            if isinstance(value, Mapping):
                if (
                    isinstance(value.get("dir_info"), Mapping)
                    and value["dir_info"].get("editable") is True
                ):
                    install_kind = "editable"
                vcs = value.get("vcs_info")
                direct_url = value.get("url")
                if (
                    isinstance(vcs, Mapping)
                    and vcs.get("vcs") == "git"
                    and isinstance(vcs.get("commit_id"), str)
                    and _FULL_SHA.fullmatch(vcs["commit_id"])
                    and isinstance(direct_url, str)
                ):
                    direct_revision = vcs["commit_id"]
                    direct_official = _official_remote(direct_url)
                    if install_kind == "package":
                        install_kind = "vcs-package"

    repository = _find_source_repository()
    revision = direct_revision
    branch = ""
    official = direct_official
    dirty: bool | None = None
    use_repository_identity = repository is not None and (
        not direct_revision or install_kind == "editable"
    )
    if use_repository_identity and repository is not None:
        observed = _git_value(repository, ["rev-parse", "--verify", "HEAD^{commit}"])
        if not direct_revision:
            revision = observed if _FULL_SHA.fullmatch(observed) else ""
        observed_branch = _git_value(repository, ["rev-parse", "--abbrev-ref", "HEAD"])
        if observed_branch and len(observed_branch) <= 128 and "\n" not in observed_branch:
            branch = observed_branch
        official = _official_remote(_git_value(repository, ["remote", "get-url", "origin"]))
        dirty_result = _run_read_only_git(
            repository,
            ["status", "--porcelain=v1", "--untracked-files=normal"],
        )
        if dirty_result.returncode == 0:
            dirty_output = str(dirty_result.stdout or "")
            if len(dirty_output.encode("utf-8", errors="replace")) <= 64 * 1024:
                dirty = bool(dirty_output.strip()) or bool(
                    direct_revision
                    and _FULL_SHA.fullmatch(observed)
                    and observed != direct_revision
                )
        if install_kind == "package":
            install_kind = "source-checkout"

    build_identity = __version__
    if revision:
        build_identity = f"{__version__}+g{revision[:12]}"
    if dirty is True:
        build_identity = f"{build_identity}.dirty"
    return {
        "package_version": __version__,
        "build_identity": build_identity,
        "source_revision": revision or None,
        "source_branch": branch or None,
        "source_dirty": dirty,
        "install_kind": install_kind,
        "official_repository": official,
    }


def _gh_environment() -> dict[str, str]:
    allowed = {
        "APPDATA",
        "GH_CONFIG_DIR",
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "HOME",
        "HTTPS_PROXY",
        "HTTP_PROXY",
        "LOCALAPPDATA",
        "NO_PROXY",
        "SSL_CERT_DIR",
        "SSL_CERT_FILE",
        "SYSTEMROOT",
        "TEMP",
        "TMP",
        "USERPROFILE",
        "WINDIR",
    }
    environment = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    environment.update(
        {
            "GH_PROMPT_DISABLED": "1",
            "GH_PAGER": "cat",
            "NO_COLOR": "1",
        }
    )
    return environment


def _gh_api_bytes(path: str, timeout: float) -> bytes:
    forbidden_roots = repository_forbidden_roots()
    argv = prepare_process_argv(
        [
            "gh",
            "api",
            "--hostname",
            "github.com",
            "--method",
            "GET",
            path,
        ],
        forbidden_roots=forbidden_roots,
    )
    freeze_process_argv(argv, forbidden_roots=forbidden_roots)
    result: BoundedProcessResult = run_bounded_process(
        argv,
        timeout=timeout,
        env=_gh_environment(),
        max_output_chars=MAX_RESPONSE_BYTES,
    )
    if result.timed_out:
        raise UpdateCheckError("GitHub CLI update check timed out")
    if result.stdout_truncated or result.stderr_truncated:
        raise UpdateCheckError("GitHub CLI update response exceeded its size limit")
    if result.returncode != 0:
        raise UpdateCheckError("GitHub CLI could not read the requested update target")
    return result.stdout.encode("utf-8")


def _https_api_bytes(path: str, timeout: float) -> bytes:
    url = f"{GITHUB_API_ORIGIN}/{path}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": f"agency-runtime/{__version__}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
        method="GET",
    )
    try:
        with open_no_redirect(request, timeout=timeout) as response:
            final_url = str(response.geturl())
            parsed = urlsplit(final_url)
            if parsed.scheme != "https" or parsed.netloc.casefold() != "api.github.com":
                raise UpdateCheckError("GitHub update response changed origin")
            content_length = response.headers.get("Content-Length")
            if content_length is not None:
                try:
                    declared = int(content_length)
                except ValueError as exc:
                    raise UpdateCheckError("GitHub update response length is invalid") from exc
                if declared < 0 or declared > MAX_RESPONSE_BYTES:
                    raise UpdateCheckError("GitHub update response exceeded its size limit")
            payload = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise UpdateCheckError("the requested release or ref is not published") from exc
        raise UpdateCheckError(f"GitHub update check failed with HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise UpdateCheckError("GitHub update service is unavailable") from exc
    if len(payload) > MAX_RESPONSE_BYTES:
        raise UpdateCheckError("GitHub update response exceeded its size limit")
    return payload


def _github_json(path: str, timeout: float) -> Mapping[str, Any]:
    deadline = time.monotonic() + timeout
    failures: list[Exception] = []
    for reader in (_gh_api_bytes, _https_api_bytes):
        try:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise UpdateCheckError("GitHub update check timed out")
            raw = reader(path, remaining)
            value = safe_load_bounded_json(
                raw,
                maximum_bytes=MAX_RESPONSE_BYTES,
                maximum_depth=16,
                maximum_nodes=5_000,
            )
            if not isinstance(value, Mapping):
                raise UpdateCheckError("GitHub update response is not an object")
            return value
        except (BoundedJSONError, FileNotFoundError, OSError, UpdateCheckError) as exc:
            failures.append(exc)
    if failures:
        raise UpdateCheckError(str(failures[-1])) from failures[-1]
    raise UpdateCheckError("GitHub update service is unavailable")


def _validate_commit(value: Mapping[str, Any]) -> tuple[str, str]:
    sha = _bounded_text(value.get("sha"), label="GitHub commit identity", limit=40)
    if _FULL_SHA.fullmatch(sha) is None:
        raise UpdateCheckError("GitHub commit identity is invalid")
    url = _bounded_text(value.get("html_url"), label="GitHub commit URL", limit=512)
    parsed = urlsplit(url)
    expected_path = f"/{REPOSITORY}/commit/{sha}".casefold()
    if (
        parsed.scheme != "https"
        or parsed.netloc.casefold() != "github.com"
        or parsed.path.casefold() != expected_path
        or parsed.query
        or parsed.fragment
    ):
        raise UpdateCheckError("GitHub commit URL is invalid")
    return sha, url


def _validate_release_url(value: object, tag: str) -> str:
    url = _bounded_text(value, label="GitHub release URL", limit=512)
    parsed = urlsplit(url)
    expected_prefix = f"/{REPOSITORY}/releases/tag/".casefold()
    if (
        parsed.scheme != "https"
        or parsed.netloc.casefold() != "github.com"
        or not parsed.path.casefold().startswith(expected_prefix)
        or unquote(parsed.path[len(expected_prefix) :]) != tag
        or parsed.query
        or parsed.fragment
    ):
        raise UpdateCheckError("GitHub release URL is invalid")
    return url


def _fetch_commit(ref: str, timeout: float, fetch_json: JsonFetcher) -> tuple[str, str]:
    encoded = quote(_normalize_ref(ref), safe="")
    return _validate_commit(fetch_json(f"repos/{REPOSITORY}/commits/{encoded}", timeout))


def _fetch_target(
    selector: Mapping[str, str],
    timeout: float,
    fetch_json: JsonFetcher,
) -> dict[str, Any]:
    kind = selector["kind"]
    value = selector["value"]
    if kind == "channel" and value == "release":
        release = fetch_json(f"repos/{REPOSITORY}/releases/latest", timeout)
        if release.get("draft") is True or release.get("prerelease") is True:
            raise UpdateCheckError("GitHub latest release is not a stable published release")
        tag = _normalize_ref(release.get("tag_name"), label="release tag")
        release_url = _validate_release_url(release.get("html_url"), tag)
        published = release.get("published_at")
        if published is not None:
            published = _bounded_text(published, label="release publication time", limit=64)
        sha, _commit_url = _fetch_commit(tag, timeout, fetch_json)
        version = tag.removeprefix("v") if _VERSION.fullmatch(tag) else None
        return {
            "kind": "release",
            "label": tag,
            "version": version,
            "ref": tag,
            "commit_sha": sha,
            "url": release_url,
            "published_at": published,
        }

    ref = selector["ref"]
    sha, url = _fetch_commit(ref, timeout, fetch_json)
    target_kind = "main" if kind == "channel" else kind
    return {
        "kind": target_kind,
        "label": value,
        "version": value if kind == "version" else None,
        "ref": ref,
        "commit_sha": sha,
        "url": url,
        "published_at": None,
    }


def _validated_cached_target(selector: Mapping[str, str], value: object) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    try:
        sha = _bounded_text(value.get("commit_sha"), label="cached commit", limit=40)
        if _FULL_SHA.fullmatch(sha) is None:
            raise UpdateCheckError("cached commit is invalid")
        kind = _bounded_text(value.get("kind"), label="cached target kind", limit=16)
        label = _bounded_text(value.get("label"), label="cached target label", limit=128)
        ref = _normalize_ref(value.get("ref"), label="cached target ref")
        version: str | None = None
        published: str | None = None
        expected_kind = selector["kind"]
        if expected_kind == "channel" and selector["value"] == "release":
            if kind != "release" or label != ref:
                raise UpdateCheckError("cached release target is invalid")
            url = _validate_release_url(value.get("url"), ref)
            if _VERSION.fullmatch(ref):
                version = ref.removeprefix("v")
            if value.get("published_at") is not None:
                published = _bounded_text(
                    value.get("published_at"), label="cached release time", limit=64
                )
        else:
            expected_target_kind = "main" if expected_kind == "channel" else expected_kind
            if kind != expected_target_kind or label != selector["value"] or ref != selector["ref"]:
                raise UpdateCheckError("cached update target is invalid")
            _validated_sha, url = _validate_commit({"sha": sha, "html_url": value.get("url")})
            if expected_kind == "version":
                version = _normalize_version(value.get("version"))
                if version != selector["value"]:
                    raise UpdateCheckError("cached release version is invalid")
        return {
            "kind": kind,
            "label": label,
            "version": version,
            "ref": ref,
            "commit_sha": sha,
            "url": url,
            "published_at": published,
        }
    except (TypeError, UpdateCheckError, ValueError):
        return None


def _cache_path(*, home_dir: str | Path | None, create: bool) -> Path:
    if home_dir is None:
        if create:
            parent = private_runtime_directory("updates")
        else:
            parent = Path.home() / ".agency-runtime" / "updates"
    else:
        home = Path(os.path.abspath(Path(home_dir).expanduser()))
        runtime_root = home / ".agency-runtime"
        if create:
            bootstrap_private_directory(runtime_root)
            parent = ensure_private_directory(runtime_root / "updates")
        else:
            parent = runtime_root / "updates"
    return parent / "checks-v1.json"


def _cache_read_paths(*, home_dir: str | Path | None) -> tuple[Path, ...]:
    if home_dir is not None:
        return (_cache_path(home_dir=home_dir, create=False),)
    return tuple(root / "updates" / "checks-v1.json" for root in private_runtime_root_candidates())


def _regular_single_link(path: Path) -> bool:
    try:
        metadata = os.lstat(path)
    except OSError:
        return False
    return (
        stat.S_ISREG(metadata.st_mode)
        and not stat.S_ISLNK(metadata.st_mode)
        and int(getattr(metadata, "st_nlink", 1) or 0) == 1
        and int(metadata.st_size) <= MAX_CACHE_BYTES
    )


def _read_cache_path(path: Path) -> dict[str, Any] | None:
    if not _regular_single_link(path):
        return None
    try:
        validate_private_directory(path.parent)
        raw = path.read_bytes()
        if len(raw) > MAX_CACHE_BYTES or not _regular_single_link(path):
            raise ValueError("update cache exceeded its size limit")
        value = safe_load_bounded_json(
            raw,
            maximum_bytes=MAX_CACHE_BYTES,
            maximum_depth=16,
            maximum_nodes=5_000,
        )
    except (BoundedJSONError, OSError, PermissionError, UnicodeDecodeError, ValueError):
        return None
    if (
        not isinstance(value, Mapping)
        or value.get("schema_version") != CACHE_SCHEMA_VERSION
        or not isinstance(value.get("entries"), Mapping)
    ):
        return None
    entries = dict(value["entries"])
    if len(entries) > MAX_CACHE_ENTRIES:
        return None
    return {"schema_version": CACHE_SCHEMA_VERSION, "entries": entries}


def _read_cache(*, home_dir: str | Path | None) -> dict[str, Any]:
    for path in _cache_read_paths(home_dir=home_dir):
        cache = _read_cache_path(path)
        if cache is not None:
            return cache
    return {"schema_version": CACHE_SCHEMA_VERSION, "entries": {}}


def _cache_epoch(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    parsed = float(value)
    if not math.isfinite(parsed) or not 0 <= parsed <= 253_402_300_799:
        return None
    return parsed


def _cached_error(value: object) -> str | None:
    if value is None:
        return None
    try:
        return _bounded_text(value, label="cached update error", limit=512)
    except UpdateCheckError:
        return "cached update result was invalid"


def _cache_entry_is_reusable(
    selector: Mapping[str, str],
    entry: object,
    *,
    now: float,
) -> bool:
    if not isinstance(entry, Mapping):
        return False
    checked = _cache_epoch(entry.get("checked_at"))
    expires = _cache_epoch(entry.get("expires_at"))
    if checked is None or expires is None or checked > now or expires <= now:
        return False
    raw_target = entry.get("target")
    target = _validated_cached_target(selector, raw_target)
    if raw_target is not None and target is None:
        return False
    raw_error = entry.get("error")
    if target is not None:
        if raw_error is not None:
            return False
        maximum_ttl = DEFAULT_CACHE_TTL_SECONDS
    else:
        try:
            error = _bounded_text(raw_error, label="cached update error", limit=512)
        except UpdateCheckError:
            return False
        if not error:
            return False
        maximum_ttl = FAILED_CACHE_TTL_SECONDS
    return checked <= expires <= checked + maximum_ttl


def _write_cache(value: Mapping[str, Any], *, home_dir: str | Path | None) -> None:
    path = _cache_path(home_dir=home_dir, create=True)
    validate_private_directory(path.parent)
    if (path.exists() or os.path.lexists(path)) and not _regular_single_link(path):
        raise PermissionError("update cache target is unsafe")
    payload = (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        + b"\n"
    )
    if len(payload) > MAX_CACHE_BYTES:
        raise ValueError("update cache exceeded its size limit")
    descriptor, name = tempfile.mkstemp(prefix=".checks-", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            descriptor = -1
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        restrict_private_file(temporary)
        if not _regular_single_link(temporary):
            raise PermissionError("update cache temporary file is unsafe")
        if (path.exists() or os.path.lexists(path)) and not _regular_single_link(path):
            raise PermissionError("update cache changed before publication")
        os.replace(temporary, path)
        restrict_private_file(path)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        temporary.unlink(missing_ok=True)


def _cache_process_lock(path: Path):
    def ensure_parent(target: Path) -> None:
        validate_private_directory(target.parent)

    def restrict(target: Path, **_kwargs: object) -> bool:
        restrict_private_file(target)
        return True

    return config_lock(
        path,
        timeout=1.0,
        ensure_parent=ensure_parent,
        restrict=restrict,
    )


def _release_key(value: object) -> tuple[int, int, int, int, int] | None:
    match = _VERSION.fullmatch(str(value or ""))
    if match is None:
        return None
    phase = match.group(4)
    phase_rank = {"a": 0, "b": 1, "rc": 2, None: 3}[phase]
    phase_number = int(match.group(5) or 0)
    return (
        int(match.group(1)),
        int(match.group(2)),
        int(match.group(3)),
        phase_rank,
        phase_number,
    )


def _comparison(
    installed: Mapping[str, Any],
    selector: Mapping[str, str],
    target: Mapping[str, Any] | None,
) -> tuple[str, bool | None]:
    if target is None:
        return "unavailable", None
    revision = str(installed.get("source_revision") or "")
    target_sha = str(target.get("commit_sha") or "")
    if selector["kind"] == "ref" or selector["value"] == "main":
        if revision and target_sha:
            if revision != target_sha:
                return "different_target", None
            if installed.get("source_dirty") is True:
                return "local_changes", False
            return "current", False
        return "unknown", None
    current_key = _release_key(installed.get("package_version"))
    target_key = _release_key(target.get("version"))
    if current_key is None or target_key is None:
        return "unknown", None
    if target_key > current_key:
        return "update_available", True
    if target_key < current_key:
        return "newer_installed", False
    if revision and target_sha and revision != target_sha:
        return "different_target", None
    if installed.get("source_dirty") is True:
        return "local_changes", False
    return "current", False


def _status_from_entry(
    selector: Mapping[str, str],
    installed: Mapping[str, Any],
    entry: Mapping[str, Any] | None,
    *,
    now: float,
    cache_hit: bool,
) -> dict[str, Any]:
    raw_target = entry.get("target") if isinstance(entry, Mapping) else None
    target = _validated_cached_target(selector, raw_target)
    error = _cached_error(entry.get("error")) if isinstance(entry, Mapping) else None
    if raw_target is not None and target is None:
        error = "cached update target was invalid"
    checked_epoch = _cache_epoch(entry.get("checked_at")) if isinstance(entry, Mapping) else None
    expires_epoch = _cache_epoch(entry.get("expires_at")) if isinstance(entry, Mapping) else None
    status, available = _comparison(installed, selector, target)
    if error and target is None:
        status = "unavailable"
        available = None
    return {
        "schema_version": UPDATE_SCHEMA_VERSION,
        "installed": dict(installed),
        "selector": dict(selector),
        "checked": checked_epoch is not None,
        "cache_hit": cache_hit,
        "stale": expires_epoch is None or expires_epoch <= now,
        "checking": False,
        "checked_at": _utc_iso(float(checked_epoch)) if checked_epoch is not None else None,
        "status": status if checked_epoch is not None else "unchecked",
        "update_available": available if checked_epoch is not None else None,
        "target": dict(target) if target is not None else None,
        "error": error,
        "command": selector_command(selector),
    }


def selector_command(selector: Mapping[str, str]) -> str:
    if selector["kind"] == "version":
        return f"agency upgrade --version {selector['value']}"
    if selector["kind"] == "ref":
        return f"agency upgrade --ref {selector['value']}"
    return f"agency upgrade --channel {selector['value']}"


def cached_update_status(
    *,
    channel: str | None = None,
    version: str | None = None,
    ref: str | None = None,
    home_dir: str | Path | None = None,
    clock: Clock = time.time,
) -> dict[str, Any]:
    selector = normalize_update_selector(channel=channel, version=version, ref=ref)
    with _CACHE_LOCK:
        cache = _read_cache(home_dir=home_dir)
    entry = cache["entries"].get(selector["key"])
    return _status_from_entry(
        selector,
        installed_version_snapshot(),
        entry if isinstance(entry, Mapping) else None,
        now=clock(),
        cache_hit=isinstance(entry, Mapping),
    )


def check_for_update(
    *,
    channel: str | None = None,
    version: str | None = None,
    ref: str | None = None,
    refresh: bool = False,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    home_dir: str | Path | None = None,
    fetch_json: JsonFetcher = _github_json,
    clock: Clock = time.time,
) -> dict[str, Any]:
    """Resolve one selector, reusing only a fresh validated cache entry."""

    if (
        isinstance(timeout, bool)
        or not isinstance(timeout, (int, float))
        or not 0.1 <= timeout <= 30
    ):
        raise ValueError("update timeout must be from 0.1 through 30 seconds")
    selector = normalize_update_selector(channel=channel, version=version, ref=ref)
    installed = installed_version_snapshot()
    now = _cache_epoch(clock())
    if now is None:
        raise ValueError("update clock returned an invalid time")
    with _CACHE_LOCK:
        cache = _read_cache(home_dir=home_dir)
    entries = dict(cache["entries"])
    cached = entries.get(selector["key"])
    if not refresh and _cache_entry_is_reusable(selector, cached, now=now):
        assert isinstance(cached, Mapping)
        return _status_from_entry(
            selector,
            installed,
            cached,
            now=now,
            cache_hit=True,
        )

    target: dict[str, Any] | None = None
    error: str | None = None
    ttl = DEFAULT_CACHE_TTL_SECONDS
    try:
        deadline = time.monotonic() + float(timeout)

        def deadline_fetch(path: str, _requested_timeout: float) -> Mapping[str, Any]:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise UpdateCheckError("GitHub update check timed out")
            return fetch_json(path, remaining)

        target = _fetch_target(selector, float(timeout), deadline_fetch)
    except (OSError, UpdateCheckError, ValueError) as exc:
        error = str(exc)[:512] or type(exc).__name__
        ttl = FAILED_CACHE_TTL_SECONDS
    entry = {
        "checked_at": now,
        "expires_at": now + ttl,
        "target": target,
        "error": error,
    }
    cached_status, cached_available = _comparison(installed, selector, target)
    entry["observed_status"] = cached_status
    entry["update_available"] = cached_available
    entry["installed_build_identity"] = installed.get("build_identity")
    entry["installed_package_version"] = installed.get("package_version")
    with suppress(OSError, PermissionError, ValueError):
        cache_path = _cache_path(home_dir=home_dir, create=True)
        with _CACHE_LOCK, _cache_process_lock(cache_path):
            latest = _read_cache(home_dir=home_dir)
            entries = dict(latest["entries"])
            entries[selector["key"]] = entry
            if len(entries) > MAX_CACHE_ENTRIES:
                ordered = sorted(
                    entries.items(),
                    key=lambda item: (
                        _cache_epoch(item[1].get("checked_at")) or 0
                        if isinstance(item[1], Mapping)
                        else 0
                    ),
                    reverse=True,
                )[:MAX_CACHE_ENTRIES]
                entries = dict(ordered)
            _write_cache(
                {"schema_version": CACHE_SCHEMA_VERSION, "entries": entries},
                home_dir=home_dir,
            )
    return _status_from_entry(selector, installed, entry, now=now, cache_hit=False)


def _display_argv(argv: list[str]) -> str:
    if os.name == "nt":
        return subprocess.list2cmdline(argv)
    return shlex.join(argv)


def attended_upgrade_plan(status: Mapping[str, Any]) -> dict[str, Any]:
    """Build a non-executing exact-source plan from a resolved target."""

    target = status.get("target")
    if not isinstance(target, Mapping):
        return {
            "mode": "unavailable",
            "mutation_performed": False,
            "commands": [],
            "reason": str(status.get("error") or "an immutable update target is unavailable"),
        }
    sha = str(target.get("commit_sha") or "")
    if _FULL_SHA.fullmatch(sha) is None:
        raise ValueError("upgrade target lacks an immutable commit identity")
    if status.get("status") == "current":
        return {
            "mode": "current",
            "mutation_performed": False,
            "commands": [],
            "reason": "the installed source already matches the resolved target",
        }
    source = f"agency-runtime @ git+{REPOSITORY_GIT_URL}@{sha}"
    install = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--upgrade",
        "--force-reinstall",
        source,
    ]
    refresh_codex = [
        sys.executable,
        "-m",
        "agency_runtime.cli",
        "install",
        "--agent",
        "codex",
        "--no-dashboard",
    ]
    commands = [install, refresh_codex]
    return {
        "mode": "attended-external",
        "mutation_performed": False,
        "commands": [{"argv": argv, "display": _display_argv(argv)} for argv in commands],
        "reason": (
            "Agency resolved an immutable source target but did not execute package or host "
            "mutations; review and run each command from an owner-controlled terminal"
        ),
        "requires_operator_presence": True,
        "requires_post_install_activation_check": True,
    }


def _scheduled_worker(selector: Mapping[str, str], home_dir: str | Path | None) -> None:
    try:
        kwargs: dict[str, str] = {}
        if selector["kind"] == "version":
            kwargs["version"] = selector["value"]
        elif selector["kind"] == "ref":
            kwargs["ref"] = selector["value"]
        else:
            kwargs["channel"] = selector["value"]
        with suppress(OSError, PermissionError, RuntimeError, TypeError, ValueError):
            check_for_update(home_dir=home_dir, **kwargs)
    finally:
        with _INFLIGHT_LOCK:
            _INFLIGHT.discard(selector["key"])


def schedule_update_check(
    *,
    channel: str,
    home_dir: str | Path | None = None,
) -> bool:
    """Start at most one daemon refresh for a channel and return immediately."""

    selector = normalize_update_selector(channel=channel)
    cached = cached_update_status(channel=channel, home_dir=home_dir)
    if cached["stale"] is False:
        return False
    return _schedule_selector(selector, home_dir)


def _schedule_selector(
    selector: Mapping[str, str],
    home_dir: str | Path | None,
) -> bool:
    with _INFLIGHT_LOCK:
        if selector["key"] in _INFLIGHT:
            return False
        _INFLIGHT.add(selector["key"])
    thread = threading.Thread(
        target=_scheduled_worker,
        args=(selector, home_dir),
        daemon=True,
        name=f"agency-update-{selector['value']}",
    )
    try:
        thread.start()
    except RuntimeError:
        with _INFLIGHT_LOCK:
            _INFLIGHT.discard(selector["key"])
        return False
    return True


def dashboard_update_snapshot(
    *,
    home_dir: str | Path | None = None,
    schedule: bool = True,
) -> dict[str, Any]:
    """Return both prerelease and release status for the read-only dashboard."""

    now = time.time()
    with _CACHE_LOCK:
        cache = _read_cache(home_dir=home_dir)
    installed = _dashboard_installed_version_snapshot()
    selectors = {
        channel: normalize_update_selector(channel=channel) for channel in ("release", "main")
    }
    statuses = {
        channel: _status_from_entry(
            selector,
            installed,
            cache["entries"].get(selector["key"])
            if isinstance(cache["entries"].get(selector["key"]), Mapping)
            else None,
            now=now,
            cache_hit=isinstance(cache["entries"].get(selector["key"]), Mapping),
        )
        for channel, selector in selectors.items()
    }
    release = statuses["release"]
    main = statuses["main"]
    if schedule:
        for channel, status in statuses.items():
            if status["stale"]:
                _schedule_selector(selectors[channel], home_dir)
                status["checking"] = True
    recommended = release if release.get("update_available") is True else main
    return {
        "schema_version": DASHBOARD_UPDATE_SCHEMA_VERSION,
        "installed": installed,
        "release": release,
        "main": main,
        "recommended": recommended.get("selector", {}).get("value"),
        "checking": bool(release.get("checking") or main.get("checking")),
    }


def _dashboard_installed_version_snapshot() -> dict[str, Any]:
    global _DASHBOARD_IDENTITY_CACHE

    now = time.monotonic()
    with _DASHBOARD_IDENTITY_LOCK:
        if (
            _DASHBOARD_IDENTITY_CACHE is not None
            and now - _DASHBOARD_IDENTITY_CACHE[0] < DASHBOARD_IDENTITY_TTL_SECONDS
        ):
            return dict(_DASHBOARD_IDENTITY_CACHE[1])
        identity = installed_version_snapshot()
        _DASHBOARD_IDENTITY_CACHE = (now, dict(identity))
        return dict(identity)


def cached_startup_notice(
    *,
    home_dir: str | Path | None = None,
    clock: Clock = time.time,
) -> str | None:
    """Return a cache-only interactive notice without Git or network work."""

    with _CACHE_LOCK:
        cache = _read_cache(home_dir=home_dir)
    for key in ("channel:release", "channel:main"):
        entry = cache["entries"].get(key)
        channel = key.partition(":")[2]
        selector = normalize_update_selector(channel=channel)
        target = (
            _validated_cached_target(selector, entry.get("target"))
            if isinstance(entry, Mapping)
            else None
        )
        if (
            not isinstance(entry, Mapping)
            or entry.get("update_available") is not True
            or entry.get("installed_package_version") != __version__
            or (_cache_epoch(entry.get("expires_at")) or 0) <= clock()
            or target is None
        ):
            continue
        label = target["label"]
        sha = target["commit_sha"]
        return (
            f"Agency update information is cached for {channel} {label} ({sha[:12]}). "
            f"Run `agency upgrade check --channel {channel}` to compare it."
        )
    return None


__all__ = [
    "CACHE_SCHEMA_VERSION",
    "DASHBOARD_UPDATE_SCHEMA_VERSION",
    "DEFAULT_CHANNEL",
    "UPDATE_SCHEMA_VERSION",
    "UpdateCheckError",
    "attended_upgrade_plan",
    "cached_startup_notice",
    "cached_update_status",
    "check_for_update",
    "dashboard_update_snapshot",
    "installed_version_snapshot",
    "normalize_update_selector",
    "schedule_update_check",
    "selector_command",
]
