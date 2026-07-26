"""Host bundle manifests assembled from rendered payload components."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any

from agency_runtime.core.installer_contracts import (
    MARKETPLACE_ID,
    PLUGIN_ID,
    PLUGIN_VERSION,
)

_DESCRIPTION = "Agency Runtime specialist routing, delegation evidence, and operational tools."


def render_codex_plugin_version(
    manifest: Mapping[str, Any],
    component_files: Mapping[str, str],
    *,
    bundle_digest: Callable[[Mapping[str, str]], str],
) -> str:
    """Build a deterministic Codex cachebuster from load-bearing content."""

    fingerprint_inputs = dict(component_files)
    fingerprint_inputs[".codex-plugin/plugin.json"] = json.dumps(
        manifest,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return f"{PLUGIN_VERSION}+codex.{bundle_digest(fingerprint_inputs)[:12]}"


def build_hermes_bundle(plugin_source: str) -> tuple[dict[str, str], str]:
    files = {
        "__init__.py": plugin_source,
        "plugin.yaml": (
            f"name: {PLUGIN_ID}\n"
            f'version: "{PLUGIN_VERSION}"\n'
            f"description: {_DESCRIPTION}\n"
            "provides_hooks:\n"
            "  - pre_llm_call\n"
            "  - post_tool_call\n"
            "  - post_api_request\n"
            "  - subagent_start\n"
            "  - subagent_stop\n"
            "  - pre_verify\n"
            "  - transform_llm_output\n"
            "  - on_session_end\n"
        ),
    }
    return files, "__init__.py"


def build_openclaw_bundle(index_source: str) -> tuple[dict[str, str], str]:
    files = {
        "index.js": index_source,
        "openclaw.plugin.json": json.dumps(
            {
                "id": PLUGIN_ID,
                "name": "Agency Preflight",
                "description": _DESCRIPTION,
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


def build_codex_bundle(
    *,
    hooks: Mapping[str, Any],
    mcp: Mapping[str, Any],
    control_skill: str,
    version_builder: Callable[[Mapping[str, Any], Mapping[str, str]], str],
) -> tuple[dict[str, str], str]:
    plugin_prefix = f"plugins/{PLUGIN_ID}"
    manifest: dict[str, Any] = {
        "name": PLUGIN_ID,
        "description": _DESCRIPTION,
        "author": {"name": "Agency Runtime Contributors"},
        "license": "MIT",
        "keywords": ["routing", "delegation", "observability"],
        "hooks": "./hooks/hooks.json",
        "mcpServers": "./.mcp.json",
        "interface": {
            "displayName": "Agency Runtime",
            "shortDescription": "Specialist routing and delegation evidence",
            "longDescription": _DESCRIPTION,
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
        f"{plugin_prefix}/hooks/hooks.json": json.dumps(hooks, indent=2) + "\n",
        f"{plugin_prefix}/.mcp.json": json.dumps(mcp, indent=2) + "\n",
        f"{plugin_prefix}/skills/agency/SKILL.md": control_skill,
    }
    manifest["version"] = version_builder(manifest, component_files)
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


def build_claude_bundle(
    *,
    hooks: Mapping[str, Any],
    mcp: Mapping[str, Any],
    control_skill: str,
) -> tuple[dict[str, str], str]:
    plugin_prefix = f"plugins/{PLUGIN_ID}"
    manifest = {
        "name": PLUGIN_ID,
        "displayName": "Agency Runtime",
        "version": PLUGIN_VERSION,
        "description": _DESCRIPTION,
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
                "description": _DESCRIPTION,
                "version": PLUGIN_VERSION,
            }
        ],
    }
    files = {
        ".claude-plugin/marketplace.json": json.dumps(marketplace, indent=2) + "\n",
        f"{plugin_prefix}/.claude-plugin/plugin.json": json.dumps(manifest, indent=2) + "\n",
        f"{plugin_prefix}/hooks/hooks.json": json.dumps(hooks, indent=2) + "\n",
        f"{plugin_prefix}/.mcp.json": json.dumps(mcp, indent=2) + "\n",
        f"{plugin_prefix}/skills/agency/SKILL.md": control_skill,
    }
    return files, f"{plugin_prefix}/.claude-plugin/plugin.json"


def build_zcode_bundle(*, hooks: Mapping[str, Any]) -> tuple[dict[str, str], str]:
    """Build the owned fragment merged into ZCode's user configuration.

    ZCode 3.5.2 consumes hooks directly from the user cli config. It has no
    repository-proven marketplace/plugin CLI contract, so the managed bundle
    contains only the declarative fragment used by the config transaction.
    """

    primary = "zcode-hooks.json"
    return {primary: json.dumps(hooks, indent=2) + "\n"}, primary
