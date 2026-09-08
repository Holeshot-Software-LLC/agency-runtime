"""Execute the generated native terminal hook, including channel isolation."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from agency_runtime.core.installer_payload_openclaw import render_openclaw_index


@pytest.mark.parametrize("channel", ["webchat", "telegram", "", None])
@pytest.mark.parametrize("decision", ["allow_pending", "terminal", "unavailable"])
def test_native_terminal_routes_only_verified_internal_delivery(
    tmp_path: Path, channel: str | None, decision: str
) -> None:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required to execute the generated plugin")
    source = (
        render_openclaw_index(
            5, python_executable="/unused/python", bootstrap_path="/unused/bootstrap.py"
        )
        .replace(
            'import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";',
            "const definePluginEntry = (entry) => entry;",
        )
        .replace("export default definePluginEntry(", "const plugin = definePluginEntry(")
    )
    script = (
        source
        + r"""
const hooks = new Map();
plugin.register({
  config: {},
  on: (name, callback) => hooks.set(name, callback),
  registerCommand: () => {},
  registerAgentToolResultMiddleware: () => {},
});
const calls = [];
invokeAgency = async (payload) => {
  calls.push(payload);
  if (payload.action === "pre_verify") {
    if (DECISION === "terminal") return {action: "terminal", terminalRejected: true};
    if (DECISION === "unavailable") return {};
    return {action: "allow_pending", evidenceRevision: 7};
  }
  return {action: "allow", authoritative: true, terminalBound: true};
};
await hooks.get("before_agent_finalize")(
  {lastAssistantMessage: "Exact visible response."},
  {sessionKey: "session", runId: "turn", modelId: "model", channel: CHANNEL},
);
process.stdout.write(JSON.stringify(calls));
""".replace("DECISION", json.dumps(decision)).replace("CHANNEL", json.dumps(channel))
    )
    path = tmp_path / "native-terminal.mjs"
    path.write_text(script)
    result = subprocess.run(
        [node, str(path)], capture_output=True, text=True, timeout=15, check=True
    )
    calls = json.loads(result.stdout)
    terminal_expected = channel == "webchat" and decision == "allow_pending"
    assert [call["action"] for call in calls] == (
        ["pre_verify", "outbound_gate"] if terminal_expected else ["pre_verify"]
    )
    for call in calls:
        assert call["sessionId"] == "session"
        assert call["traceId"] == "turn"
        assert call["finalResponse"] == "Exact visible response."
        assert "outboundPayload" not in call
