"""Generated host plugin payloads and install-time configuration."""

from __future__ import annotations

import json
import math
import shlex
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from agency_runtime.core.config import AgencyConfig
from agency_runtime.core.installer_contracts import (
    HOOK_TIMEOUT_BUFFER_SECONDS,
    MARKETPLACE_ID,
    MAX_HOOK_TIMEOUT_SECONDS,
    PLUGIN_ID,
    PLUGIN_VERSION,
)
from agency_runtime.core.process_argv import absolute_executable_path


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
    executable = absolute_executable_path(sys.executable)
    argv = (executable, "-m", module, *args)
    posix = " ".join(shlex.quote(part) for part in argv)
    # Codex executes commandWindows through the selected Windows shell. Its
    # native PowerShell environment needs the call operator when argv[0] is a
    # quoted path; single-quoted literals keep metacharacters inert.
    windows = "& " + " ".join(_powershell_literal(part) for part in argv)
    return posix, windows


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
    """Conservatively bound the selector's sequential provider attempts."""
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
    return max(max(0.0, float(cfg.judge.timeout)), sum(budgets))


def hook_timeout_seconds(cfg: AgencyConfig) -> int:
    requested = math.ceil(_effective_judge_budget_seconds(cfg) + HOOK_TIMEOUT_BUFFER_SECONDS)
    # OpenClaw permits at most 600 seconds and the generated bridge reserves a
    # two-second host margin. Normal schema-validated configs remain well below
    # this cap; it protects programmatic callers that construct AgencyConfig
    # directly without passing through the config validator.
    return min(MAX_HOOK_TIMEOUT_SECONDS, max(1, requested))


def mcp_config() -> dict[str, Any]:
    return {
        "mcpServers": {
            "agency-runtime": {
                "command": absolute_executable_path(sys.executable),
                "args": ["-m", "agency_runtime.server.mcp", "--stdio"],
            }
        }
    }


def codex_hooks(timeout_seconds: int) -> dict[str, Any]:
    command, command_windows = _python_commands("agency_runtime.cli", "hook", "codex")
    handler = {
        "type": "command",
        "command": command,
        "commandWindows": command_windows,
        "async": False,
        "timeout": timeout_seconds,
        "statusMessage": "Routing with Agency Runtime",
    }
    observer = {**handler, "statusMessage": "Recording Agency Runtime evidence"}
    return {
        "hooks": {
            "UserPromptSubmit": [{"hooks": [handler]}],
            "PostToolUse": [{"matcher": "*", "hooks": [observer]}],
            "Stop": [
                {
                    "hooks": [
                        {
                            **handler,
                            "statusMessage": "Checking Agency Runtime response contract",
                        }
                    ]
                }
            ],
        }
    }


def claude_hooks(timeout_seconds: int) -> dict[str, Any]:
    executable = absolute_executable_path(sys.executable)
    base = {
        "type": "command",
        "command": executable,
        "args": ["-m", "agency_runtime.cli", "hook", "claude"],
        "timeout": timeout_seconds,
    }
    return {
        "hooks": {
            "UserPromptSubmit": [{"hooks": [base]}],
            "PostToolUse": [{"matcher": "*", "hooks": [base]}],
            "PostToolUseFailure": [{"matcher": "*", "hooks": [base]}],
            "Stop": [{"hooks": [base]}],
        }
    }


def agency_control_skill(host: str) -> str:
    """Build the host-aware conversation control skill for Codex and Claude."""
    return f"""---
name: agency
description: Inspect, enable, or disable Agency Runtime for this host.
---

# Agency Runtime control

Handle the conversation forms `agency status`, `agency on`, and `agency off`.
Some clients may present the same text with a leading slash; treat it as the
same request when the host routes it through this skill.

- For status, call `agency.host_status` with `host` set to `{host}`.
- For on, call `agency.host_control` with `host` set to `{host}`, `enabled`
  set to `true`, and `confirm` set exactly to `ENABLE {host}`.
- For off, call `agency.host_control` with `host` set to `{host}`, `enabled`
  set to `false`, and `confirm` set exactly to `DISABLE {host}`.

Report the returned soft-control state. Do not claim that native plugin
registration changed, and do not claim a live canary unless the returned
evidence explicitly proves one.
"""


_HERMES_PLUGIN = '''"""Agency Runtime native Hermes plugin (managed file)."""

from agency_runtime.adapters.hermes.plugin import HermesAdapter

_adapter = None


def _get_adapter():
    global _adapter
    if _adapter is None:
        _adapter = HermesAdapter()
    return _adapter


def _pre_llm_call(**kwargs):
    trace_id = str(
        kwargs.get("turn_id")
        or kwargs.get("trace_id")
        or kwargs.get("task_id")
        or ""
    )
    return _get_adapter().pre_llm_call_handler(
        session_id=str(kwargs.get("session_id") or kwargs.get("task_id") or ""),
        user_message=str(kwargs.get("user_message") or ""),
        model=str(kwargs.get("model") or ""),
        trace_id=trace_id,
    )


def _post_tool_call(tool_name="", args=None, result=None, **kwargs):
    _get_adapter().post_tool_call_handler(
        tool_name=tool_name,
        args=args or {},
        result=result,
        session_id=str(kwargs.get("session_id") or kwargs.get("task_id") or ""),
        **{key: value for key, value in kwargs.items() if key not in {"session_id", "task_id"}},
    )


def _post_api_request(**kwargs):
    _get_adapter().post_api_request_handler(**kwargs)


def _transform_llm_output(response_text="", **kwargs):
    return _get_adapter().apply_finalization(
        response_text,
        str(kwargs.get("session_id") or kwargs.get("task_id") or ""),
        str(kwargs.get("model") or ""),
    )


def _agency_command(*args, **kwargs):
    raw_args = kwargs.get("args") or kwargs.get("raw_args") or ""
    if not raw_args:
        raw_args = next(
            (value for value in reversed(args) if isinstance(value, str)),
            "",
        )
    from agency_runtime.core.host_control import handle_host_control_command

    result = handle_host_control_command(
        "hermes",
        str(raw_args),
        store=_get_adapter().store,
        source="hermes-command",
    )
    return result["message"]


def register(ctx):
    ctx.register_hook("pre_llm_call", _pre_llm_call)
    ctx.register_hook("post_tool_call", _post_tool_call)
    ctx.register_hook("post_api_request", _post_api_request)
    ctx.register_hook("transform_llm_output", _transform_llm_output)
    ctx.register_command("agency", _agency_command, description="Agency Runtime status, on, or off")
'''


def openclaw_index(timeout_seconds: int) -> str:
    python = json.dumps(absolute_executable_path(sys.executable))
    timeout_ms = timeout_seconds * 1000
    host_timeout_ms = (timeout_seconds + 2) * 1000
    return f"""import {{ definePluginEntry }} from "openclaw/plugin-sdk/plugin-entry";
import {{ execFile }} from "node:child_process";

const PYTHON = process.env.AGENCY_RUNTIME_PYTHON || {python};
const MODULE_ARGS = ["-m", "agency_runtime.adapters.openclaw.node_bridge"];

function invokeAgency(payload) {{
  return new Promise((resolve, reject) => {{
    const child = execFile(PYTHON, MODULE_ARGS, {{ timeout: {timeout_ms}, maxBuffer: 1024 * 1024 }}, (error, stdout, stderr) => {{
      if (error) {{
        reject(new Error((stderr || error.message || "Agency Runtime hook failed").trim()));
        return;
      }}
      try {{ resolve(JSON.parse(stdout || "{{}}")); }}
      catch (parseError) {{ reject(parseError); }}
    }});
    child.stdin.end(JSON.stringify(payload));
  }});
}}

function sessionId(event, ctx) {{
  return String(ctx?.sessionKey || ctx?.sessionId || event?.sessionKey || event?.sessionId || "");
}}

function traceId(event, ctx) {{
  return String(ctx?.turnId || event?.turnId || ctx?.runId || event?.runId || "");
}}

function modelId(ctx) {{
  return String(ctx?.modelId || ctx?.activeModel?.modelId || ctx?.model || "");
}}

function finalAssistantText(event) {{
  return String(event?.lastAssistantMessage || event?.finalAssistantText || event?.assistantText || event?.text || "");
}}

export default definePluginEntry({{
  id: "agency-preflight",
  name: "Agency Preflight",
  description: "Agency Runtime routing, evidence, and final-response enforcement.",
  register(api) {{
    api.registerCommand({{
      name: "agency",
      description: "Agency Runtime status, on, or off",
      acceptsArgs: true,
      requireAuth: true,
      handler: async (ctx) => {{
        const result = await invokeAgency({{
          action: "control",
          command: String(ctx?.args || "status"),
        }});
        return {{ text: String(result?.message || "Agency Runtime control completed.") }};
      }},
    }});

    api.on("before_prompt_build", async (event, ctx) => {{
      const result = await invokeAgency({{
        action: "preflight",
        sessionId: sessionId(event, ctx),
        traceId: traceId(event, ctx),
        userMessage: String(event?.prompt || ""),
        model: modelId(ctx),
      }});
      return result.context ? {{ appendContext: result.context }} : undefined;
    }}, {{ priority: 100, timeoutMs: {host_timeout_ms} }});

    api.on("after_tool_call", async (event, ctx) => {{
      await invokeAgency({{
        action: "post_tool_call",
        sessionId: sessionId(event, ctx),
        traceId: traceId(event, ctx),
        toolName: String(event?.toolName || ""),
        toolInput: event?.params || {{}},
        toolResult: event?.result,
        error: String(event?.error?.message || event?.error || ""),
      }});
    }}, {{ timeoutMs: {host_timeout_ms} }});

    api.on("before_agent_finalize", async (event, ctx) => {{
      const decision = await invokeAgency({{
        action: "pre_verify",
        sessionId: sessionId(event, ctx),
        traceId: traceId(event, ctx),
        finalResponse: finalAssistantText(event),
        model: modelId(ctx),
        attempt: Number(event?.attempt || 0),
      }});
      if (decision.action !== "continue") return undefined;
      return {{
        action: "revise",
        reason: String(decision.message || "Agency Runtime response contract is incomplete."),
        retry: {{
          instruction: String(decision.message || "Repair the Agency Runtime response contract."),
          idempotencyKey: "agency-preflight-header",
          maxAttempts: 2,
        }},
      }};
    }}, {{ priority: 100, timeoutMs: {host_timeout_ms} }});
  }},
}});
"""


def codex_plugin_version(
    manifest: Mapping[str, Any],
    component_files: Mapping[str, str],
) -> str:
    """Build a deterministic Codex cachebuster from load-bearing content."""
    fingerprint_inputs = dict(component_files)
    fingerprint_inputs[".codex-plugin/plugin.json"] = json.dumps(
        manifest,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"{PLUGIN_VERSION}+codex.{_bundle_digest(fingerprint_inputs)[:12]}"


def bundle_files(host: str, cfg: AgencyConfig | None = None) -> tuple[dict[str, str], str]:
    description = "Agency Runtime specialist routing, delegation evidence, and operational tools."
    timeout_seconds = _hook_timeout_seconds(cfg or AgencyConfig())
    if host == "hermes":
        files = {
            "__init__.py": _HERMES_PLUGIN,
            "plugin.yaml": (
                f"name: {PLUGIN_ID}\n"
                f'version: "{PLUGIN_VERSION}"\n'
                f"description: {description}\n"
                "provides_hooks:\n"
                "  - pre_llm_call\n"
                "  - post_tool_call\n"
                "  - post_api_request\n"
                "  - transform_llm_output\n"
            ),
        }
        return files, "__init__.py"

    if host == "openclaw":
        files = {
            "index.js": _openclaw_index(timeout_seconds),
            "openclaw.plugin.json": json.dumps(
                {
                    "id": PLUGIN_ID,
                    "name": "Agency Preflight",
                    "description": description,
                    "activation": {"onStartup": True, "onCapabilities": ["hook"]},
                    "configSchema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {},
                    },
                },
                indent=2,
            )
            + "\n",
            "package.json": json.dumps(
                {
                    "name": "agency-preflight-openclaw",
                    "version": PLUGIN_VERSION,
                    "type": "module",
                    "private": True,
                    "openclaw": {"extensions": ["./index.js"]},
                },
                indent=2,
            )
            + "\n",
        }
        return files, "index.js"

    if host == "codex":
        plugin_prefix = f"plugins/{PLUGIN_ID}"
        manifest: dict[str, Any] = {
            "name": PLUGIN_ID,
            "description": description,
            "author": {"name": "Agency Runtime Contributors"},
            "license": "MIT",
            "keywords": ["routing", "delegation", "observability"],
            "hooks": "./hooks/hooks.json",
            "mcpServers": "./.mcp.json",
            "interface": {
                "displayName": "Agency Runtime",
                "shortDescription": "Specialist routing and delegation evidence",
                "longDescription": description,
                "developerName": "Agency Runtime Contributors",
                "category": "Developer Tools",
                "capabilities": ["Read", "Write"],
                "defaultPrompt": (
                    "Use Agency Runtime for specialist routing, delegation evidence, "
                    "and auditable response finalization."
                ),
            },
        }
        component_files = {
            f"{plugin_prefix}/hooks/hooks.json": json.dumps(_codex_hooks(timeout_seconds), indent=2)
            + "\n",
            f"{plugin_prefix}/.mcp.json": json.dumps(_mcp_config(), indent=2) + "\n",
            f"{plugin_prefix}/skills/agency/SKILL.md": _agency_control_skill("codex"),
        }
        manifest["version"] = _codex_plugin_version(manifest, component_files)
        marketplace = {
            "name": MARKETPLACE_ID,
            "interface": {"displayName": "Agency Runtime"},
            "plugins": [
                {
                    "name": PLUGIN_ID,
                    "source": {"source": "local", "path": f"./plugins/{PLUGIN_ID}"},
                    "policy": {
                        "installation": "AVAILABLE",
                        "authentication": "ON_INSTALL",
                    },
                    "category": "Developer Tools",
                }
            ],
        }
        files = {
            ".agents/plugins/marketplace.json": json.dumps(marketplace, indent=2) + "\n",
            f"{plugin_prefix}/.codex-plugin/plugin.json": json.dumps(manifest, indent=2) + "\n",
            **component_files,
        }
        return files, f"{plugin_prefix}/.codex-plugin/plugin.json"

    plugin_prefix = f"plugins/{PLUGIN_ID}"
    manifest = {
        "name": PLUGIN_ID,
        "displayName": "Agency Runtime",
        "version": PLUGIN_VERSION,
        "description": description,
        "author": {"name": "Agency Runtime Contributors"},
        "license": "MIT",
        "hooks": "./hooks/hooks.json",
        "mcpServers": "./.mcp.json",
    }
    marketplace = {
        "name": MARKETPLACE_ID,
        "owner": {"name": "Agency Runtime Contributors"},
        "plugins": [
            {
                "name": PLUGIN_ID,
                "source": f"./plugins/{PLUGIN_ID}",
                "description": description,
                "version": PLUGIN_VERSION,
            }
        ],
    }
    files = {
        ".claude-plugin/marketplace.json": json.dumps(marketplace, indent=2) + "\n",
        f"{plugin_prefix}/.claude-plugin/plugin.json": json.dumps(manifest, indent=2) + "\n",
        f"{plugin_prefix}/hooks/hooks.json": json.dumps(_claude_hooks(timeout_seconds), indent=2)
        + "\n",
        f"{plugin_prefix}/.mcp.json": json.dumps(_mcp_config(), indent=2) + "\n",
        f"{plugin_prefix}/skills/agency/SKILL.md": _agency_control_skill("claude"),
    }
    return files, f"{plugin_prefix}/.claude-plugin/plugin.json"
