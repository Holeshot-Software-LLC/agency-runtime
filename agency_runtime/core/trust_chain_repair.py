"""Known trust-chain scan and consented permission repair (AR-358).

Agency's read-time trust rules -- ``posix_directory_chain_is_trusted`` for
storage and executable namespaces, ``_assert_executable_artifact_trusted`` for
executables -- are never established at write time by the external writers
Agency depends on. Measured three times during the 2026-09-01 deploy: the
Claude Code npm self-update left ``@anthropic-ai/claude-code`` group-writable,
``npm install -g openclaw`` left the OpenClaw tree group-writable, and
``claude plugin update`` recreated plugin cache directories that were not
owner-private. Each time an operator rediscovered the same chmod dance by
forensics.

This module moves that lore into the product without widening its reach:

* the chains are a fixed registry per host -- Claude's plugin cache and npm
  package tree, OpenClaw's npm package tree, Agency's own runtime home and
  marketplaces -- resolved from the host-root and executable identities the
  installer already uses, never from caller-supplied paths;
* :func:`scan_trust_chains` is content-free: path classes, break kinds, and
  counts leave it, nothing else;
* :func:`repair_trust_chains` applies only the minimal mode change the trust
  rule needs (strip group/other write bits; make private directories
  owner-only), only with an explicit consent flag, only on entries the
  current account owns, and never through a symbolic link.
"""

from __future__ import annotations

import os
import shutil
import stat
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agency_runtime.core.filesystem_trust import metadata_is_link_or_reparse_point
from agency_runtime.core.installer_contracts import HOSTS, BinaryResolver

TRUST_CHAIN_HOSTS: tuple[str, ...] = ("claude", "openclaw", "agency")
BREAK_KINDS: tuple[str, ...] = ("group_writable", "other_writable", "final_dir_not_private")
POLICY_PRIVATE = "private"
POLICY_EXECUTABLE = "executable"
# The npm package each host executable must resolve into. A realpath that
# lands anywhere else (a wrapper, a native binary) registers no npm chain.
_NPM_PACKAGES: dict[str, str] = {
    "claude": "@anthropic-ai/claude-code",
    "openclaw": "openclaw",
}
_MAX_CHAIN_ENTRIES = 100_000
_MAX_EXAMPLES = 12
_MAX_EXAMPLE_CHARS = 200
_GROUP_OTHER_WRITE = stat.S_IWGRP | stat.S_IWOTH
_GROUP_OTHER_ALL = stat.S_IRWXG | stat.S_IRWXO
_POSIX = os.name != "nt"

Executables = Mapping[str, str | None]


@dataclass(frozen=True, slots=True)
class TrustChain:
    """One registered chain: a root tree plus the in-home ancestors the rule walks."""

    host: str
    name: str
    path_class: str
    root: Path
    policy: str
    recursive: bool
    ancestors: tuple[Path, ...]
    unavailable: str | None = None

    @property
    def available(self) -> bool:
        return self.unavailable is None


@dataclass(frozen=True, slots=True)
class TrustChainFinding:
    """Content-free evidence of one break kind on one chain."""

    host: str
    chain: str
    path_class: str
    root: str
    kind: str
    count: int
    scanned: int
    unowned: int
    truncated: bool

    def as_dict(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "chain": self.chain,
            "path_class": self.path_class,
            "root": self.root,
            "kind": self.kind,
            "count": self.count,
            "scanned": self.scanned,
            "unowned": self.unowned,
            "truncated": self.truncated,
        }


@dataclass(frozen=True, slots=True)
class TrustChainRepair:
    """What one consented repair changed on one chain, in bounded counts."""

    host: str
    chain: str
    path_class: str
    root: str
    changed: int = 0
    skipped_unowned: int = 0
    failed: int = 0
    truncated: bool = False
    refused: str | None = None
    examples: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "chain": self.chain,
            "path_class": self.path_class,
            "root": self.root,
            "changed": self.changed,
            "skipped_unowned": self.skipped_unowned,
            "failed": self.failed,
            "truncated": self.truncated,
            "refused": self.refused,
            "examples": list(self.examples),
        }


@dataclass(frozen=True, slots=True)
class TrustChainRepairReport:
    consent: bool
    chains: tuple[TrustChainRepair, ...]

    @property
    def applied(self) -> bool:
        return self.consent and any(repair.refused is None for repair in self.chains)

    @property
    def changed(self) -> int:
        return sum(repair.changed for repair in self.chains)

    @property
    def ok(self) -> bool:
        return all(repair.refused is None and repair.failed == 0 for repair in self.chains)

    def as_dict(self) -> dict[str, Any]:
        return {
            "consent": self.consent,
            "applied": self.applied,
            "ok": self.ok,
            "changed": self.changed,
            "chains": [repair.as_dict() for repair in self.chains],
        }


@dataclass(frozen=True, slots=True)
class _Entry:
    path: Path
    metadata: os.stat_result
    ancestor: bool


def _effective_uid() -> int | None:
    getter = getattr(os, "geteuid", None)
    return int(getter()) if callable(getter) else None


def _home(home_dir: str | Path | None) -> Path:
    from agency_runtime.core.installer_native import home_path

    return home_path("~", home_dir=home_dir)


def _selected_hosts(host: str | None) -> tuple[str, ...]:
    if host is None:
        return TRUST_CHAIN_HOSTS
    if host not in TRUST_CHAIN_HOSTS:
        raise ValueError(f"no trust chains are registered for host: {host!r}")
    return (host,)


def _root_unavailable(root: Path) -> str | None:
    try:
        metadata = os.lstat(root)
    except FileNotFoundError:
        return "missing"
    except OSError:
        return "unreadable"
    if metadata_is_link_or_reparse_point(metadata):
        return "root_is_symlink"
    if not stat.S_ISDIR(metadata.st_mode):
        return "root_not_directory"
    return None


def _ancestors_within(home: Path, root: Path) -> tuple[Path, ...]:
    """Directories strictly between the home boundary and the chain root.

    The trust rule walks every ancestor, so a group-writable ``~/.npm-global``
    breaks the chain as surely as the package tree does. Nothing outside the
    home boundary, and never the home directory itself, is a chain member.
    """

    try:
        if root == home or not root.is_relative_to(home):
            return ()
    except ValueError:
        return ()
    between = [parent for parent in root.parents if parent != home and parent.is_relative_to(home)]
    return tuple(reversed(between))


def _chain(
    host: str,
    name: str,
    path_class: str,
    root: Path,
    *,
    policy: str,
    recursive: bool,
    home: Path,
) -> TrustChain:
    unavailable = _root_unavailable(root)
    return TrustChain(
        host=host,
        name=name,
        path_class=path_class,
        root=root,
        policy=policy,
        recursive=recursive,
        ancestors=() if unavailable else _ancestors_within(home, root),
        unavailable=unavailable,
    )


def _npm_package_root(executable: str | None, expected: str) -> Path | None:
    """Resolve the npm package tree an executable really lives in, or nothing."""

    if not executable:
        return None
    try:
        resolved = Path(executable).resolve(strict=True)
    except (OSError, RuntimeError, ValueError):
        return None
    for parent in resolved.parents:
        if parent.name != "node_modules":
            continue
        relative = resolved.relative_to(parent).parts
        depth = 2 if relative and relative[0].startswith("@") else 1
        if len(relative) <= depth or "/".join(relative[:depth]) != expected:
            return None
        return parent.joinpath(*relative[:depth])
    return None


def _executable_for(
    host: str,
    executables: Executables | None,
    resolver: BinaryResolver | None,
) -> str | None:
    if executables is not None and host in executables:
        return executables[host]
    lookup = resolver or shutil.which
    return lookup(str(HOSTS[host]["binary"]))


def _npm_chain(host: str, executable: str | None, home: Path) -> list[TrustChain]:
    root = _npm_package_root(executable, _NPM_PACKAGES[host])
    if root is None:
        return []
    return [
        _chain(
            host,
            f"{host}_npm_tree",
            "npm_package",
            root,
            policy=POLICY_EXECUTABLE,
            recursive=True,
            home=home,
        )
    ]


def _host_chains(
    host: str,
    *,
    home: Path,
    home_dir: str | Path | None,
    executable: str | None,
) -> list[TrustChain]:
    from agency_runtime.core.installer_native import host_root, runtime_home

    if host == "claude":
        root = host_root("claude", home_dir=home_dir)
        return [
            _chain(
                "claude",
                "claude_plugins",
                "plugin_cache",
                root / "plugins",
                policy=POLICY_PRIVATE,
                recursive=True,
                home=home,
            ),
            # Where Claude writes its child transcripts. The child-delivery
            # evidence read requires an owner-private final parent and no
            # group-writable ancestor, and the host creates these directories
            # group-writable, so the canary could not prove a delivered card
            # (measured 2026-09-02: artifact_not_trusted with projects at 0775).
            _chain(
                "claude",
                "claude_child_artifacts",
                "child_artifacts",
                root / "projects",
                policy=POLICY_PRIVATE,
                recursive=True,
                home=home,
            ),
            *_npm_chain("claude", executable, home),
        ]
    if host == "openclaw":
        return _npm_chain("openclaw", executable, home)
    runtime = runtime_home(home_dir=home_dir)
    return [
        _chain(
            "agency",
            "agency_home",
            "runtime_home",
            runtime,
            policy=POLICY_PRIVATE,
            recursive=False,
            home=home,
        ),
        _chain(
            "agency",
            "agency_marketplaces",
            "marketplace",
            runtime / "marketplaces",
            policy=POLICY_PRIVATE,
            recursive=True,
            home=home,
        ),
    ]


def known_trust_chains(
    host: str | None = None,
    *,
    home_dir: str | Path | None = None,
    executables: Executables | None = None,
    resolver: BinaryResolver | None = None,
) -> tuple[TrustChain, ...]:
    """Return the registered chains for one host, or every host.

    ``executables`` pins the executable per host (the installer passes the
    binary it resolved for this very install); a host absent from it is
    looked up through ``resolver`` (``shutil.which`` by default).
    """

    home = _home(home_dir)
    chains: list[TrustChain] = []
    for selected in _selected_hosts(host):
        executable = (
            _executable_for(selected, executables, resolver) if selected in _NPM_PACKAGES else None
        )
        chains.extend(_host_chains(selected, home=home, home_dir=home_dir, executable=executable))
    return tuple(chains)


class _ChainWalk:
    """Bounded traversal of one chain that never follows a link.

    Ancestors come first, then the root and (for recursive chains) its tree
    in sorted order. Symbolic links are yielded as themselves so the caller
    can refuse them; they are never descended, so a link out of the chain
    cannot pull foreign paths in.
    """

    def __init__(self, chain: TrustChain, limit: int) -> None:
        self.chain = chain
        self.limit = limit
        self.count = 0
        self.truncated = False

    def _lstat(self, path: Path, *, ancestor: bool) -> _Entry | None:
        try:
            metadata = os.lstat(path)
        except OSError:
            return None
        self.count += 1
        return _Entry(path, metadata, ancestor)

    def __iter__(self) -> Iterator[_Entry]:
        for ancestor in self.chain.ancestors:
            entry = self._lstat(ancestor, ancestor=True)
            if entry is not None:
                yield entry
        root = self._lstat(self.chain.root, ancestor=False)
        if root is None:
            return
        yield root
        if not self.chain.recursive:
            return
        yield from self._descend(self.chain.root)

    def _descend(self, root: Path) -> Iterator[_Entry]:
        stack = [root]
        while stack:
            directory = stack.pop()
            try:
                with os.scandir(directory) as iterator:
                    children = sorted(iterator, key=lambda child: child.name)
            except OSError:
                continue
            for child in children:
                if self.count >= self.limit:
                    self.truncated = True
                    return
                try:
                    metadata = child.stat(follow_symlinks=False)
                except OSError:
                    continue
                self.count += 1
                path = Path(child.path)
                yield _Entry(path, metadata, False)
                if stat.S_ISDIR(metadata.st_mode) and not metadata_is_link_or_reparse_point(
                    metadata
                ):
                    stack.append(path)


def _break_kinds(entry: _Entry, policy: str) -> tuple[str, ...]:
    """Classify one entry against the rule its chain must satisfy."""

    metadata = entry.metadata
    if metadata_is_link_or_reparse_point(metadata):
        return ()
    mode = stat.S_IMODE(metadata.st_mode)
    is_directory = stat.S_ISDIR(metadata.st_mode)
    if is_directory and policy == POLICY_PRIVATE and not entry.ancestor:
        return ("final_dir_not_private",) if mode & _GROUP_OTHER_ALL else ()
    if is_directory and mode & stat.S_ISVTX:
        # A sticky shared directory is exactly what the trust rule tolerates
        # in an ancestor (the /tmp shape); it is not ours to tighten.
        return ()
    kinds: list[str] = []
    if mode & stat.S_IWGRP:
        kinds.append("group_writable")
    if mode & stat.S_IWOTH:
        kinds.append("other_writable")
    return tuple(kinds)


def _repaired_mode(entry: _Entry, kinds: Sequence[str]) -> int:
    mode = stat.S_IMODE(entry.metadata.st_mode)
    if "final_dir_not_private" in kinds:
        return mode & ~_GROUP_OTHER_ALL
    return mode & ~_GROUP_OTHER_WRITE


def _identity(metadata: os.stat_result) -> tuple[int, int]:
    return int(metadata.st_dev), int(getattr(metadata, "st_ino", 0) or 0)


def _chmod_verified(path: Path, before: os.stat_result, mode: int) -> bool:
    """Apply a mode through a descriptor matched to the lstat snapshot.

    The pathname is never trusted twice: the descriptor is opened without
    following a final link, then matched to the snapshot's identity, kind,
    and owner before ``fchmod``. Anything that changed underneath is a
    failure, not a chmod of whatever now sits at that name.
    """

    directory = stat.S_ISDIR(before.st_mode)
    flags = os.O_RDONLY | int(getattr(os, "O_CLOEXEC", 0)) | int(getattr(os, "O_NOFOLLOW", 0))
    if directory:
        flags |= int(getattr(os, "O_DIRECTORY", 0))
    try:
        descriptor = os.open(path, flags)
    except OSError:
        return False
    try:
        opened = os.fstat(descriptor)
        if (
            _identity(opened) != _identity(before)
            or int(opened.st_uid) != int(before.st_uid)
            or stat.S_ISDIR(opened.st_mode) != directory
        ):
            return False
        os.fchmod(descriptor, mode)
        return stat.S_IMODE(os.fstat(descriptor).st_mode) == mode
    except OSError:
        return False
    finally:
        os.close(descriptor)


def _scan_chain(
    chain: TrustChain,
    *,
    uid: int | None,
    seen: set[tuple[int, int]],
) -> list[TrustChainFinding]:
    walk = _ChainWalk(chain, _MAX_CHAIN_ENTRIES)
    counts = dict.fromkeys(BREAK_KINDS, 0)
    scanned = 0
    unowned = 0
    for entry in walk:
        identity = _identity(entry.metadata)
        if identity in seen:
            continue
        seen.add(identity)
        scanned += 1
        kinds = _break_kinds(entry, chain.policy)
        if not kinds:
            continue
        if uid is None or int(entry.metadata.st_uid) != uid:
            unowned += 1
        for kind in kinds:
            counts[kind] += 1
    return [
        TrustChainFinding(
            host=chain.host,
            chain=chain.name,
            path_class=chain.path_class,
            root=str(chain.root),
            kind=kind,
            count=count,
            scanned=scanned,
            unowned=unowned,
            truncated=walk.truncated,
        )
        for kind, count in counts.items()
        if count
    ]


def scan_trust_chains(
    host: str | None = None,
    *,
    home_dir: str | Path | None = None,
    executables: Executables | None = None,
    resolver: BinaryResolver | None = None,
) -> list[TrustChainFinding]:
    """Report permission breaks on the registered chains, content-free.

    Windows has no mode bits worth reporting; its ACL trust is checked per
    artifact elsewhere, so the scan is empty there by design.
    """

    if not _POSIX:
        return []
    uid = _effective_uid()
    seen: set[tuple[int, int]] = set()
    findings: list[TrustChainFinding] = []
    for chain in known_trust_chains(
        host,
        home_dir=home_dir,
        executables=executables,
        resolver=resolver,
    ):
        if chain.available:
            findings.extend(_scan_chain(chain, uid=uid, seen=seen))
    return findings


def _example(entry: _Entry, root: Path) -> str:
    rendered = str(entry.path) if entry.ancestor else os.path.relpath(entry.path, root)
    return rendered[:_MAX_EXAMPLE_CHARS]


def _repair_chain(
    chain: TrustChain,
    *,
    uid: int | None,
    seen: set[tuple[int, int]],
) -> TrustChainRepair:
    walk = _ChainWalk(chain, _MAX_CHAIN_ENTRIES)
    changed = skipped_unowned = failed = 0
    examples: list[str] = []
    for entry in walk:
        identity = _identity(entry.metadata)
        if identity in seen:
            continue
        seen.add(identity)
        kinds = _break_kinds(entry, chain.policy)
        if not kinds:
            continue
        if uid is None or int(entry.metadata.st_uid) != uid:
            skipped_unowned += 1
            continue
        if _chmod_verified(entry.path, entry.metadata, _repaired_mode(entry, kinds)):
            changed += 1
            if len(examples) < _MAX_EXAMPLES:
                examples.append(_example(entry, chain.root))
        else:
            failed += 1
    return TrustChainRepair(
        host=chain.host,
        chain=chain.name,
        path_class=chain.path_class,
        root=str(chain.root),
        changed=changed,
        skipped_unowned=skipped_unowned,
        failed=failed,
        truncated=walk.truncated,
        examples=tuple(examples),
    )


def _requested_chains(
    findings: Sequence[TrustChainFinding],
) -> list[tuple[str, str, str, str]]:
    requested: dict[tuple[str, str, str, str], None] = {}
    for finding in findings:
        requested.setdefault((finding.host, finding.chain, finding.path_class, finding.root), None)
    return list(requested)


def _refused(request: tuple[str, str, str, str], reason: str) -> TrustChainRepair:
    host, chain, path_class, root = request
    return TrustChainRepair(host, chain, path_class, root, refused=reason)


def repair_trust_chains(
    findings: Sequence[TrustChainFinding],
    *,
    consent: bool,
    home_dir: str | Path | None = None,
    executables: Executables | None = None,
    resolver: BinaryResolver | None = None,
) -> TrustChainRepairReport:
    """Apply the minimal mode repair to the chains named by ``findings``.

    Without ``consent`` nothing is touched and every request is refused as
    ``consent_required``. A finding whose chain is not in the registry, or
    whose root differs from the registered root, is refused as
    ``unregistered_chain``: findings are a request, never an authority.
    """

    requested = _requested_chains(findings)
    if not consent:
        return TrustChainRepairReport(
            consent=False,
            chains=tuple(_refused(request, "consent_required") for request in requested),
        )
    if not _POSIX:
        return TrustChainRepairReport(
            consent=True,
            chains=tuple(_refused(request, "not_applicable") for request in requested),
        )
    registry: dict[tuple[str, str, str, str], TrustChain] = {}
    for selected in dict.fromkeys(request[0] for request in requested):
        if selected not in TRUST_CHAIN_HOSTS:
            continue
        for chain in known_trust_chains(
            selected,
            home_dir=home_dir,
            executables=executables,
            resolver=resolver,
        ):
            if chain.available:
                registry[(chain.host, chain.name, chain.path_class, str(chain.root))] = chain
    uid = _effective_uid()
    seen: set[tuple[int, int]] = set()
    repairs = [
        _repair_chain(registry[request], uid=uid, seen=seen)
        if request in registry
        else _refused(request, "unregistered_chain")
        for request in requested
    ]
    return TrustChainRepairReport(consent=True, chains=tuple(repairs))


__all__ = [
    "BREAK_KINDS",
    "POLICY_EXECUTABLE",
    "POLICY_PRIVATE",
    "TRUST_CHAIN_HOSTS",
    "TrustChain",
    "TrustChainFinding",
    "TrustChainRepair",
    "TrustChainRepairReport",
    "known_trust_chains",
    "repair_trust_chains",
    "scan_trust_chains",
]
