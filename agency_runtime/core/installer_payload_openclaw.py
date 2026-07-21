"""OpenClaw host plugin payload rendering."""

from __future__ import annotations

import json


def render_openclaw_index(
    timeout_seconds: int,
    *,
    python_executable: str,
    bootstrap_path: str,
    config_path: str = "",
) -> str:
    python = json.dumps(python_executable)
    bootstrap = json.dumps(bootstrap_path)
    config_args = f', "--config", {json.dumps(config_path)}' if config_path else ""
    timeout_ms = timeout_seconds * 1000
    host_timeout_ms = (timeout_seconds + 2) * 1000
    outbound_timeout_ms = min(2_000, max(250, timeout_ms))
    return f"""import {{ definePluginEntry }} from "openclaw/plugin-sdk/plugin-entry";
import {{ execFile, execFileSync }} from "node:child_process";
import {{ createHash, randomUUID }} from "node:crypto";

const PYTHON = {python};
const MODULE_ARGS = ["-I", {bootstrap}, "agency_runtime.adapters.openclaw.node_bridge"{config_args}];
const FINALIZATION_UNAVAILABLE = "Agency Runtime could not verify this response. Restore the local runtime and retry.";
const TERMINAL_REJECTION_MESSAGE = "Agency Runtime blocked this response because its required evidence contract remained invalid after the bounded revision. Start a new turn after restoring the runtime or correcting the response.";
const MAX_BRIDGE_INPUT_BYTES = 1024 * 1024;
const MAX_BRIDGE_OUTPUT_BYTES = 128 * 1024;
const MAX_BRIDGE_TEXT_BYTES = 64 * 1024;
const MAX_OUTBOUND_PAYLOAD_BYTES = 256 * 1024;
const MAX_OUTBOUND_PAYLOAD_NODES = 8192;
const MAX_OUTBOUND_PAYLOAD_DEPTH = 20;
const MAX_TOOL_PAYLOAD_BYTES = 96 * 1024;
const MAX_TOOL_PROJECTION_NODES = 2048;
const MAX_TOOL_PROJECTION_BYTES = MAX_TOOL_PAYLOAD_BYTES;
const TOOL_TRUNCATED = "[truncated]";
const TERMINAL_REJECTION_TTL_MS = 10 * 60 * 1000;
const MAX_TERMINAL_REJECTIONS = 128;
const OUTBOUND_AUTHORIZATION_TTL_MS = 30 * 1000;
const MAX_OUTBOUND_AUTHORIZATIONS = 128;
const CONTROL_AUTHORIZATION_FIELD = "agencyRuntimeControlAuthorization";
const terminalRejections = new Map();
const finalizeAttempts = new Map();
const outboundAuthorizations = new Map();
const controlAuthorizations = new Map();
const nativeChildParents = new Map();
const DISPATCH_MARKER_START = "\u2063";
const DISPATCH_MARKER_ZERO = "\u200b";
const DISPATCH_MARKER_ONE = "\u200c";
const DISPATCH_MARKER_LENGTH = 130;
let runtimeEnabled = true;
let runtimeStateEpoch = 0;
let deliveryCompatibility = {{
  verified: false,
  unsafe: ["OpenClaw delivery configuration has not been inspected"],
}};
const PREVIEW_STREAMING_CHANNELS = new Set([
  "discord", "feishu", "matrix", "mattermost", "msteams", "slack", "telegram",
]);
const TOOL_PAYLOAD_KEYS = [
  "name", "skill", "skill_name", "command", "slug", "agent_slug",
  "agent", "agentId", "agent_id", "recommended_agent", "subagent_type",
  "task_name", "target", "goal", "task", "prompt", "description", "message",
  "work_unit_id", "workUnitId", "unit_id", "task_id", "taskId", "run_id",
  "runId", "session_id", "sessionId", "child_session_key", "childSessionKey",
  "backend", "success", "ok", "delegated", "loaded", "isError", "is_error",
  "cancelled", "canceled", "timed_out", "status", "returncode", "return_code",
  "exit_code", "exitCode", "error", "reason", "detail", "stderr", "result",
  "output", "data", "content", "text",
];

function boundedUtf8(value, maximumBytes) {{
  let text;
  try {{ text = String(value ?? ""); }}
  catch {{ return ""; }}
  const encoded = Buffer.from(text, "utf8");
  if (encoded.length <= maximumBytes) return text;
  let boundary = maximumBytes;
  while (boundary > 0 && (encoded[boundary] & 0xc0) === 0x80) boundary -= 1;
  return encoded.subarray(0, boundary).toString("utf8");
}}

function boundedCorrelation(value) {{
  let text;
  try {{ text = String(value ?? ""); }}
  catch {{ return "!".repeat(513); }}
  return Buffer.byteLength(text, "utf8") <= 512 ? text : "!".repeat(513);
}}

function spendToolProjectionBytes(budget, amount) {{
  budget.bytes = Math.max(0, budget.bytes - Math.max(0, amount));
}}

function projectToolText(value, maximumBytes, budget) {{
  const available = Math.max(0, Math.min(maximumBytes, budget.bytes - 2));
  if (available === 0) {{
    budget.bytes = 0;
    return TOOL_TRUNCATED;
  }}
  const text = boundedUtf8(value, available);
  spendToolProjectionBytes(budget, Buffer.byteLength(text, "utf8") + 2);
  return text;
}}

function projectToolValue(
  value,
  seen = new WeakSet(),
  depth = 0,
  budget = {{ nodes: MAX_TOOL_PROJECTION_NODES, bytes: MAX_TOOL_PROJECTION_BYTES }},
) {{
  if (budget.nodes <= 0 || budget.bytes <= 0) return TOOL_TRUNCATED;
  budget.nodes -= 1;
  if (value === null || value === undefined) {{
    spendToolProjectionBytes(budget, 4);
    return null;
  }}
  if (typeof value === "string") return projectToolText(value, 16 * 1024, budget);
  if (typeof value === "number") {{
    spendToolProjectionBytes(budget, 32);
    return Number.isFinite(value) ? value : null;
  }}
  if (typeof value === "boolean") {{
    spendToolProjectionBytes(budget, 5);
    return value;
  }}
  if (typeof value !== "object") return projectToolText(value, 1024, budget);
  if (depth >= 6 || seen.has(value)) {{
    spendToolProjectionBytes(budget, 13);
    return TOOL_TRUNCATED;
  }}
  seen.add(value);
  try {{
    let isArray;
    try {{
      isArray = Array.isArray(value);
    }} catch {{
      spendToolProjectionBytes(budget, 13);
      return TOOL_TRUNCATED;
    }}
    spendToolProjectionBytes(budget, 2);
    if (isArray) {{
      const result = [];
      let length;
      try {{
        length = Math.min(Math.max(Number(value.length) || 0, 0), 32);
      }} catch {{
        return [TOOL_TRUNCATED];
      }}
      for (let index = 0; index < length; index += 1) {{
        if (budget.nodes <= 0 || budget.bytes <= 0) {{
          result.push(TOOL_TRUNCATED);
          break;
        }}
        let item;
        try {{
          item = value[index];
        }} catch {{
          item = TOOL_TRUNCATED;
        }}
        if (result.length > 0) spendToolProjectionBytes(budget, 1);
        result.push(projectToolValue(item, seen, depth + 1, budget));
      }}
      return result;
    }}
    const result = Object.create(null);
    for (const key of TOOL_PAYLOAD_KEYS) {{
      if (budget.nodes <= 0 || budget.bytes <= 0) break;
      let nested;
      try {{
        if (!(key in value)) continue;
        nested = value[key];
      }} catch {{
        continue;
      }}
      spendToolProjectionBytes(budget, Buffer.byteLength(key, "utf8") + 4);
      result[key] = projectToolValue(nested, seen, depth + 1, budget);
    }}
    return result;
  }} finally {{
    seen.delete(value);
  }}
}}

function boundedToolPayload(value) {{
  const projected = projectToolValue(value);
  let encoded = JSON.stringify(projected);
  if (Buffer.byteLength(encoded, "utf8") <= MAX_TOOL_PAYLOAD_BYTES) return projected;
  if (Array.isArray(projected)) {{
    const result = [];
    for (const item of projected) {{
      const candidate = [...result, item];
      encoded = JSON.stringify(candidate);
      if (Buffer.byteLength(encoded, "utf8") > MAX_TOOL_PAYLOAD_BYTES) break;
      result.push(item);
    }}
    return result;
  }}
  if (projected && typeof projected === "object") {{
    const result = {{}};
    for (const [key, item] of Object.entries(projected)) {{
      const candidate = {{ ...result, [key]: item }};
      encoded = JSON.stringify(candidate);
      if (Buffer.byteLength(encoded, "utf8") <= MAX_TOOL_PAYLOAD_BYTES) {{
        result[key] = item;
      }}
    }}
    return result;
  }}
  return "[truncated]";
}}

function serializeBridgePayload(payload) {{
  const action = boundedUtf8(payload?.action, 64);
  const projected = {{
    action,
    command: boundedUtf8(payload?.command, 256),
    sessionId: boundedCorrelation(payload?.sessionId),
    traceId: boundedCorrelation(payload?.traceId),
    parentSessionId: boundedCorrelation(payload?.parentSessionId),
    parentTraceId: boundedCorrelation(payload?.parentTraceId),
    userMessage: boundedUtf8(payload?.userMessage, MAX_BRIDGE_TEXT_BYTES),
    finalResponse: boundedUtf8(payload?.finalResponse, MAX_BRIDGE_TEXT_BYTES),
    outboundPayload: boundedUtf8(payload?.outboundPayload, MAX_OUTBOUND_PAYLOAD_BYTES),
    model: boundedUtf8(payload?.model, 1024),
    attempt: Number.isSafeInteger(payload?.attempt) ? payload.attempt : 0,
    toolName: boundedUtf8(payload?.toolName, 1024),
    error: boundedUtf8(payload?.error, 32 * 1024),
  }};
  if (action === "post_tool_call") {{
    projected.toolInput = boundedToolPayload(payload?.toolInput);
    projected.toolResult = boundedToolPayload(payload?.toolResult);
  }}
  const encoded = JSON.stringify(projected);
  if (Buffer.byteLength(encoded, "utf8") > MAX_BRIDGE_INPUT_BYTES) {{
    throw new Error("Agency Runtime bridge payload exceeds the transport limit");
  }}
  return encoded;
}}

function parseAgencyResult(stdout) {{
  const text = String(stdout || "");
  if (Buffer.byteLength(text, "utf8") > MAX_BRIDGE_OUTPUT_BYTES) {{
    throw new Error("Agency Runtime bridge response exceeds the transport limit");
  }}
  const result = JSON.parse(text || "{{}}");
  if (!result || Array.isArray(result) || typeof result !== "object") {{
    throw new Error("Agency Runtime bridge returned an invalid response");
  }}
  return result;
}}

function invokeAgencySync(payload, processTimeoutMs = {outbound_timeout_ms}) {{
  const encoded = serializeBridgePayload(payload);
  const safeTimeoutMs = Number.isSafeInteger(processTimeoutMs) && processTimeoutMs > 0
    ? Math.min(processTimeoutMs, {outbound_timeout_ms})
    : {outbound_timeout_ms};
  const stdout = execFileSync(PYTHON, MODULE_ARGS, {{
    input: encoded,
    encoding: "utf8",
    timeout: safeTimeoutMs,
    maxBuffer: MAX_BRIDGE_OUTPUT_BYTES,
    windowsHide: true,
    shell: false,
  }});
  return parseAgencyResult(stdout);
}}

function invokeAgency(payload, processTimeoutMs = {timeout_ms}) {{
  let encoded;
  try {{
    encoded = serializeBridgePayload(payload);
  }} catch (error) {{
    return Promise.reject(error instanceof Error ? error : new Error(String(error)));
  }}
  return new Promise((resolve, reject) => {{
    let settled = false;
    let child;
    const stopChild = () => {{
      try {{ child?.stdin?.destroy?.(); }} catch {{ /* best-effort child cleanup */ }}
      try {{ child?.kill?.(); }} catch {{ /* best-effort child cleanup */ }}
    }};
    const rejectOnce = (error) => {{
      if (settled) return;
      settled = true;
      stopChild();
      reject(error instanceof Error ? error : new Error(String(error || "stdin write failed")));
    }};
    const safeTimeoutMs = Number.isSafeInteger(processTimeoutMs) && processTimeoutMs > 0
      ? Math.min(processTimeoutMs, {timeout_ms})
      : {timeout_ms};
    child = execFile(PYTHON, MODULE_ARGS, {{
      timeout: safeTimeoutMs,
      maxBuffer: 1024 * 1024,
      windowsHide: true,
    }}, (error, stdout, stderr) => {{
      if (settled) return;
      if (error) {{
        rejectOnce(new Error(String(stderr || error.message || "Agency Runtime hook failed").trim()));
        return;
      }}
      try {{
        const result = parseAgencyResult(stdout);
        settled = true;
        resolve(result);
      }} catch (parseError) {{
        rejectOnce(parseError);
      }}
    }});
    if (settled) {{
      stopChild();
      return;
    }}
    if (!child.stdin) {{
      rejectOnce(new Error("Agency Runtime bridge stdin is unavailable"));
      return;
    }}
    child.stdin.on("error", rejectOnce);
    try {{
      child.stdin.end(encoded, "utf8", (error) => {{
        if (error) rejectOnce(error);
      }});
    }} catch (error) {{
      rejectOnce(error);
    }}
  }});
}}

function sessionId(event, ctx) {{
  return String(ctx?.sessionKey || ctx?.sessionId || event?.sessionKey || event?.sessionId || "");
}}

function traceId(event, ctx) {{
  return String(ctx?.runId || event?.runId || ctx?.turnId || event?.turnId || "");
}}

function modelId(ctx) {{
  return String(ctx?.modelId || ctx?.activeModel?.modelId || ctx?.model || "");
}}

function modelProviderId(ctx) {{
  return String(
    ctx?.modelProviderId
    || ctx?.activeModel?.provider
    || ctx?.activeModel?.providerId
    || ""
  );
}}

function modelCallReceipt(event, ctx) {{
  const provider = String(event?.provider || modelProviderId(ctx));
  const requestedModel = modelId(ctx);
  const observedModel = String(event?.model || requestedModel);
  const routerBacked = provider.toLowerCase().includes("litellm");
  return {{
    action: "post_api_request",
    sessionId: String(event?.sessionKey || event?.sessionId || sessionId(event, ctx)),
    traceId: String(event?.runId || traceId(event, ctx)),
    requestedModel,
    modelGroup: requestedModel,
    resolvedProvider: routerBacked ? "" : provider,
    resolvedModel: routerBacked ? "" : observedModel,
    modelId: String(event?.callId || ""),
    source: routerBacked ? "openclaw-litellm-router" : "openclaw-model-call",
    status: String(event?.outcome || "success"),
  }};
}}

function finalAssistantText(event) {{
  return String(event?.lastAssistantMessage || event?.finalAssistantText || event?.assistantText || event?.text || "");
}}

function revisionKey(decision, event, ctx) {{
  const turn = String(decision?.turnId || traceId(event, ctx));
  const correlation = `${{sessionId(event, ctx)}}\\0${{turn}}`;
  const digest = createHash("sha256").update(correlation).digest("hex").slice(0, 32);
  return `agency-preflight-header:${{digest}}`;
}}

function responseDigest(value) {{
  return createHash("sha256").update(String(value || ""), "utf8").digest("hex");
}}

function canonicalJsonValue(
  value,
  seen = new WeakSet(),
  depth = 0,
  budget = {{ nodes: MAX_OUTBOUND_PAYLOAD_NODES }},
) {{
  budget.nodes -= 1;
  if (budget.nodes < 0 || depth > MAX_OUTBOUND_PAYLOAD_DEPTH) {{
    throw new Error("outbound payload exceeds the canonicalization budget");
  }}
  if (value === null) return null;
  if (typeof value === "string" || typeof value === "boolean") return value;
  if (typeof value === "number") return Number.isFinite(value) ? value : null;
  if (["undefined", "function", "symbol"].includes(typeof value)) return undefined;
  if (typeof value === "bigint") throw new Error("outbound payload contains a bigint");
  if (typeof value !== "object" || seen.has(value)) {{
    throw new Error("outbound payload is not an acyclic JSON value");
  }}
  seen.add(value);
  try {{
    if (Array.isArray(value)) {{
      return value.map((item) => canonicalJsonValue(item, seen, depth + 1, budget) ?? null);
    }}
    const result = Object.create(null);
    for (const key of Object.keys(value).sort()) {{
      const item = canonicalJsonValue(value[key], seen, depth + 1, budget);
      if (item !== undefined) result[key] = item;
    }}
    return result;
  }} finally {{
    seen.delete(value);
  }}
}}

function canonicalOutboundPayload(payload) {{
  const canonical = canonicalJsonValue(payload);
  if (!canonical || Array.isArray(canonical) || typeof canonical !== "object") {{
    throw new Error("outbound payload must be an object");
  }}
  const encoded = JSON.stringify(canonical);
  if (Buffer.byteLength(encoded, "utf8") > MAX_OUTBOUND_PAYLOAD_BYTES) {{
    throw new Error("outbound payload exceeds the bridge limit");
  }}
  return encoded;
}}

function outboundTextSurfaces(payload) {{
  return [
    payload?.text,
    payload?.spokenText,
    payload?.ttsSupplement?.spokenText,
  ].filter((value) => typeof value === "string" && value.trim());
}}

function outboundPolicyText(payload) {{
  const surfaces = outboundTextSurfaces(payload);
  if (surfaces.length === 0) return "";
  const policyText = surfaces[0];
  if (surfaces.some((value) => value !== policyText)) {{
    throw new Error("outbound text surfaces disagree");
  }}
  return policyText;
}}

function newDispatchMarker() {{
  const hexadecimal = randomUUID().replaceAll("-", "");
  let bits = "";
  for (const digit of hexadecimal) {{
    const value = Number.parseInt(digit, 16);
    for (let shift = 3; shift >= 0; shift -= 1) {{
      bits += (value & (1 << shift)) === 0 ? DISPATCH_MARKER_ZERO : DISPATCH_MARKER_ONE;
    }}
  }}
  return `${{DISPATCH_MARKER_START}}${{bits}}${{DISPATCH_MARKER_START}}`;
}}

function hasOutboundMedia(payload) {{
  if (typeof payload?.mediaUrl === "string" && payload.mediaUrl.trim()) return true;
  return Array.isArray(payload?.mediaUrls)
    && payload.mediaUrls.some((value) => typeof value === "string" && value.trim());
}}

function markOutboundPayload(payload, allowMediaOnly = false) {{
  const marked = canonicalJsonValue(payload);
  if (!marked || Array.isArray(marked) || typeof marked !== "object") return null;
  const marker = newDispatchMarker();
  if (typeof marked.text === "string" && marked.text.trim()) {{
    marked.text = `${{marked.text}}${{marker}}`;
    return {{ payload: marked, texts: [marked.text] }};
  }}
  if (
    (typeof marked.spokenText === "string" && marked.spokenText.trim())
    || (
      typeof marked.ttsSupplement?.spokenText === "string"
      && marked.ttsSupplement.spokenText.trim()
    )
  ) {{
    // OpenClaw's local dispatcher invokes message_sending only when top-level
    // text is truthy. Carry the one-use seal in a marker-only text field so
    // audio/TTS content stays byte-for-byte unchanged and the delivery hook
    // strips the carrier before transport rendering.
    marked.text = marker;
    return {{ payload: marked, texts: [marked.text] }};
  }}
  if (allowMediaOnly && hasOutboundMedia(marked)) {{
    marked.text = marker;
    return {{ payload: marked, texts: [marked.text] }};
  }}
  return null;
}}

function unmarkOutboundText(value) {{
  if (typeof value !== "string" || value.length < DISPATCH_MARKER_LENGTH) return null;
  const marker = value.slice(-DISPATCH_MARKER_LENGTH);
  if (
    marker[0] !== DISPATCH_MARKER_START
    || marker[DISPATCH_MARKER_LENGTH - 1] !== DISPATCH_MARKER_START
  ) return null;
  for (const bit of marker.slice(1, -1)) {{
    if (bit !== DISPATCH_MARKER_ZERO && bit !== DISPATCH_MARKER_ONE) return null;
  }}
  return {{ content: value.slice(0, -DISPATCH_MARKER_LENGTH), markedText: value }};
}}

function authorizeMarkedPayload(session, payload, kind, run = "", allowMediaOnly = false) {{
  try {{
    const marked = markOutboundPayload(payload, allowMediaOnly);
    if (!marked) return null;
    for (const text of marked.texts) {{
      if (!authorizeOutbound(session, text, kind, run)) return null;
    }}
    return marked.payload;
  }} catch {{
    return null;
  }}
}}

function streamingSettings(value) {{
  if (!value || typeof value !== "object" || Array.isArray(value)) {{
    return {{ mode: undefined, blockEnabled: undefined }};
  }}
  const streaming = value.streaming;
  if (!streaming || typeof streaming !== "object" || Array.isArray(streaming)) {{
    return {{
      mode: typeof streaming === "string" ? streaming.toLowerCase() : undefined,
      blockEnabled: value.blockStreaming === true ? true : undefined,
    }};
  }}
  return {{
    mode: typeof streaming.mode === "string" ? streaming.mode.toLowerCase() : undefined,
    blockEnabled: typeof streaming.block?.enabled === "boolean"
      ? streaming.block.enabled
      : value.blockStreaming === true ? true : undefined,
  }};
}}

function inspectFinalOnlyDelivery(config) {{
  const unsafe = [];
  if (config?.agents?.defaults?.blockStreamingDefault === "on") {{
    unsafe.push("agents.defaults.blockStreamingDefault");
  }}
  const channels = config?.channels;
  if (!channels || typeof channels !== "object" || Array.isArray(channels)) {{
    return {{ verified: true, unsafe }};
  }}
  for (const [channelName, channel] of Object.entries(channels)) {{
    if (!channel || typeof channel !== "object" || Array.isArray(channel) || channel.enabled === false) {{
      continue;
    }}
    const channelSettings = streamingSettings(channel);
    const normalizedName = String(channelName).toLowerCase();
    if (
      channelSettings.blockEnabled === true
      || (PREVIEW_STREAMING_CHANNELS.has(normalizedName) && channelSettings.mode !== "off")
      || (channelSettings.mode && channelSettings.mode !== "off")
    ) {{
      unsafe.push(`channels.${{channelName}}.streaming`);
    }}
    const accounts = channel.accounts;
    if (!accounts || typeof accounts !== "object" || Array.isArray(accounts)) continue;
    for (const [accountName, account] of Object.entries(accounts)) {{
      if (!account || typeof account !== "object" || Array.isArray(account) || account.enabled === false) {{
        continue;
      }}
      const accountSettings = streamingSettings(account);
      const effectiveMode = accountSettings.mode ?? channelSettings.mode;
      const effectiveBlock = accountSettings.blockEnabled ?? channelSettings.blockEnabled;
      if (
        effectiveBlock === true
        || (PREVIEW_STREAMING_CHANNELS.has(normalizedName) && effectiveMode !== "off")
        || (effectiveMode && effectiveMode !== "off")
      ) {{
        unsafe.push(`channels.${{channelName}}.accounts.${{accountName}}.streaming`);
      }}
    }}
  }}
  return {{ verified: true, unsafe }};
}}

function outboundAuthorizationKey(session, text, kind = "final") {{
  if (!session || !text) return "";
  return `${{responseDigest(session)}}\\0${{responseDigest(text)}}\\0${{kind}}`;
}}

function pruneOutboundAuthorizations(now = Date.now()) {{
  for (const [key, state] of outboundAuthorizations) {{
    if (Number(state?.expiresAt || 0) <= now) outboundAuthorizations.delete(key);
  }}
  while (outboundAuthorizations.size >= MAX_OUTBOUND_AUTHORIZATIONS) {{
    outboundAuthorizations.delete(outboundAuthorizations.keys().next().value);
  }}
  for (const [key, state] of controlAuthorizations) {{
    if (Number(state?.expiresAt || 0) <= now) controlAuthorizations.delete(key);
  }}
  while (controlAuthorizations.size >= MAX_OUTBOUND_AUTHORIZATIONS) {{
    controlAuthorizations.delete(controlAuthorizations.keys().next().value);
  }}
}}

function authorizeOutbound(session, text, kind = "final", run = "") {{
  const key = outboundAuthorizationKey(session, text, kind);
  if (!key) return false;
  const now = Date.now();
  pruneOutboundAuthorizations(now);
  const previous = Number(outboundAuthorizations.get(key)?.count || 0);
  const previousRuns = Array.isArray(outboundAuthorizations.get(key)?.runs)
    ? outboundAuthorizations.get(key).runs
    : [];
  outboundAuthorizations.set(key, {{
    count: Math.min(previous + 1, 8),
    expiresAt: now + OUTBOUND_AUTHORIZATION_TTL_MS,
    runs: [...previousRuns.slice(-7), String(run || "")],
  }});
  return true;
}}

function controlAuthorizationKey(session, payload, kind, canonicalPayload) {{
  const nonce = payload?.channelData?.[CONTROL_AUTHORIZATION_FIELD];
  if (!session || kind !== "final" || typeof nonce !== "string" || !nonce.trim()) return "";
  return [
    responseDigest(session), responseDigest(nonce), responseDigest(canonicalPayload), kind,
  ].join("\\0");
}}

function authorizeControlOutbound(session, payload, kind = "final") {{
  const canonicalPayload = canonicalOutboundPayload(payload);
  const key = controlAuthorizationKey(session, payload, kind, canonicalPayload);
  if (!key) return false;
  const now = Date.now();
  pruneOutboundAuthorizations(now);
  controlAuthorizations.set(key, {{ expiresAt: now + OUTBOUND_AUTHORIZATION_TTL_MS }});
  return true;
}}

function consumeControlOutboundAuthorization(session, payload, kind, canonicalPayload) {{
  const key = controlAuthorizationKey(session, payload, kind, canonicalPayload);
  const state = key ? controlAuthorizations.get(key) : undefined;
  if (Number(state?.expiresAt || 0) <= Date.now()) return false;
  controlAuthorizations.delete(key);
  return true;
}}

function consumeOutboundAuthorization(session, text) {{
  if (!session) return null;
  const now = Date.now();
  pruneOutboundAuthorizations(now);
  for (const kind of ["final", "tool", "control", "disabled"]) {{
    const exact = outboundAuthorizationKey(session, text, kind);
    const exactState = outboundAuthorizations.get(exact);
    if (
      Number(exactState?.expiresAt || 0) > now
      && Number(exactState?.count || 0) > 0
    ) {{
      const runs = Array.isArray(exactState.runs) ? [...exactState.runs] : [];
      const runId = String(runs.shift() || "");
      if (Number(exactState.count) > 1) {{
        outboundAuthorizations.set(exact, {{
          ...exactState,
          count: exactState.count - 1,
          runs,
        }});
      }} else {{
        outboundAuthorizations.delete(exact);
      }}
      return {{ kind, runId }};
    }}
  }}
  return null;
}}

function terminalRejectionKey(session, run, text) {{
  if (!session || !run || !text) return "";
  return `${{session}}\\0${{run}}\\0${{responseDigest(text)}}`;
}}

function pruneTerminalRejections(now = Date.now()) {{
  for (const [key, state] of terminalRejections) {{
    if (Number(state?.expiresAt || 0) <= now) terminalRejections.delete(key);
  }}
  while (terminalRejections.size >= MAX_TERMINAL_REJECTIONS) {{
    terminalRejections.delete(terminalRejections.keys().next().value);
  }}
  for (const [key, state] of finalizeAttempts) {{
    if (Number(state?.expiresAt || 0) <= now) finalizeAttempts.delete(key);
  }}
  while (finalizeAttempts.size >= MAX_TERMINAL_REJECTIONS) {{
    finalizeAttempts.delete(finalizeAttempts.keys().next().value);
  }}
}}

function nextFinalizeAttempt(event, ctx) {{
  const session = sessionId(event, ctx);
  const run = traceId(event, ctx);
  if (!session || !run) return 0;
  const now = Date.now();
  pruneTerminalRejections(now);
  const key = `${{session}}\\0${{run}}`;
  const previous = Number(finalizeAttempts.get(key)?.count || 0);
  finalizeAttempts.set(key, {{
    count: Math.min(previous + 1, 2),
    expiresAt: now + TERMINAL_REJECTION_TTL_MS,
  }});
  return previous > 0 ? 1 : 0;
}}

function rememberTerminalRejection(decision, event, ctx) {{
  if (decision?.terminalRejected !== true) return;
  const responseHash = String(decision?.responseHash || "");
  const text = finalAssistantText(event);
  if (!/^[0-9a-f]{{64}}$/.test(responseHash) || responseHash !== responseDigest(text)) return;
  const key = terminalRejectionKey(
    sessionId(event, ctx),
    String(decision?.turnId || traceId(event, ctx)),
    text,
  );
  if (!key) return;
  const now = Date.now();
  pruneTerminalRejections(now);
  terminalRejections.set(key, {{
    expiresAt: now + TERMINAL_REJECTION_TTL_MS,
    message: String(decision?.message || TERMINAL_REJECTION_MESSAGE),
  }});
}}

function blockedReplyResult(session, run, message = TERMINAL_REJECTION_MESSAGE) {{
  void session;
  void run;
  return {{ cancel: true, reason: String(message || TERMINAL_REJECTION_MESSAGE) }};
}}

function observeRuntimeState(result, epoch = runtimeStateEpoch) {{
  if (epoch !== runtimeStateEpoch) return false;
  if (
    result?.runtime_enabled === false
    || result?.runtimeEnabled === false
    || result?.runtimeDisabled === true
  ) {{
    runtimeEnabled = false;
    outboundAuthorizations.clear();
    controlAuthorizations.clear();
  }} else if (result?.runtime_enabled === true || result?.runtimeEnabled === true) {{
    runtimeEnabled = true;
  }}
  return true;
}}

function refreshRuntimeStateSync() {{
  const stateEpoch = ++runtimeStateEpoch;
  try {{
    const state = invokeAgencySync({{ action: "control", command: "status" }});
    return observeRuntimeState(state, stateEpoch);
  }} catch {{
    runtimeEnabled = true;
    return false;
  }}
}}

export default definePluginEntry({{
  id: "agency-preflight",
  name: "Agency Preflight",
  description: "Agency Runtime routing, evidence, and final-response enforcement.",
  register(api) {{
    deliveryCompatibility = inspectFinalOnlyDelivery(api?.config);
    api.on("gateway_start", (_event, ctx) => {{
      deliveryCompatibility = inspectFinalOnlyDelivery(ctx?.config);
    }});

    api.on("before_agent_run", async () => {{
      const stateEpoch = ++runtimeStateEpoch;
      try {{
        const state = await invokeAgency({{ action: "control", command: "status" }});
        observeRuntimeState(state, stateEpoch);
      }} catch {{
        runtimeEnabled = true;
        return {{
          outcome: "block",
          reason: "agency_runtime_unavailable",
          category: "runtime_unavailable",
          message: "Agency Runtime could not prove its enforcement state. Restore the local runtime and retry.",
        }};
      }}
      if (!runtimeEnabled) return {{ outcome: "pass" }};
      if (deliveryCompatibility.verified && deliveryCompatibility.unsafe.length === 0) {{
        return {{ outcome: "pass" }};
      }}
      return {{
        outcome: "block",
        reason: "agency_final_only_delivery_required",
        category: "runtime_configuration",
        message: "Agency Runtime requires OpenClaw preview and block streaming to be disabled. Stop the gateway and rerun the Agency installer.",
      }};
    }}, {{ priority: 1000, timeoutMs: {host_timeout_ms} }});

    api.registerCommand({{
      name: "agency",
      description: "Agency Runtime status, on, or off",
      acceptsArgs: true,
      requireAuth: true,
      handler: async (ctx) => {{
        const stateEpoch = ++runtimeStateEpoch;
        const result = await invokeAgency({{
          action: "control",
          command: String(ctx?.args || "status"),
        }});
        observeRuntimeState(result, stateEpoch);
        const text = String(result?.message || "Agency Runtime control completed.");
        if (!runtimeEnabled) return {{ text }};
        const payload = {{
          text,
          channelData: {{ [CONTROL_AUTHORIZATION_FIELD]: randomUUID() }},
        }};
        if (!authorizeControlOutbound(sessionId({{}}, ctx), payload)) {{
          throw new Error("Agency Runtime could not bind its control reply");
        }}
        return payload;
      }},
    }});

    api.on("before_prompt_build", async (event, ctx) => {{
      const stateEpoch = ++runtimeStateEpoch;
      const childParent = nativeChildParents.get(sessionId(event, ctx));
      const result = await invokeAgency({{
        action: "preflight",
        sessionId: sessionId(event, ctx),
        traceId: traceId(event, ctx),
        userMessage: String(event?.prompt || ""),
        model: modelId(ctx),
        parentSessionId: String(childParent?.sessionId || ""),
        parentTraceId: String(childParent?.traceId || ""),
      }});
      const stateApplied = observeRuntimeState(result, stateEpoch);
      if (!stateApplied && !runtimeEnabled) return undefined;
      return result.context ? {{ appendContext: result.context }} : undefined;
    }}, {{ priority: 100, timeoutMs: {host_timeout_ms} }});

    api.on("model_call_ended", async (event, ctx) => {{
      if (!runtimeEnabled) return;
      await invokeAgency(modelCallReceipt(event, ctx));
    }}, {{ timeoutMs: {host_timeout_ms} }});

    api.on("subagent_spawned", async (event, ctx) => {{
      if (!runtimeEnabled) return;
      const childSession = String(event?.childSessionKey || "");
      const parentSession = sessionId(event, ctx);
      const parentTrace = String(ctx?.runId || ctx?.turnId || event?.parentRunId || event?.parentTurnId || "");
      if (childSession && parentSession && parentTrace) {{
        nativeChildParents.set(childSession, {{ sessionId: parentSession, traceId: parentTrace }});
        if (nativeChildParents.size > 512) nativeChildParents.delete(nativeChildParents.keys().next().value);
      }}
      await invokeAgency({{
        action: "native_child_started",
        sessionId: sessionId(event, ctx),
        traceId: String(ctx?.runId || ctx?.turnId || event?.parentRunId || event?.parentTurnId || ""),
        workUnitId: String(event?.workUnitId || event?.taskName || ""),
        workerId: String(event?.childSessionKey || ""),
        nativeRunId: String(event?.runId || ""),
      }});
    }}, {{ timeoutMs: {host_timeout_ms} }});

    api.on("subagent_ended", async (event, ctx) => {{
      if (!runtimeEnabled) return;
      nativeChildParents.delete(String(event?.targetSessionKey || ""));
      await invokeAgency({{
        action: "native_child_ended",
        sessionId: sessionId(event, ctx),
        traceId: String(ctx?.runId || ctx?.turnId || event?.parentRunId || event?.parentTurnId || ""),
        workUnitId: String(event?.workUnitId || event?.taskName || ""),
        workerId: String(event?.targetSessionKey || ""),
        nativeRunId: String(event?.runId || ""),
        outcome: String(event?.outcome || "unknown"),
        error: String(event?.error || event?.reason || ""),
      }});
    }}, {{ timeoutMs: {host_timeout_ms} }});

    api.on("after_tool_call", async (event, ctx) => {{
      if (!runtimeEnabled) return;
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
      const stateEpoch = ++runtimeStateEpoch;
      let decision;
      const attempt = nextFinalizeAttempt(event, ctx);
      const finalText = finalAssistantText(event);
      try {{
        decision = await invokeAgency({{
          action: "pre_verify",
          sessionId: sessionId(event, ctx),
          traceId: traceId(event, ctx),
          finalResponse: finalText,
          model: modelId(ctx),
          attempt,
        }});
      }} catch {{
        decision = attempt > 0
          ? {{
              action: "terminal",
              message: FINALIZATION_UNAVAILABLE,
              terminalRejected: true,
              terminalStatus: "verification_failed",
              responseHash: responseDigest(finalText),
              turnId: traceId(event, ctx),
            }}
          : {{ action: "continue", message: FINALIZATION_UNAVAILABLE }};
      }}
      const stateApplied = observeRuntimeState(decision, stateEpoch);
      if (!stateApplied) {{
        if (!runtimeEnabled) return undefined;
        if (attempt > 0) {{
          rememberTerminalRejection({{
            action: "terminal",
            message: FINALIZATION_UNAVAILABLE,
            terminalRejected: true,
            terminalStatus: "verification_failed",
            responseHash: responseDigest(finalText),
            turnId: traceId(event, ctx),
          }}, event, ctx);
          return undefined;
        }}
        return {{
          action: "revise",
          reason: FINALIZATION_UNAVAILABLE,
          retry: {{
            instruction: FINALIZATION_UNAVAILABLE,
            idempotencyKey: revisionKey(decision, event, ctx),
            maxAttempts: 1,
          }},
        }};
      }}
      if (!runtimeEnabled) return undefined;
      if (decision?.terminalRejected === true) {{
        rememberTerminalRejection(decision, event, ctx);
        return undefined;
      }}
      if (decision.action !== "continue") return undefined;
      return {{
        action: "revise",
        reason: String(decision.message || "Agency Runtime response contract is incomplete."),
        retry: {{
          instruction: String(decision.message || "Repair the Agency Runtime response contract."),
          idempotencyKey: revisionKey(decision, event, ctx),
          maxAttempts: 1,
        }},
      }};
    }}, {{ priority: 100, timeoutMs: {host_timeout_ms} }});

    api.on("reply_payload_sending", (event, ctx) => {{
      try {{
      const session = String(event?.sessionKey || ctx?.sessionKey || "");
      const kind = String(event?.kind || "");
      if (kind !== "final") {{
        refreshRuntimeStateSync();
        if (!runtimeEnabled) {{
          const marked = authorizeMarkedPayload(session, event?.payload, "disabled", "", true);
          return marked
            ? {{ payload: marked }}
            : {{ cancel: true, reason: FINALIZATION_UNAVAILABLE }};
        }}
        if (kind === "tool") {{
          const marked = authorizeMarkedPayload(session, event?.payload, "tool");
          return marked
            ? {{ payload: marked }}
            : {{ cancel: true, reason: FINALIZATION_UNAVAILABLE }};
        }}
        if (kind === "block") {{
          return {{
            cancel: true,
            reason: "Agency Runtime requires final-only OpenClaw delivery while enforcement is enabled.",
          }};
        }}
        return {{
          cancel: true,
          reason: "Agency Runtime rejected an unsupported OpenClaw reply payload kind.",
        }};
      }}
      const run = String(event?.runId || ctx?.runId || "");
      let text;
      let outboundPayload;
      try {{
        text = outboundPolicyText(event?.payload);
        outboundPayload = canonicalOutboundPayload(event.payload);
      }} catch {{
        return blockedReplyResult(session, run, FINALIZATION_UNAVAILABLE);
      }}
      if (!text) {{
        refreshRuntimeStateSync();
        if (!runtimeEnabled) {{
          const marked = authorizeMarkedPayload(session, event.payload, "disabled", "", true);
          if (marked) return {{ payload: marked }};
        }}
        return blockedReplyResult(session, run, FINALIZATION_UNAVAILABLE);
      }}
      if (consumeControlOutboundAuthorization(session, event.payload, kind, outboundPayload)) {{
        const marked = authorizeMarkedPayload(session, event.payload, "control");
        if (marked) return {{ payload: marked }};
        return blockedReplyResult(session, run, FINALIZATION_UNAVAILABLE);
      }}
      const key = terminalRejectionKey(session, run, text);
      if (!session || !text) return blockedReplyResult(session, run, FINALIZATION_UNAVAILABLE);
      const now = Date.now();
      pruneTerminalRejections(now);
      const terminalRejection = key ? terminalRejections.get(key) : undefined;
      if (Number(terminalRejection?.expiresAt || 0) > now) {{
        return blockedReplyResult(session, run, terminalRejection?.message);
      }}
      let gate;
      const stateEpoch = ++runtimeStateEpoch;
      try {{
        gate = invokeAgencySync({{
          action: "outbound_gate",
          sessionId: session,
          traceId: run,
          finalResponse: text,
          outboundPayload,
          model: modelId(ctx),
        }}, {outbound_timeout_ms});
      }} catch {{
        return blockedReplyResult(session, run, FINALIZATION_UNAVAILABLE);
      }}
      const exactGateHash = String(gate?.responseHash || "") === responseDigest(outboundPayload);
      const stateApplied = observeRuntimeState(gate, stateEpoch);
      if (!stateApplied) return blockedReplyResult(session, run, FINALIZATION_UNAVAILABLE);
      if (!runtimeEnabled) {{
        const marked = gate?.action === "allow" && exactGateHash
          ? authorizeMarkedPayload(session, event.payload, "disabled", "", true)
          : null;
        if (marked) return {{ payload: marked }};
        return blockedReplyResult(session, run, FINALIZATION_UNAVAILABLE);
      }}
      if (gate?.action === "allow" && exactGateHash) {{
        const effectiveRun = String(gate?.turnId || run || "");
        if (!effectiveRun) return blockedReplyResult(session, run, FINALIZATION_UNAVAILABLE);
        const marked = authorizeMarkedPayload(session, event.payload, "final", effectiveRun);
        if (marked) return {{ payload: marked }};
        return blockedReplyResult(session, run, FINALIZATION_UNAVAILABLE);
      }}
      if (gate?.action !== "replace" || !exactGateHash) {{
        return blockedReplyResult(session, run, FINALIZATION_UNAVAILABLE);
      }}
      if (key) terminalRejections.set(key, {{
        expiresAt: now + TERMINAL_REJECTION_TTL_MS,
        message: String(gate.message || TERMINAL_REJECTION_MESSAGE),
      }});
      return blockedReplyResult(session, run, gate.message);
      }} catch {{
        return {{ cancel: true, reason: FINALIZATION_UNAVAILABLE }};
      }}
    }}, {{ priority: Number.NEGATIVE_INFINITY, timeoutMs: {outbound_timeout_ms + 1_000} }});

    api.on("message_sending", (event, ctx) => {{
      try {{
      const session = String(event?.sessionKey || ctx?.sessionKey || "");
      const content = typeof event?.content === "string" ? event.content : "";
      const unmarked = unmarkOutboundText(content);
      const authorized = unmarked
        ? consumeOutboundAuthorization(session, unmarked.markedText)
        : null;
      if (authorized) return {{ content: unmarked.content }};
      return {{
        cancel: true,
        cancelReason: "Agency Runtime cancelled an outbound message that did not match final validation.",
      }};
      }} catch {{
        return {{
          cancel: true,
          cancelReason: "Agency Runtime could not verify the outbound dispatch marker.",
        }};
      }}
    }}, {{ priority: Number.NEGATIVE_INFINITY, timeoutMs: {outbound_timeout_ms + 1_000} }});
  }},
}});
"""
