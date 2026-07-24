"""Generated host plugin payloads and install-time configuration."""

from __future__ import annotations

import math
import shlex
import sys
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import replace
from pathlib import Path
from typing import Any

from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.configuration_persistence import resolve_config_path
from agency_runtime.core.installer_contracts import (
    HOOK_TIMEOUT_BUFFER_SECONDS,
    MAX_HOOK_TIMEOUT_SECONDS,
)
from agency_runtime.core.installer_payload_hermes import render_hermes_plugin
from agency_runtime.core.installer_payload_manifests import (
    build_claude_bundle,
    build_codex_bundle,
    build_hermes_bundle,
    build_openclaw_bundle,
    render_codex_plugin_version,
)
from agency_runtime.core.installer_payload_openclaw import render_openclaw_index
from agency_runtime.core.process_argv import (
    absolute_executable_path,
    agency_bootstrap_path,
)

_BOUND_LAUNCHER_ARTIFACTS: ContextVar[tuple[str, str] | None] = ContextVar(
    "agency_bound_launcher_artifacts",
    default=None,
)


def _facade():
    """Resolve facade dependencies at call time for monkeypatch compatibility."""

    from agency_runtime.core import installer

    return installer


def _runtime_home(*args: Any, **kwargs: Any) -> Path:
    return _facade()._runtime_home(*args, **kwargs)


def _bundle_digest(*args: Any, **kwargs: Any) -> str:
    return _facade()._bundle_digest(*args, **kwargs)


def _hook_timeout_seconds(*args: Any, **kwargs: Any) -> int:
    return _facade()._hook_timeout_seconds(*args, **kwargs)


def _python_commands(*args: Any, **kwargs: Any) -> tuple[str, str]:
    return _facade()._python_commands(*args, **kwargs)


def _effective_judge_budget_seconds(*args: Any, **kwargs: Any) -> float:
    return _facade()._effective_judge_budget_seconds(*args, **kwargs)


def _mcp_config(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _facade()._mcp_config(*args, **kwargs)


def _codex_hooks(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _facade()._codex_hooks(*args, **kwargs)


def _claude_hooks(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _facade()._claude_hooks(*args, **kwargs)


def _zcode_hooks(*args: Any, **kwargs: Any) -> dict[str, Any]:
    return _facade()._zcode_hooks(*args, **kwargs)


def _agency_control_skill(*args: Any, **kwargs: Any) -> str:
    return _facade()._agency_control_skill(*args, **kwargs)


def _openclaw_index(*args: Any, **kwargs: Any) -> str:
    return _facade()._openclaw_index(*args, **kwargs)


def _codex_plugin_version(*args: Any, **kwargs: Any) -> str:
    return _facade()._codex_plugin_version(*args, **kwargs)


def _powershell_literal(value: str) -> str:
    """Render one inert PowerShell string literal."""

    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def python_commands(module: str, *args: str) -> tuple[str, str]:
    argv = runtime_python_argv(module, *args)
    posix = " ".join(shlex.quote(part) for part in argv)
    # Codex executes commandWindows through the selected Windows shell. Its
    # native PowerShell environment needs the call operator when argv[0] is a
    # quoted path; single-quoted literals keep metacharacters inert.
    windows = "& " + " ".join(_powershell_literal(part) for part in argv)
    return posix, windows


def launcher_artifact_paths() -> tuple[str, str]:
    """Return the exact interpreter and bootstrap persisted by every adapter."""

    if bound := _BOUND_LAUNCHER_ARTIFACTS.get():
        return bound
    return absolute_executable_path(sys.executable), agency_bootstrap_path()


@contextmanager
def bind_launcher_artifact_paths(paths: tuple[str, str]) -> Iterator[None]:
    """Bind one already-attested launcher pair during deterministic rendering."""

    if not isinstance(paths, tuple) or len(paths) != 2:
        raise ValueError("launcher artifact binding requires two paths")
    bound = tuple(absolute_executable_path(path) for path in paths)
    token = _BOUND_LAUNCHER_ARTIFACTS.set(bound)
    try:
        yield
    finally:
        _BOUND_LAUNCHER_ARTIFACTS.reset(token)


def runtime_python_argv(module: str, *args: str) -> list[str]:
    """Build the exact isolated argv shared by payloads and fingerprints."""

    python_executable, bootstrap_path = launcher_artifact_paths()
    return [python_executable, "-I", "-S", bootstrap_path, module, *args]


def resolve_install_config(
    cfg: AgencyConfig | None,
    *,
    home_dir: str | Path | None,
) -> AgencyConfig:
    if cfg is not None:
        return cfg
    if home_dir is not None:
        return _facade().load_config(_runtime_home(home_dir=home_dir) / "agency.yaml", reload=True)
    return _facade().load_config(reload=True)


def effective_judge_budget_seconds(cfg: AgencyConfig) -> float:
    """Conservatively bound every sequential inference path in one hook."""
    budgets = [
        max(0.0, float(provider.timeout))
        for provider in cfg.providers
        if (
            (provider.model and provider.base_url)
            or (
                provider.type.strip().lower() == "cli"
                and provider.transport.strip().lower() in {"codex", "claude"}
            )
        )
    ]
    if cfg.judge.model and cfg.judge.base_url:
        budgets.append(max(0.0, float(cfg.judge.timeout)))
    if cfg.ollama.enabled and cfg.ollama.model:
        budgets.append(max(0.0, float(cfg.judge.timeout)))
    selector_budget = max(max(0.0, float(cfg.judge.timeout)), sum(budgets))
    workforce_calls = {
        "fast": cfg.workforce.fast_call_budget,
        "balanced": cfg.workforce.balanced_call_budget,
        "strict": cfg.workforce.strict_call_budget,
    }[cfg.workforce.mode]
    workforce_provider_timeouts = [
        max(0.0, float(provider.timeout))
        for provider in cfg.providers
        if (
            (provider.model and provider.base_url)
            or (
                provider.type.strip().lower() == "cli"
                and provider.transport.strip().lower() in {"codex", "claude"}
            )
        )
    ]
    if not workforce_provider_timeouts and (
        (cfg.judge.model and cfg.judge.base_url) or (cfg.ollama.enabled and cfg.ollama.model)
    ):
        workforce_provider_timeouts = [max(0.0, float(cfg.judge.timeout))]
    workforce_budget = (
        workforce_calls * max(workforce_provider_timeouts) if workforce_provider_timeouts else 0.0
    )
    return max(selector_budget, workforce_budget)


def hook_timeout_seconds(cfg: AgencyConfig) -> int:
    requested = math.ceil(_effective_judge_budget_seconds(cfg) + HOOK_TIMEOUT_BUFFER_SECONDS)
    # OpenClaw permits at most 600 seconds and the generated bridge reserves a
    # two-second host margin. Normal schema-validated configs remain well below
    # this cap; it protects programmatic callers that construct AgencyConfig
    # directly without passing through the config validator.
    return min(MAX_HOOK_TIMEOUT_SECONDS, max(1, requested))


def _bound_config_path(cfg: AgencyConfig) -> str:
    """Return the validated durable config identity embedded in a host bundle."""

    if not cfg.config_path:
        return ""
    return str(resolve_config_path(cfg.config_path, use_environment=False))


def _config_args(config_path: str) -> tuple[str, ...]:
    return ("--config", config_path) if config_path else ()


def _runtime_control_args(control_path: str) -> tuple[str, ...]:
    return ("--runtime-control", control_path) if control_path else ()


def mcp_config(config_path: str = "") -> dict[str, Any]:
    argv = runtime_python_argv(
        "agency_runtime.server.mcp",
        "--stdio",
        *_config_args(config_path),
    )
    return {
        "mcpServers": {
            "agency-runtime": {
                "command": argv[0],
                "args": argv[1:],
            }
        }
    }


def codex_hooks(
    timeout_seconds: int,
    config_path: str = "",
    runtime_control_path_value: str = "",
) -> dict[str, Any]:
    def handler(event: str, status_message: str) -> dict[str, Any]:
        command, command_windows = _python_commands(
            "agency_runtime.cli",
            "hook",
            "codex",
            "--event",
            event,
            *_config_args(config_path),
            *_runtime_control_args(runtime_control_path_value),
        )
        return {
            "type": "command",
            "command": command,
            "commandWindows": command_windows,
            "async": False,
            "timeout": timeout_seconds,
            "statusMessage": status_message,
        }

    return {
        "hooks": {
            "SessionStart": [
                {"hooks": [handler("SessionStart", "Loading Agency Runtime managers")]}
            ],
            "UserPromptSubmit": [
                {"hooks": [handler("UserPromptSubmit", "Routing with Agency Runtime")]}
            ],
            "PreToolUse": [
                {
                    "matcher": "spawn_agent",
                    "hooks": [
                        handler(
                            "PreToolUse",
                            "Binding exact Agency specialist to native child",
                        )
                    ],
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "*",
                    "hooks": [handler("PostToolUse", "Recording Agency Runtime evidence")],
                }
            ],
            "SubagentStart": [
                {"hooks": [handler("SubagentStart", "Binding Agency child identity")]}
            ],
            "SubagentStop": [
                {"hooks": [handler("SubagentStop", "Recording Agency child lifecycle")]}
            ],
            "PostCompact": [
                {"hooks": [handler("PostCompact", "Restoring Agency Runtime managers")]}
            ],
            "Stop": [{"hooks": [handler("Stop", "Checking Agency Runtime response contract")]}],
        }
    }


def claude_hooks(
    timeout_seconds: int,
    config_path: str = "",
    runtime_control_path_value: str = "",
) -> dict[str, Any]:
    base_argv = runtime_python_argv("agency_runtime.cli")

    def handler(event: str) -> dict[str, Any]:
        return {
            "type": "command",
            "command": base_argv[0],
            "args": [
                *base_argv[1:],
                "hook",
                "claude",
                "--event",
                event,
                *_config_args(config_path),
                *_runtime_control_args(runtime_control_path_value),
            ],
            "timeout": timeout_seconds,
        }

    return {
        "hooks": {
            "SessionStart": [{"hooks": [handler("SessionStart")]}],
            "UserPromptSubmit": [{"hooks": [handler("UserPromptSubmit")]}],
            "PreToolUse": [{"matcher": "Agent", "hooks": [handler("PreToolUse")]}],
            "PostToolUse": [{"matcher": "*", "hooks": [handler("PostToolUse")]}],
            "PostToolUseFailure": [{"matcher": "*", "hooks": [handler("PostToolUseFailure")]}],
            "SubagentStart": [{"hooks": [handler("SubagentStart")]}],
            "SubagentStop": [{"hooks": [handler("SubagentStop")]}],
            "PostCompact": [{"hooks": [handler("PostCompact")]}],
            "Stop": [{"hooks": [handler("Stop")]}],
            "SessionEnd": [{"hooks": [handler("SessionEnd")]}],
        }
    }


def zcode_hooks(
    timeout_seconds: int,
    config_path: str = "",
    runtime_control_path_value: str = "",
) -> dict[str, Any]:
    """ZCode hook registration (same event model as Codex, Agent-tool like Claude).

    ZCode supports exactly seven hook events: SessionStart, UserPromptSubmit,
    PreToolUse, PermissionRequest, PostToolUse, PostToolUseFailure, Stop.
    It does NOT support SubagentStart/SubagentStop/PostCompact/SessionEnd.
    Native children spawn via the Agent tool (same as Claude), so PreToolUse
    matches on "Agent". ZCode hooks live in ~/.zcode/cli/config.json under the
    "hooks" key (or workspace .zcode/config.json) and must set enabled: true.
    """

    def handler(event: str, status_message: str) -> dict[str, Any]:
        command, command_windows = _python_commands(
            "agency_runtime.cli",
            "hook",
            "zcode",
            "--event",
            event,
            *_config_args(config_path),
            *_runtime_control_args(runtime_control_path_value),
        )
        return {
            "type": "command",
            "command": command,
            "commandWindows": command_windows,
            "async": False,
            "timeout": timeout_seconds,
            "statusMessage": status_message,
        }

    return {
        "hooks": {
            "SessionStart": [
                {"hooks": [handler("SessionStart", "Loading Agency Runtime managers")]}
            ],
            "UserPromptSubmit": [
                {"hooks": [handler("UserPromptSubmit", "Routing with Agency Runtime")]}
            ],
            "PreToolUse": [
                {
                    "matcher": "Agent",
                    "hooks": [
                        handler("PreToolUse", "Binding exact Agency specialist to native child")
                    ],
                }
            ],
            "PostToolUse": [
                {
                    "matcher": "*",
                    "hooks": [handler("PostToolUse", "Recording Agency Runtime evidence")],
                }
            ],
            "Stop": [{"hooks": [handler("Stop", "Checking Agency Runtime response contract")]}],
        }
    }


def agency_control_skill(host: str) -> str:
    """Build the host-aware conversation control skill for Codex and Claude."""
    from agency_runtime.core.runtime_control_command import (
        RUNTIME_CONTROL_CONVERSATION_FORMS,
    )

    forms = ", ".join(f"`{form}`" for form in RUNTIME_CONTROL_CONVERSATION_FORMS)
    return f"""---
name: agency
description: Inspect, enable, or disable Agency Runtime for this host.
---

# Agency Runtime control

Handle only these exact conversation forms: {forms}. Punctuation, extra text,
and broad words such as `status`, `ping`, or `heartbeat` are ordinary user
requests, not runtime controls.

- For status, call `agency.host_status` with `host` set to `{host}`.
- For on or off, first call `agency.host_status` immediately before the
  mutation and read its exact `runtime_control_generation`.
- For on, call `agency.host_control` with `host` set to `{host}`, `enabled`
  set to `true`, `expected_generation` set to that exact generation, and
  `confirm` set exactly to `ENABLE {host}`.
- For off, call `agency.host_control` with `host` set to `{host}`, `enabled`
  set to `false`, `expected_generation` set to that exact generation, and
  `confirm` set exactly to `DISABLE {host}`.

Report the returned soft-control state. Do not claim that native plugin
registration changed, and do not claim a live canary unless the returned
evidence explicitly proves one. If the mutation reports a generation conflict,
report the current state instead of retrying with an unverified value.
"""


def hermes_plugin(timeout_seconds: int, cfg: AgencyConfig) -> str:
    """Render a stdlib-only bridge bound to the installed Agency interpreter."""

    python_executable, bootstrap_path = launcher_artifact_paths()
    return render_hermes_plugin(
        timeout_seconds,
        cfg,
        python_executable=python_executable,
        bootstrap_path=bootstrap_path,
    )


def openclaw_index(timeout_seconds: int, config_path: str = "") -> str:
    python_executable, bootstrap_path = launcher_artifact_paths()
    return render_openclaw_index(
        timeout_seconds,
        python_executable=python_executable,
        bootstrap_path=bootstrap_path,
        config_path=config_path,
    )


def codex_plugin_version(
    manifest: Mapping[str, Any],
    component_files: Mapping[str, str],
) -> str:
    return render_codex_plugin_version(
        manifest,
        component_files,
        bundle_digest=_bundle_digest,
    )


def bundle_files(
    host: str,
    cfg: AgencyConfig | None = None,
    *,
    runtime_control_path_value: str = "",
) -> tuple[dict[str, str], str]:
    effective_cfg = cfg or AgencyConfig()
    config_path = _bound_config_path(effective_cfg)
    if config_path and effective_cfg.config_path != config_path:
        effective_cfg = replace(effective_cfg, config_path=config_path)
    timeout_seconds = _hook_timeout_seconds(effective_cfg)
    if host == "hermes":
        return build_hermes_bundle(hermes_plugin(timeout_seconds, effective_cfg))

    if host == "openclaw":
        index = (
            _openclaw_index(timeout_seconds, config_path)
            if config_path
            else _openclaw_index(timeout_seconds)
        )
        return build_openclaw_bundle(index)

    if host == "codex":
        hooks = (
            _codex_hooks(timeout_seconds, config_path, runtime_control_path_value)
            if config_path or runtime_control_path_value
            else _codex_hooks(timeout_seconds)
        )
        mcp = _mcp_config(config_path) if config_path else _mcp_config()
        return build_codex_bundle(
            hooks=hooks,
            mcp=mcp,
            control_skill=_agency_control_skill("codex"),
            version_builder=_codex_plugin_version,
        )

    hooks = (
        _claude_hooks(timeout_seconds, config_path, runtime_control_path_value)
        if config_path or runtime_control_path_value
        else _claude_hooks(timeout_seconds)
    )
    mcp = _mcp_config(config_path) if config_path else _mcp_config()
    return build_claude_bundle(
        hooks=hooks,
        mcp=mcp,
        control_skill=_agency_control_skill("claude"),
    )
