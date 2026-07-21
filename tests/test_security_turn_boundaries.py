"""Adversarial coverage for tool authority, correlation, and host transport."""

from __future__ import annotations

import io
import json
import shutil
import subprocess
from http import HTTPStatus
from pathlib import Path
from types import SimpleNamespace

import pytest

from agency_runtime.adapters import hooks
from agency_runtime.adapters.hooks import HookBridge, run_hook_stdio
from agency_runtime.adapters.openclaw import node_bridge
from agency_runtime.core.correlation import (
    MAX_CORRELATION_ID_BYTES,
    validate_correlation_id,
)
from agency_runtime.core.installer_payloads import openclaw_index
from agency_runtime.core.store.sqlite import Store
from agency_runtime.server import http


@pytest.mark.parametrize(
    ("host", "tool_name", "canonical"),
    [
        ("codex", "mcp__agency__agency.load_specialist", "agency_agents_load"),
        ("codex", "mcp__agency__agency_agents_delegate", "agency_agents_delegate"),
        ("codex", "functions.collaboration.spawn_agent", "spawn_agent"),
        ("codex", "agency.record_skill_loaded", "skill_view"),
        ("claude", "Agent", "delegate_task"),
    ],
)
def test_authoritative_tool_names_require_exact_allowlisted_identity(
    host: str,
    tool_name: str,
    canonical: str,
) -> None:
    observed, _arguments = hooks._canonical_tool_call(
        host,
        tool_name,
        {"agent": "reviewer", "name": "review"},
        {"agent_id": "worker"},
    )

    assert observed == canonical


@pytest.mark.parametrize(
    "tool_name",
    [
        "mcp__evil__agency_agents_load",
        "mcp__evil__agency_agents_delegate",
        "mcp__evil__agency.record_skill_loaded",
        "evil.delegate",
        "functions.evil.spawn_agent",
    ],
)
def test_unrelated_tool_names_cannot_fabricate_agency_evidence(
    tmp_path: Path,
    tool_name: str,
) -> None:
    store = Store(tmp_path / "agency.db")
    store.create_run(trace_id="turn", session_id="session", host="codex")

    assert (
        HookBridge("codex", store=store).handle(
            {
                "hook_event_name": "PostToolUse",
                "session_id": "session",
                "turn_id": "turn",
                "tool_use_id": "tool",
                "tool_name": tool_name,
                "tool_input": {
                    "slug": "code-reviewer",
                    "agent": "code-reviewer",
                    "name": "security-review",
                },
                "tool_response": {"success": True, "agent_id": "worker"},
            }
        )
        == {}
    )
    assert store.get_skills_for_trace("session", "turn") == []
    assert store.get_specialists_for_trace("session", "turn") == []
    assert store.get_delegations("turn") == []


def test_correlation_validator_accepts_exact_ascii_and_multibyte_budgets() -> None:
    ascii_value = "a" * MAX_CORRELATION_ID_BYTES
    multibyte_value = "é" * (MAX_CORRELATION_ID_BYTES // 2)

    assert validate_correlation_id(ascii_value, field="trace_id") == ascii_value
    assert validate_correlation_id(multibyte_value, field="session_id") == multibyte_value
    assert validate_correlation_id(None, required=False) == ""


@pytest.mark.parametrize(
    "value",
    [
        7,
        " ",
        "trace\nforged",
        "a" * (MAX_CORRELATION_ID_BYTES + 1),
        "é" * (MAX_CORRELATION_ID_BYTES // 2 + 1),
        "\ud800",
    ],
)
def test_correlation_validator_rejects_noncanonical_or_unbounded_values(
    value: object,
) -> None:
    with pytest.raises(ValueError):
        validate_correlation_id(value, field="trace_id")


@pytest.mark.parametrize(
    ("session_id", "trace_id"),
    [
        ("s" * 513, "trace"),
        ("session", "t" * 513),
        ("é" * 257, "trace"),
        ("session", "trace\x00forged"),
    ],
)
def test_invalid_store_correlation_is_rejected_without_creating_a_row(
    tmp_path: Path,
    session_id: str,
    trace_id: str,
) -> None:
    store = Store(tmp_path / "agency.db")

    with pytest.raises(ValueError):
        store.create_run(trace_id=trace_id, session_id=session_id)

    assert store.runtime_table_counts()["runs"] == 0


@pytest.mark.parametrize(
    ("method_name", "arguments"),
    [
        ("get_run", ("t" * 513,)),
        ("get_open_traces_for_session", ("s" * 513,)),
        ("get_model_receipt", ("t" * 513,)),
        ("get_skills_for_session", ("s" * 513,)),
        ("get_delegations", ("t" * 513,)),
    ],
)
def test_invalid_store_lookup_is_rejected_before_database_access(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    method_name: str,
    arguments: tuple[str, ...],
) -> None:
    store = Store(tmp_path / "agency.db")
    monkeypatch.setattr(
        store,
        "_connect",
        lambda: (_ for _ in ()).throw(AssertionError("database was queried")),
    )

    with pytest.raises(ValueError):
        getattr(store, method_name)(*arguments)


def _bare_http_handler(store: object) -> tuple[http.AgencyHTTPHandler, list[tuple[int, str]]]:
    handler = object.__new__(http.AgencyHTTPHandler)
    handler.server = SimpleNamespace(store=store, allow_context_writes=False)
    errors: list[tuple[int, str]] = []
    handler._json_error = lambda status, message: errors.append((int(status), message))
    handler._json_ok = lambda _payload: pytest.fail("invalid correlation was accepted")
    return handler, errors


@pytest.mark.parametrize(
    ("handler_name", "payload"),
    [
        (
            "_handle_preflight",
            {"session_id": "s" * 513, "user_message": "review"},
        ),
        (
            "_handle_explain",
            {"session_id": "bad\nvalue", "task": "review"},
        ),
        (
            "_handle_finalize",
            {
                "session_id": "session",
                "trace_id": "é" * 257,
                "draft_text": "response",
            },
        ),
    ],
)
def test_http_rejects_invalid_correlation_as_bad_request(
    handler_name: str,
    payload: dict[str, object],
) -> None:
    handler, errors = _bare_http_handler(object())

    getattr(handler, handler_name)(payload)

    assert errors
    assert errors[0][0] == HTTPStatus.BAD_REQUEST


def test_malformed_native_stop_correlation_fails_closed_without_store_rows(
    tmp_path: Path,
) -> None:
    store = Store(tmp_path / "agency.db")
    source = io.BytesIO(
        json.dumps(
            {
                "hook_event_name": "Stop",
                "session_id": "session",
                "turn_id": "t" * 513,
                "last_assistant_message": "candidate",
            }
        ).encode()
    )
    sink = io.BytesIO()

    assert (
        run_hook_stdio(
            "codex",
            store=store,
            expected_event="Stop",
            input_stream=source,
            output_stream=sink,
        )
        == 0
    )

    rejection = json.loads(sink.getvalue())
    assert rejection["continue"] is False
    assert store.runtime_table_counts()["runs"] == 0


def test_openclaw_invalid_terminal_correlation_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        node_bridge,
        "_read_payload",
        lambda: {
            "action": "pre_verify",
            "sessionId": "session",
            "traceId": "t" * 513,
            "finalResponse": "candidate",
        },
    )
    monkeypatch.setattr(
        node_bridge,
        "OpenClawAdapter",
        lambda: pytest.fail("adapter must not be constructed for invalid correlation"),
    )

    assert node_bridge.main() == 0

    result = json.loads(capsys.readouterr().out)
    assert result["action"] == "continue"


def _openclaw_transport_source() -> str:
    source = openclaw_index(5).split("export default", 1)[0]
    source = source.replace(
        'import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";\n',
        "",
    )
    return source


def _openclaw_plugin_harness_source() -> str:
    source = openclaw_index(5)
    source = source.replace(
        'import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";\n',
        (
            "const registeredHooks = new Map();\n"
            "const registeredHookOptions = new Map();\n"
            "let registeredCommand;\n"
            "function definePluginEntry(definition) {\n"
            "  definition.register({\n"
            "    config: { agents: { defaults: { blockStreamingDefault: 'off' } }, channels: {} },\n"
            "    registerCommand(command) { registeredCommand = command; },\n"
            "    on(name, handler, options = {}) {\n"
            "      registeredHooks.set(name, handler);\n"
            "      registeredHookOptions.set(name, options);\n"
            "    },\n"
            "  });\n"
            "  return definition;\n"
            "}\n"
        ),
    )
    source = source.replace(
        'import { execFile, execFileSync } from "node:child_process";',
        (
            "let outboundQueries = 0;\n"
            "let outboundDelayMs = 0;\n"
            "let failOutboundSync = false;\n"
            "let failPreflight = false;\n"
            "let failControl = false;\n"
            "let runtimeControlEnabled = true;\n"
            "const bridgeCalls = [];\n"
            "function syncBridgeResult(payload) {\n"
            "  bridgeCalls.push(payload);\n"
            "  if (payload.action === 'control') {\n"
            "    if (failControl) throw new Error('control unavailable');\n"
            "    if (payload.command === 'off') runtimeControlEnabled = false;\n"
            "    if (payload.command === 'on') runtimeControlEnabled = true;\n"
            "    return { runtime_enabled: runtimeControlEnabled, message: 'control updated' };\n"
            "  }\n"
            "  if (payload.action !== 'outbound_gate') return {};\n"
            "  if (failOutboundSync) throw new Error('outbound unavailable');\n"
            "  outboundQueries += 1;\n"
            "  const outboundBinding = payload.outboundPayload || payload.finalResponse;\n"
            "  const responseHash = createHash('sha256').update(outboundBinding).digest('hex');\n"
            "  if (!runtimeControlEnabled) return { action: 'allow', runtimeDisabled: true, responseHash };\n"
            "  if (payload.sessionId === 'persisted-session' && payload.traceId === 'persisted-run' && payload.finalResponse === 'persisted invalid') {\n"
            "    return { action: 'replace', message: 'durable rejection', responseHash };\n"
            "  }\n"
            "  if (payload.finalResponse === 'mutated invalid') {\n"
            "    return { action: 'replace', message: 'mutation rejected', responseHash };\n"
            "  }\n"
            "  return { action: 'allow', responseHash, turnId: payload.traceId };\n"
            "}\n"
            "function execFileSync(_python, _args, options) {\n"
            "  return JSON.stringify(syncBridgeResult(JSON.parse(options.input)));\n"
            "}\n"
            "function execFile(_python, _args, _options, callback) {\n"
            "  const stdin = {\n"
            "    on() {},\n"
            "    destroy() {},\n"
            "    end(encoded, _encoding, done) {\n"
            "      const payload = JSON.parse(encoded);\n"
            "      bridgeCalls.push(payload);\n"
            "      if (failPreflight && payload.action === 'preflight') {\n"
            "        setImmediate(() => { callback(new Error('preflight unavailable'), '', 'preflight unavailable'); done?.(); });\n"
            "        return;\n"
            "      }\n"
            "      if (failControl && payload.action === 'control') {\n"
            "        setImmediate(() => { callback(new Error('control unavailable'), '', 'control unavailable'); done?.(); });\n"
            "        return;\n"
            "      }\n"
            "      let result = {};\n"
            "      if (payload.action === 'pre_verify') {\n"
            "        result = payload.attempt > 0\n"
            "          ? {\n"
            "              action: 'continue', message: 'repair', turnId: payload.traceId,\n"
            "              terminalRejected: true,\n"
            "              responseHash: createHash('sha256').update(payload.finalResponse).digest('hex'),\n"
            "            }\n"
            "          : {\n"
            "              action: 'continue', message: 'repair', turnId: payload.traceId,\n"
            "              revisionId: '00000000-0000-0000-0000-000000000001',\n"
            "            };\n"
            "      } else if (payload.action === 'control') {\n"
            "        if (payload.command === 'off') runtimeControlEnabled = false;\n"
            "        if (payload.command === 'on') runtimeControlEnabled = true;\n"
            "        result = {\n"
            "          runtime_enabled: runtimeControlEnabled,\n"
            "          message: 'control updated',\n"
            "        };\n"
            "      } else if (payload.action === 'outbound_gate') {\n"
            "        outboundQueries += 1;\n"
            "        const outboundBinding = payload.outboundPayload || payload.finalResponse;\n"
            "        if (!runtimeControlEnabled) {\n"
            "          result = {\n"
            "            action: 'allow', runtimeDisabled: true,\n"
            "            responseHash: createHash('sha256').update(outboundBinding).digest('hex'),\n"
            "          };\n"
            "        } else if (payload.sessionId === 'persisted-session'\n"
            "            && payload.traceId === 'persisted-run'\n"
            "            && payload.finalResponse === 'persisted invalid') {\n"
            "          result = {\n"
            "            action: 'replace', message: 'durable rejection',\n"
            "            responseHash: createHash('sha256').update(outboundBinding).digest('hex'),\n"
            "          };\n"
            "        } else if (payload.finalResponse === 'mutated invalid') {\n"
            "          result = {\n"
            "            action: 'replace', message: 'mutation rejected',\n"
            "            responseHash: createHash('sha256').update(outboundBinding).digest('hex'),\n"
            "          };\n"
            "        } else {\n"
            "          result = {\n"
            "            action: 'allow',\n"
            "            responseHash: createHash('sha256').update(outboundBinding).digest('hex'),\n"
            "            turnId: payload.traceId,\n"
            "          };\n"
            "        }\n"
            "      }\n"
            "      const deliver = () => { callback(null, JSON.stringify(result), ''); done?.(); };\n"
            "      if (payload.action === 'outbound_gate' && outboundDelayMs > 0) {\n"
            "        setTimeout(deliver, outboundDelayMs);\n"
            "      } else {\n"
            "        setImmediate(deliver);\n"
            "      }\n"
            "    },\n"
            "  };\n"
            "  return { stdin, kill() {} };\n"
            "}"
        ),
    )
    return source.replace("export default definePluginEntry", "const plugin = definePluginEntry")


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_generated_openclaw_transport_bounds_oversized_results_and_handles_epipe(
    tmp_path: Path,
) -> None:
    source = _openclaw_transport_source().replace(
        'import { execFile, execFileSync } from "node:child_process";',
        (
            'import { EventEmitter } from "node:events";\n'
            "let spawnCalls = 0;\n"
            "let killCalls = 0;\n"
            'let execMode = "epipe";\n'
            "function execFileSync() { throw new Error('sync bridge not expected'); }\n"
            "function execFile(_python, _args, _options, _callback) {\n"
            "  spawnCalls += 1;\n"
            "  const child = { kill() { killCalls += 1; } };\n"
            "  if (execMode === 'missing-stdin') return child;\n"
            "  const stdin = new EventEmitter();\n"
            "  stdin.destroy = () => {};\n"
            "  stdin.end = (_payload, _encoding, callback) => {\n"
            "    if (execMode === 'throw') throw new Error('sync stdin failure');\n"
            "    setImmediate(() => {\n"
            "      const error = Object.assign(new Error('write EPIPE'), { code: 'EPIPE' });\n"
            "      stdin.emit('error', error);\n"
            "      callback(error);\n"
            "    });\n"
            "  };\n"
            "  child.stdin = stdin;\n"
            "  return child;\n"
            "}"
        ),
    )
    source += """
let uncaught = 0;
process.on("uncaughtException", () => { uncaught += 1; });
const huge = "é".repeat(1024 * 1024);
const encoded = serializeBridgePayload({
  action: "post_tool_call",
  sessionId: "session",
  traceId: "trace",
  parentSessionId: "parent-session",
  parentTraceId: "parent-trace",
  toolName: "delegate_task",
  toolInput: { agent: "reviewer", prompt: huge, ignored: huge },
  toolResult: { success: true, message: huge, ignored: huge },
});
if (Buffer.byteLength(encoded, "utf8") > MAX_BRIDGE_INPUT_BYTES) process.exit(21);
const projected = JSON.parse(encoded);
if ("ignored" in projected.toolInput || "ignored" in projected.toolResult) process.exit(22);
if (projected.parentSessionId !== "parent-session" || projected.parentTraceId !== "parent-trace") process.exit(33);
const hostileText = String.fromCharCode(34, 92, 1).repeat(16 * 1024);
const hostilePayload = canonicalOutboundPayload({ text: hostileText });
const hostileEnvelope = serializeBridgePayload({
  action: "outbound_gate",
  sessionId: "session",
  traceId: "trace",
  finalResponse: hostileText,
  outboundPayload: hostilePayload,
});
if (Buffer.byteLength(hostileEnvelope, "utf8") > MAX_BRIDGE_INPUT_BYTES) process.exit(32);
const invalidCorrelation = JSON.parse(serializeBridgePayload({
  action: "preflight",
  sessionId: "é".repeat(257),
  traceId: "trace",
  userMessage: "review",
}));
if (Buffer.byteLength(invalidCorrelation.sessionId, "utf8") <= 512) process.exit(23);
let projectionReads = 0;
let bushy = { message: "leaf" };
for (let depth = 0; depth < 6; depth += 1) {
  const children = Array(32).fill(bushy);
  bushy = new Proxy(children, {
    get(target, key, receiver) {
      if (key === "length" || /^\\d+$/.test(String(key))) projectionReads += 1;
      return Reflect.get(target, key, receiver);
    },
  });
}
const bushyEncoded = serializeBridgePayload({
  action: "post_tool_call",
  sessionId: "session",
  traceId: "trace",
  toolName: "delegate_task",
  toolResult: bushy,
});
if (Buffer.byteLength(bushyEncoded, "utf8") > MAX_BRIDGE_INPUT_BYTES) process.exit(26);
if (!bushyEncoded.includes(TOOL_TRUNCATED)) process.exit(27);
if (projectionReads > MAX_TOOL_PROJECTION_NODES * 3) process.exit(28);
let serializationRejected = false;
try {
  await invokeAgency(new Proxy({}, {
    get() { throw new Error("serialization failure"); },
  }));
} catch (error) {
  serializationRejected = error?.message === "serialization failure";
}
if (!serializationRejected || spawnCalls !== 0) process.exit(29);
execMode = "missing-stdin";
let missingStdinRejected = false;
try {
  await invokeAgency({ action: "preflight", sessionId: "session", traceId: "trace" });
} catch (error) {
  missingStdinRejected = error?.message === "Agency Runtime bridge stdin is unavailable";
}
if (!missingStdinRejected || spawnCalls !== 1 || killCalls !== 1) process.exit(30);
execMode = "throw";
let syncWriteRejected = false;
try {
  await invokeAgency({ action: "preflight", sessionId: "session", traceId: "trace" });
} catch (error) {
  syncWriteRejected = error?.message === "sync stdin failure";
}
if (!syncWriteRejected || spawnCalls !== 2 || killCalls !== 2) process.exit(31);
execMode = "epipe";
let rejected = false;
try {
  await invokeAgency({
    action: "post_tool_call",
    sessionId: "session",
    traceId: "trace",
    toolName: "delegate_task",
    toolResult: { message: huge },
  });
} catch (error) {
  rejected = error?.code === "EPIPE";
}
await new Promise((resolve) => setImmediate(resolve));
if (!rejected || spawnCalls !== 3 || killCalls !== 3) process.exit(32);
if (uncaught !== 0) process.exit(33);
"""
    script = tmp_path / "openclaw-transport.mjs"
    script.write_text(source, encoding="utf-8")

    completed = subprocess.run(
        [str(shutil.which("node")), str(script)],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is not installed")
def test_generated_openclaw_outbound_gate_blocks_upstream_retry_exhaustion(
    tmp_path: Path,
) -> None:
    source = _openclaw_plugin_harness_source()
    source += """
const finalize = registeredHooks.get("before_agent_finalize");
const preflight = registeredHooks.get("before_prompt_build");
const outbound = registeredHooks.get("reply_payload_sending");
const messageSeal = registeredHooks.get("message_sending");
const beforeRun = registeredHooks.get("before_agent_run");
const gatewayStart = registeredHooks.get("gateway_start");
if (typeof finalize !== "function" || typeof preflight !== "function" || typeof outbound !== "function" || typeof messageSeal !== "function" || typeof beforeRun !== "function" || typeof gatewayStart !== "function" || typeof registeredCommand?.handler !== "function") process.exit(41);
if (registeredHookOptions.get("reply_payload_sending")?.priority !== Number.NEGATIVE_INFINITY) process.exit(52);
if (registeredHookOptions.get("message_sending")?.priority !== Number.NEGATIVE_INFINITY) process.exit(53);
const equalPriorityOrder = [
  { id: "agency", priority: Number.NEGATIVE_INFINITY },
  { id: "trusted-peer", priority: Number.NEGATIVE_INFINITY },
].sort((left, right) => right.priority - left.priority);
if (equalPriorityOrder[1]?.id !== "trusted-peer") process.exit(99);

if (outboundPolicyText({ spokenText: "audio only" }) !== "audio only") process.exit(84);
let mismatchedSurfacesBlocked = false;
try { outboundPolicyText({ text: "visible", ttsSupplement: { spokenText: "different" } }); }
catch { mismatchedSurfacesBlocked = true; }
if (!mismatchedSurfacesBlocked) process.exit(85);
const protoPayload = JSON.parse('{"text":"safe","__proto__":{"polluted":true},"constructor":{"nested":true}}');
const protoCanonical = JSON.parse(canonicalOutboundPayload(protoPayload));
if (!Object.hasOwn(protoCanonical, "__proto__") || protoCanonical.__proto__.polluted !== true || ({}).polluted) process.exit(86);
const cyclicPayload = { text: "cycle" };
cyclicPayload.self = cyclicPayload;
let cyclicBlocked = false;
try { canonicalOutboundPayload(cyclicPayload); } catch { cyclicBlocked = true; }
if (!cyclicBlocked) process.exit(87);

if ((await beforeRun())?.outcome !== "pass") process.exit(72);
failControl = true;
if ((await beforeRun())?.outcome !== "block") process.exit(73);
failControl = false;
gatewayStart({}, { config: { agents: { defaults: { blockStreamingDefault: "on" } } } });
if ((await beforeRun())?.outcome !== "block") process.exit(74);
runtimeControlEnabled = false;
if ((await beforeRun())?.outcome !== "pass") process.exit(75);
runtimeControlEnabled = true;
gatewayStart({}, { config: { agents: { defaults: { blockStreamingDefault: "off" } }, channels: {} } });
if ((await beforeRun())?.outcome !== "pass") process.exit(83);

const natural = "still invalid";
const context = { sessionKey: "session", runId: "run" };
const firstDecision = await finalize(
  { lastAssistantMessage: natural, stopHookActive: false },
  context,
);
if (firstDecision?.action !== "revise" || firstDecision?.retry?.maxAttempts !== 1) process.exit(42);
const decision = await finalize(
  { lastAssistantMessage: natural, stopHookActive: false },
  context,
);
// The second failure is a terminal bridge outcome, not another revise request.
// OpenClaw may complete its native finalize lifecycle; the final-only outbound
// gate below then denies the exact rejected response without reopening the turn.
if (decision !== undefined) process.exit(51);

const fastPath = await outbound(
  {
    payload: { text: natural, mediaUrl: "should-not-leak", spokenText: natural },
    kind: "final",
    sessionKey: "session",
    runId: "run",
  },
  context,
);
if (fastPath?.cancel !== true || fastPath?.reason === natural) process.exit(44);
if (outboundQueries !== 0) process.exit(46);

const duplicate = await outbound(
  { payload: { text: natural }, kind: "final", sessionKey: "session", runId: "run" },
  context,
);
if (duplicate?.cancel !== true || outboundQueries !== 0) process.exit(47);

const durable = await outbound(
  {
    payload: { text: "persisted invalid" },
    kind: "final",
    sessionKey: "persisted-session",
    runId: "persisted-run",
  },
  {},
);
if (durable?.cancel !== true || durable?.reason !== "durable rejection" || outboundQueries !== 1) process.exit(48);

const toolPayload = await outbound(
  { payload: { text: natural }, kind: "tool", sessionKey: "session", runId: "run" },
  context,
);
if (!toolPayload?.payload?.text || toolPayload.payload.text === natural || outboundQueries !== 1) process.exit(49);
const toolMessage = messageSeal(
  { content: toolPayload.payload.text, sessionKey: "session" },
  { sessionKey: "session" },
);
if (toolMessage?.content !== natural) process.exit(76);
const blockPayload = await outbound(
  { payload: { text: natural }, kind: "block", sessionKey: "session", runId: "run" },
  context,
);
if (blockPayload?.cancel !== true || outboundQueries !== 1) process.exit(54);
const partialPayload = await outbound(
  { payload: { text: natural }, kind: "partial", sessionKey: "session", runId: "run" },
  context,
);
if (partialPayload?.cancel !== true || partialPayload?.payload || outboundQueries !== 1) process.exit(111);
const unknownPayload = await outbound(
  { payload: { text: natural }, kind: "future-kind", sessionKey: "session", runId: "run" },
  context,
);
if (unknownPayload?.cancel !== true || unknownPayload?.payload || outboundQueries !== 1) process.exit(112);
runtimeControlEnabled = false;
const disabledUnknownPayload = await outbound(
  {
    payload: { text: natural }, kind: "future-kind",
    sessionKey: "disabled-unknown-session", runId: "disabled-unknown-run",
  },
  { sessionKey: "disabled-unknown-session", runId: "disabled-unknown-run" },
);
if (disabledUnknownPayload?.cancel || !disabledUnknownPayload?.payload?.text
    || outboundQueries !== 1) process.exit(113);
await registeredCommand.handler({ args: "on", sessionKey: "restore-unknown-control-session" });
const uncorrelated = await outbound(
  { payload: { text: natural }, kind: "final", sessionKey: "session" },
  {},
);
if (uncorrelated?.cancel !== true || uncorrelated?.reason === natural) process.exit(50);

// Model the two sequential OpenClaw mutation stages. Higher priorities execute
// first, so Agency's minimum-priority handlers validate and seal last.
const replyEvent = {
  payload: { text: "original invalid" }, kind: "final",
  sessionKey: "sealed-session", runId: "sealed-run",
};
const replyHooks = [
  {
    priority: 0,
    handler: async () => ({ payload: { text: "mutated invalid", mediaUrl: "must-not-leak" } }),
  },
  {
    priority: registeredHookOptions.get("reply_payload_sending").priority,
    handler: outbound,
  },
].sort((left, right) => right.priority - left.priority);
let replyCancelled = false;
for (const hook of replyHooks) {
  const result = await hook.handler(replyEvent, { sessionKey: "sealed-session", runId: "sealed-run" });
  if (result?.cancel) { replyCancelled = true; break; }
  if (result?.payload) replyEvent.payload = { ...replyEvent.payload, ...result.payload };
}
if (!replyCancelled || replyEvent.payload.text !== "mutated invalid") process.exit(56);
if (outboundQueries !== 3) process.exit(57);

const validReply = await outbound(
  {
    payload: { text: "validated final" }, kind: "final",
    sessionKey: "message-session", runId: "message-run",
  },
  { sessionKey: "message-session", runId: "message-run" },
);
if (!validReply?.payload?.text || validReply.payload.text === "validated final" || outboundQueries !== 4) process.exit(59);
const messageEvent = { content: validReply.payload.text, sessionKey: "message-session" };
const messageHooks = [
  { priority: 0, handler: async () => ({ content: "leaked original invalid" }) },
  {
    priority: registeredHookOptions.get("message_sending").priority,
    handler: messageSeal,
  },
].sort((left, right) => right.priority - left.priority);
let messageCancelled = false;
let finalContent = messageEvent.content;
for (const hook of messageHooks) {
  const result = await hook.handler(messageEvent, { sessionKey: "message-session" });
  if (result?.content) finalContent = result.content;
  if (result?.cancel) { messageCancelled = true; break; }
}
if (messageCancelled || finalContent !== "validated final") process.exit(58);

const pendingReply = await outbound(
  {
    payload: { text: "another validated final" }, kind: "final",
    sessionKey: "mismatch-session", runId: "mismatch-run",
  },
  { sessionKey: "mismatch-session", runId: "mismatch-run" },
);
if (!pendingReply?.payload?.text || pendingReply.payload.text === "another validated final" || outboundQueries !== 5) process.exit(60);
const mismatch = await messageSeal(
  { content: "different invalid", sessionKey: "mismatch-session" },
  { sessionKey: "mismatch-session" },
);
if (mismatch?.cancel !== true || !mismatch?.cancelReason) process.exit(61);

// If OpenClaw skips or times out the reply hook, the synchronous message seal
// still fails closed because enabled preflight marked the session pending.
await preflight(
  { prompt: "review", sessionKey: "skipped-session", runId: "skipped-run" },
  { sessionKey: "skipped-session", runId: "skipped-run" },
);
const skippedReply = await messageSeal(
  { content: "unverified final", sessionKey: "skipped-session" },
  { sessionKey: "skipped-session" },
);
if (skippedReply?.cancel !== true || !skippedReply?.cancelReason) process.exit(62);
const secondSkippedReply = await messageSeal(
  { content: "second unverified final", sessionKey: "skipped-session" },
  { sessionKey: "skipped-session" },
);
if (secondSkippedReply?.cancel !== true || !secondSkippedReply?.cancelReason) process.exit(64);

failPreflight = true;
let failedPreflight = false;
try {
  await preflight(
    { prompt: "review", sessionKey: "failed-session", runId: "failed-run" },
    { sessionKey: "failed-session", runId: "failed-run" },
  );
} catch {
  failedPreflight = true;
}
failPreflight = false;
const failedPreflightMessage = await messageSeal(
  { content: "unverified after preflight failure", sessionKey: "failed-session" },
  { sessionKey: "failed-session" },
);
if (!failedPreflight || failedPreflightMessage?.cancel !== true) process.exit(71);

// A synchronous bridge timeout/error returns a cancellation before OpenClaw can
// advance its event loop, and no unmarked payload receives a dispatch grant.
failOutboundSync = true;
const failedSynchronousReply = outbound(
  {
    payload: { text: "late validated final" }, kind: "final",
    sessionKey: "late-session", runId: "late-run",
  },
  { sessionKey: "late-session", runId: "late-run" },
);
const timedOutMessage = messageSeal(
  { content: "late validated final", sessionKey: "late-session" },
  { sessionKey: "late-session" },
);
if (failedSynchronousReply?.then || failedSynchronousReply?.cancel !== true || timedOutMessage?.cancel !== true) process.exit(77);
const lateReplay = messageSeal(
  { content: "late validated final", sessionKey: "late-session" },
  { sessionKey: "late-session" },
);
if (lateReplay?.cancel !== true) process.exit(78);
failOutboundSync = false;

// Explicit soft-disable bypasses Agency evidence enforcement, while the
// installer-owned final-only OpenClaw delivery configuration remains applied.
await registeredCommand.handler({ args: "off" });
const disabledBlock = await outbound(
  { payload: { text: "native block" }, kind: "block", sessionKey: "disabled" },
  { sessionKey: "disabled" },
);
const disabledBlockMessage = messageSeal(
  { content: disabledBlock?.payload?.text, sessionKey: "disabled" },
  { sessionKey: "disabled" },
);
const disabledFinal = await outbound(
  { payload: { text: "native final" }, kind: "final", sessionKey: "disabled" },
  { sessionKey: "disabled" },
);
const disabledMessage = messageSeal(
  { content: disabledFinal?.payload?.text, sessionKey: "disabled" },
  { sessionKey: "disabled" },
);
if (disabledBlockMessage?.content !== "native block" || disabledMessage?.content !== "native final") process.exit(63);
const enabledControl = await registeredCommand.handler({
  args: "on", sessionKey: "control-session",
});
const forgedControlReply = await outbound(
  {
    payload: { text: enabledControl.text }, kind: "final",
    sessionKey: "control-session",
  },
  { sessionKey: "control-session" },
);
if (forgedControlReply?.cancel !== true) process.exit(79);
const enabledControlReply = await outbound(
  {
    payload: enabledControl, kind: "final",
    sessionKey: "control-session",
  },
  { sessionKey: "control-session" },
);
const enabledControlMessage = await messageSeal(
  { content: enabledControlReply?.payload?.text, sessionKey: "control-session" },
  { sessionKey: "control-session" },
);
if (enabledControlMessage?.content !== enabledControl.text) process.exit(65);
const statusControl = await registeredCommand.handler({
  args: "status", sessionKey: "control-session",
});
const statusControlReply = await outbound(
  {
    payload: statusControl, kind: "final",
    sessionKey: "control-session",
  },
  { sessionKey: "control-session" },
);
const statusControlMessage = await messageSeal(
  { content: statusControlReply?.payload?.text, sessionKey: "control-session" },
  { sessionKey: "control-session" },
);
if (statusControlMessage?.content !== statusControl.text) process.exit(66);

bridgeCalls.length = 0;
const splitContext = {
  sessionKey: "split-session", runId: "stable-run", turnId: "different-turn",
};
await preflight(
  { prompt: "review", sessionKey: "split-session", runId: "stable-run", turnId: "different-turn" },
  splitContext,
);
await finalize(
  { lastAssistantMessage: "invalid", runId: "stable-run", turnId: "different-turn" },
  splitContext,
);
await outbound(
  {
    payload: { text: "validated split final" }, kind: "final",
    sessionKey: "split-session", runId: "stable-run", turnId: "different-turn",
  },
  splitContext,
);
const correlatedCalls = bridgeCalls.filter((call) =>
  ["preflight", "pre_verify", "outbound_gate"].includes(call.action)
);
if (correlatedCalls.length !== 3 || correlatedCalls.some((call) => call.traceId !== "stable-run")) process.exit(67);

await preflight(
  { prompt: "first", sessionKey: "concurrent-session", runId: "concurrent-a" },
  { sessionKey: "concurrent-session", runId: "concurrent-a" },
);
await preflight(
  { prompt: "second", sessionKey: "concurrent-session", runId: "concurrent-b" },
  { sessionKey: "concurrent-session", runId: "concurrent-b" },
);
const firstConcurrentReply = await outbound(
  {
    payload: { text: "first validated" }, kind: "final",
    sessionKey: "concurrent-session", runId: "concurrent-a",
  },
  { sessionKey: "concurrent-session", runId: "concurrent-a" },
);
const firstConcurrentMessage = await messageSeal(
  { content: firstConcurrentReply?.payload?.text, sessionKey: "concurrent-session" },
  { sessionKey: "concurrent-session" },
);
if (firstConcurrentMessage?.content !== "first validated") process.exit(68);
const sameTextA = await outbound(
  {
    payload: { text: "same text", mediaUrl: "sealed-a" }, kind: "final",
    sessionKey: "race-session", runId: "race-a",
  },
  { sessionKey: "race-session", runId: "race-a" },
);
failOutboundSync = true;
const sameTextB = outbound(
  {
    payload: { text: "same text", mediaUrl: "unsealed-b" }, kind: "final",
    sessionKey: "race-session", runId: "race-b",
  },
  { sessionKey: "race-session", runId: "race-b" },
);
failOutboundSync = false;
if (sameTextB?.cancel !== true) process.exit(88);
const unmarkedRace = messageSeal(
  { content: "same text", sessionKey: "race-session" },
  { sessionKey: "race-session" },
);
if (unmarkedRace?.cancel !== true) process.exit(80);
const sameTextAMessage = messageSeal(
  { content: sameTextA?.payload?.text, sessionKey: "race-session" },
  { sessionKey: "race-session" },
);
if (sameTextAMessage?.content !== "same text") process.exit(81);
const lateSameText = messageSeal(
  { content: "same text", sessionKey: "race-session" },
  { sessionKey: "race-session" },
);
if (lateSameText?.cancel !== true) process.exit(82);
const skippedConcurrentMessage = await messageSeal(
  { content: "second unverified", sessionKey: "concurrent-session" },
  { sessionKey: "concurrent-session" },
);
if (skippedConcurrentMessage?.cancel !== true) process.exit(69);

// Mirror OpenClaw's local buildMessageSendingBeforeDeliver contract: only a
// truthy top-level text field invokes message_sending. The marker-only carrier
// must force that call without mutating any spoken or media surface.
let localMessageInvocations = 0;
function runLocalMessageSending(payload, sessionKey) {
  if (!payload?.text) return payload;
  localMessageInvocations += 1;
  const result = messageSeal(
    { content: payload.text, sessionKey },
    { sessionKey },
  );
  if (result?.cancel) return null;
  return { ...payload, text: result?.content ?? payload.text };
}
const audioReply = outbound(
  {
    payload: {
      spokenText: "audio only",
      ttsSupplement: { spokenText: "audio only" },
      mediaUrl: "voice.ogg",
      audioAsVoice: true,
    },
    kind: "final", sessionKey: "audio-session", runId: "audio-run",
  },
  { sessionKey: "audio-session", runId: "audio-run" },
);
if (audioReply?.then || audioReply?.cancel || !audioReply?.payload?.text) process.exit(89);
if (audioReply.payload.spokenText !== "audio only"
    || audioReply.payload.ttsSupplement?.spokenText !== "audio only"
    || audioReply.payload.mediaUrl !== "voice.ogg") process.exit(90);
const audioMarker = audioReply.payload.text;
const deliveredAudio = runLocalMessageSending(audioReply.payload, "audio-session");
if (!deliveredAudio || deliveredAudio.text !== "" || localMessageInvocations !== 1) process.exit(91);
if (deliveredAudio.spokenText !== "audio only"
    || deliveredAudio.ttsSupplement?.spokenText !== "audio only"
    || deliveredAudio.mediaUrl !== "voice.ogg") process.exit(92);
if (messageSeal(
  { content: audioMarker, sessionKey: "audio-session" },
  { sessionKey: "audio-session" },
)?.cancel !== true) process.exit(93);

const ttsOnlyReply = outbound(
  {
    payload: {
      ttsSupplement: { spokenText: "tts only" },
      mediaUrl: "tts.ogg",
    },
    kind: "final", sessionKey: "tts-session", runId: "tts-run",
  },
  { sessionKey: "tts-session", runId: "tts-run" },
);
if (ttsOnlyReply?.then || ttsOnlyReply?.cancel || !ttsOnlyReply?.payload?.text) process.exit(100);
if (ttsOnlyReply.payload.ttsSupplement?.spokenText !== "tts only"
    || ttsOnlyReply.payload.mediaUrl !== "tts.ogg") process.exit(101);
const deliveredTtsOnly = runLocalMessageSending(ttsOnlyReply.payload, "tts-session");
if (!deliveredTtsOnly || deliveredTtsOnly.text !== ""
    || deliveredTtsOnly.ttsSupplement?.spokenText !== "tts only"
    || deliveredTtsOnly.mediaUrl !== "tts.ogg"
    || localMessageInvocations !== 2) process.exit(102);

const enabledPureMedia = outbound(
  {
    payload: { mediaUrl: "enabled.png" }, kind: "final",
    sessionKey: "enabled-media-session", runId: "enabled-media-run",
  },
  { sessionKey: "enabled-media-session", runId: "enabled-media-run" },
);
if (enabledPureMedia?.then || enabledPureMedia?.cancel !== true) process.exit(94);
failControl = true;
const unknownControlPureMedia = outbound(
  {
    payload: { mediaUrl: "unknown-control.png" }, kind: "final",
    sessionKey: "unknown-control-session", runId: "unknown-control-run",
  },
  { sessionKey: "unknown-control-session", runId: "unknown-control-run" },
);
if (unknownControlPureMedia?.then || unknownControlPureMedia?.cancel !== true) process.exit(107);
failControl = false;

// Model an external CLI/dashboard soft-off after the plugin cached enabled.
// The pure-media tool path must refresh once, seal the marker carrier, strip it
// locally, and reject replay without changing the media payload.
runtimeControlEnabled = false;
const nonMediaRefreshBefore = bridgeCalls.filter(
  (call) => call.action === "control" && call.command === "status",
).length;
const staleDisabledToolText = outbound(
  {
    payload: { text: "disabled tool text" }, kind: "tool",
    sessionKey: "disabled-tool-text-session", runId: "disabled-tool-text-run",
  },
  { sessionKey: "disabled-tool-text-session", runId: "disabled-tool-text-run" },
);
const nonMediaRefreshAfter = bridgeCalls.filter(
  (call) => call.action === "control" && call.command === "status",
).length;
if (nonMediaRefreshAfter - nonMediaRefreshBefore !== 1) process.exit(114);
if (staleDisabledToolText?.then || staleDisabledToolText?.cancel
    || !staleDisabledToolText?.payload?.text
    || staleDisabledToolText.payload.text === "disabled tool text") process.exit(115);
const disableRefreshBefore = bridgeCalls.filter(
  (call) => call.action === "control" && call.command === "status",
).length;
const staleDisabledToolMedia = outbound(
  {
    payload: { mediaUrl: "disabled-tool.png" }, kind: "tool",
    sessionKey: "disabled-tool-session", runId: "disabled-tool-run",
  },
  { sessionKey: "disabled-tool-session", runId: "disabled-tool-run" },
);
if (staleDisabledToolMedia?.then || staleDisabledToolMedia?.cancel
    || !staleDisabledToolMedia?.payload?.text) process.exit(103);
const disableRefreshAfter = bridgeCalls.filter(
  (call) => call.action === "control" && call.command === "status",
).length;
if (disableRefreshAfter - disableRefreshBefore !== 1) process.exit(108);
if (staleDisabledToolMedia.payload.mediaUrl !== "disabled-tool.png") process.exit(104);
const staleDisabledToolMarker = staleDisabledToolMedia.payload.text;
const deliveredDisabledToolMedia = runLocalMessageSending(
  staleDisabledToolMedia.payload,
  "disabled-tool-session",
);
if (!deliveredDisabledToolMedia || deliveredDisabledToolMedia.text !== ""
    || deliveredDisabledToolMedia.mediaUrl !== "disabled-tool.png"
    || localMessageInvocations !== 3) process.exit(105);
if (messageSeal(
  { content: staleDisabledToolMarker, sessionKey: "disabled-tool-session" },
  { sessionKey: "disabled-tool-session" },
)?.cancel !== true) process.exit(106);
await registeredCommand.handler({ args: "on", sessionKey: "restore-tool-control-session" });

await registeredCommand.handler({ args: "off" });
const disabledPureMedia = outbound(
  {
    payload: { mediaUrls: ["", "disabled.png"] }, kind: "final",
    sessionKey: "disabled-media-session", runId: "disabled-media-run",
  },
  { sessionKey: "disabled-media-session", runId: "disabled-media-run" },
);
if (disabledPureMedia?.then || disabledPureMedia?.cancel || !disabledPureMedia?.payload?.text) process.exit(95);
if (disabledPureMedia.payload.mediaUrls?.[1] !== "disabled.png") process.exit(96);
const disabledMediaMarker = disabledPureMedia.payload.text;
const deliveredDisabledMedia = runLocalMessageSending(
  disabledPureMedia.payload,
  "disabled-media-session",
);
if (!deliveredDisabledMedia || deliveredDisabledMedia.text !== ""
    || deliveredDisabledMedia.mediaUrls?.[1] !== "disabled.png"
    || localMessageInvocations !== 4) process.exit(97);
if (messageSeal(
  { content: disabledMediaMarker, sessionKey: "disabled-media-session" },
  { sessionKey: "disabled-media-session" },
)?.cancel !== true) process.exit(98);

// Model an external re-enable while the plugin still caches disabled.  The
// inverse stale state must refresh once and fail closed instead of issuing a
// disabled-mode pure-media seal.
runtimeControlEnabled = true;
const enableRefreshBefore = bridgeCalls.filter(
  (call) => call.action === "control" && call.command === "status",
).length;
const staleEnabledToolMedia = outbound(
  {
    payload: { mediaUrl: "must-not-bypass.png" }, kind: "tool",
    sessionKey: "enabled-tool-session", runId: "enabled-tool-run",
  },
  { sessionKey: "enabled-tool-session", runId: "enabled-tool-run" },
);
const enableRefreshAfter = bridgeCalls.filter(
  (call) => call.action === "control" && call.command === "status",
).length;
if (enableRefreshAfter - enableRefreshBefore !== 1) process.exit(109);
if (staleEnabledToolMedia?.then || staleEnabledToolMedia?.cancel !== true
    || staleEnabledToolMedia?.payload) process.exit(110);
await registeredCommand.handler({ args: "on", sessionKey: "restore-control-session" });
"""
    script = tmp_path / "openclaw-outbound-gate.mjs"
    script.write_text(source, encoding="utf-8")

    completed = subprocess.run(
        [str(shutil.which("node")), str(script)],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
