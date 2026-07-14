"""Stable data contracts and host metadata shared by installer modules."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

PLUGIN_ID = "agency-preflight"
MARKETPLACE_ID = "agency-runtime"
INSTALL_MANIFEST = ".agency-runtime-install.json"
PLUGIN_VERSION = "0.1.0"
HOOK_TIMEOUT_BUFFER_SECONDS = 5.0
MAX_HOOK_TIMEOUT_SECONDS = 595
MAX_NATIVE_OUTPUT_CHARS = 256 * 1024
CODEX_HOOK_TRUST_ACTION = (
    "Open Codex, run `/hooks`, review and trust the three Agency Runtime "
    "command hooks, then start a new session."
)


# ``HOSTS`` intentionally stays JSON-like because the dashboard and downstream
# callers treat it as public inventory metadata.
HOSTS: dict[str, dict[str, Any]] = {
    "hermes": {
        "binary": "hermes",
        "root": "~/.hermes",
        "current_markers": ["config.yaml", "config.yml"],
        "plugin_dir": "~/.hermes/plugins/agency-preflight",
        "native_lifecycle": "hermes plugins",
    },
    "openclaw": {
        "binary": "openclaw",
        "root": "~/.openclaw",
        "current_markers": ["openclaw.json", "state.db", "state.sqlite"],
        "plugin_dir": "~/.agency-runtime/host-plugins/openclaw/agency-preflight",
        "native_lifecycle": "openclaw plugins",
    },
    "codex": {
        "binary": "codex",
        "root": "~/.codex",
        "current_markers": ["config.toml", "auth.json", "state_5.sqlite"],
        "plugin_dir": "~/.agency-runtime/marketplaces/codex",
        "native_lifecycle": "codex plugin",
    },
    "claude": {
        "binary": "claude",
        "root": "~/.claude",
        "current_markers": [
            "settings.json",
            ".credentials.json",
            "plugins/known_marketplaces.json",
        ],
        "plugin_dir": "~/.agency-runtime/marketplaces/claude",
        "native_lifecycle": "claude plugin",
    },
}


BinaryResolver = Callable[[str], str | None]
CommandRunner = Callable[..., Any]


@dataclass(frozen=True)
class NativeCommandResult:
    """Normalized result from an injected or real native host command."""

    command: tuple[str, ...]
    returncode: int
    stdout: str = ""
    stderr: str = ""
    stdout_truncated: bool = False
    stderr_truncated: bool = False

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and not self.stdout_truncated and not self.stderr_truncated

    def to_dict(self, *, expose_output: bool = False) -> dict[str, Any]:
        result: dict[str, Any] = {
            "command": list(self.command),
            "returncode": self.returncode,
            "ok": self.ok,
            "stdout_truncated": self.stdout_truncated,
            "stderr_truncated": self.stderr_truncated,
        }
        if expose_output:
            result["stdout"] = self.stdout
            result["stderr"] = self.stderr
        elif not self.ok:
            result["error"] = (self.stderr or self.stdout or "native command failed").strip()[:500]
        return result
