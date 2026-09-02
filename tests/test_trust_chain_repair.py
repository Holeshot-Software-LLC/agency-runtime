"""AR-358: installers leave their known trust chains trusted; doctor repairs them.

The three break shapes here were each measured during the 2026-09-01 deploy and
each cost an operator a forensic session: the Claude Code npm self-update left
its package tree group-writable, `npm install -g openclaw` left the OpenClaw
tree group-writable, and `claude plugin update` recreated plugin cache
directories that were not owner-private. The repair is deliberately narrow --
only registered chains, only entries this account owns, only the minimal mode
change, never through a link -- so these tests pin the refusals as hard as the
repairs.
"""

from __future__ import annotations

import os
import stat
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime.core import doctor
from agency_runtime.core import trust_chain_repair as subject

pytestmark = pytest.mark.skipif(os.name == "nt", reason="POSIX mode bits only")


def _mode(path: Path) -> int:
    return stat.S_IMODE(path.lstat().st_mode)


def _npm_tree(home: Path, package: str, binary: str) -> Path:
    """Build the npm layout an installed host executable really resolves into."""

    root = home / ".npm-global" / "lib" / "node_modules"
    parts = package.split("/")
    tree = root.joinpath(*parts)
    (tree / "cli").mkdir(parents=True)
    executable = tree / "cli" / binary
    executable.write_text("#!/usr/bin/env node\n", encoding="utf-8")
    executable.chmod(0o755)
    return tree


def _claude_home(home: Path) -> Path:
    plugins = home / ".claude" / "plugins" / "cache"
    plugins.mkdir(parents=True)
    (plugins / "agency").mkdir()
    return home / ".claude" / "plugins"


def _kinds(findings: list[subject.TrustChainFinding], chain: str) -> set[str]:
    return {finding.kind for finding in findings if finding.chain == chain}


def test_the_claude_npm_self_update_break_is_found_and_repaired(tmp_path: Path) -> None:
    tree = _npm_tree(tmp_path, "@anthropic-ai/claude-code", "claude")
    _claude_home(tmp_path)
    # The measured shape: the auto-updater rewrote the tree group-writable.
    for path in [tree, tree / "cli", tree / "cli" / "claude"]:
        path.chmod(_mode(path) | stat.S_IWGRP)
    executables = {"claude": str(tree / "cli" / "claude")}

    findings = subject.scan_trust_chains("claude", home_dir=tmp_path, executables=executables)

    assert "group_writable" in _kinds(findings, "claude_npm_tree")
    report = subject.repair_trust_chains(
        findings, consent=True, home_dir=tmp_path, executables=executables
    )
    assert report.ok and report.applied
    assert report.changed >= 3
    for path in [tree, tree / "cli", tree / "cli" / "claude"]:
        assert not _mode(path) & stat.S_IWGRP
    assert subject.scan_trust_chains("claude", home_dir=tmp_path, executables=executables) == []


def test_the_openclaw_global_install_break_is_found_and_repaired(tmp_path: Path) -> None:
    tree = _npm_tree(tmp_path, "openclaw", "openclaw")
    entry = tree / "openclaw.mjs"
    entry.write_text("export default 1;\n", encoding="utf-8")
    entry.chmod(0o775)
    executables = {"openclaw": str(tree / "cli" / "openclaw")}

    findings = subject.scan_trust_chains("openclaw", home_dir=tmp_path, executables=executables)

    assert "group_writable" in _kinds(findings, "openclaw_npm_tree")
    subject.repair_trust_chains(findings, consent=True, home_dir=tmp_path, executables=executables)
    assert _mode(entry) == 0o755
    assert subject.scan_trust_chains("openclaw", home_dir=tmp_path, executables=executables) == []


def test_the_plugin_cache_break_requires_owner_private_directories(tmp_path: Path) -> None:
    plugins = _claude_home(tmp_path)
    # `claude plugin update` recreated the cache directories world-readable.
    (plugins / "cache").chmod(0o755)
    (plugins / "cache" / "agency").chmod(0o750)

    findings = subject.scan_trust_chains("claude", home_dir=tmp_path, executables={"claude": None})

    assert _kinds(findings, "claude_plugins") == {"final_dir_not_private"}
    subject.repair_trust_chains(
        findings, consent=True, home_dir=tmp_path, executables={"claude": None}
    )
    assert _mode(plugins / "cache") == 0o700
    assert _mode(plugins / "cache" / "agency") == 0o700


def test_a_group_writable_ancestor_breaks_the_chain_and_is_repaired(tmp_path: Path) -> None:
    tree = _npm_tree(tmp_path, "openclaw", "openclaw")
    ancestor = tmp_path / ".npm-global"
    ancestor.chmod(0o775)
    executables = {"openclaw": str(tree / "cli" / "openclaw")}

    findings = subject.scan_trust_chains("openclaw", home_dir=tmp_path, executables=executables)

    assert "group_writable" in _kinds(findings, "openclaw_npm_tree")
    subject.repair_trust_chains(findings, consent=True, home_dir=tmp_path, executables=executables)
    assert not _mode(ancestor) & stat.S_IWGRP
    # The home boundary itself is never a chain member, so it is never touched.
    assert not any(str(tmp_path) == finding.root for finding in findings)


def test_repair_refuses_without_consent_and_outside_the_registry(tmp_path: Path) -> None:
    tree = _npm_tree(tmp_path, "openclaw", "openclaw")
    tree.chmod(_mode(tree) | stat.S_IWGRP)
    executables = {"openclaw": str(tree / "cli" / "openclaw")}
    findings = subject.scan_trust_chains("openclaw", home_dir=tmp_path, executables=executables)
    assert findings

    refused = subject.repair_trust_chains(
        findings, consent=False, home_dir=tmp_path, executables=executables
    )
    assert refused.applied is False
    assert [repair.refused for repair in refused.chains] == ["consent_required"]
    assert _mode(tree) & stat.S_IWGRP

    # A finding is a request, never an authority: a root outside the registry
    # is refused even with consent.
    outside = tmp_path / "outside"
    outside.mkdir()
    outside.chmod(0o777)  # mkdir's mode is masked by umask; chmod is not
    forged = subject.TrustChainFinding(
        host="openclaw",
        chain="openclaw_npm_tree",
        path_class="npm_package",
        root=str(outside),
        kind="group_writable",
        count=1,
        scanned=1,
        unowned=0,
        truncated=False,
    )
    report = subject.repair_trust_chains(
        [forged], consent=True, home_dir=tmp_path, executables=executables
    )
    assert [repair.refused for repair in report.chains] == ["unregistered_chain"]
    assert _mode(outside) == 0o777


def test_a_symlinked_entry_is_never_chmod_ed_through(tmp_path: Path) -> None:
    tree = _npm_tree(tmp_path, "openclaw", "openclaw")
    victim = tmp_path / "victim"
    victim.mkdir()
    victim.chmod(0o777)
    (tree / "link").symlink_to(victim, target_is_directory=True)
    executables = {"openclaw": str(tree / "cli" / "openclaw")}

    findings = subject.scan_trust_chains("openclaw", home_dir=tmp_path, executables=executables)
    subject.repair_trust_chains(findings, consent=True, home_dir=tmp_path, executables=executables)

    # The link is neither classified nor descended, so the target keeps its mode.
    assert _mode(victim) == 0o777


def test_an_executable_outside_its_npm_package_registers_no_chain(tmp_path: Path) -> None:
    stray = tmp_path / "bin" / "openclaw"
    stray.parent.mkdir(parents=True)
    stray.write_text("#!/bin/sh\n", encoding="utf-8")

    chains = subject.known_trust_chains(
        "openclaw", home_dir=tmp_path, executables={"openclaw": str(stray)}
    )

    assert chains == ()
    with pytest.raises(ValueError, match="no trust chains are registered"):
        subject.known_trust_chains("hermes", home_dir=tmp_path)


def test_doctor_lists_breaks_and_repairs_them_only_with_consent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tree = _npm_tree(tmp_path, "openclaw", "openclaw")
    tree.chmod(_mode(tree) | stat.S_IWGRP)
    executables = {"openclaw": str(tree / "cli" / "openclaw")}

    # Bind the real functions before patching, or the doubles call themselves.
    real_scan = subject.scan_trust_chains
    real_repair = subject.repair_trust_chains

    def _scan(*_args: object, **_kwargs: object) -> list[subject.TrustChainFinding]:
        return real_scan("openclaw", home_dir=tmp_path, executables=executables)

    def _repair(findings: object, **kwargs: object) -> subject.TrustChainRepairReport:
        return real_repair(
            findings,  # type: ignore[arg-type]
            consent=bool(kwargs.get("consent")),
            home_dir=tmp_path,
            executables=executables,
        )

    monkeypatch.setattr(subject, "scan_trust_chains", _scan)
    monkeypatch.setattr(subject, "repair_trust_chains", _repair)

    listed = doctor._trust_chain_checks(fix_perms=False)
    assert [check.status for check in listed] == ["warn"]
    assert "agency doctor --fix-perms" in listed[0].detail
    assert _mode(tree) & stat.S_IWGRP

    repaired = doctor._trust_chain_checks(fix_perms=True)
    assert [check.status for check in repaired] == ["pass"]
    assert not _mode(tree) & stat.S_IWGRP
    assert doctor._trust_chain_checks(fix_perms=False)[0].status == "pass"


def test_doctor_cli_passes_consent_through(monkeypatch: pytest.MonkeyPatch) -> None:
    from agency_runtime.cli import config_commands

    seen: dict[str, object] = {}

    def _run_doctor(_cfg: object, *, fix_perms: bool = False) -> object:
        seen["fix_perms"] = fix_perms
        return SimpleNamespace(
            to_dict=lambda: {"status": "HEALTHY", "exit_code": 0, "checks": []},
            exit_code=0,
        )

    monkeypatch.setattr(config_commands, "run_doctor", _run_doctor)
    dependencies = SimpleNamespace(load_config=lambda: object())

    assert (
        config_commands.cmd_doctor(
            Namespace(json=True, verbose=False, fix_perms=True),
            dependencies=dependencies,  # type: ignore[arg-type]
        )
        == 0
    )
    assert seen["fix_perms"] is True

    config_commands.cmd_doctor(
        Namespace(json=True, verbose=False, fix_perms=False),
        dependencies=dependencies,  # type: ignore[arg-type]
    )
    assert seen["fix_perms"] is False


def test_an_executing_probe_normalizes_the_chain_first(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AR-368: the host rewrites its own tree, so the probe must repair first.

    Claude Code chmods its npm package tree group-writable on every
    invocation (measured 2026-09-02: the tree's ctime moved to each probe),
    so an install-time repair is already undone by the time the canary reads
    the chain. Normalization therefore runs immediately before the executing
    probe, and only when the caller asked for it.
    """

    from agency_runtime.core import installer_inventory

    tree = _npm_tree(tmp_path, "openclaw", "openclaw")
    tree.chmod(_mode(tree) | stat.S_IWGRP)
    executable = str(tree / "cli" / "openclaw")
    observed: list[int] = []

    def _probe(state: object, **_kwargs: object) -> None:
        observed.append(_mode(tree))

    monkeypatch.setattr(installer_inventory, "_probe_native_host", _probe)

    evidence = installer_inventory._normalized_chain_evidence("openclaw", executable, tmp_path)
    assert evidence is not None and evidence.startswith("trust-chain:normalized:")
    assert not _mode(tree) & stat.S_IWGRP
    # A clean chain records nothing; there is no repair to report.
    assert installer_inventory._normalized_chain_evidence("openclaw", executable, tmp_path) is None
    # A host with no registered chains is never touched.
    assert installer_inventory._normalized_chain_evidence("codex", executable, tmp_path) is None


def test_a_read_only_inspection_never_chmods(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`agency status` and `doctor` inspect; only the canary opts into repair."""

    from agency_runtime.core import installer_inventory

    calls: list[tuple[str, str | None]] = []

    def _record(host: str, executable: str | None, _home: object) -> str | None:
        calls.append((host, executable))
        return "trust-chain:normalized:1"

    monkeypatch.setattr(installer_inventory, "_normalized_chain_evidence", _record)
    monkeypatch.setattr(installer_inventory, "_can_execute_native", lambda **_kwargs: True)
    monkeypatch.setattr(installer_inventory, "_probe_native_host", lambda *_a, **_k: None)

    installer_inventory.inspect_host_installations(home_dir=tmp_path, hosts=["openclaw"])
    assert calls == []
