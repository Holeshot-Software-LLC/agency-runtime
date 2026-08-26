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
from agency_runtime.core.configuration_contracts import ConfigValidationError
from agency_runtime.core.configuration_persistence import resolve_config_path
from agency_runtime.core.inference_profiles import (
    resolve as resolve_inference_route,
)
from agency_runtime.core.inference_profiles import (
    resolve_explicit_capability_route,
)
from agency_runtime.core.installer_contracts import (
    CODEX_HOOK_EVENTS,
    CODEX_NATIVE_CHILD_HOOK_MATCHER,
    HOOK_TIMEOUT_BUFFER_SECONDS,
    MAX_HOOK_TIMEOUT_SECONDS,
)
from agency_runtime.core.installer_payload_hermes import render_hermes_plugin
from agency_runtime.core.installer_payload_manifests import (
    build_claude_bundle,
    build_codex_bundle,
    build_hermes_bundle,
    build_openclaw_bundle,
    build_zcode_bundle,
    render_claude_plugin_version,
    render_codex_plugin_version,
)
from agency_runtime.core.installer_payload_openclaw import render_openclaw_index
from agency_runtime.core.process_argv import (
    absolute_executable_path,
    agency_bootstrap_path,
)
from agency_runtime.core.workforce.hybrid_recall import MAX_HYBRID_EMBEDDING_CALLS
from agency_runtime.core.workforce.planning_contracts import MAX_WORK_UNITS

_BOUND_LAUNCHER_ARTIFACTS: ContextVar[tuple[str, str] | None] = ContextVar(
    "agency_bound_launcher_artifacts",
    default=None,
)

_OPENCLAW_NATIVE_CHILD_JUDGE_CALLS = 2
_SELECTOR_MAX_JUDGE_DEADLINE_SECONDS = 60.0
_WORKFORCE_ROUTE_KEYS = (
    "workforce.planner",
    "workforce.recruiter",
)
_HIRING_ROUTE_KEYS = (
    "workforce.hiring",
    "workforce.hiring.critic",
    "workforce.hiring.security_review",
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


def _claude_plugin_version(*args: Any, **kwargs: Any) -> str:
    return _facade()._claude_plugin_version(*args, **kwargs)


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


def _legacy_workforce_timeout_seconds(cfg: AgencyConfig) -> float:
    """Return the longest static timeout in the runtime fallback chain."""

    providers = [
        provider
        for provider in cfg.providers
        if (
            (provider.model and provider.base_url)
            or (
                provider.type.strip().lower() == "cli"
                and provider.transport.strip().lower() in {"codex", "claude"}
            )
        )
    ]
    preferred = cfg.workforce.provider.strip().casefold()
    if preferred:
        providers = [provider for provider in providers if provider.name.casefold() == preferred]
    timeouts = [max(0.0, float(provider.timeout)) for provider in providers]
    if not timeouts and (
        cfg.judge.model and cfg.judge.base_url and (cfg.judge.api_key or cfg.judge.api_key_env)
    ):
        timeouts.append(max(0.0, float(cfg.judge.timeout)))
    return max(timeouts, default=0.0)


def _host_inference_budget_seconds(cfg: AgencyConfig, harness: str) -> float:
    """Bound static host-scoped workforce and optional recall inference.

    One workforce call budget is shared by planner, recruiter, repair, and
    critic stages. Each call may consume the longest profile reachable by the
    owning harness. Dense recall owns a separate fixed two-call budget, and
    every inferred gap may enter its own bounded hiring call budget. Resolution
    is config-only: environment overrides and live providers must not mutate an
    installed launcher budget.
    """

    normalized_harness = str(harness or "").strip().casefold()
    profile_timeouts: list[float] = []
    route_keys = _WORKFORCE_ROUTE_KEYS + (
        ("workforce.recruiter.critic",) if cfg.workforce.mode == "strict" else ()
    )
    for route_key in route_keys:
        try:
            resolution = resolve_inference_route(
                cfg,
                route_key,
                harness=normalized_harness,
            )
        except ConfigValidationError:
            continue
        profile_timeouts.append(max(0.0, float(resolution.provider.timeout)))

    workforce_calls = {
        "fast": cfg.workforce.fast_call_budget,
        "balanced": cfg.workforce.balanced_call_budget,
        "strict": cfg.workforce.strict_call_budget,
    }[cfg.workforce.mode]
    workforce_budget = workforce_calls * max(profile_timeouts, default=0.0)

    hiring_timeouts: list[float] = []
    hiring_fallback_reachable = False
    for route_key in _HIRING_ROUTE_KEYS:
        try:
            resolution = resolve_inference_route(
                cfg,
                route_key,
                harness=normalized_harness,
            )
        except ConfigValidationError:
            hiring_fallback_reachable = True
            continue
        hiring_timeouts.append(max(0.0, float(resolution.provider.timeout)))
    if hiring_fallback_reachable:
        fallback_timeout = _legacy_workforce_timeout_seconds(cfg)
        if fallback_timeout:
            hiring_timeouts.append(fallback_timeout)
    maximum_gap_attempts = min(cfg.workforce.max_work_units, MAX_WORK_UNITS)
    hiring_budget = (
        maximum_gap_attempts * cfg.workforce.hiring_call_budget * max(hiring_timeouts, default=0.0)
    )

    recall_budget = 0.0
    if cfg.workforce.dense_recall_mode != "off":
        try:
            embedding = resolve_explicit_capability_route(
                cfg,
                "workforce.recall.embedding",
                capability_class="embeddings",
                harness=normalized_harness,
            )
            reranker = resolve_explicit_capability_route(
                cfg,
                "workforce.recall.reranker",
                capability_class="text",
                harness=normalized_harness,
            )
        except ConfigValidationError:
            embedding = None
            reranker = None
        if embedding is not None and reranker is not None:
            recall_budget = MAX_HYBRID_EMBEDDING_CALLS * max(
                0.0, float(embedding.provider.timeout)
            ) + max(0.0, float(reranker.provider.timeout))

    # Keep the legacy/provider-chain calculation as a floor for stages that
    # have no explicit profile. Recall is a separate path and therefore sits
    # outside that maximum rather than disappearing when the legacy floor is
    # longer than the host profile budget.
    return (
        max(_effective_judge_budget_seconds(cfg), workforce_budget) + recall_budget + hiring_budget
    )


def hook_timeout_seconds(cfg: AgencyConfig, *, harness: str = "") -> int:
    inference_budget = (
        _host_inference_budget_seconds(cfg, harness)
        if harness
        else _effective_judge_budget_seconds(cfg)
    )
    requested = math.ceil(inference_budget + HOOK_TIMEOUT_BUFFER_SECONDS)
    # OpenClaw permits at most 600 seconds and the generated bridge reserves a
    # two-second host margin. Complete workforce and hiring envelopes may reach
    # this ceiling; it also protects programmatic callers that construct
    # AgencyConfig directly without passing through the config validator.
    return min(MAX_HOOK_TIMEOUT_SECONDS, max(1, requested))


def openclaw_native_child_timeout_seconds(cfg: AgencyConfig) -> int:
    """Return the process budget for OpenClaw's native-child staffing hook.

    Native-child staffing can make one selection request and one abstention
    repair request.  Each selector invocation has a 60-second aggregate
    deadline even when its harness-scoped inference profile permits a longer
    provider timeout.  Resolve only the static OpenClaw route here: environment
    overrides and live canary providers must not change an installed bundle.
    """

    try:
        resolution = resolve_inference_route(
            cfg,
            "workforce.recruiter",
            harness="openclaw",
        )
    except ConfigValidationError:
        return 0
    per_call = min(
        max(0.0, float(resolution.provider.timeout)),
        _SELECTOR_MAX_JUDGE_DEADLINE_SECONDS,
    )
    requested = math.ceil(
        (_OPENCLAW_NATIVE_CHILD_JUDGE_CALLS * per_call) + HOOK_TIMEOUT_BUFFER_SECONDS
    )
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
        result = {
            "type": "command",
            "command": command,
            "commandWindows": command_windows,
            "async": False,
            "timeout": timeout_seconds,
            "statusMessage": status_message,
        }
        if event == "UserPromptSubmit":
            # Agency bounds the plan to 32,000 characters and the final hook
            # output to 48,000. Codex's 2,500-token default would spill it.
            result["additionalContextLimit"] = 0
        return result

    hooks = {
        "SessionStart": [{"hooks": [handler("SessionStart", "Loading Agency Runtime managers")]}],
        "UserPromptSubmit": [
            {"hooks": [handler("UserPromptSubmit", "Routing with Agency Runtime")]}
        ],
        "PreToolUse": [
            {
                "matcher": CODEX_NATIVE_CHILD_HOOK_MATCHER,
                "hooks": [
                    handler(
                        "PreToolUse",
                        "Checking Agency native child staffing",
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
        "SubagentStart": [{"hooks": [handler("SubagentStart", "Binding Agency child identity")]}],
        "SubagentStop": [{"hooks": [handler("SubagentStop", "Recording Agency child lifecycle")]}],
        "PostCompact": [{"hooks": [handler("PostCompact", "Restoring Agency Runtime managers")]}],
        "Stop": [{"hooks": [handler("Stop", "Checking Agency Runtime response contract")]}],
    }
    if tuple(hooks) != CODEX_HOOK_EVENTS:
        raise RuntimeError("Codex hook payload drifted from the canonical trust inventory")
    return {"hooks": hooks}


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

    base_argv = runtime_python_argv("agency_runtime.cli")

    def handler(event: str, status_message: str) -> dict[str, Any]:
        # ZCode hooks: use type "process" (argument vector, no shell) — the
        # most portable format per the ZCode hook docs. The prior type "command"
        # with POSIX single-quotes / a non-standard commandWindows field failed
        # silently on Windows because ZCode doesn't recognize commandWindows and
        # the POSIX command syntax is invalid in cmd.exe.
        args = [
            *base_argv[1:],
            "hook",
            "zcode",
            "--event",
            event,
            *_config_args(config_path),
            *_runtime_control_args(runtime_control_path_value),
        ]
        return {
            "type": "process",
            "command": base_argv[0],
            "args": args,
            "enabled": True,
            "timeoutMs": timeout_seconds * 1000,
            "statusMessage": status_message,
        }

    return {
        "hooks": {
            "enabled": True,
            "timeoutMs": timeout_seconds * 1000,
            "events": {
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
                            handler("PreToolUse", "Selecting Agency native child team by inference")
                        ],
                    }
                ],
                "PermissionRequest": [
                    {
                        "matcher": "*",
                        "hooks": [
                            handler(
                                "PermissionRequest",
                                "Checking Agency Runtime tool permission",
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
                "PostToolUseFailure": [
                    {
                        "matcher": "*",
                        "hooks": [
                            handler(
                                "PostToolUseFailure",
                                "Recording Agency Runtime tool failure",
                            )
                        ],
                    }
                ],
                "Stop": [{"hooks": [handler("Stop", "Checking Agency Runtime response contract")]}],
            },
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
description: Use only when the user's entire message exactly matches agency status, agency on, or agency off.
---

# Agency Runtime control

Handle only these exact conversation forms: {forms}. Punctuation, extra text,
and broad words such as `status`, `ping`, or `heartbeat` are ordinary user
requests, not runtime controls.

- For status, call `agency.host_status` with `host` set to `{host}`.
- For on or off, do not call a mutation tool. Model-facing Agency tools are
  read-only. Tell the operator to use the owner-authenticated dashboard UI or
  run `agency on --agent {host}` / `agency off --agent {host}` from a normal user shell.

Report only returned soft-control state. Do not claim that native plugin
registration changed, a mutation occurred, or a live canary passed unless
owner-side evidence explicitly proves it.
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


def claude_plugin_version(
    manifest: Mapping[str, Any],
    component_files: Mapping[str, str],
) -> str:
    return render_claude_plugin_version(
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
    timeout_seconds = _hook_timeout_seconds(effective_cfg, harness=host)
    if host == "hermes":
        return build_hermes_bundle(
            hermes_plugin(timeout_seconds, effective_cfg),
            mcp=_mcp_config(config_path) if config_path else _mcp_config(),
        )

    if host == "openclaw":
        timeout_seconds = max(
            timeout_seconds,
            openclaw_native_child_timeout_seconds(effective_cfg),
        )
        index = (
            _openclaw_index(timeout_seconds, config_path)
            if config_path
            else _openclaw_index(timeout_seconds)
        )
        return build_openclaw_bundle(
            index,
            mcp=_mcp_config(config_path) if config_path else _mcp_config(),
        )

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

    if host == "zcode":
        hooks = (
            _zcode_hooks(timeout_seconds, config_path, runtime_control_path_value)
            if config_path or runtime_control_path_value
            else _zcode_hooks(timeout_seconds)
        )
        return build_zcode_bundle(hooks=hooks)

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
        version_builder=_claude_plugin_version,
    )
