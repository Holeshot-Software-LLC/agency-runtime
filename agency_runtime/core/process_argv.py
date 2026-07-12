"""Cross-platform argv preparation that rejects unsafe Windows batch shims."""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable, Sequence
from pathlib import Path


BinaryResolver = Callable[[str], str | None]


def _trusted_npm_companion(
    shim: Path,
    resolver: BinaryResolver,
) -> list[str] | None:
    """Resolve allowlisted npm CLIs without sending stdin through PowerShell."""

    command = shim.stem.casefold()
    npm_root = shim.parent
    if command == "codex":
        native_candidates = [
            npm_root
            / "node_modules"
            / "@openai"
            / "codex"
            / "node_modules"
            / "@openai"
            / package
            / "vendor"
            / target
            / "bin"
            / "codex.exe"
            for package, target in (
                ("codex-win32-x64", "x86_64-pc-windows-msvc"),
                ("codex-win32-arm64", "aarch64-pc-windows-msvc"),
            )
        ]
        native_candidates.extend(
            npm_root
            / "node_modules"
            / "@openai"
            / package
            / "vendor"
            / target
            / "bin"
            / "codex.exe"
            for package, target in (
                ("codex-win32-x64", "x86_64-pc-windows-msvc"),
                ("codex-win32-arm64", "aarch64-pc-windows-msvc"),
            )
        )
        native = next((path for path in native_candidates if path.is_file()), None)
        if native is not None:
            return [str(native)]
        script = npm_root / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
    elif command == "claude":
        script = (
            npm_root
            / "node_modules"
            / "@anthropic-ai"
            / "claude-code"
            / "cli.js"
        )
    else:
        return None

    if not script.is_file():
        return None
    sibling_node = npm_root / "node.exe"
    node = str(sibling_node) if sibling_node.is_file() else resolver("node.exe")
    return [node, str(script)] if node else None


def prepare_process_argv(
    argv: Sequence[str],
    *,
    platform_name: str | None = None,
    resolver: BinaryResolver | None = None,
) -> list[str]:
    """Resolve argv[0] and never send user arguments through cmd.exe."""

    if isinstance(argv, (str, bytes)) or not argv:
        raise TypeError("argv must be a non-empty sequence of strings")
    process_argv = [str(part) for part in argv]
    if any(not part or "\x00" in part for part in process_argv):
        raise ValueError("argv contains an invalid item")
    binary_resolver = resolver or shutil.which
    resolved = binary_resolver(process_argv[0])
    if not resolved:
        raise FileNotFoundError(f"executable not found: {process_argv[0]}")
    process_argv[0] = resolved
    if (platform_name or os.name) != "nt":
        return process_argv

    shim = Path(resolved)
    suffix = shim.suffix.casefold()
    if suffix in {".cmd", ".bat"}:
        native = shim.with_suffix(".exe")
        if native.is_file():
            return [str(native), *process_argv[1:]]
        npm_companion = _trusted_npm_companion(shim, binary_resolver)
        if npm_companion is not None:
            return [*npm_companion, *process_argv[1:]]
        powershell_shim = shim.with_suffix(".ps1")
        if powershell_shim.is_file():
            return [
                "powershell.exe",
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(powershell_shim),
                *process_argv[1:],
            ]
        raise OSError(
            "refusing unsafe cmd.exe shim invocation without .exe or .ps1 "
            f"companion: {shim}"
        )
    if suffix == ".ps1":
        return [
            "powershell.exe",
            "-NoLogo",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            *process_argv,
        ]
    return process_argv


__all__ = ["BinaryResolver", "prepare_process_argv"]
