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
const MODULE_ARGS = ["-I", "-S", {bootstrap}, "agency_runtime.adapters.openclaw.node_bridge"{config_args}];
const FINALIZATION_UNAVAILABLE = "Agency Runtime could not verify this response. Restore the local runtime and retry.";
const TERMINAL_REJECTION_MESSAGE = "Agency Runtime blocked this response because its required evidence contract was invalid. No correction was requested or accepted; start a new turn after restoring the runtime or fixing first-pass header generation.";
const MAX_BRIDGE_INPUT_BYTES = 1024 * 1024;
const MAX_BRIDGE_OUTPUT_BYTES = 128 * 1024;
const MAX_BRIDGE_TEXT_BYTES = 64 * 1024;
const MAX_OUTBOUND_PAYLOAD_BYTES = 256 * 1024;
const MAX_OUTBOUND_PAYLOAD_NODES = 8192;
const MAX_OUTBOUND_PAYLOAD_DEPTH = 20;
const MAX_TOOL_PAYLOAD_BYTES = 96 * 1024;
const MAX_TOOL_PROJECTION_NODES = 2048;
const MAX_TOOL_PROJECTION_BYTES = MAX_TOOL_PAYLOAD_BYTES;
const MAX_OPENCLAW_MIDDLEWARE_CONTENT_BLOCKS = 200;
const MAX_OPENCLAW_MIDDLEWARE_TEXT_CHARS = 100000;
const TOOL_TRUNCATED = "[truncated]";
const TERMINAL_REJECTION_TTL_MS = 10 * 60 * 1000;
const MAX_TERMINAL_REJECTIONS = 128;
const PREFLIGHT_CONTEXT_TTL_MS = 10 * 60 * 1000;
const MAX_PREFLIGHT_CONTEXTS = 128;
const TOOL_CORRELATION_TTL_MS = 10 * 60 * 1000;
const MAX_TOOL_CORRELATIONS = 128;
const NATIVE_CHILD_OBSERVATION_TTL_MS = 10 * 60 * 1000;
const MAX_NATIVE_CHILD_STATES = 512;
const OUTBOUND_AUTHORIZATION_TTL_MS = 30 * 1000;
const NATIVE_ERROR_TTL_MS = 30 * 1000;
const NATIVE_CONTROL_ACK_TTL_MS = 10 * 1000;
const NATIVE_CONTROL_ACK_WAIT_MS = 1_000;
const NATIVE_CONTROL_ACK_POLL_MS = 10;
const MAX_OUTBOUND_AUTHORIZATIONS = 128;
const MAX_NATIVE_ERROR_MARKERS = 128;
const CONTROL_AUTHORIZATION_FIELD = "agencyRuntimeControlAuthorization";
const preflightContexts = new Map();
const toolCorrelations = new Map();
const terminalRejections = new Map();
const outboundAuthorizations = new Map();
const controlAuthorizations = new Map();
const nativeControlAuthorizations = new Map();
const nativeErrorMarkers = new Map();
let nativeControlDiagnosticBudget = 64;
const nativeChildParents = new Map();
const nativeChildObservations = new Map();
const NATIVE_CONTROL_ACKS = new Map([
  ["/new", "✅ New session started."],
  ["/reset", "✅ Session reset."],
]);
const NATIVE_CONTROL_ACK_TEXTS = new Set(NATIVE_CONTROL_ACKS.values());
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
  "name", "skill", "skill_name", "command", "path", "slug", "agent_slug",
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
    launchId: boundedCorrelation(payload?.launchId),
    workUnitId: boundedUtf8(payload?.workUnitId, 160),
    workerId: boundedUtf8(payload?.workerId, 256),
    nativeRunId: boundedUtf8(payload?.nativeRunId, 256),
    childSessionId: boundedCorrelation(payload?.childSessionId),
    goal: boundedUtf8(payload?.goal, MAX_BRIDGE_TEXT_BYTES),
    outcome: boundedUtf8(payload?.outcome, 32),
    userMessage: boundedUtf8(payload?.userMessage, MAX_BRIDGE_TEXT_BYTES),
    finalResponse: boundedUtf8(payload?.finalResponse, MAX_BRIDGE_TEXT_BYTES),
    draftText: boundedUtf8(payload?.draftText, MAX_BRIDGE_TEXT_BYTES),
    outboundPayload: boundedUtf8(payload?.outboundPayload, MAX_OUTBOUND_PAYLOAD_BYTES),
    responseHash: boundedUtf8(payload?.responseHash, 65),
    model: boundedUtf8(payload?.model, 1024),
    requestedModel: boundedUtf8(payload?.requestedModel, 1024),
    modelGroup: boundedUtf8(payload?.modelGroup, 1024),
    resolvedProvider: boundedUtf8(payload?.resolvedProvider, 1024),
    resolvedModel: boundedUtf8(payload?.resolvedModel, 1024),
    modelId: boundedUtf8(payload?.modelId, 1024),
    source: boundedUtf8(payload?.source, 256),
    status: boundedUtf8(payload?.status, 64),
    attempt: Number.isSafeInteger(payload?.attempt) ? payload.attempt : 0,
    includeHeaderContext: payload?.includeHeaderContext === true,
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

function isNativeSubagentSession(event, ctx) {{
  return sessionId(event, ctx).includes(":subagent:");
}}

function nativeChildIdentityKey(childSession, nativeRunId) {{
  const boundedSession = boundedNativeChildIdentity(childSession);
  const boundedRun = boundedNativeChildIdentity(nativeRunId);
  return boundedSession && boundedRun
    ? JSON.stringify([boundedSession, boundedRun])
    : "";
}}

function authenticatedNativeChildState(event, ctx) {{
  const key = nativeChildIdentityKey(sessionId(event, ctx), traceId(event, ctx));
  const state = key ? nativeChildParents.get(key) : undefined;
  return state?.startedRecorded === true ? state : undefined;
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
  const requestedModel = modelId(ctx) || String(event?.model || "");
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
  for (const [key, state] of nativeControlAuthorizations) {{
    if (Number(state?.expiresAt || 0) <= now) nativeControlAuthorizations.delete(key);
  }}
  while (nativeControlAuthorizations.size >= MAX_OUTBOUND_AUTHORIZATIONS) {{
    nativeControlAuthorizations.delete(nativeControlAuthorizations.keys().next().value);
  }}
}}

function nativeControlAuthorizationKey(session, text) {{
  if (!session || !text) return "";
  return `${{responseDigest(session)}}\\0${{responseDigest(text)}}`;
}}

function authorizeNativeControlAcknowledgement(session, command) {{
  const expected = NATIVE_CONTROL_ACKS.get(String(command || "").trim().toLowerCase());
  const key = expected ? nativeControlAuthorizationKey(session, expected) : "";
  if (!key) return false;
  const now = Date.now();
  pruneOutboundAuthorizations(now);
  nativeControlAuthorizations.set(key, {{
    expected,
    expiresAt: now + NATIVE_CONTROL_ACK_TTL_MS,
  }});
  return true;
}}

function logNativeControlDiagnostic(api, phase, details = {{}}) {{
  if (nativeControlDiagnosticBudget <= 0) return;
  nativeControlDiagnosticBudget -= 1;
  api?.logger?.info?.(`agency-preflight native-control ${{JSON.stringify({{
    phase,
    sessionPresent: details.sessionPresent === true,
    exactText: details.exactText === true,
    kindFinal: details.kindFinal === true,
    authorizationPresent: details.authorizationPresent === true,
    allowed: details.allowed === true,
    textSurfaceCount: Number(details.textSurfaceCount || 0),
    contentLength: Number(details.contentLength || 0),
    authorizationCount: nativeControlAuthorizations.size,
  }})}}`);
}}

function nativeControlAcknowledgementAuthorization(session, text) {{
  if (!NATIVE_CONTROL_ACK_TEXTS.has(text)) return false;
  const now = Date.now();
  pruneOutboundAuthorizations(now);
  if (session) {{
    const key = nativeControlAuthorizationKey(session, text);
    const state = key ? nativeControlAuthorizations.get(key) : undefined;
    if (Number(state?.expiresAt || 0) > now) return key;
  }}
  let candidate = "";
  for (const [key, state] of nativeControlAuthorizations) {{
    if (state?.expected !== text || Number(state?.expiresAt || 0) <= now) continue;
    if (candidate) return "";
    candidate = key;
  }}
  return candidate;
}}

function hasNativeControlAcknowledgementAuthorization(session, text) {{
  return Boolean(nativeControlAcknowledgementAuthorization(session, text));
}}

function consumeNativeControlAcknowledgement(session, text) {{
  const candidate = nativeControlAcknowledgementAuthorization(session, text);
  if (!candidate) return false;
  nativeControlAuthorizations.delete(candidate);
  return true;
}}

async function waitForNativeControlAcknowledgementAuthorization(session, text) {{
  if (!NATIVE_CONTROL_ACK_TEXTS.has(text)) return false;
  const deadline = Date.now() + NATIVE_CONTROL_ACK_WAIT_MS;
  while (Date.now() < deadline) {{
    await new Promise((resolve) => setTimeout(resolve, NATIVE_CONTROL_ACK_POLL_MS));
    if (hasNativeControlAcknowledgementAuthorization(session, text)) return true;
  }}
  return false;
}}

async function waitForNativeControlAcknowledgement(session, text) {{
  if (!NATIVE_CONTROL_ACK_TEXTS.has(text)) return false;
  const deadline = Date.now() + NATIVE_CONTROL_ACK_WAIT_MS;
  while (Date.now() < deadline) {{
    await new Promise((resolve) => setTimeout(resolve, NATIVE_CONTROL_ACK_POLL_MS));
    if (consumeNativeControlAcknowledgement(session, text)) return true;
  }}
  return false;
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
  for (const kind of [
    "final", "error", "tool", "control", "disabled", "child_completion",
  ]) {{
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

function nativeErrorMarkerKey(session, run) {{
  const exactSession = boundedCorrelation(session);
  const exactRun = boundedCorrelation(run);
  if (
    !exactSession
    || !exactRun
    || Buffer.byteLength(exactSession, "utf8") > 512
    || Buffer.byteLength(exactRun, "utf8") > 512
  ) return "";
  return `${{responseDigest(exactSession)}}\\0${{responseDigest(exactRun)}}`;
}}

function pruneNativeErrorMarkers(now = Date.now()) {{
  for (const [key, state] of nativeErrorMarkers) {{
    if (Number(state?.expiresAt || 0) <= now) nativeErrorMarkers.delete(key);
  }}
  while (nativeErrorMarkers.size >= MAX_NATIVE_ERROR_MARKERS) {{
    nativeErrorMarkers.delete(nativeErrorMarkers.keys().next().value);
  }}
}}

function observeAgentEnd(event, ctx) {{
  const session = sessionId(event, ctx);
  const run = String(event?.runId || ctx?.runId || "");
  const key = nativeErrorMarkerKey(session, run);
  if (!key) return false;
  const now = Date.now();
  pruneNativeErrorMarkers(now);
  if (event?.success === false) {{
    nativeErrorMarkers.set(key, {{ expiresAt: now + NATIVE_ERROR_TTL_MS }});
    return true;
  }}
  if (event?.success === true) nativeErrorMarkers.delete(key);
  return false;
}}

function clearNativeErrorMarker(session, run) {{
  const key = nativeErrorMarkerKey(session, run);
  if (key) nativeErrorMarkers.delete(key);
}}

function consumeNativeErrorMarker(session, run) {{
  const key = nativeErrorMarkerKey(session, run);
  if (!key) return false;
  const state = nativeErrorMarkers.get(key);
  nativeErrorMarkers.delete(key);
  return Number(state?.expiresAt || 0) > Date.now();
}}

function terminalRejectionKey(session, run, text) {{
  if (!session || !run) return "";
  return `${{session}}\\0${{run}}\\0${{responseDigest(text)}}`;
}}

function pruneTerminalRejections(now = Date.now()) {{
  for (const [key, state] of terminalRejections) {{
    if (Number(state?.expiresAt || 0) <= now) terminalRejections.delete(key);
  }}
  while (terminalRejections.size >= MAX_TERMINAL_REJECTIONS) {{
    terminalRejections.delete(terminalRejections.keys().next().value);
  }}
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

function preflightContextKey(event, ctx) {{
  const session = sessionId(event, ctx);
  const run = traceId(event, ctx);
  return session && run ? `${{session}}\\0${{run}}` : "";
}}

function prunePreflightContexts(now = Date.now()) {{
  for (const [key, state] of preflightContexts) {{
    if (Number(state?.expiresAt || 0) <= now) preflightContexts.delete(key);
  }}
  while (preflightContexts.size >= MAX_PREFLIGHT_CONTEXTS) {{
    preflightContexts.delete(preflightContexts.keys().next().value);
  }}
}}

function rememberPreflightContext(result, event, ctx) {{
  const key = preflightContextKey(event, ctx);
  const context = typeof result?.context === "string" ? result.context : "";
  const completion = result?.completion === true;
  const headerContextHash = String(result?.headerContextHash || "");
  if (
    !key
    || !context
    || Buffer.byteLength(context, "utf8") > MAX_BRIDGE_TEXT_BYTES
    || (
      completion
      && (
        !/^[0-9a-f]{{64}}$/.test(headerContextHash)
        || headerContextHash !== responseDigest(context)
      )
    )
  ) return false;
  const now = Date.now();
  prunePreflightContexts(now);
  preflightContexts.set(key, {{
    context,
    model: boundedUtf8(modelId(ctx), 1024),
    kind: completion ? "native_child_completion" : "ordinary",
    headerContextHash: completion ? headerContextHash : "",
    completionRunId: completion ? toolCorrelationIdentity(result?.completionRunId) : "",
    parentSessionId: completion ? toolCorrelationIdentity(result?.parentSessionId) : "",
    parentTraceId: completion ? toolCorrelationIdentity(result?.parentTraceId) : "",
    workerId: completion ? boundedNativeChildIdentity(result?.workerId) : "",
    nativeRunId: completion ? boundedNativeChildIdentity(result?.nativeRunId) : "",
    launchId: completion ? toolCorrelationIdentity(result?.launchId) : "",
    workUnitId: completion ? boundedUtf8(result?.workUnitId, 160) : "",
    expiresAt: now + PREFLIGHT_CONTEXT_TTL_MS,
  }});
  return true;
}}

function readPreflightState(event, ctx) {{
  const key = preflightContextKey(event, ctx);
  const state = key ? preflightContexts.get(key) : undefined;
  if (Number(state?.expiresAt || 0) <= Date.now()) {{
    if (key) preflightContexts.delete(key);
    return undefined;
  }}
  return state;
}}

function readPreflightContext(event, ctx) {{
  const state = readPreflightState(event, ctx);
  return String(state?.context || "");
}}

function readPreflightModel(event, ctx) {{
  const state = readPreflightState(event, ctx);
  return String(state?.model || "");
}}

function isNativeChildCompletionContext(event, ctx) {{
  return readPreflightState(event, ctx)?.kind === "native_child_completion";
}}

function splitOpenClawMiddlewareText(text) {{
  const chunks = [];
  let offset = 0;
  while (offset < text.length) {{
    let end = Math.min(offset + MAX_OPENCLAW_MIDDLEWARE_TEXT_CHARS, text.length);
    if (
      end < text.length
      && end > offset
      && text.charCodeAt(end - 1) >= 0xd800
      && text.charCodeAt(end - 1) <= 0xdbff
      && text.charCodeAt(end) >= 0xdc00
      && text.charCodeAt(end) <= 0xdfff
    ) {{
      end -= 1;
    }}
    chunks.push(text.slice(offset, end));
    offset = end;
  }}
  return chunks;
}}

function frameToolResultWithHeader(content, context) {{
  const prefix = `${{context}}\n\n`;
  const firstTextIndex = content.findIndex(
    (item) => item?.type === "text" && typeof item.text === "string",
  );
  if (firstTextIndex < 0) {{
    if (content.length >= MAX_OPENCLAW_MIDDLEWARE_CONTENT_BLOCKS) return null;
    return [...content, {{ type: "text", text: context }}];
  }}
  const first = content[firstTextIndex];
  const chunks = splitOpenClawMiddlewareText(`${{prefix}}${{first.text}}`);
  const additionalBlocks = chunks.length - 1;
  if (content.length + additionalBlocks <= MAX_OPENCLAW_MIDDLEWARE_CONTENT_BLOCKS) {{
    const replacements = chunks.map((text, index) => (
      index === 0 ? {{ ...first, text }} : {{ type: "text", text }}
    ));
    return [
      ...content.slice(0, firstTextIndex),
      ...replacements,
      ...content.slice(firstTextIndex + 1),
    ];
  }}
  return null;
}}

function forgetPreflightContext(event, ctx) {{
  const key = preflightContextKey(event, ctx);
  if (key) preflightContexts.delete(key);
}}

function pruneToolCorrelations(now = Date.now()) {{
  for (const [key, state] of toolCorrelations) {{
    if (Number(state?.expiresAt || 0) <= now) toolCorrelations.delete(key);
  }}
  while (toolCorrelations.size >= MAX_TOOL_CORRELATIONS) {{
    toolCorrelations.delete(toolCorrelations.keys().next().value);
  }}
}}

function toolCorrelationIdentity(value) {{
  const identity = boundedCorrelation(value);
  return identity && Buffer.byteLength(identity, "utf8") <= 512 ? identity : "";
}}

function boundedNativeChildIdentity(value, maximumBytes = 256) {{
  let identity;
  try {{ identity = String(value ?? ""); }}
  catch {{ return ""; }}
  if (!identity || identity.includes("\\0")) return "";
  return Buffer.byteLength(identity, "utf8") <= maximumBytes ? identity : "";
}}

function acceptedSessionsSpawnResult(result) {{
  try {{
    const details = result?.details;
    if (!details || typeof details !== "object" || details.status !== "accepted") return null;
    const childSessionKey = boundedNativeChildIdentity(details.childSessionKey);
    const runId = boundedNativeChildIdentity(details.runId);
    return childSessionKey && runId ? {{ childSessionKey, runId }} : null;
  }} catch {{
    return null;
  }}
}}

function nativeChildCompletionRunId(childSession, nativeRunId) {{
  const boundedSession = boundedNativeChildIdentity(childSession);
  const boundedRun = boundedNativeChildIdentity(nativeRunId);
  if (!boundedSession || !boundedRun) return "";
  return toolCorrelationIdentity(`announce:v1:${{boundedSession}}:${{boundedRun}}`);
}}

function hostAuthenticatedNativeChildCompletionRun(event, ctx) {{
  // OpenClaw owns the hook event/context run identity for its internal announce
  // agent. The prefix is sufficient to classify the run for fail-closed
  // handling, but never to recover or split child identities: both identities
  // may themselves contain colons. Rehydration therefore remains
  // exact-identity-only.
  const contextRun = toolCorrelationIdentity(ctx?.runId);
  const eventRun = toolCorrelationIdentity(event?.runId);
  if (contextRun.startsWith("announce:v1:")) return contextRun;
  return eventRun.startsWith("announce:v1:") ? eventRun : "";
}}

function resolveNativeChildCompletionState(event, ctx) {{
  const contextRun = toolCorrelationIdentity(ctx?.runId);
  const eventRun = toolCorrelationIdentity(event?.runId);
  if (contextRun && eventRun && eventRun !== contextRun) return {{ matched: true }};
  const run = hostAuthenticatedNativeChildCompletionRun(event, ctx);
  const requesterSessionId = toolCorrelationIdentity(sessionId(event, ctx));
  if (!run || !requesterSessionId) return null;
  const matches = [];
  for (const [key, state] of nativeChildParents) {{
    if (state?.completionRunId !== run) continue;
    matches.push({{ key, state }});
    if (matches.length > 1) break;
  }}
  if (matches.length === 0) return null;
  if (matches.length !== 1) return {{ matched: true }};
  const match = matches[0];
  if (
    match.state?.requesterSessionId !== requesterSessionId
    || match.state?.startedRecorded !== true
    || match.state?.completionDeliveryState !== "pending"
  ) return {{ matched: true }};
  return {{
    matched: true,
    key: match.key,
    state: match.state,
    requesterSessionId,
    completionRunId: run,
  }};
}}

function markNativeChildCompletionConsumed(session, run) {{
  const requesterSessionId = toolCorrelationIdentity(session);
  const completionRunId = toolCorrelationIdentity(run);
  if (!requesterSessionId || !completionRunId) return false;
  const matches = [];
  for (const state of nativeChildParents.values()) {{
    if (
      state?.requesterSessionId === requesterSessionId
      && state?.completionRunId === completionRunId
      && state?.completionDeliveryState === "authorized"
    ) matches.push(state);
    if (matches.length > 1) break;
  }}
  if (matches.length !== 1) return false;
  matches[0].completionDeliveryState = "consumed";
  return true;
}}

async function authorizeNativeChildCompletionMessage(event, ctx, completion) {{
  const childState = completion?.state;
  const prepared = readPreflightState(event, ctx);
  const exactPreparedState = Boolean(
    prepared?.kind === "native_child_completion"
    && prepared?.completionRunId === completion?.completionRunId
    && prepared?.parentSessionId === childState?.sessionId
    && prepared?.parentTraceId === childState?.traceId
    && prepared?.workerId === childState?.workerId
    && prepared?.nativeRunId === childState?.nativeRunId
    && prepared?.launchId === childState?.launchId
    && prepared?.workUnitId === childState?.workUnitId
    && /^[0-9a-f]{{64}}$/.test(String(prepared?.headerContextHash || ""))
  );
  if (!childState || !exactPreparedState) return {{
    block: true,
    blockReason: "Agency Runtime rejected an uncorrelated native child completion.",
  }};
  // A correlated completion gets one first-pass delivery attempt. Invalid
  // envelopes and failed receipts remain durable failures rather than opening
  // a second message-tool path in the same host run.
  childState.completionDeliveryState = "attempted";
  const params = (
    event?.params
    && typeof event.params === "object"
    && !Array.isArray(event.params)
  ) ? event.params : null;
  const exactEnvelope = Boolean(
    params
    && Object.keys(params).length === 2
    && Object.prototype.hasOwnProperty.call(params, "action")
    && Object.prototype.hasOwnProperty.call(params, "message")
    && params.action === "send"
    && typeof params.message === "string"
    && params.message.trim()
  );
  let messageBytes = 0;
  try {{ messageBytes = exactEnvelope ? Buffer.byteLength(params.message, "utf8") : 0; }}
  catch {{ messageBytes = 0; }}
  if (!exactEnvelope || messageBytes > MAX_BRIDGE_TEXT_BYTES) return {{
    block: true,
    blockReason: "Agency Runtime requires one text-only implicit-target child completion.",
  }};
  const text = params.message;
  let outboundPayload;
  try {{ outboundPayload = canonicalOutboundPayload({{ text }}); }}
  catch {{ return {{ block: true, blockReason: FINALIZATION_UNAVAILABLE }}; }}
  const stateEpoch = ++runtimeStateEpoch;
  let gate;
  try {{
    gate = await invokeAgency({{
      action: "native_child_completion_finalize",
      sessionId: completion.requesterSessionId,
      traceId: completion.completionRunId,
      parentSessionId: childState.sessionId,
      parentTraceId: childState.traceId,
      workerId: childState.workerId,
      nativeRunId: childState.nativeRunId,
      launchId: childState.launchId,
      workUnitId: childState.workUnitId,
      headerContextHash: prepared.headerContextHash,
      finalResponse: text,
      outboundPayload,
      model: modelId(ctx) || readPreflightModel(event, ctx),
    }});
  }} catch {{
    return {{ block: true, blockReason: FINALIZATION_UNAVAILABLE }};
  }}
  const exactReceipt = Boolean(
    gate?.action === "allow"
    && gate?.authoritative === true
    && gate?.terminalBound === true
    && gate?.terminalStatus === "completed"
    && String(gate?.responseHash || "") === responseDigest(outboundPayload)
    && String(gate?.turnId || "") === childState.traceId
    && String(gate?.parentSessionId || "") === childState.sessionId
    && String(gate?.parentTraceId || "") === childState.traceId
    && String(gate?.completionRunId || "") === completion.completionRunId
  );
  if (
    !observeRuntimeState(gate, stateEpoch)
    || !runtimeEnabled
    || !exactReceipt
    || nativeChildParents.get(completion.key) !== childState
  ) return {{ block: true, blockReason: FINALIZATION_UNAVAILABLE }};
  const marked = authorizeMarkedPayload(
    completion.requesterSessionId,
    {{ text }},
    "child_completion",
    completion.completionRunId,
  );
  if (!marked?.text) return {{ block: true, blockReason: FINALIZATION_UNAVAILABLE }};
  childState.completionDeliveryState = "authorized";
  return {{ params: {{ ...params, message: marked.text }} }};
}}

function pruneNativeChildState(now = Date.now()) {{
  for (const [key, observation] of nativeChildObservations) {{
    if (Number(observation?.expiresAt || 0) <= now) nativeChildObservations.delete(key);
  }}
  while (nativeChildObservations.size >= MAX_NATIVE_CHILD_STATES) {{
    nativeChildObservations.delete(nativeChildObservations.keys().next().value);
  }}
  while (nativeChildParents.size >= MAX_NATIVE_CHILD_STATES) {{
    nativeChildParents.delete(nativeChildParents.keys().next().value);
  }}
}}

function nativeChildRequester(event, ctx) {{
  return toolCorrelationIdentity(ctx?.requesterSessionKey || event?.requesterSessionKey);
}}

function rememberNativeChildSpawn(event, ctx) {{
  const childSession = boundedNativeChildIdentity(event?.childSessionKey || ctx?.childSessionKey);
  const nativeRunId = boundedNativeChildIdentity(event?.runId || ctx?.runId);
  const requesterSessionId = nativeChildRequester(event, ctx);
  const key = nativeChildIdentityKey(childSession, nativeRunId);
  if (!key || !requesterSessionId) return null;
  const now = Date.now();
  pruneNativeChildState(now);
  const previous = nativeChildObservations.get(key);
  const previousActive = Number(previous?.expiresAt || 0) > now;
  const ambiguous = previousActive && (
    previous?.ambiguous === true
    || previous?.requesterSessionId !== requesterSessionId
  );
  const observation = {{
    childSession,
    nativeRunId,
    requesterSessionId,
    pendingEnd: previousActive ? previous?.pendingEnd : undefined,
    ambiguous,
    expiresAt: now + NATIVE_CHILD_OBSERVATION_TTL_MS,
  }};
  nativeChildObservations.set(key, observation);
  return ambiguous ? null : observation;
}}

function pendingNativeChildEnd(event, ctx) {{
  const childSession = boundedNativeChildIdentity(event?.targetSessionKey || ctx?.childSessionKey);
  const nativeRunId = boundedNativeChildIdentity(event?.runId || ctx?.runId);
  const requesterSessionId = nativeChildRequester(event, ctx);
  if (!childSession) return {{ correlationHandled: true }};
  const outcome = boundedUtf8(event?.outcome || "unknown", 32);
  const error = boundedUtf8(event?.error || event?.reason || "", 32 * 1024);
  const key = nativeChildIdentityKey(childSession, nativeRunId);
  let existing = key ? nativeChildParents.get(key) : undefined;
  let ambiguous = false;
  if (!existing && (!nativeRunId || !requesterSessionId)) {{
    const matches = [];
    for (const state of nativeChildParents.values()) {{
      if (state?.workerId !== childSession) continue;
      if (nativeRunId && state?.nativeRunId !== nativeRunId) continue;
      if (requesterSessionId && state?.requesterSessionId !== requesterSessionId) continue;
      matches.push(state);
      if (matches.length > 1) break;
    }}
    ambiguous = matches.length > 1;
    existing = matches.length === 1 ? matches[0] : undefined;
  }}
  if (existing) {{
    if (
      (requesterSessionId && existing.requesterSessionId !== requesterSessionId)
      || (nativeRunId && existing.nativeRunId !== nativeRunId)
    ) return {{ correlationHandled: true }};
    existing.pendingEnd = {{ outcome, error }};
    return existing;
  }}
  if (ambiguous || !requesterSessionId) return {{ correlationHandled: true }};
  if (!key) return null;
  const observation = nativeChildObservations.get(key);
  if (
    !observation
    || observation.ambiguous === true
    || Number(observation.expiresAt || 0) <= Date.now()
    || observation.requesterSessionId !== requesterSessionId
  ) return observation ? {{ correlationHandled: true }} : null;
  if (observation.terminal === true) return {{ correlationHandled: true }};
  observation.pendingEnd = {{ outcome, error }};
  return {{ correlationHandled: true }};
}}

async function persistNativeChildEnd(key, childState) {{
  if (!childState?.startedRecorded || !childState?.pendingEnd || childState?.endInFlight) {{
    return false;
  }}
  childState.endInFlight = true;
  try {{
    const receipt = await invokeAgency({{
      action: "native_child_ended",
      sessionId: String(childState.sessionId || ""),
      traceId: String(childState.traceId || ""),
      workUnitId: String(childState.workUnitId || ""),
      workerId: String(childState.workerId || ""),
      nativeRunId: String(childState.nativeRunId || ""),
      outcome: String(childState.pendingEnd.outcome || "unknown"),
      error: String(childState.pendingEnd.error || ""),
    }});
    if (receipt?.recorded !== true) throw new Error("native child end was not recorded");
  }} catch {{
    childState.endInFlight = false;
    return false;
  }}
  if (nativeChildParents.get(key) === childState) nativeChildParents.delete(key);
  pruneNativeChildState();
  nativeChildObservations.set(key, {{
    childSession: String(childState.workerId || ""),
    nativeRunId: String(childState.nativeRunId || ""),
    requesterSessionId: String(childState.requesterSessionId || ""),
    terminal: true,
    expiresAt: Date.now() + NATIVE_CHILD_OBSERVATION_TTL_MS,
  }});
  return true;
}}

async function reconcilePersistedNativeChildEnd(event, ctx) {{
  const childSession = boundedNativeChildIdentity(event?.targetSessionKey || ctx?.childSessionKey);
  const nativeRunId = boundedNativeChildIdentity(event?.runId || ctx?.runId);
  const requesterSessionId = nativeChildRequester(event, ctx);
  if (!childSession || !requesterSessionId) return false;
  let receipt;
  try {{
    receipt = await invokeAgency({{
      action: "native_child_ended",
      sessionId: requesterSessionId,
      workerId: childSession,
      nativeRunId,
      outcome: boundedUtf8(event?.outcome || "unknown", 32),
      error: boundedUtf8(event?.error || event?.reason || "", 32 * 1024),
    }});
  }} catch {{
    return false;
  }}
  if (receipt?.recorded !== true) return false;
  const key = nativeChildIdentityKey(childSession, nativeRunId);
  if (key) {{
    pruneNativeChildState();
    nativeChildObservations.set(key, {{
      childSession,
      nativeRunId,
      requesterSessionId,
      terminal: true,
      expiresAt: Date.now() + NATIVE_CHILD_OBSERVATION_TTL_MS,
    }});
  }}
  return true;
}}

function rememberToolCorrelation(event, ctx, parentScope = undefined) {{
  const toolCallId = toolCorrelationIdentity(event?.toolCallId || ctx?.toolCallId);
  const sourceSessionId = toolCorrelationIdentity(sessionId(event, ctx));
  const sourceTraceId = toolCorrelationIdentity(traceId(event, ctx));
  const session = toolCorrelationIdentity(parentScope?.sessionId || sourceSessionId);
  const run = toolCorrelationIdentity(parentScope?.traceId || sourceTraceId);
  const model = boundedUtf8(modelId(ctx) || readPreflightModel(event, ctx), 1024);
  const toolName = boundedUtf8(event?.toolName || ctx?.toolName, 512);
  const params = (
    event?.params
    && typeof event.params === "object"
    && !Array.isArray(event.params)
  ) ? event.params : {{}};
  const task = toolName === "sessions_spawn"
    ? boundedUtf8(typeof params.task === "string" ? params.task : "", MAX_BRIDGE_TEXT_BYTES)
    : "";
  const workUnitId = toolName === "sessions_spawn"
    ? boundedUtf8(typeof params.taskName === "string" ? params.taskName : "", 160)
    : "";
  if (!toolCallId || !session || !run) return false;
  const now = Date.now();
  pruneToolCorrelations(now);
  const previous = toolCorrelations.get(toolCallId);
  const previousActive = Number(previous?.expiresAt || 0) > now;
  const ambiguous = previousActive && (
    previous?.ambiguous === true
    || previous?.sessionId !== session
    || previous?.traceId !== run
    || previous?.toolName !== toolName
    || previous?.task !== task
    || previous?.workUnitId !== workUnitId
    || previous?.sourceSessionId !== sourceSessionId
    || previous?.sourceTraceId !== sourceTraceId
  );
  toolCorrelations.set(toolCallId, {{
    sessionId: session,
    traceId: run,
    model,
    toolName,
    task,
    workUnitId,
    launchId: toolCallId,
    sourceSessionId,
    sourceTraceId,
    nativeParent: Boolean(parentScope),
    ambiguous,
    expiresAt: now + TOOL_CORRELATION_TTL_MS,
  }});
  return !ambiguous;
}}

function consumeToolCorrelation(event, ctx) {{
  const toolCallId = toolCorrelationIdentity(event?.toolCallId || ctx?.toolCallId);
  if (!toolCallId) return null;
  const state = toolCorrelations.get(toolCallId);
  toolCorrelations.delete(toolCallId);
  if (
    !state
    || state.ambiguous === true
    || Number(state.expiresAt || 0) <= Date.now()
  ) return null;
  return {{
    sessionId: String(state.sessionId || ""),
    traceId: String(state.traceId || ""),
    model: String(state.model || ""),
    toolName: String(state.toolName || ""),
    task: String(state.task || ""),
    workUnitId: String(state.workUnitId || ""),
    launchId: String(state.launchId || ""),
    sourceSessionId: String(state.sourceSessionId || ""),
    sourceTraceId: String(state.sourceTraceId || ""),
    nativeParent: state.nativeParent === true,
  }};
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
    nativeControlAuthorizations.clear();
    nativeErrorMarkers.clear();
    preflightContexts.clear();
    toolCorrelations.clear();
    nativeChildParents.clear();
    nativeChildObservations.clear();
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
    api.on("before_tool_call", async (event, ctx) => {{
      if (!runtimeEnabled) return undefined;
      const toolName = String(event?.toolName || ctx?.toolName || "");
      const completionRun = hostAuthenticatedNativeChildCompletionRun(event, ctx);
      const completion = resolveNativeChildCompletionState(event, ctx);
      if (completion?.matched === true) {{
        if (toolName === "message") {{
          return authorizeNativeChildCompletionMessage(event, ctx, completion);
        }}
        if (completion?.state) completion.state.completionDeliveryState = "attempted";
        return {{
          block: true,
          blockReason: "Agency Runtime permits only the bound child-completion message.",
        }};
      }}
      if (completionRun) {{
        return {{
          block: true,
          blockReason: "Agency Runtime rejected an uncorrelated native child completion.",
        }};
      }}
      if (isNativeChildCompletionContext(event, ctx)) {{
        return {{
          block: true,
          blockReason: "Agency Runtime permits only the bound child-completion message.",
        }};
      }}
      const nativeSubagent = isNativeSubagentSession(event, ctx);
      const nativeParent = nativeSubagent
        ? authenticatedNativeChildState(event, ctx)
        : undefined;
      if (nativeSubagent && (!nativeParent || toolName !== "sessions_spawn")) {{
        return undefined;
      }}
      if (!rememberToolCorrelation(event, ctx, nativeParent)) return undefined;
      if (toolName !== "sessions_spawn") return undefined;
      const params = (
        event?.params
        && typeof event.params === "object"
        && !Array.isArray(event.params)
      ) ? event.params : null;
      const task = typeof params?.task === "string" ? params.task : "";
      const launchId = toolCorrelationIdentity(event?.toolCallId || ctx?.toolCallId);
      let taskBytes;
      try {{ taskBytes = Buffer.byteLength(task, "utf8"); }}
      catch {{ return undefined; }}
      if (
        !params
        || !task
        || !launchId
        || taskBytes > MAX_BRIDGE_TEXT_BYTES
      ) return undefined;
      const stateEpoch = ++runtimeStateEpoch;
      let preparation;
      try {{
        preparation = await invokeAgency({{
          action: "native_child_prepare",
          sessionId: String(nativeParent?.sessionId || sessionId(event, ctx)),
          traceId: String(nativeParent?.traceId || traceId(event, ctx)),
          launchId,
          goal: task,
        }});
      }} catch {{
        return undefined;
      }}
      if (!observeRuntimeState(preparation, stateEpoch) || !runtimeEnabled) return undefined;
      const rewrittenTask = typeof preparation?.rewrittenTask === "string"
        ? preparation.rewrittenTask
        : "";
      if (
        preparation?.staffed !== true
        || !rewrittenTask
        || Buffer.byteLength(rewrittenTask, "utf8") > MAX_BRIDGE_TEXT_BYTES
      ) return undefined;
      return {{ params: {{ ...params, task: rewrittenTask }} }};
    }}, {{ timeoutMs: {host_timeout_ms} }});

    api.registerAgentToolResultMiddleware(async (event, ctx) => {{
      if (!runtimeEnabled) return undefined;
      const correlation = consumeToolCorrelation(event, ctx);
      const correlatedSession = correlation?.sessionId || sessionId(event, ctx);
      const correlatedTrace = correlation?.traceId || traceId(event, ctx);
      if (!correlatedSession || !correlatedTrace) return undefined;
      const stateEpoch = ++runtimeStateEpoch;
      const acceptedChild = correlation?.toolName === "sessions_spawn"
        ? acceptedSessionsSpawnResult(event?.result)
        : null;
      if (acceptedChild) {{
        const childKey = nativeChildIdentityKey(
          acceptedChild.childSessionKey,
          acceptedChild.runId,
        );
        const observation = nativeChildObservations.get(childKey);
        const observedRequesterMatches = Boolean(
          observation
          && observation.ambiguous !== true
          && Number(observation.expiresAt || 0) > Date.now()
          && observation.requesterSessionId === correlation?.sourceSessionId
        );
        const childState = {{
          sessionId: correlatedSession,
          traceId: correlatedTrace,
          workerId: acceptedChild.childSessionKey,
          nativeRunId: acceptedChild.runId,
          workUnitId: correlation?.workUnitId || "",
          launchId: correlation?.launchId || "",
          requesterSessionId: correlation?.sourceSessionId || "",
          completionRunId: nativeChildCompletionRunId(
            acceptedChild.childSessionKey,
            acceptedChild.runId,
          ),
          completionDeliveryState: "pending",
          pendingEnd: observedRequesterMatches ? observation?.pendingEnd : undefined,
          startedRecorded: false,
          endInFlight: false,
        }};
        pruneNativeChildState();
        nativeChildParents.set(childKey, childState);
        nativeChildObservations.delete(childKey);
        try {{
          const startedReceipt = await invokeAgency({{
            action: "native_child_started",
            sessionId: childState.sessionId,
            traceId: childState.traceId,
            launchId: childState.launchId,
            workUnitId: childState.workUnitId,
            workerId: childState.workerId,
            nativeRunId: childState.nativeRunId,
            childSessionId: childState.workerId,
            goal: correlation?.task || "",
          }});
          const recordedWorkUnit = boundedUtf8(startedReceipt?.workUnitId, 160);
          if (
            startedReceipt?.recorded !== true
            || startedReceipt?.launchBound !== true
            || !recordedWorkUnit
            || (childState.workUnitId && childState.workUnitId !== recordedWorkUnit)
          ) {{
            throw new Error("native child start was not launch-bound exactly");
          }}
          childState.workUnitId = recordedWorkUnit;
          childState.startedRecorded = true;
        }} catch {{
          // Host execution already succeeded; lifecycle evidence remains partial.
        }}
        if (childState.pendingEnd) await persistNativeChildEnd(childKey, childState);
        if (correlation?.nativeParent === true) return undefined;
      }}
      let result;
      try {{
        result = await invokeAgency({{
          action: "post_tool_call",
          sessionId: correlatedSession,
          traceId: correlatedTrace,
          model: correlation?.model || modelId(ctx) || readPreflightModel(event, ctx),
          toolName: String(event?.toolName || ""),
          toolInput: event?.args || {{}},
          toolResult: event?.result,
          error: event?.isError === true ? "tool_result_error" : "",
          includeHeaderContext: true,
        }});
      }} catch {{
        return undefined;
      }}
      if (!observeRuntimeState(result, stateEpoch) || !runtimeEnabled) return undefined;
      const context = typeof result?.context === "string" ? result.context : "";
      if (!context || Buffer.byteLength(context, "utf8") > MAX_BRIDGE_TEXT_BYTES) {{
        return undefined;
      }}
      const original = (
        event?.result
        && typeof event.result === "object"
        && !Array.isArray(event.result)
      ) ? event.result : {{}};
      const content = Array.isArray(original.content) ? original.content : [];
      const framedContent = frameToolResultWithHeader(content, context);
      if (!framedContent) return undefined;
      return {{
        result: {{
          ...original,
          content: framedContent,
        }},
      }};
    }}, {{ runtimes: ["openclaw"] }});

    api.on("gateway_start", (_event, ctx) => {{
      deliveryCompatibility = inspectFinalOnlyDelivery(ctx?.config);
    }});

    api.on("before_reset", (event, ctx) => {{
      const reason = String(event?.reason || "").trim().toLowerCase();
      const session = String(event?.sessionKey || ctx?.sessionKey || "");
      const authorized = authorizeNativeControlAcknowledgement(
        session,
        reason === "new" || reason === "reset" ? `/${{reason}}` : "",
      );
      logNativeControlDiagnostic(api, "before_reset", {{
        sessionPresent: Boolean(session),
        authorizationPresent: authorized,
        allowed: authorized,
      }});
    }});

    api.on("before_agent_run", async (event, ctx) => {{
      if (
        hostAuthenticatedNativeChildCompletionRun(event, ctx)
        && !isNativeChildCompletionContext(event, ctx)
      ) {{
        return {{
          outcome: "block",
          reason: "agency_native_child_completion_uncorrelated",
          category: "runtime_unavailable",
          message: "Agency Runtime could not correlate this native child completion.",
        }};
      }}
      if (isNativeSubagentSession(event, ctx)) return {{ outcome: "pass" }};
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
      if (!(deliveryCompatibility.verified && deliveryCompatibility.unsafe.length === 0)) {{
        return {{
          outcome: "block",
          reason: "agency_final_only_delivery_required",
          category: "runtime_configuration",
          message: "Agency Runtime requires OpenClaw preview and block streaming to be disabled. Stop the gateway and rerun the Agency installer.",
        }};
      }}
      if (!readPreflightContext(event, ctx)) {{
        return {{
          outcome: "block",
          reason: "agency_preflight_failed",
          category: "runtime_unavailable",
          message: "Agency Runtime could not complete preflight. Restore the local runtime and retry.",
        }};
      }}
      return {{ outcome: "pass" }};
    }}, {{ priority: 1000, timeoutMs: {host_timeout_ms} }});

    api.registerCommand({{
      name: "agency",
      description: "Agency Runtime read-only status; persistent on/off commands are denied",
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
      const completionRun = hostAuthenticatedNativeChildCompletionRun(event, ctx);
      const completion = resolveNativeChildCompletionState(event, ctx);
      if (completion?.matched === true) {{
        const childState = completion?.state;
        if (!childState) return undefined;
        const stateEpoch = ++runtimeStateEpoch;
        let result;
        try {{
          result = await invokeAgency({{
            action: "native_child_completion_prepare",
            sessionId: completion.requesterSessionId,
            traceId: completion.completionRunId,
            parentSessionId: childState.sessionId,
            parentTraceId: childState.traceId,
            workerId: childState.workerId,
            nativeRunId: childState.nativeRunId,
            launchId: childState.launchId,
            workUnitId: childState.workUnitId,
            model: modelId(ctx),
          }});
        }} catch {{
          return undefined;
        }}
        const exactReceipt = Boolean(
          result?.prepared === true
          && result?.completion === true
          && String(result?.completionRunId || "") === completion.completionRunId
          && String(result?.parentSessionId || "") === childState.sessionId
          && String(result?.parentTraceId || "") === childState.traceId
          && String(result?.workerId || "") === childState.workerId
          && String(result?.nativeRunId || "") === childState.nativeRunId
          && String(result?.launchId || "") === childState.launchId
          && String(result?.workUnitId || "") === childState.workUnitId
        );
        const stateApplied = observeRuntimeState(result, stateEpoch);
        if (!runtimeEnabled) return undefined;
        if (
          !stateApplied
          || !exactReceipt
          || nativeChildParents.get(completion.key) !== childState
          || !rememberPreflightContext(result, event, ctx)
        ) return undefined;
        const context = readPreflightContext(event, ctx);
        return context ? {{ appendContext: context }} : undefined;
      }}
      if (completionRun) return undefined;
      if (isNativeSubagentSession(event, ctx)) return undefined;
      const stateEpoch = ++runtimeStateEpoch;
      try {{
        const state = await invokeAgency({{ action: "control", command: "status" }});
        if (!observeRuntimeState(state, stateEpoch) || !runtimeEnabled) return undefined;
      }} catch {{
        return undefined;
      }}
      const childParent = authenticatedNativeChildState(event, ctx);
      let result;
      try {{
        result = await invokeAgency({{
          action: "preflight",
          sessionId: sessionId(event, ctx),
          traceId: traceId(event, ctx),
          userMessage: String(event?.prompt || ""),
          model: modelId(ctx),
          parentSessionId: String(childParent?.sessionId || ""),
          parentTraceId: String(childParent?.traceId || ""),
          workerId: String(childParent?.workerId || ""),
          nativeRunId: String(childParent?.nativeRunId || ""),
        }});
      }} catch {{
        return undefined;
      }}
      const stateApplied = observeRuntimeState(result, stateEpoch);
      if (!runtimeEnabled) return undefined;
      if (!stateApplied || !rememberPreflightContext(result, event, ctx)) return undefined;
      const context = readPreflightContext(event, ctx);
      return context ? {{ appendContext: context }} : undefined;
    }}, {{ priority: 100, timeoutMs: {host_timeout_ms} }});

    api.on("model_call_ended", async (event, ctx) => {{
      if (!runtimeEnabled) return;
      if (hostAuthenticatedNativeChildCompletionRun(event, ctx)) return;
      if (isNativeSubagentSession(event, ctx)) return;
      if (isNativeChildCompletionContext(event, ctx)) return;
      await invokeAgency(modelCallReceipt(event, ctx));
    }}, {{ timeoutMs: {host_timeout_ms} }});

    api.on("agent_end", (event, ctx) => {{
      if (!runtimeEnabled) return;
      if (
        hostAuthenticatedNativeChildCompletionRun(event, ctx)
        || isNativeChildCompletionContext(event, ctx)
      ) {{
        forgetPreflightContext(event, ctx);
        return;
      }}
      if (isNativeSubagentSession(event, ctx)) return;
      observeAgentEnd(event, ctx);
    }});

    api.on("subagent_spawned", async (event, ctx) => {{
      if (!runtimeEnabled) return;
      rememberNativeChildSpawn(event, ctx);
    }}, {{ timeoutMs: {host_timeout_ms} }});

    api.on("subagent_ended", async (event, ctx) => {{
      if (!runtimeEnabled) return;
      const childState = pendingNativeChildEnd(event, ctx);
      if (childState?.correlationHandled === true) return;
      if (!childState) {{
        await reconcilePersistedNativeChildEnd(event, ctx);
        return;
      }}
      const childKey = nativeChildIdentityKey(childState.workerId, childState.nativeRunId);
      await persistNativeChildEnd(childKey, childState);
    }}, {{ timeoutMs: {host_timeout_ms} }});

    api.on("before_agent_finalize", async (event, ctx) => {{
      if (hostAuthenticatedNativeChildCompletionRun(event, ctx)) return undefined;
      if (isNativeSubagentSession(event, ctx)) return undefined;
      if (isNativeChildCompletionContext(event, ctx)) return undefined;
      const stateEpoch = ++runtimeStateEpoch;
      const correlatedModel = modelId(ctx) || readPreflightModel(event, ctx);
      let decision;
      const finalText = finalAssistantText(event);
      const verificationFailure = {{
        action: "terminal",
        message: FINALIZATION_UNAVAILABLE,
        terminalRejected: true,
        terminalStatus: "verification_failed",
        responseHash: responseDigest(finalText),
        turnId: traceId(event, ctx),
      }};
      try {{
        decision = await invokeAgency({{
          action: "pre_verify",
          sessionId: sessionId(event, ctx),
          traceId: traceId(event, ctx),
          finalResponse: finalText,
          model: correlatedModel,
          attempt: 0,
        }});
      }} catch {{
        decision = verificationFailure;
      }}
      const stateApplied = observeRuntimeState(decision, stateEpoch);
      if (!stateApplied) {{
        if (!runtimeEnabled) return undefined;
        rememberTerminalRejection(verificationFailure, event, ctx);
        return undefined;
      }}
      if (!runtimeEnabled) return undefined;
      if (decision?.terminalRejected === true) {{
        rememberTerminalRejection(decision, event, ctx);
        return undefined;
      }}
      if (decision?.action === "allow_pending" || decision?.action === undefined) {{
        return undefined;
      }}
      rememberTerminalRejection(verificationFailure, event, ctx);
      return undefined;
    }}, {{ priority: 100, timeoutMs: {host_timeout_ms} }});

    api.on("reply_payload_sending", (event, ctx) => {{
      try {{
      const session = String(event?.sessionKey || ctx?.sessionKey || "");
      if (
        hostAuthenticatedNativeChildCompletionRun(event, ctx)
        || isNativeChildCompletionContext(event, ctx)
      ) {{
        return {{
          cancel: true,
          reason: "Agency Runtime requires message-tool-only native child completion delivery.",
        }};
      }}
      if (isNativeSubagentSession(event, ctx)) return {{ payload: event?.payload }};
      const kind = String(event?.kind || "");
      const run = String(event?.runId || ctx?.runId || "");
      const nativeTextSurfaces = outboundTextSurfaces(event?.payload);
      const nativeTextSurfaceCount = nativeTextSurfaces.length;
      const nativeControlText = kind === "final"
        && nativeTextSurfaceCount > 0
        && nativeTextSurfaces.every((value) => value === nativeTextSurfaces[0])
        ? nativeTextSurfaces[0]
        : "";
      const nativeControlAuthorized = hasNativeControlAcknowledgementAuthorization(
        session,
        nativeControlText,
      );
      if (
        NATIVE_CONTROL_ACK_TEXTS.has(nativeControlText)
      ) {{
        logNativeControlDiagnostic(api, "reply_payload_observed", {{
          sessionPresent: Boolean(session),
          exactText: NATIVE_CONTROL_ACK_TEXTS.has(nativeControlText),
          kindFinal: kind === "final",
          authorizationPresent: nativeControlAuthorized,
          textSurfaceCount: nativeTextSurfaceCount,
        }});
      }}
      if (NATIVE_CONTROL_ACK_TEXTS.has(nativeControlText)) {{
        const allowNativeControl = () => ({{ payload: event.payload }});
        if (nativeControlAuthorized) {{
          logNativeControlDiagnostic(api, "reply_payload_result", {{
            sessionPresent: Boolean(session),
            exactText: true,
            kindFinal: true,
            authorizationPresent: true,
            allowed: true,
          }});
          return allowNativeControl();
        }}
        return waitForNativeControlAcknowledgementAuthorization(
          session,
          nativeControlText,
        ).then((allowed) => {{
          logNativeControlDiagnostic(api, "reply_payload_result", {{
            sessionPresent: Boolean(session),
            exactText: true,
            kindFinal: true,
            authorizationPresent: allowed,
            allowed,
          }});
          return allowed
            ? allowNativeControl()
            : {{
              cancel: true,
              reason: "Agency Runtime cancelled an uncorrelated native control acknowledgement.",
            }};
        }});
      }}
      if (kind === "final" && event?.payload?.isError === true) {{
        if (!consumeNativeErrorMarker(session, run)) {{
          refreshRuntimeStateSync();
          if (!runtimeEnabled) {{
            const marked = authorizeMarkedPayload(session, event.payload, "disabled");
            if (marked) return {{ payload: marked }};
          }}
          return blockedReplyResult(session, run, FINALIZATION_UNAVAILABLE);
        }}
        forgetPreflightContext(event, ctx);
        let outboundPayload;
        try {{
          outboundPayload = canonicalOutboundPayload(event.payload);
        }} catch {{
          return blockedReplyResult(session, run, FINALIZATION_UNAVAILABLE);
        }}
        const digest = responseDigest(outboundPayload);
        const stateEpoch = ++runtimeStateEpoch;
        let nativeError;
        try {{
          nativeError = invokeAgencySync({{
            action: "native_error",
            sessionId: session,
            traceId: run,
            responseHash: digest,
          }}, {outbound_timeout_ms});
        }} catch {{
          return blockedReplyResult(session, run, FINALIZATION_UNAVAILABLE);
        }}
        const exactReceipt = (
          String(nativeError?.responseHash || "") === digest
          && String(nativeError?.turnId || "") === run
        );
        const stateApplied = observeRuntimeState(nativeError, stateEpoch);
        if (!stateApplied) return blockedReplyResult(session, run, FINALIZATION_UNAVAILABLE);
        if (!runtimeEnabled) {{
          const marked = exactReceipt && nativeError?.action === "bypass_error"
            ? authorizeMarkedPayload(session, event.payload, "disabled")
            : null;
          return marked
            ? {{ payload: marked }}
            : blockedReplyResult(session, run, FINALIZATION_UNAVAILABLE);
        }}
        const authoritative = (
          nativeError?.action === "allow_error"
          && nativeError?.authoritative === true
          && nativeError?.terminalStatus === "response_invalid"
          && typeof nativeError?.finalizationId === "string"
          && nativeError.finalizationId.length > 0
          && exactReceipt
        );
        const marked = authoritative
          ? authorizeMarkedPayload(session, event.payload, "error", run)
          : null;
        return marked
          ? {{ payload: marked }}
          : blockedReplyResult(session, run, FINALIZATION_UNAVAILABLE);
      }}
      if (kind === "final") clearNativeErrorMarker(session, run);
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
      const correlatedModel = modelId(ctx) || readPreflightModel(event, ctx);
      forgetPreflightContext(event, ctx);
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
          model: correlatedModel,
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
      const completionRun = hostAuthenticatedNativeChildCompletionRun(event, ctx);
      if (!completionRun && isNativeSubagentSession(event, ctx)) return {{ content }};
      if (
        NATIVE_CONTROL_ACK_TEXTS.has(content)
      ) {{
        logNativeControlDiagnostic(api, "message_observed", {{
          sessionPresent: Boolean(session),
          exactText: NATIVE_CONTROL_ACK_TEXTS.has(content),
          authorizationPresent: hasNativeControlAcknowledgementAuthorization(session, content),
          contentLength: content.length,
        }});
      }}
      const unmarked = unmarkOutboundText(content);
      const authorized = unmarked
        ? consumeOutboundAuthorization(session, unmarked.markedText)
        : null;
      if (authorized) {{
        if (authorized.kind === "child_completion") {{
          markNativeChildCompletionConsumed(session, authorized.runId);
        }}
        return {{ content: unmarked.content }};
      }}
      if (completionRun) {{
        return {{
          cancel: true,
          cancelReason: "Agency Runtime rejected an uncorrelated native child completion.",
        }};
      }}
      if (consumeNativeControlAcknowledgement(session, content)) {{
        logNativeControlDiagnostic(api, "message_result", {{
          sessionPresent: Boolean(session),
          exactText: true,
          authorizationPresent: true,
          allowed: true,
          contentLength: content.length,
        }});
        return {{ content }};
      }}
      if (NATIVE_CONTROL_ACK_TEXTS.has(content)) {{
        return waitForNativeControlAcknowledgement(session, content).then((allowed) => {{
          logNativeControlDiagnostic(api, "message_result", {{
            sessionPresent: Boolean(session),
            exactText: true,
            authorizationPresent: allowed,
            allowed,
          }});
          return allowed
            ? {{ content }}
            : {{
              cancel: true,
              cancelReason: "Agency Runtime cancelled an uncorrelated native control acknowledgement.",
            }};
        }});
      }}
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
