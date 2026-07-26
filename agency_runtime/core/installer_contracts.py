"""Stable data contracts and host metadata shared by installer modules."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

PLUGIN_ID = "agency-preflight"
MARKETPLACE_ID = "agency-runtime"
INSTALL_MANIFEST = ".agency-runtime-install.json"
ADAPTER_LAUNCHER_MANIFEST = ".agency-runtime-launcher.json"
PLUGIN_VERSION = "0.1.0"
MINIMUM_OPENCLAW_VERSION = "2026.7.1"
OPENCLAW_REQUIRED_HOOKS = frozenset(
    {
        "gateway_start",
        "before_agent_run",
        "before_prompt_build",
        "model_call_ended",
        "after_tool_call",
        "subagent_spawned",
        "subagent_ended",
        "before_agent_finalize",
        "reply_payload_sending",
        "message_sending",
    }
)
HOOK_TIMEOUT_BUFFER_SECONDS = 5.0
MAX_HOOK_TIMEOUT_SECONDS = 595
MAX_NATIVE_OUTPUT_CHARS = 256 * 1024
CODEX_HOOK_TRUST_SURFACE = "codex-terminal-tui"
CODEX_HOOK_TRUST_COMMAND = "codex"
CODEX_HOOK_TRUST_ACTION = (
    "Open a terminal and run `codex`. In the Codex terminal TUI, choose "
    "`Trust all and continue` when the startup review lists the seven Agency "
    "Runtime hook events; if it does not appear, run `/hooks` inside that "
    "terminal TUI. Codex Desktop's `/hooks` screen manages connector setup and "
    "is not the local command-hook trust screen. Then start a new session and "
    "run `agency install --agent codex --verify-activation`."
)
_OPENCLAW_VERSION = re.compile(
    r"(?<!\d)(?P<year>\d{4})\.(?P<month>\d{1,2})\.(?P<patch>\d{1,9})"
    r"(?P<prerelease>-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?"
    r"(?![0-9A-Za-z.+-])"
)


def parse_openclaw_version(value: object) -> tuple[int, int, int] | None:
    """Parse one stable date-version without accepting prerelease capability drift."""

    match = _OPENCLAW_VERSION.search(str(value or ""))
    if match is None or match.group("prerelease"):
        return None
    return tuple(int(match.group(name)) for name in ("year", "month", "patch"))


def openclaw_version_supported(value: object) -> bool:
    """Return whether the host is in the explicitly audited OpenClaw release line."""

    observed = parse_openclaw_version(value)
    minimum = tuple(int(part) for part in MINIMUM_OPENCLAW_VERSION.split("."))
    return observed is not None and observed[:2] == minimum[:2] and observed[2] >= minimum[2]


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
    "zcode": {
        "binary": "zcode",
        "root": "~/.zcode",
        "current_markers": ["v2/config.json", "cli/config.json"],
        "plugin_dir": "~/.agency-runtime/host-plugins/zcode/agency-preflight",
        "native_lifecycle": "zcode config hooks",
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
