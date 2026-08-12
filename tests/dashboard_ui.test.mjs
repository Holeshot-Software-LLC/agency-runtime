import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";
import vm from "node:vm";

const CHARTS_PATH = fileURLToPath(new URL("../agency_runtime/dashboard/charts.js", import.meta.url));
const CHARTS_SOURCE = readFileSync(CHARTS_PATH, "utf8");
await import(pathToFileURL(CHARTS_PATH).href);
const AgencyCharts = globalThis.AgencyCharts;
const APP_PATH = fileURLToPath(new URL("../agency_runtime/dashboard/app.js", import.meta.url));
const APP_SOURCE = readFileSync(APP_PATH, "utf8");
const APP_URL = pathToFileURL(APP_PATH).href;
const ACTIONS_SOURCE = readFileSync(
  fileURLToPath(new URL("../agency_runtime/dashboard/dashboard-actions.js", import.meta.url)),
  "utf8",
);
const LIVE_SOURCE = readFileSync(
  fileURLToPath(new URL("../agency_runtime/dashboard/dashboard-live.js", import.meta.url)),
  "utf8",
);
const RENDER_SOURCE = readFileSync(
  fileURLToPath(new URL("../agency_runtime/dashboard/dashboard-render.js", import.meta.url)),
  "utf8",
);
const APP_CSS_PATH = fileURLToPath(new URL("../agency_runtime/dashboard/app.css", import.meta.url));
const APP_CSS_SOURCE = readFileSync(APP_CSS_PATH, "utf8");
const INDEX_PATH = fileURLToPath(new URL("../agency_runtime/dashboard/index.html", import.meta.url));
const INDEX_SOURCE = readFileSync(INDEX_PATH, "utf8");
const originalDocument = Object.getOwnPropertyDescriptor(globalThis, "document");
const originalWindow = Object.getOwnPropertyDescriptor(globalThis, "window");
const bootstrapNode = { hidden: false };
globalThis.document = {
  addEventListener() {},
  removeEventListener() {},
  getElementById() { return bootstrapNode; },
};
globalThis.window = {
  clearTimeout() {},
  setTimeout() { return 0; },
};
const { bootstrappedDashboard, createDashboard } = await import(APP_URL);
bootstrappedDashboard.destroy();
if (originalDocument) Object.defineProperty(globalThis, "document", originalDocument);
else delete globalThis.document;
if (originalWindow) Object.defineProperty(globalThis, "window", originalWindow);
else delete globalThis.window;

const NOW = Date.parse("2026-07-11T12:00:30.500Z");
const isoBefore = (milliseconds) => new Date(NOW - milliseconds).toISOString();

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function jsonResponse(status, payload) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: () => null },
    json: async () => payload,
  };
}

function controlSnapshot({
  config = {},
  hosts = [],
  roster = { agents: [] },
  governance = { snapshots: [] },
  restartRequired = false,
} = {}) {
  const normalizedConfig = { revision: "test-config-revision", ...config };
  const normalizedRoster = {
    agents: [],
    config_revision: normalizedConfig.revision,
    next_cursor: null,
    roster_revision: "test-roster-revision",
    truncated: false,
    ...roster,
  };
  const normalizedReviews = {
    candidates: [],
    collection_revision: "test-review-revision",
    next_cursor: null,
    truncated: false,
    ...(governance.reviews || {}),
  };
  const normalizedGovernance = {
    collection_revision: "test-snapshot-revision",
    next_cursor: null,
    snapshots: [],
    truncated: false,
    ...governance,
    reviews: normalizedReviews,
  };
  return {
    schema_version: "agency.dashboard.control.v1",
    config: normalizedConfig,
    control_revision: "test-control-revision",
    governance: normalizedGovernance,
    hosts,
    restart_required: restartRequired,
    roster: normalizedRoster,
  };
}

function routingLatencyPayload(overrides = {}) {
  return {
    schema_version: "agency.dashboard.routing_latency.v1",
    sampled_at: "2026-08-11T12:00:00+00:00",
    window: {
      kind: "most_recent_positive_latency_decisions",
      limit: 200,
      decision_count: 2,
    },
    source: {
      decision_table: "routing_decisions",
      decision_duration: "latency_ms",
      receipt_table: "model_receipts",
      receipt_duration: "latency_ms",
    },
    budget_ms: 15_000,
    over_budget: true,
    overall: { count: 2, min_ms: 12_000, p50_ms: 12_000, p95_ms: 18_000, max_ms: 18_000 },
    split: {
      decisions: 1,
      unattributed_decisions: 1,
      provider_ms: { count: 1, min_ms: 7_000, p50_ms: 7_000, p95_ms: 7_000, max_ms: 7_000 },
      derived_routing_remainder_ms: { count: 1, min_ms: 5_000, p50_ms: 5_000, p95_ms: 5_000, max_ms: 5_000 },
      calls_per_decision: 2,
    },
    by_source: {
      computed: { count: 2, min_ms: 12_000, p50_ms: 12_000, p95_ms: 18_000, max_ms: 18_000 },
    },
    slowest: [{
      created_at: "2026-08-11T11:59:00+00:00",
      latency_ms: 18_000,
      provider_calls: 0,
      provider_ms: 0,
      provider_timed_calls: 0,
      provider_unknown_calls: 0,
      source: "computed",
    }],
    ...overrides,
  };
}

function selectionDistributionPayload(overrides = {}) {
  return {
    schema_version: "agency.dashboard.selection_distribution.v1",
    sampled_at: "2026-08-11T12:00:01+00:00",
    source: {
      decision_table: "routing_decisions",
      selection_field: "selected_ids",
      roster_measure: "current_enabled_roster",
    },
    decisions_with_selections: 202,
    distinct_selected_specialists: 39,
    selection_occurrences: 222,
    active_roster_size: 263,
    top_10_selection_occurrences: 182,
    top_10_share_of_selection_occurrences: 182 / 222,
    top_specialists: [{
      slug: "code-reviewer",
      decisions_containing_specialist: 146,
      share_of_decisions_with_selections: 146 / 202,
      selection_occurrences: 146,
      share_of_selection_occurrences: 146 / 222,
    }],
    long_tail: {
      specialist_count: 0,
      decisions_containing_specialist: 0,
      share_of_decisions_with_selections: 0,
      selection_occurrences: 0,
      share_of_selection_occurrences: 0,
    },
    selection_bearing_decision_scan_limit: 10_000,
    selection_bearing_decision_scan_truncated: false,
    ...overrides,
  };
}

function childDeliveryPayload(overrides = {}) {
  return {
    schema_version: "agency.dashboard.child_delivery.v1",
    sampled_at: "2026-08-11T12:00:02+00:00",
    source: {
      authority: "host_written_child_artifacts",
      artifact_hosts: ["claude", "codex"],
      agency_store_consulted: false,
      evidence_meaning: "hash_verified_specialist_cards_in_child_input_before_first_speech",
    },
    window: {
      kind: "newest_verified_child_delivery_evidence",
      hosts: ["claude", "codex"],
      detail_limit: 50,
    },
    bounds: {
      artifact_scan_limit_per_host: 4096,
      filesystem_visit_limit_per_host: 16_384,
      artifact_prefix_bytes: 524_288,
      artifact_record_limit: 64,
      detail_limit: 50,
    },
    hosts: [{
      host: "claude",
      root: "C:\\Users\\owner\\.claude\\projects",
      root_present: true,
      artifact_candidates: 1,
      artifact_candidate_count_complete: true,
      artifacts_scanned: 1,
      artifact_scan_truncated: false,
      filesystem_entries_visited: 4,
      evidence_count: 1,
      staffed_children: 1,
      correlated_staffed_children: 1,
      uncorrelated_staffed_children: 0,
      legacy_deliveries: 0,
      detail_limit: 50,
      detail_truncated: false,
      children: [{
        child_id: "child-1",
        artifact: "C:\\Users\\owner\\.claude\\projects\\child-1.jsonl",
        parent_id: "parent-1",
        envelope_parent_id: "parent-1",
        correlated: true,
        legacy: false,
        cards: [{
          slug: "code-reviewer",
          version: "1",
          prompt_hash: "a".repeat(64),
        }],
      }],
    }, {
      host: "codex",
      root: "C:\\Users\\owner\\.codex\\sessions",
      root_present: true,
      artifact_candidates: 0,
      artifact_candidate_count_complete: true,
      artifacts_scanned: 0,
      artifact_scan_truncated: false,
      filesystem_entries_visited: 3,
      evidence_count: 0,
      staffed_children: 0,
      correlated_staffed_children: 0,
      uncorrelated_staffed_children: 0,
      legacy_deliveries: 0,
      detail_limit: 50,
      detail_truncated: false,
      children: [],
    }],
    ...overrides,
  };
}

function rule8EvidencePayload(overrides = {}) {
  return {
    schema_version: "agency.dashboard.rule8_evidence.v1",
    sampled_at: "2026-08-11T12:00:03+00:00",
    source: {
      authority: "agency_store",
      table: "runs",
      field: "status",
      host_execution_proof: false,
    },
    window: {
      kind: "most_recent_matching_exceptional_runs",
      host: null,
      limit: 50,
      returned: 2,
    },
    counts: { matching_exceptional_runs: 2, withheld: 1, agency_blind: 1 },
    withheld_statuses: ["delegation_declined", "response_invalid", "retry_exhausted"],
    agency_blind_statuses: ["preflight_failed", "verification_failed"],
    withheld: [{
      trace_id: "trace-withheld",
      session_id: "session-1",
      host: "claude",
      started_at: "2026-08-11T11:58:00+00:00",
      ended_at: "2026-08-11T11:59:00+00:00",
      status: "response_invalid",
    }],
    agency_blind: [{
      trace_id: "trace-blind",
      session_id: "session-2",
      host: "codex",
      started_at: "2026-08-11T11:56:00+00:00",
      ended_at: "2026-08-11T11:57:00+00:00",
      status: "preflight_failed",
    }],
    service_binding: { status: "bound" },
    ...overrides,
  };
}

function wiringEvidencePayload(overrides = {}) {
  return {
    schema_version: "agency.dashboard.host_wiring.v1",
    sampled_at: "2026-08-11T12:00:04+00:00",
    source: {
      authority: "trusted_staged_and_host_cache_files",
      measured_hosts: ["claude"],
      live_canary: false,
    },
    window: { kind: "current_wiring_files", hosts: ["claude", "codex"] },
    bounds: { file_prefix_bytes: 524_288 },
    hosts: [{
      host: "claude",
      measurement_status: "measured",
      status: "wired",
      wired: true,
      reason_code: "wired",
      reason: "",
      staged_state: "observed",
      staged_projection: "a".repeat(64),
      staged_path: "C:\\Users\\owner\\.agency-runtime\\hooks.json",
      wired_state: "observed",
      wired_projection: "a".repeat(64),
      wired_path: "C:\\Users\\owner\\.claude\\plugins\\hooks.json",
    }, {
      host: "codex",
      measurement_status: "not_measured",
      status: "not_measured",
      wired: false,
      reason_code: "host_not_measured",
      reason: "this host's wiring location is not measured",
      staged_state: "not_measured",
      staged_projection: "",
      staged_path: "",
      wired_state: "not_measured",
      wired_projection: "",
      wired_path: "",
    }],
    ...overrides,
  };
}

function emptyRosterPage(
  revision = "test-roster-revision",
  configRevision = "test-config-revision",
) {
  return {
    agents: [],
    config_revision: configRevision,
    next_cursor: null,
    roster_revision: revision,
    truncated: false,
  };
}

function emptyReviewPage(revision = "test-review-revision") {
  return {
    candidates: [],
    collection_revision: revision,
    next_cursor: null,
    truncated: false,
  };
}

function emptyGovernancePage(revision = "test-snapshot-revision") {
  return {
    collection_revision: revision,
    next_cursor: null,
    reviews: emptyReviewPage(),
    snapshots: [],
    truncated: false,
  };
}

function encodedCursor(kind, ...fields) {
  return btoa(JSON.stringify([kind, ...fields]))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

function verifiedHost(host = "codex", capabilities = ["repository-read", "test-execution"]) {
  return {
    effective_enabled: true,
    enabled: true,
    executable_discovered: true,
    host,
    inspection_status: "complete",
    registered: true,
    runtime_enabled: true,
    execution_capabilities: {
      capabilities,
      contract_version: "1",
      evidence: [`native-inventory-verified:${host}`],
      execution_host: host,
      inference_surface: "",
      platform: "windows",
      source: "native-installation-evidence",
      status: "native-installation-verified",
      surface: host,
      unknown_tools: [],
      session_id: "",
      trace_id: "",
      observed_at: "",
    },
  };
}

function hiringCaseSummary(id, overrides = {}) {
  return {
    applied_at: null,
    case_type: "hire",
    created_at: "2026-07-26T12:00:00Z",
    decided_at: null,
    evidence_included: false,
    human_approval_required: false,
    human_approved_at: null,
    human_approved_by: null,
    id,
    proposed_slug: `candidate-${id}`,
    risk_tier: "standard",
    status: "proposed",
    target_worker_id: null,
    work_unit_id: `work-${id}`,
    ...overrides,
  };
}

function fullHiringCase(id, marker = id) {
  return {
    ...hiringCaseSummary(id),
    evidence_included: true,
    contract_evidence: { marker: `${marker}-contract` },
    critic_evidence: { marker: `${marker}-critic` },
    duplicate_evidence: { marker: `${marker}-duplicate` },
    gap_evidence: { marker: `${marker}-gap` },
    model_evidence: { marker: `${marker}-model` },
  };
}

function workforceCollection(workers = [], overrides = {}) {
  return {
    collection_revision: "workforce-collection-v1",
    counts: {},
    next_cursor: null,
    truncated: false,
    workers,
    ...overrides,
  };
}

function hiringCollection(hiringCases = [], overrides = {}) {
  return {
    collection_revision: "hiring-collection-v1",
    hiring_cases: hiringCases,
    next_cursor: null,
    truncated: false,
    ...overrides,
  };
}

class FakeClassList {
  constructor() {
    this.values = new Set();
  }

  toggle(name, force) {
    const enabled = force === undefined ? !this.values.has(name) : Boolean(force);
    if (enabled) this.values.add(name);
    else this.values.delete(name);
    return enabled;
  }

  contains(name) {
    return this.values.has(name);
  }

  add(name) {
    this.values.add(name);
  }

  remove(name) {
    this.values.delete(name);
  }
}

class FakeNode {
  constructor(id = "") {
    this.id = id;
    this.attributes = new Map();
    this.classList = new FakeClassList();
    this.children = [];
    this.checked = false;
    this.className = "";
    this.closestNode = null;
    this.dataset = {};
    this.disabled = false;
    this.focusCount = 0;
    this.hidden = false;
    this.isConnected = true;
    this.listeners = new Map();
    this.labels = [];
    this.offsetWidth = 1;
    this.parentElement = null;
    this.queryNodes = [];
    this.tabIndex = 0;
    this.textContent = "";
    this.type = "";
    this.value = "";
    this.validationMessage = "";
  }

  addEventListener(name, listener) {
    const listeners = this.listeners.get(name) || [];
    listeners.push(listener);
    this.listeners.set(name, listeners);
  }

  removeEventListener(name, listener) {
    const listeners = this.listeners.get(name) || [];
    this.listeners.set(name, listeners.filter((candidate) => candidate !== listener));
  }

  append(...children) {
    this.children.push(...children);
  }

  get options() {
    return this.children;
  }

  closest() {
    return this.closestNode;
  }

  focus() { this.focusCount += 1; }

  getAttribute(name) {
    return this.attributes.get(name) ?? null;
  }

  querySelectorAll() {
    return this.queryNodes;
  }

  removeAttribute(name) {
    this.attributes.delete(name);
  }

  replaceChildren(...children) {
    this.children = [...children];
  }

  setAttribute(name, value) {
    this.attributes.set(name, String(value));
  }

  setCustomValidity(message) {
    this.validationMessage = String(message);
  }
}

class FakeSvgNode {
  constructor(tag) {
    this.tag = tag;
    this.attributes = new Map();
    this.children = [];
    this.dataset = {};
    this.textContent = "";
  }

  append(...children) { this.children.push(...children); }
  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  replaceChildren(...children) { this.children = [...children]; }
}

function svgHarness() {
  const documentRef = { createElementNS: (_namespace, tag) => new FakeSvgNode(tag) };
  const root = new FakeSvgNode("root");
  root.ownerDocument = documentRef;
  return root;
}

function descendants(root) {
  const nodes = [];
  const visit = (node) => {
    nodes.push(node);
    node.children?.forEach(visit);
  };
  visit(root);
  return nodes;
}

function createAppHarness(fetchImpl) {
  let nextTimerId = 1;
  const timerTasks = new Map();
  const nodes = new Map();
  const documentListeners = new Map();
  const historyCalls = [];
  const missingIds = new Set();
  const sessionValues = new Map();
  const windowListeners = new Map();
  const selectorNodes = new Map();
  const node = (id) => {
    if (!nodes.has(id)) nodes.set(id, new FakeNode(id));
    return nodes.get(id);
  };
  const addListener = (registry, name, listener) => {
    const listeners = registry.get(name) || [];
    listeners.push(listener);
    registry.set(name, listeners);
  };
  const removeListener = (registry, name, listener) => {
    const listeners = registry.get(name) || [];
    registry.set(name, listeners.filter((candidate) => candidate !== listener));
  };
  const timers = {
    tasks: timerTasks,
    set(callback, delay = 0) {
      const id = nextTimerId;
      nextTimerId += 1;
      timerTasks.set(id, { callback, delay: Number(delay) });
      return id;
    },
    clear(id) {
      timerTasks.delete(id);
    },
  };
  const document = {
    activeElement: null,
    visibilityState: "visible",
    addEventListener: (name, listener) => addListener(documentListeners, name, listener),
    removeEventListener: (name, listener) => removeListener(documentListeners, name, listener),
    createElement: (tag) => new FakeNode(tag),
    getElementById: (id) => (missingIds.has(id) ? null : node(id)),
    querySelector: (selector) => {
      if (selector === ".rail-foot") return node("rail-foot");
      if (selector === ".shell") return node("shell");
      if (selectorNodes.has(selector)) return selectorNodes.get(selector)[0] || null;
      return null;
    },
    querySelectorAll: (selector) => selectorNodes.get(selector) || [],
  };
  const HTMLElement = FakeNode;
  class HTMLInputElement extends FakeNode {}
  const window = {
    location: { hash: "", pathname: "/" },
    addEventListener: (name, listener) => addListener(windowListeners, name, listener),
    removeEventListener: (name, listener) => removeListener(windowListeners, name, listener),
    clearTimeout: (id) => timers.clear(id),
    setTimeout: (callback, delay) => timers.set(callback, delay),
  };
  const context = {
    AbortController,
    AgencyCharts,
    DOMException,
    Headers,
    HTMLElement,
    HTMLInputElement,
    URLSearchParams,
    console,
    crypto: {
      randomUUID() {
        return "00000000-0000-4000-8000-000000000001";
      },
    },
    document,
    fetch: fetchImpl,
    history: { replaceState: (...args) => historyCalls.push(args) },
    sessionStorage: {
      getItem: (key) => sessionValues.get(key) ?? null,
      setItem: (key, value) => sessionValues.set(key, String(value)),
    },
    window,
  };
  const api = createDashboard(context);
  return {
    api,
    context,
    document,
    documentListeners,
    historyCalls,
    HTMLInputElement,
    node,
    nodes,
    missing(id) { missingIds.add(id); },
    sessionValues,
    select(selector, values) { selectorNodes.set(selector, values); },
    timers,
    windowListeners,
  };
}

test("app.js accepts a token fragment that arrives after initial page load", () => {
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });

  harness.context.window.location.hash = "#token=late-token";
  harness.api.installToken();

  assert.equal(harness.api.state.token, "late-token");
  assert.equal(harness.sessionValues.get("agency-dashboard-token"), "late-token");
  assert.equal(harness.historyCalls.length, 1);
});

test("app.js preserves non-token fragments for native in-page navigation", () => {
  const harness = createAppHarness(() => {
    throw new Error("in-page navigation must not fetch");
  });
  harness.sessionValues.set("agency-dashboard-token", "session-token");
  harness.context.window.location.hash = "#main-content";

  harness.api.installToken();

  assert.equal(harness.api.state.token, "session-token");
  assert.equal(harness.api.hasTokenFragment(), false);
  assert.equal(harness.historyCalls.length, 0);
});

test("app.js API requests keep credentials in-memory and fail closed on malformed errors", async () => {
  const calls = [];
  const harness = createAppHarness(async (path, options) => {
    calls.push({ path, options });
    if (path === "/malformed") {
      return {
        ok: false,
        status: 503,
        headers: { get: (name) => (name === "Retry-After" ? "7" : null) },
        json: async () => { throw new Error("not JSON"); },
      };
    }
    if (path === "/hostile-request-id") {
      return jsonResponse(503, {
        error: "hostile correlation",
        request_id: "<img src=x onerror=alert(1)>",
      });
    }
    if (path === "/wrong-response-body-id") {
      return jsonResponse(200, {
        ok: true,
        request_id: "00000000-0000-4000-8000-000000000002",
      });
    }
    if (path === "/wrong-response-header-id") {
      return {
        ok: true,
        status: 200,
        headers: {
          get: (name) => (name === "X-Agency-Request-ID"
            ? "00000000-0000-4000-8000-000000000003"
            : null),
        },
        json: async () => ({ ok: true }),
      };
    }
    if (path === "/malformed-response-body-id") {
      return jsonResponse(200, {
        ok: true,
        request_id: " 00000000-0000-4000-8000-000000000001 ",
      });
    }
    if (path === "/nonstring-response-body-id") {
      return jsonResponse(200, { ok: true, request_id: 17 });
    }
    if (path === "/malformed-response-header-id") {
      return {
        ok: true,
        status: 200,
        headers: {
          get: (name) => (name === "X-Agency-Request-ID" ? "not-a-request-id" : null),
        },
        json: async () => ({ ok: true }),
      };
    }
    if (path === "/malformed-legacy-response-header-id") {
      return {
        ok: true,
        status: 200,
        headers: {
          get: (name) => (name === "X-Request-ID" ? " request-id " : null),
        },
        json: async () => ({ ok: true }),
      };
    }
    return jsonResponse(200, { ok: true });
  });
  harness.api.state.token = "fragment-only-secret";

  assert.equal((await harness.api.api("/ok", {
    body: "{}",
    headers: {
      authorization: "Bearer attacker-token",
      "Content-Type": "text/plain",
      "x-AGENCY-request-ID": "00000000-0000-4000-8000-000000000002",
      "x-request-ID": "00000000-0000-4000-8000-000000000005",
      "X-Preserved": "yes",
    },
    method: "POST",
  })).ok, true);
  assert.equal(calls[0].options.headers.get("Authorization"), "Bearer fragment-only-secret");
  assert.equal(calls[0].options.headers.get("Content-Type"), "application/json");
  assert.equal(
    calls[0].options.headers.get("X-Agency-Request-ID"),
    "00000000-0000-4000-8000-000000000001",
  );
  assert.equal(calls[0].options.headers.get("X-Preserved"), "yes");
  assert.equal(calls[0].options.headers.get("X-Request-ID"), null);
  assert.equal(calls[0].options.cache, "no-store");
  assert.equal(calls[0].options.credentials, "omit");

  const headersCompatible = new Headers({
    AUTHORIZATION: "Bearer second-attacker",
    "X-Agency-Request-ID": "00000000-0000-4000-8000-000000000004",
    "x-ReQuEsT-iD": "00000000-0000-4000-8000-000000000005",
    "X-Headers-Compatible": "retained",
  });
  await harness.api.api("/ok", { headers: headersCompatible });
  assert.equal(calls[1].options.headers.get("Authorization"), "Bearer fragment-only-secret");
  assert.equal(
    calls[1].options.headers.get("X-Agency-Request-ID"),
    "00000000-0000-4000-8000-000000000001",
  );
  assert.equal(calls[1].options.headers.get("X-Headers-Compatible"), "retained");
  assert.equal(calls[1].options.headers.get("X-Request-ID"), null);

  await assert.rejects(
    harness.api.api("/malformed"),
    (error) => error.name === "APIError"
      && error.status === 503
      && error.retryAfter === "7"
      && error.requestId === "00000000-0000-4000-8000-000000000001"
      && error.message === "HTTP 503. Request ID 00000000-0000-4000-8000-000000000001.",
  );
  await assert.rejects(
    harness.api.api("/hostile-request-id"),
    (error) => error.requestId === "00000000-0000-4000-8000-000000000001"
      && !error.message.includes("<img")
      && /Request ID 00000000-0000-4000-8000-000000000001/.test(error.message),
  );

  const mismatchLogs = [];
  harness.context.console = { error: (message) => mismatchLogs.push(String(message)) };
  const invalidCorrelationPaths = [
    "/wrong-response-body-id",
    "/wrong-response-header-id",
    "/malformed-response-body-id",
    "/nonstring-response-body-id",
    "/malformed-response-header-id",
    "/malformed-legacy-response-header-id",
  ];
  for (const path of invalidCorrelationPaths) {
    await assert.rejects(
      harness.api.api(path),
      (error) => error.name === "APIError"
        && error.status === 200
        && error.requestId === "00000000-0000-4000-8000-000000000001"
        && /response correlation did not match/i.test(error.message)
        && !/00000000000[234]|not-a-request-id|request-id/i.test(
          error.message.replace("Request ID", ""),
        ),
    );
  }
  assert.equal(mismatchLogs.length, invalidCorrelationPaths.length);
  assert.ok(mismatchLogs.every((message) => (
    message.includes("00000000-0000-4000-8000-000000000001")
      && !/00000000000[234]/.test(message)
  )));
});

test("app.js typed confirmations trap focus and reject incorrect phrases", async () => {
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  const returnFocus = new FakeNode("return-focus");
  const first = new FakeNode("first");
  const last = new FakeNode("last");
  harness.document.activeElement = returnFocus;
  harness.node("confirmation-modal").queryNodes = [first, last];

  const rejected = harness.api.requestConfirmation("SAVE CONFIG", "Review this change.");
  assert.equal(harness.node("shell").inert, true);
  harness.node("confirmation-input").value = "save config";
  harness.api.finishConfirmation(true);
  assert.notEqual(harness.api.state.confirmation, null);
  assert.equal(harness.node("confirmation-error").hidden, false);

  harness.document.activeElement = first;
  let trapped = false;
  harness.api.handleModalKeyboard({
    key: "Tab",
    preventDefault() { trapped = true; },
    shiftKey: true,
  });
  assert.equal(trapped, true);
  assert.equal(last.focusCount, 1);

  let escaped = false;
  harness.api.handleModalKeyboard({
    key: "Escape",
    preventDefault() { escaped = true; },
  });
  assert.equal(escaped, true);
  assert.equal(await rejected, false);
  assert.equal(harness.node("shell").inert, false);

  harness.document.activeElement = returnFocus;
  const accepted = harness.api.requestConfirmation("ENABLE HOST", "Enable it.");
  harness.node("confirmation-input").value = "ENABLE HOST";
  harness.api.finishConfirmation(true);
  assert.equal(await accepted, true);
  assert.equal(returnFocus.focusCount, 2);
});

test("app.js renders provider configuration without reflecting stored API keys", () => {
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  const providers = new FakeNode("config-providers");
  providers.dataset.configPath = "providers";
  providers.dataset.valueType = "json";
  providers.labels = [{ textContent: "Providers" }];
  harness.nodes.set("config-providers", providers);
  harness.select("[data-config-path]", [providers]);

  harness.api.renderConfig({
    effective: {
      providers: [{ api_key: "must-not-reach-the-dom", name: "primary", weight: 2 }],
    },
    environment_overrides: { "judge.model": "AGENCY_JUDGE_MODEL" },
    path: "C:/safe/config.yaml",
    revision: "1234567890abcdef",
  });

  assert.equal(providers.value.includes("must-not-reach-the-dom"), false);
  assert.deepEqual(JSON.parse(providers.value), [{ name: "primary", weight: 2 }]);
  assert.equal(harness.node("config-provider-secret-index").disabled, true);
  assert.equal(harness.node("config-provider-secret-index").value, "0");
  assert.equal(harness.node("config-override-count").textContent, "1 ENV OVERRIDE");
  assert.equal(harness.node("config-revision").textContent, "1234567890");

  harness.node("config-provider-secret").value = "replacement-secret";
  const operations = harness.api.collectConfigChanges();
  assert.equal(operations.length, 1);
  assert.equal(operations[0].op, "secret");
  assert.equal(operations[0].path, "providers.0.api_key");
  assert.equal(operations[0].action, "replace");
  assert.equal(operations[0].value, "replacement-secret");

	assert.equal(typeof harness.api.saveConfig, "function");
  assert.throws(
    () => harness.api.appendSecretOperation([], "judge.api_key", "new", true),
    /either a new value or clear/i,
  );
});

test("provider builder exposes and stages a LiteLLM router alias", () => {
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  const providers = new FakeNode("config-providers");
  providers.dataset.configPath = "providers";
  providers.dataset.valueType = "json";
  providers.labels = [{ textContent: "Providers" }];
  providers.value = "[]";
  harness.nodes.set("config-providers", providers);
  harness.select("[data-config-path]", [providers]);
  harness.api.state.configBaseline = new Map([["providers", JSON.stringify([])]]);

  harness.node("provider-builder-name").value = "agency-router";
  harness.node("provider-builder-type").value = "litellm";
  harness.node("provider-builder-model").value = "task-agency-router";
  harness.node("provider-builder-transport").value = "";
  harness.node("provider-builder-url").value = "http://127.0.0.1:4000/v1";
  harness.node("provider-builder-env").value = "LITELLM_API_KEY";
  harness.node("provider-builder-timeout").value = "15";

  const provider = harness.api.upsertProviderDraft();

  assert.equal(provider.model, "task-agency-router");
  assert.deepEqual(JSON.parse(providers.value), [{
    name: "agency-router",
    type: "litellm",
    transport: "",
    model: "task-agency-router",
    base_url: "http://127.0.0.1:4000/v1",
    api_key_env: "LITELLM_API_KEY",
    ollama_mode: false,
    timeout: 15,
    reasoning_effort: "",
  }]);
  assert.equal(harness.node("config-provider-secret-index").value, "0");
  assert.equal(harness.node("config-save-button").disabled, false);
});

test("provider builder discovers signed-in Codex models and keeps manual fallback", async () => {
  const calls = [];
  const harness = createAppHarness(async (path) => {
    calls.push(path);
    return jsonResponse(200, {
      transport: "codex",
      source: "codex-cli",
      models: [
        {
          slug: "gpt-cheap",
          display_name: "Cheap",
          description: "Low cost",
          supported_reasoning_levels: ["low", "medium"],
        },
        { slug: "gpt-frontier", display_name: "Frontier", description: "Deep work" },
      ],
    });
  });
  harness.node("provider-builder-type").value = "cli";
  harness.node("provider-builder-transport").value = "codex";
  harness.node("provider-builder-name").value = "codex-subscription";
  harness.node("provider-builder-timeout").value = "60";
  assert.equal(await harness.api.loadProviderModels({ refresh: true }), true);
  assert.equal(calls[0], "/api/providers/models?transport=codex&refresh=true");
  assert.equal(harness.node("provider-builder-model-select").value, "gpt-cheap");
  assert.equal(harness.node("provider-builder-model").hidden, true);
  assert.deepEqual(
    harness.node("provider-builder-reasoning-effort").options.map((option) => option.value),
    ["", "low", "medium"],
  );
  harness.node("provider-builder-reasoning-effort").value = "low";
  assert.equal(harness.api.providerBuilderDraft().reasoning_effort, "low");
  assert.match(harness.node("provider-builder-model-status").textContent, /2 account models/);
  harness.node("provider-builder-model-select").value = "__manual__";
  harness.api.syncProviderModelInput();
  assert.equal(harness.node("provider-builder-model").hidden, false);
});

test("provider builder recommends subscription-safe timeouts without overwriting custom values", () => {
  const harness = createAppHarness(() => { throw new Error("no fetch expected"); });
  const type = harness.node("provider-builder-type");
  const timeout = harness.node("provider-builder-timeout");

  type.value = "cli";
  timeout.value = "15";
  harness.api.syncProviderTimeoutRecommendation();
  assert.equal(timeout.value, "60");

  type.value = "litellm";
  harness.api.syncProviderTimeoutRecommendation();
  assert.equal(timeout.value, "15");

  timeout.value = "30";
  type.value = "cli";
  harness.api.syncProviderTimeoutRecommendation();
  assert.equal(timeout.value, "30");
});

test("workforce fallback provider exposes configured providers without model discovery", () => {
  let calls = 0;
  const harness = createAppHarness(async () => {
    calls += 1;
    throw new Error("workforce fallback-provider synchronization must not fetch");
  });
  harness.node("config-providers").value = JSON.stringify([
    { name: "codex-subscription", type: "cli", transport: "codex" },
    { name: "task-router", type: "litellm", model: "task-agency-router" },
  ]);

  harness.api.syncWorkforceProviderOptions();
  assert.deepEqual(
    harness.node("workforce-provider-options").options.map((option) => option.value),
    ["codex-subscription", "task-router"],
  );
  assert.equal(calls, 0);
  assert.equal(typeof harness.api.loadWorkforceModels, "undefined");
});

test("workforce detail renders comparison, promotion, prompt, history, and state-safe actions", () => {
  const harness = createAppHarness(() => {
    throw new Error("workforce detail rendering does not fetch");
  });
  harness.api.state.selectedWorkerDetail = {
    worker: {
      agent_slug: "typescript-application-engineer",
      current_version: "contractor-v1",
      display_label: "Contractor · TypeScript Application Engineer",
      employment_class: "contractor",
      origin: "agency",
      revision: 2,
      state: "contractor",
      worker_id: "worker-typescript",
    },
    recruitment_contract: {
      archetype: "implementer",
      authority: "modify",
      domains: ["software-engineering"],
      evidence_requirements: ["tests"],
      outcomes: ["production TypeScript"],
      scope: "Production TypeScript applications",
      stacks: ["typescript"],
    },
    closest_workers: [{
      recommendation: "keep_distinct",
      reasons: ["different stack ownership"],
      right: "python-application-engineer",
      score: 0.42,
    }],
    compiled_prompt: {
      hash: "a".repeat(64),
      preview: "Use the governed TypeScript contract.",
      truncated: false,
      version: "contractor-v1",
    },
    promotion_readiness: {
      automatic_policy_enabled: true,
      eligible_for_automatic_promotion: false,
      evidence_rule: "Independent acceptance receipts only.",
      reasons: ["1 more independently verified assignment is required."],
      required_successes: 2,
      verified_successes: 1,
    },
    events: Array.from({ length: 7 }, (_, index) => ({
      created_at: `2026-07-22T12:00:${String(59 - index).padStart(2, "0")}Z`,
      event_type: index ? "reviewed" : "generated",
      reason_hash: "f".repeat(64),
      reason_present: true,
    })),
    outcomes: Array.from({ length: 7 }, (_, index) => ({
      created_at: `2026-07-22T13:00:0${index}Z`,
      event_type: "acceptance",
      outcome: index ? `passed-${index}` : "passed",
    })),
    hiring_cases: [{
      case_type: "hire",
      created_at: "2026-07-22T10:00:00Z",
      id: "hiring-case-1",
      proposed_slug: "typescript-application-engineer",
      status: "applied",
    }],
    hiring_cases_total_count: 4,
    hiring_cases_truncated: true,
    lineage: [{
      agent_version_id: "version-id-1",
      created_at: "2026-07-22T11:00:00Z",
      relation: "generated",
      version: "contractor-v1",
    }],
    lineage_total_count: 7,
    lineage_truncated: true,
  };
  harness.api.state.workforceCounts = {
    contractor: 1,
    disabled: 2,
    employee: 3,
    merged: 4,
    retired: 5,
    suspended: 6,
  };
  harness.api.renderWorkforce();
  assert.equal(harness.node("workforce-retired").textContent, "5");
  assert.equal(harness.node("workforce-merged").textContent, "4");

  harness.api.renderWorkerDetail();

  const text = descendants(harness.node("workforce-detail"))
    .map((item) => item.textContent)
    .join(" ");
  assert.match(text, /1 \/ 2 verified assignments/);
  assert.match(text, /python-application-engineer/);
  assert.match(text, /42% overlap/);
  assert.match(text, /Use the governed TypeScript contract/);
  assert.match(text, /Owner-only governed specialist definition/);
  assert.match(text, /separate from runtime observation capture/);
  assert.match(text, /Reason recorded/);
  assert.doesNotMatch(text, /SHA-256|ffffffffffff|known contractor installed|lifecycle evidence/);
  assert.match(text, /1 of 7 version records \(bounded\)/);
  assert.match(text, /1 of 4 hiring records \(bounded\)/);
  assert.match(text, /Loaded version lineage evidence/);
  assert.match(text, /contractor-v1/);
  assert.match(text, /Loaded hiring case metadata/);
  assert.match(text, /applied · typescript-application-engineer/);
  assert.match(text, /Showing 12 of 14 loaded lifecycle and outcome records/);
	assert.deepEqual(
		harness.node("workforce-action-kind").options.map((option) => option.value),
		["promote", "disable", "suspend", "retire", "merge"],
	);
	assert.equal(harness.node("workforce-action-form").hidden, false);
	assert.equal(harness.node("workforce-action-worker").value, "typescript-application-engineer");
	assert.equal(harness.node("workforce-action-revision").value, "2");

  harness.api.state.selectedWorkerDetail.lineage_total_count = "7";
  harness.api.state.selectedWorkerDetail.lineage_truncated = true;
  harness.api.state.selectedWorkerDetail.hiring_cases_total_count = 0;
  harness.api.renderWorkerDetail();
  const malformedMetadataText = descendants(harness.node("workforce-detail"))
    .map((item) => item.textContent)
    .join(" ");
  assert.match(
    malformedMetadataText,
    /1 version records shown \(bounded; total unavailable\)/,
  );
  assert.match(
    malformedMetadataText,
    /1 hiring records shown \(bounded; total unavailable\)/,
  );

	harness.api.state.selectedWorkerDetail.worker.state = "disabled";
	harness.api.renderWorkerDetail();
	assert.deepEqual(
		harness.node("workforce-action-kind").options.map((option) => option.value),
		["enable", "suspend", "retire", "merge"],
	);
	assert.equal(harness.node("workforce-action-form").hidden, false);

  harness.api.state.selectedWorkerDetail.worker.state = "retired";
  harness.api.renderWorkerDetail();
  assert.equal(harness.node("workforce-action-kind").options.length, 0);
  assert.equal(harness.node("workforce-action-form").hidden, true);
});

test("workforce cards use one delegated click listener across repeated live renders", async () => {
  const calls = [];
  const harness = createAppHarness(async (path) => {
    calls.push(path);
    return jsonResponse(200, {
      detail: {
        worker: {
          agent_slug: "worker-one",
          current_version: "1.0.0",
          display_label: "Worker One",
          revision: 1,
          state: "employee",
          worker_id: "worker-one-id",
        },
        events: [],
        hiring_cases: [],
        lineage: [],
        outcomes: [],
      },
    });
  });
  harness.api.state.workforce = [{
    agent_slug: "worker-one",
    current_version: "1.0.0",
    display_label: "Worker One",
    revision: 1,
    state: "employee",
  }];
  assert.equal(harness.api.bindEvents(), true);

  for (let index = 0; index < 50; index += 1) harness.api.renderWorkforce();

  const grid = harness.node("workforce-grid");
  assert.equal(grid.listeners.get("click").length, 1);
  assert.equal(harness.api.bindEvents(), false);
  assert.equal(grid.listeners.get("click").length, 1);
  assert.ok(grid.children.every((card) => !card.listeners.has("click")));

  const card = grid.children[0];
  const nestedLabel = card.children[0].children[0];
  nestedLabel.closestNode = card;
  grid.listeners.get("click")[0]({ target: nestedLabel });
  await new Promise((resolve) => setImmediate(resolve));
  await new Promise((resolve) => setImmediate(resolve));

  assert.equal(calls[0], "/api/workforce?worker=worker-one&limit=100");
  assert.equal(harness.api.state.selectedWorkerDetail.worker.agent_slug, "worker-one");
  assert.equal(harness.api.destroy(), true);
  assert.equal(grid.listeners.get("click").length, 0);
});

test("hiring summaries load full exact evidence through one delegated control", async () => {
  const calls = [];
  const exact = fullHiringCase("case-a", "exact-a");
  const harness = createAppHarness(async (path, options) => {
    calls.push({ path, signal: options.signal });
    return jsonResponse(200, { hiring_case: exact });
  });
  assert.equal(harness.api.bindEvents(), true);
  harness.api.state.activeView = "workforce";
  harness.api.state.hiring = [hiringCaseSummary("case-a", {
    gap_evidence: { marker: "collection-gap-must-not-render" },
    duplicate_evidence: { marker: "collection-duplicate-must-not-render" },
  })];
  harness.api.renderWorkforce();

  const hiringList = harness.node("hiring-list");
  let renderedText = descendants(hiringList).map((node) => node.textContent).join(" ");
  assert.match(renderedText, /Metadata summary only/);
  assert.doesNotMatch(renderedText, /collection-gap-must-not-render/);
  assert.doesNotMatch(renderedText, /collection-duplicate-must-not-render/);
  let loadControls = descendants(hiringList)
    .filter((node) => node.dataset?.hiringEvidenceCase === "case-a");
  assert.equal(loadControls.length, 1);
  assert.equal(loadControls[0].textContent, "Load full evidence");
  assert.equal(loadControls[0].getAttribute("aria-expanded"), "false");

  loadControls[0].closestNode = loadControls[0];
  hiringList.listeners.get("click")[0]({ target: loadControls[0] });
  await new Promise((resolve) => setImmediate(resolve));
  await new Promise((resolve) => setImmediate(resolve));

  assert.equal(calls.length, 1);
  assert.equal(calls[0].path, "/api/hiring?case_id=case-a");
  assert.equal(calls[0].signal.aborted, false);
  assert.equal(harness.api.state.hiringEvidence.id, "case-a");
  renderedText = descendants(hiringList).map((node) => node.textContent).join(" ");
  for (const marker of [
    "exact-a-gap",
    "exact-a-duplicate",
    "exact-a-contract",
    "exact-a-critic",
    "exact-a-model",
  ]) assert.match(renderedText, new RegExp(marker));
  assert.match(renderedText, /Full evidence loaded from the exact hiring-case response/);
  assert.equal(
    descendants(hiringList).filter((node) => node.className === "hiring-evidence").length,
    5,
  );
  loadControls = descendants(hiringList)
    .filter((node) => node.dataset?.hiringEvidenceCase === "case-a");
  assert.equal(loadControls.length, 1);
  assert.equal(loadControls[0].getAttribute("aria-expanded"), "true");

  const preserveNodes = descendants(hiringList)
    .filter((node) => node.dataset?.preserveKey || node.dataset?.worker);
  const syncPreserveNodes = () => {
    preserveNodes.splice(
      0,
      preserveNodes.length,
      ...descendants(hiringList)
        .filter((node) => node.dataset?.preserveKey || node.dataset?.worker),
    );
  };
  const replaceChildren = hiringList.replaceChildren.bind(hiringList);
  hiringList.replaceChildren = (...children) => {
    replaceChildren(...children);
    syncPreserveNodes();
  };
  const append = hiringList.append.bind(hiringList);
  hiringList.append = (...children) => {
    append(...children);
    syncPreserveNodes();
  };
  harness.select("[data-preserve-key], [data-worker]", preserveNodes);
  const openEvidence = descendants(hiringList)
    .find((node) => node.dataset?.preserveKey?.endsWith(":gap_evidence"));
  const focusedLoad = loadControls[0];
  openEvidence.id = "";
  openEvidence.open = true;
  focusedLoad.id = "";
  harness.document.activeElement = focusedLoad;
  harness.select("details[open]", [openEvidence]);

  harness.api.renderPreservingInteraction(harness.api.renderWorkforce);

  const restoredEvidence = descendants(hiringList)
    .find((node) => node.dataset?.preserveKey?.endsWith(":gap_evidence"));
  const restoredLoad = descendants(hiringList)
    .find((node) => node.dataset?.hiringEvidenceCase === "case-a");
  assert.equal(restoredEvidence.open, true);
  assert.equal(restoredLoad.focusCount, 1);
});

test("exact hiring evidence rejects malformed, summary, and wrong-case responses", async () => {
  const missingModel = fullHiringCase("case-a", "missing-model");
  delete missingModel.model_evidence;
  const missingEvidenceMarker = fullHiringCase("case-a", "missing-marker");
  delete missingEvidenceMarker.evidence_included;
  const payloads = [
    null,
    {},
    { hiring_case: fullHiringCase("case-b", "wrong-case") },
    { hiring_case: missingModel },
    { hiring_case: missingEvidenceMarker },
    { hiring_case: { ...fullHiringCase("case-a", "summary"), evidence_included: false } },
  ];
  for (const payload of payloads) {
    const harness = createAppHarness(async () => jsonResponse(200, payload));
    harness.api.state.activeView = "workforce";
    harness.api.state.hiring = [hiringCaseSummary("case-a")];
    assert.equal(await harness.api.loadHiringEvidence("case-a"), false);
    assert.equal(harness.api.state.hiringEvidence, null);
    assert.match(harness.node("notice").textContent, /exact hiring evidence response/i);
  }

  let invalidCalls = 0;
  const invalid = createAppHarness(async () => {
    invalidCalls += 1;
    return jsonResponse(200, {});
  });
  assert.equal(await invalid.api.loadHiringEvidence(7), false);
  assert.equal(await invalid.api.loadHiringEvidence(" case-a "), false);
  assert.equal(invalidCalls, 0);
  assert.match(invalid.node("notice").textContent, /case id/i);
});

test("a stale exact hiring response cannot replace a newer case", async () => {
  const caseA = deferred();
  const caseB = deferred();
  const calls = [];
  const harness = createAppHarness((path, options) => {
    calls.push({ path, signal: options.signal });
    if (path.endsWith("case-a")) return caseA.promise;
    if (path.endsWith("case-b")) return caseB.promise;
    throw new Error(`unexpected exact hiring path ${path}`);
  });
  harness.api.state.activeView = "workforce";
  harness.api.state.hiring = [hiringCaseSummary("case-a"), hiringCaseSummary("case-b")];

  const staleA = harness.api.loadHiringEvidence("case-a");
  const newerB = harness.api.loadHiringEvidence("case-b");
  assert.equal(calls[0].signal.aborted, true);
  assert.equal(calls[1].signal.aborted, false);

  caseB.resolve(jsonResponse(200, { hiring_case: fullHiringCase("case-b", "newer-b") }));
  assert.equal(await newerB, true);
  assert.equal(harness.api.state.hiringEvidence.id, "case-b");
  caseA.resolve(jsonResponse(200, { hiring_case: fullHiringCase("case-a", "stale-a") }));
  assert.equal(await staleA, false);
  assert.equal(harness.api.state.hiringEvidence.id, "case-b");
  const renderedText = descendants(harness.node("hiring-list"))
    .map((node) => node.textContent).join(" ");
  assert.match(renderedText, /newer-b-gap/);
  assert.doesNotMatch(renderedText, /stale-a-gap/);
});

test("failed exact hiring loads preserve the last-good full case", async () => {
  const harness = createAppHarness(async (path) => {
    if (path.endsWith("case-a")) {
      return jsonResponse(200, { hiring_case: fullHiringCase("case-a", "last-good-a") });
    }
    if (path.endsWith("case-b")) {
      return jsonResponse(503, { error: "exact case unavailable" });
    }
    throw new Error(`unexpected last-good hiring path ${path}`);
  });
  harness.api.state.activeView = "workforce";
  harness.api.state.hiring = [hiringCaseSummary("case-a"), hiringCaseSummary("case-b")];

  assert.equal(await harness.api.loadHiringEvidence("case-a"), true);
  assert.equal(harness.api.state.hiringEvidence.id, "case-a");
  assert.equal(await harness.api.loadHiringEvidence("case-b"), false);
  assert.equal(harness.api.state.hiringEvidence.id, "case-a");
  assert.match(harness.node("notice").textContent, /exact case unavailable/i);
  const renderedText = descendants(harness.node("hiring-list"))
    .map((node) => node.textContent).join(" ");
  assert.match(renderedText, /last-good-a-gap/);
});

test("hiring evidence controls retain one delegated listener across repeated renders", () => {
  const harness = createAppHarness(() => {
    throw new Error("listener retention does not fetch");
  });
  assert.equal(harness.api.bindEvents(), true);
  harness.api.state.activeView = "workforce";
  harness.api.state.hiring = [hiringCaseSummary("case-a"), hiringCaseSummary("case-b")];
  harness.api.state.hiringEvidence = fullHiringCase("case-a", "loaded-a");

  for (let index = 0; index < 50; index += 1) harness.api.renderWorkforce();

  const hiringList = harness.node("hiring-list");
  assert.equal(hiringList.listeners.get("click").length, 1);
  assert.equal(harness.api.bindEvents(), false);
  assert.equal(hiringList.listeners.get("click").length, 1);
  const controls = descendants(hiringList)
    .filter((node) => node.dataset?.hiringEvidenceCase);
  assert.equal(controls.length, 2);
  assert.ok(controls.every((control) => !control.listeners.has("click")));
});

test("hiring filters apply on the first request, preserve type while paging, and clear directly", async () => {
  const calls = [];
  const cursor = encodedCursor("hiring.v1", "2026-07-26T12:00:00Z", "case-filtered-1");
  const harness = createAppHarness(async (path) => {
    calls.push(path);
    const url = new URL(path, "http://dashboard.test");
    if (url.searchParams.has("after")) {
      return jsonResponse(200, hiringCollection(
        [hiringCaseSummary("case-filtered-2", { case_type: "amend", risk_tier: "high" })],
        { collection_revision: "filtered-v1" },
      ));
    }
    if (url.searchParams.get("status") === "proposed") {
      return jsonResponse(200, hiringCollection(
        [hiringCaseSummary("case-filtered-1", { case_type: "amend", risk_tier: "high" })],
        {
          collection_revision: "filtered-v1",
          next_cursor: cursor,
          truncated: true,
        },
      ));
    }
    return jsonResponse(200, hiringCollection([], { collection_revision: "unfiltered-v1" }));
  });
  harness.api.state.activeView = "workforce";
  harness.node("hiring-filter-status").value = "proposed";
  harness.node("hiring-filter-type").value = "amend";
  harness.node("hiring-filter-risk").value = "high";
  let prevented = false;

  assert.equal(await harness.api.applyHiringFilters({
    preventDefault() { prevented = true; },
  }), true);
  assert.equal(prevented, true);
  const first = new URL(calls[0], "http://dashboard.test").searchParams;
  assert.deepEqual(Object.fromEntries(first), {
    limit: "200",
    risk_tier: "high",
    status: "proposed",
    type: "amend",
  });
  const continuation = new URL(calls[1], "http://dashboard.test").searchParams;
  assert.equal(continuation.get("status"), "proposed");
  assert.equal(continuation.get("type"), "amend");
  assert.equal(continuation.get("risk_tier"), "high");
  assert.equal(continuation.get("after"), cursor);
  assert.deepEqual(harness.api.state.hiringFilters, {
    status: "proposed",
    type: "amend",
    risk_tier: "high",
  });
  assert.deepEqual(
    harness.api.state.hiring.map((item) => item.id),
    ["case-filtered-1", "case-filtered-2"],
  );

  assert.equal(await harness.api.clearHiringFilters(), true);
  assert.equal(calls[2], "/api/hiring?limit=200");
  assert.equal(harness.node("hiring-filter-status").value, "");
  assert.equal(harness.node("hiring-filter-type").value, "");
  assert.equal(harness.node("hiring-filter-risk").value, "");
  assert.deepEqual(harness.api.state.hiringFilters, {});
});

test("aborted hiring filter intents restore only the still-current committed state", async () => {
  const abortableHarness = () => {
    const requests = [];
    const harness = createAppHarness((_path, options) => {
      const pending = deferred();
      requests.push({ pending, signal: options.signal });
      options.signal.addEventListener("abort", () => {
        pending.reject(new DOMException("Hiring filter request aborted", "AbortError"));
      }, { once: true });
      return pending.promise;
    });
    harness.api.state.activeView = "workforce";
    harness.api.state.hiringFilters = { status: "proposed" };
    return { harness, requests };
  };

  const globalAbort = abortableHarness();
  globalAbort.harness.node("hiring-filter-status").value = "approved";
  globalAbort.harness.node("hiring-filter-type").value = "hire";
  const abandoned = globalAbort.harness.api.applyHiringFilters();
  const replacement = globalAbort.harness.api.beginViewRequest("operationalRoster");
  assert.equal(globalAbort.requests[0].signal.aborted, true);
  assert.equal(await abandoned, false);
  assert.equal(globalAbort.harness.node("hiring-filter-status").value, "proposed");
  assert.equal(globalAbort.harness.node("hiring-filter-type").value, "");
  globalAbort.harness.api.finishViewRequest("operationalRoster", replacement);

  const superseded = abortableHarness();
  superseded.harness.node("hiring-filter-status").value = "approved";
  const older = superseded.harness.api.applyHiringFilters();
  superseded.harness.node("hiring-filter-status").value = "rejected";
  superseded.harness.node("hiring-filter-type").value = "amend";
  const newer = superseded.harness.api.applyHiringFilters();
  await Promise.resolve();
  assert.equal(superseded.requests[0].signal.aborted, true);
  assert.equal(superseded.harness.node("hiring-filter-status").value, "rejected");
  assert.equal(superseded.harness.node("hiring-filter-type").value, "amend");
  superseded.requests[1].pending.resolve(jsonResponse(200, hiringCollection([
    hiringCaseSummary("newer-filter-case", { case_type: "amend", status: "rejected" }),
  ])));
  assert.equal(await older, false);
  assert.equal(await newer, true);
  assert.deepEqual(superseded.harness.api.state.hiringFilters, {
    status: "rejected",
    type: "amend",
  });
});

test("destroy aborts an exact hiring load and removes its delegated listener", async () => {
  const pending = deferred();
  let requestSignal;
  const harness = createAppHarness((_path, options) => {
    requestSignal = options.signal;
    return pending.promise;
  });
  assert.equal(harness.api.bindEvents(), true);
  harness.api.state.activeView = "workforce";
  harness.api.state.hiring = [hiringCaseSummary("case-a")];
  harness.api.renderWorkforce();

  const hiringList = harness.node("hiring-list");
  const trackedControls = descendants(hiringList)
    .filter((node) => node.dataset?.hiringEvidenceCase);
  const syncTrackedControls = () => {
    trackedControls.splice(
      0,
      trackedControls.length,
      ...descendants(hiringList).filter((node) => node.dataset?.hiringEvidenceCase),
    );
  };
  const replaceChildren = hiringList.replaceChildren.bind(hiringList);
  hiringList.replaceChildren = (...children) => {
    replaceChildren(...children);
    syncTrackedControls();
  };
  const append = hiringList.append.bind(hiringList);
  hiringList.append = (...children) => {
    append(...children);
    syncTrackedControls();
  };
  harness.select("[data-hiring-evidence-case]", trackedControls);

  const load = harness.api.loadHiringEvidence("case-a");
  assert.equal(requestSignal.aborted, false);
  assert.equal(harness.api.state.hiringEvidenceLoadingCaseId, "case-a");
  assert.equal(trackedControls[0].disabled, true);
  assert.equal(trackedControls[0].getAttribute("aria-busy"), "true");
  assert.equal(harness.api.destroy(), true);
  assert.equal(requestSignal.aborted, true);
  assert.equal(harness.api.state.requests.hiringEvidence.controller, null);
  assert.equal(harness.api.state.hiringEvidenceLoadingCaseId, "");
  assert.equal(trackedControls[0].disabled, false);
  assert.equal(trackedControls[0].getAttribute("aria-busy"), null);
  assert.equal(hiringList.listeners.get("click").length, 0);

  pending.resolve(jsonResponse(200, { hiring_case: fullHiringCase("case-a", "too-late") }));
  assert.equal(await load, false);
  assert.equal(harness.api.state.hiringEvidence, null);
});

test("provider builder validates, updates, removes, and reports discovery fallbacks", async () => {
  const harness = createAppHarness(async () => jsonResponse(200, {
    transport: "codex",
    models: [null, { slug: 7 }, { slug: "" }],
    error: "No account models",
  }));
  const providers = new FakeNode("config-providers");
  providers.dataset.configPath = "providers";
  providers.dataset.valueType = "json";
  providers.labels = [{ textContent: "Providers" }];
  providers.value = JSON.stringify([{ name: "existing", timeout: 1 }]);
  harness.nodes.set("config-providers", providers);
  harness.select("[data-config-path]", [providers]);
  harness.api.state.configBaseline = new Map([["providers", providers.value]]);

  const builder = (values) => {
    harness.node("provider-builder-name").value = values.name ?? "provider";
    harness.node("provider-builder-type").value = values.type ?? "http";
    harness.node("provider-builder-model").value = values.model ?? "model";
    harness.node("provider-builder-model-select").value = "__manual__";
    harness.node("provider-builder-transport").value = values.transport ?? "";
    harness.node("provider-builder-reasoning-effort").value = values.reasoningEffort ?? "";
    harness.node("provider-builder-timeout").value = values.timeout ?? "15";
  };
  builder({ timeout: "0" });
  assert.throws(() => harness.api.providerBuilderDraft(), /between 0.05 and 60/i);
  builder({ type: "cli", transport: "other" });
  assert.throws(() => harness.api.providerBuilderDraft(), /Codex or Claude/i);
  builder({ type: "cli", transport: "codex" });
  harness.node("provider-builder-url").value = "https://stale.example.test";
  harness.node("provider-builder-env").value = "STALE_API_KEY";
  const cliDraft = harness.api.providerBuilderDraft();
  assert.equal(cliDraft.base_url, "");
  assert.equal(cliDraft.api_key_env, "");
  assert.equal(cliDraft.reasoning_effort, "");
  builder({ type: "cli", transport: "codex", reasoningEffort: "low" });
  assert.equal(harness.api.providerBuilderDraft().reasoning_effort, "low");
  builder({ type: "cli", transport: "claude", reasoningEffort: "low" });
  assert.equal(harness.api.providerBuilderDraft().reasoning_effort, "");
  builder({ type: "litellm", model: "" });
  assert.throws(() => harness.api.providerBuilderDraft(), /model or router alias/i);

  harness.node("provider-builder-type").value = "litellm";
  assert.equal(await harness.api.loadProviderModels(), false);
  assert.match(harness.node("provider-builder-model-status").textContent, /LiteLLM router/i);
  harness.node("provider-builder-type").value = "http";
  assert.equal(await harness.api.loadProviderModels(), false);
  assert.match(harness.node("provider-builder-model-status").textContent, /CLI subscription/i);
  harness.node("provider-builder-type").value = "cli";
  harness.node("provider-builder-transport").value = "codex";
  assert.equal(await harness.api.loadProviderModels(), false);
  assert.equal(harness.node("provider-builder-model-status").textContent, "No account models");

  builder({ name: "existing", type: "http", timeout: "12" });
  harness.api.upsertProviderDraft();
  assert.equal(JSON.parse(providers.value)[0].timeout, 12);
  providers.value = JSON.stringify([{
    name: "custom-ollama",
    type: "http",
    model: "local",
    base_url: "http://127.0.0.1:11434",
    api_key_env: "",
    ollama_mode: true,
    timeout: 15,
  }]);
  builder({ name: "custom-ollama", type: "http", model: "updated", timeout: "12" });
  harness.api.upsertProviderDraft();
  assert.equal(JSON.parse(providers.value)[0].ollama_mode, true);
  builder({ name: "custom-ollama", type: "cli", transport: "codex" });
  harness.api.upsertProviderDraft();
  assert.equal(JSON.parse(providers.value)[0].ollama_mode, false);
  providers.value = JSON.stringify([{ name: "legacy", model: "old" }]);
  builder({ name: "legacy", type: "http", model: "updated", timeout: "12" });
  harness.api.upsertProviderDraft();
  assert.equal(JSON.parse(providers.value)[0].ollama_mode, false);
  harness.api.syncProviderSecretOptions();
  harness.node("config-provider-secret-index").value = "0";
  harness.api.removeSelectedProvider();
  assert.deepEqual(JSON.parse(providers.value), []);
  harness.node("config-provider-secret-index").value = "";
  assert.throws(() => harness.api.removeSelectedProvider(), /select a provider/i);

  const failed = createAppHarness(async () => jsonResponse(500, { error: "catalog offline" }));
  failed.node("provider-builder-type").value = "cli";
  failed.node("provider-builder-transport").value = "codex";
  assert.equal(await failed.api.loadProviderModels(), false);
  assert.match(failed.node("provider-builder-model-status").textContent, /catalog offline/i);
});

test("provider configuration defensive branches stay bounded", async () => {
  const missingName = createAppHarness(() => { throw new Error("no fetch"); });
  missingName.missing("provider-builder-name");
  assert.throws(() => missingName.api.providerBuilderDraft(), /name is required/i);
  const missingType = createAppHarness(() => { throw new Error("no fetch"); });
  missingType.node("provider-builder-name").value = "provider";
  missingType.missing("provider-builder-type");
  assert.throws(() => missingType.api.providerBuilderDraft(), /type is required/i);

  const sparse = createAppHarness(() => { throw new Error("no fetch"); });
  sparse.node("provider-builder-name").value = "sparse";
  sparse.node("provider-builder-type").value = "ollama";
  for (const id of [
    "provider-builder-model-select",
    "provider-builder-model",
    "provider-builder-transport",
    "provider-builder-url",
    "provider-builder-env",
    "provider-builder-timeout",
  ]) sparse.missing(id);
  const sparseDraft = sparse.api.providerBuilderDraft();
  assert.equal(sparseDraft.model, "");
  assert.equal(sparseDraft.timeout, 15);
  assert.equal(sparseDraft.ollama_mode, true);

  const selected = createAppHarness(() => { throw new Error("no fetch"); });
  selected.node("provider-builder-name").value = "selected";
  selected.node("provider-builder-type").value = "cli";
  selected.node("provider-builder-transport").value = "claude";
  selected.node("provider-builder-model-select").value = "account-model";
  selected.node("provider-builder-timeout").value = "61";
  assert.throws(() => selected.api.providerBuilderDraft(), /between 0.05 and 60/i);
  selected.node("provider-builder-timeout").value = "not-a-number";
  assert.throws(() => selected.api.providerBuilderDraft(), /between 0.05 and 60/i);
  selected.node("provider-builder-timeout").value = "10";
  assert.equal(selected.api.providerBuilderDraft().model, "account-model");

  for (const id of [
    "provider-builder-model-select",
    "provider-builder-model-status",
    "provider-builder-model",
  ]) {
    const absent = createAppHarness(() => { throw new Error("no fetch"); });
    absent.missing(id);
    assert.equal(await absent.api.loadProviderModels(), false);
  }
  const noTransport = createAppHarness(() => { throw new Error("no fetch"); });
  noTransport.node("provider-builder-type").value = "cli";
  noTransport.missing("provider-builder-transport");
  assert.equal(await noTransport.api.loadProviderModels(), false);

  const emptyCatalog = createAppHarness(async () => jsonResponse(200, null));
  emptyCatalog.node("provider-builder-type").value = "cli";
  emptyCatalog.node("provider-builder-transport").value = "codex";
  assert.equal(await emptyCatalog.api.loadProviderModels(), false);
  assert.match(emptyCatalog.node("provider-builder-model-status").textContent, /No visible/i);

  const singular = createAppHarness(async () => jsonResponse(200, {
    models: [{ slug: "solo" }],
  }));
  singular.node("provider-builder-type").value = "cli";
  singular.node("provider-builder-transport").value = "codex";
  assert.equal(await singular.api.loadProviderModels(), true);
  assert.match(singular.node("provider-builder-model-status").textContent, /1 account model from codex/i);
  assert.equal(singular.node("provider-builder-model-select").options[1].title, "solo");

  const broken = createAppHarness(async () => { throw new Error(""); });
  broken.node("provider-builder-type").value = "cli";
  broken.node("provider-builder-transport").value = "codex";
  assert.equal(await broken.api.loadProviderModels(), false);
  assert.equal(
    broken.node("provider-builder-model-status").textContent,
    "Network request failed. Request ID 00000000-0000-4000-8000-000000000001.",
  );

  const invalidProviders = createAppHarness(() => { throw new Error("no fetch"); });
  invalidProviders.node("provider-builder-name").value = "provider";
  invalidProviders.node("provider-builder-type").value = "http";
  invalidProviders.node("config-providers").value = "{}";
  assert.throws(() => invalidProviders.api.upsertProviderDraft(), /JSON list/i);
  invalidProviders.node("config-provider-secret-index").value = "0";
  assert.throws(() => invalidProviders.api.removeSelectedProvider(), /JSON list/i);

  const emptyProviders = createAppHarness(() => { throw new Error("no fetch"); });
  emptyProviders.node("provider-builder-name").value = "provider";
  emptyProviders.node("provider-builder-type").value = "http";
  emptyProviders.node("config-providers").value = "";
  assert.equal(emptyProviders.api.upsertProviderDraft().name, "provider");
  emptyProviders.node("config-providers").value = JSON.stringify([{}]);
  emptyProviders.node("provider-builder-name").value = "different";
  emptyProviders.api.upsertProviderDraft();
  assert.equal(JSON.parse(emptyProviders.node("config-providers").value).length, 2);

  const missingSelect = createAppHarness(() => { throw new Error("no fetch"); });
  missingSelect.missing("config-provider-secret-index");
  assert.throws(() => missingSelect.api.removeSelectedProvider(), /select a provider/i);
  const emptyRemove = createAppHarness(() => { throw new Error("no fetch"); });
  emptyRemove.node("config-provider-secret-index").value = "0";
  emptyRemove.node("config-providers").value = "";
  emptyRemove.api.removeSelectedProvider();
  assert.equal(emptyRemove.node("config-providers").value, "[]");
  const missingModelSelect = createAppHarness(() => { throw new Error("no fetch"); });
  missingModelSelect.missing("provider-builder-model-select");
  missingModelSelect.api.syncProviderModelInput();
  const missingManual = createAppHarness(() => { throw new Error("no fetch"); });
  missingManual.missing("provider-builder-model");
  missingManual.api.syncProviderModelInput();
});

test("app.js config controls normalize typed values and preserve dirty edits on refresh", () => {
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  const booleanControl = new FakeNode("boolean");
  booleanControl.checked = true;
  booleanControl.dataset.valueType = "boolean";
  const integerControl = new FakeNode("integer");
  integerControl.dataset.valueType = "integer";
  integerControl.labels = [{ textContent: "Worker count" }];
  integerControl.value = "12";
  const numberControl = new FakeNode("number");
  numberControl.dataset.valueType = "number";
  numberControl.value = "0.75";
  const nullableControl = new FakeNode("nullable");
  nullableControl.dataset.nullable = "true";
  nullableControl.value = "  ";

  assert.equal(harness.api.readConfigControl(booleanControl), true);
  assert.equal(harness.api.readConfigControl(integerControl), 12);
  assert.equal(harness.api.readConfigControl(numberControl), 0.75);
  assert.equal(harness.api.readConfigControl(nullableControl), null);
  integerControl.value = "1.5";
  assert.throws(() => harness.api.readConfigControl(integerControl), /must be an integer/i);
  numberControl.value = "Infinity";
  assert.throws(() => harness.api.readConfigControl(numberControl), /finite number/i);

  harness.api.state.activeView = "overview";
  assert.equal(harness.api.applyConfigSnapshot({ revision: "pending", effective: {} }), false);
  assert.equal(harness.api.state.config.revision, "pending");
  assert.equal(harness.api.state.pendingConfig.revision, "pending");

  harness.api.state.activeView = "settings";
  harness.api.state.config = { revision: "old" };
  harness.api.state.configDirty = true;
  assert.equal(harness.api.applyConfigSnapshot({ revision: "new", effective: {} }), false);
  assert.equal(harness.api.state.pendingConfig.revision, "new");
  assert.match(harness.node("notice").textContent, /changed outside this dashboard/i);

  harness.api.state.configDirty = false;
  assert.equal(
    harness.api.applyConfigSnapshot({ revision: "forced", effective: {} }, { force: true }),
    true,
  );
  assert.equal(harness.api.state.config.revision, "forced");
});

test("live workforce change controls stay typed and bounded", () => {
  const harness = createAppHarness(() => {
    throw new Error("typed workforce settings do not fetch");
  });
  const controls = [
    ["config-workforce-hires-turn", "workforce.max_hires_per_turn", "integer", "1", "256", "17", 17],
    ["config-workforce-daily-alert", "workforce.daily_hire_alert_threshold", "integer", "0", "10000", "42", 42],
    ["config-workforce-repair-budget", "workforce.hiring_repair_budget", "integer", "0", "8", "3", 3],
    ["config-workforce-amend-overlap", "workforce.amend_overlap_threshold", "number", "0", "1", "0.73", 0.73],
  ];

  for (const [id, path, valueType, minimum, maximum, value, expected] of controls) {
    const tag = INDEX_SOURCE.match(new RegExp(`<input id="${id}"[^>]*>`))?.[0] || "";
    assert.match(tag, new RegExp(`data-config-path="${path.replaceAll(".", "\\.")}"`));
    assert.match(tag, new RegExp(`data-value-type="${valueType}"`));
    assert.match(tag, /type="number"/);
    assert.match(tag, new RegExp(`min="${minimum}"`));
    assert.match(tag, new RegExp(`max="${maximum}"`));
    const control = new FakeNode(id);
    control.dataset.valueType = valueType;
    control.labels = [{ textContent: id }];
    control.value = value;
    assert.equal(harness.api.readConfigControl(control), expected);
  }
  const overlapTag = INDEX_SOURCE.match(
    /<input id="config-workforce-amend-overlap"[^>]*>/,
  )?.[0] || "";
  assert.match(overlapTag, /step="0\.01"/);
});

test("config snapshots keep effective privacy and retention summaries current", () => {
  const harness = createAppHarness(() => {
    throw new Error("summary projection does not fetch");
  });
  harness.api.state.activeView = "overview";

  assert.equal(harness.api.applyConfigSnapshot({
    effective: { observability: { capture_content: true, retention_days: 45 } },
    revision: "summary-current",
  }), false);
  assert.equal(harness.api.state.overview.capture_content, true);
  assert.equal(harness.api.state.overview.retention_days, 45);
  assert.equal(harness.node("setting-capture").textContent, "Opt-in enabled");
  assert.equal(harness.node("setting-retention").textContent, "45 days");
  assert.equal(harness.node("privacy-chip").textContent, "Redacted runtime content");

  harness.api.state.activeView = "settings";
  harness.api.state.config = { revision: "editor-old" };
  harness.api.state.configDirty = true;
  assert.equal(harness.api.applyConfigSnapshot({
    effective: { observability: { capture_content: false, retention_days: 60 } },
    revision: "external-new",
  }), false);
  assert.equal(harness.api.state.config.revision, "editor-old");
  assert.equal(harness.api.state.pendingConfig.revision, "external-new");
  assert.equal(harness.api.state.overview.capture_content, false);
  assert.equal(harness.api.state.overview.retention_days, 60);
  assert.equal(harness.node("setting-capture").textContent, "Disabled");
  assert.equal(harness.node("setting-retention").textContent, "60 days");
  assert.equal(harness.node("privacy-chip").textContent, "Runtime metadata only");
});

test("app.js host and formatting helpers distinguish unknown, stale, and installed states", () => {
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  assert.equal(harness.api.formatBytes(512), "512 B");
  assert.equal(harness.api.formatBytes(1536), "1.5 KB");
  assert.equal(harness.api.formatBytes(2 * (1024 ** 2)), "2.0 MB");
  assert.equal(harness.api.formatTime(null), "—");
  assert.equal(harness.api.formatTime("invalid-time"), "invalid-time");
  assert.equal(harness.api.hostState({ runtime_enabled: false }), "runtime-disabled");
  assert.equal(harness.api.hostState({ inspection_status: "stale" }), "inspection-stale");
  assert.equal(harness.api.hostState({ discovered: true }), "host-discovered");
  assert.equal(harness.api.hostState({}), "absent");
  assert.equal(harness.api.hostLocation({ executable: "/usr/bin/codex" }), "/usr/bin/codex");
  assert.equal(
    harness.api.hostLocation({ native_root: "/safe/plugin", native_root_exists: true }),
    "/safe/plugin",
  );
  assert.equal(
    harness.api.hostLocation({ current_native_root: true }),
    "Current native payload detected",
  );
  assert.equal(harness.api.hostLocation({}), "Not discovered");
  assert.equal(harness.api.truthLabel(true, "yes", "no", "unknown"), "yes");
  assert.equal(harness.api.truthLabel(false, "yes", "no", "unknown"), "no");
  assert.equal(harness.api.truthLabel(null, "yes", "no", "unknown"), "unknown");
});

test("host views disclose empty inventories and unknown runtime controls truthfully", () => {
  const harness = createAppHarness(() => {
    throw new Error("render-only test does not fetch");
  });
  harness.api.state.overview = { status: "ok", recent: {} };
  harness.api.state.activity = {};
  harness.api.state.hosts = [];

  harness.api.renderOverview();
  assert.match(
    harness.node("overview-hosts").children[0].textContent,
    /no supported agent hosts were found/i,
  );
  harness.api.renderHosts();
  assert.match(
    harness.node("host-grid").children[0].textContent,
    /install or register a host, then refresh/i,
  );

  harness.api.state.hosts = [{
    hook_trust_action: "Run /hooks, then verify activation.",
    host: "codex",
    maturity: "activation-required",
  }];
  harness.api.renderHosts();
  const labels = descendants(harness.node("host-grid")).map((node) => node.textContent);
  assert.ok(labels.includes("runtime state unknown"));
  assert.equal(labels.includes("runtime on"), false);
  assert.ok(labels.includes("Run /hooks, then verify activation."));
});

test("host view copies only the write-free attended uninstall preview", async () => {
  const copied = [];
  const harness = createAppHarness(() => {
    throw new Error("copy-only test does not fetch");
  });
  harness.context.window.navigator = {
    clipboard: { writeText: async (value) => copied.push(value) },
  };
  harness.api.state.hosts = [{ host: "codex", maturity: "runtime-verified" }];
  harness.api.renderHosts();
  harness.api.bindEvents();

  const command = descendants(harness.node("host-grid"))
    .find((node) => node.id === "uninstall-preview-command");
  const button = descendants(harness.node("host-grid"))
    .find((node) => node.id === "uninstall-copy-button");
  assert.equal(command.textContent, "agency uninstall --all --dry-run");
  assert.equal(button.textContent, "Copy uninstall preview");
  await harness.node("host-grid").listeners.get("click")[0]({ target: button });

  assert.deepEqual(copied, ["agency uninstall --all --dry-run"]);
  assert.match(harness.node("notice").textContent, /owner-controlled terminal/i);
});

test("host cards render activation proof truthfully without adding canary controls", () => {
  const harness = createAppHarness(() => {
    throw new Error("render-only test does not fetch");
  });
  const digest = "a".repeat(64);
  const attestation = {
    passed_at: "2026-07-27T12:34:56Z",
    profile_scope: "current-profile",
    proof_contract: "agency.codex-activation-canary.v2",
    proof_digest: digest,
    trace_id: "trace-safe",
  };

  harness.api.state.hosts = [{
    canary_attestation: attestation,
    canary_attestation_status: "verified",
    host: "codex",
    inspection_status: "complete",
    maturity: "runtime-verified",
  }];
  harness.api.renderHosts();
  let labels = descendants(harness.node("host-grid")).map((node) => node.textContent);
  assert.ok(labels.includes("Last successful activation proof"));
  assert.ok(labels.includes(`Proof fingerprint · ${digest}`));
  assert.ok(labels.includes("Contract · agency.codex-activation-canary.v2"));
  assert.ok(labels.includes("Profile · current-profile"));
  assert.ok(labels.includes("Trace · trace-safe"));
  assert.deepEqual(
    descendants(harness.node("host-grid"))
      .filter((node) => node.type === "button")
      .map((node) => node.id),
    ["uninstall-copy-button"],
  );

  harness.api.state.hosts = [{
    canary_attestation: attestation,
    canary_attestation_status: "stale",
    canary_stale_reasons: ["bundle_digest"],
    host: "codex",
    inspection_status: "complete",
    maturity: "activation-required",
  }];
  harness.api.renderHosts();
  labels = descendants(harness.node("host-grid")).map((node) => node.textContent);
  assert.ok(labels.includes("Historical activation proof"));
  assert.ok(labels.some((label) => /bundle_digest/.test(label)));
  assert.equal(labels.includes("Last successful activation proof"), false);

  harness.api.state.hosts = [{
    canary_attestation_status: "absent",
    host: "codex",
    inspection_status: "complete",
  }];
  harness.api.renderHosts();
  labels = descendants(harness.node("host-grid")).map((node) => node.textContent);
  assert.ok(labels.includes("No current-profile Codex activation proof is attested."));

  const hostile = "<img src=x onerror=globalThis.compromised=true>";
  harness.api.state.hosts = [{
    canary_attestation: { ...attestation, proof_digest: hostile },
    canary_attestation_status: "inspection-unavailable",
    host: "codex",
    inspection_status: "stale",
    maturity: "inspection-stale",
  }];
  harness.api.renderHosts();
  labels = descendants(harness.node("host-grid")).map((node) => node.textContent);
  assert.ok(labels.includes("Activation proof unavailable"));
  assert.ok(labels.includes("Historical proof metadata (not current)"));
  assert.equal(labels.includes("Last successful activation proof"), false);
  assert.ok(labels.some((label) => label.includes(hostile)));
  assert.ok(descendants(harness.node("host-grid")).every((node) => node.innerHTML === undefined));
  assert.equal(harness.context.compromised, undefined);
});

test("Route Lab offers only unambiguous bounded execution hosts and preserves explicit choice", () => {
  const missing = createAppHarness(() => {
    throw new Error("missing optional Route Lab controls do not fetch");
  });
  missing.missing("route-host");
  assert.equal(missing.api.renderRouteHosts(), "");

  const harness = createAppHarness(() => {
    throw new Error("host rendering does not fetch");
  });
  harness.api.state.master = { enabled: true, generation: 1 };

  assert.equal(harness.api.renderRouteHosts(), "");
  assert.equal(harness.node("route-host").disabled, true);
  assert.equal(harness.node("route-button").disabled, true);
  assert.match(harness.node("route-host-help").textContent, /no current native installation/i);

  harness.api.state.hosts = [
    null,
    {
      effective_enabled: true,
      host: "codex",
      execution_capabilities: {
        capabilities: ["repository-read"],
        execution_host: "codex",
        status: "native-evidence-unproven",
      },
    },
    verifiedHost("claude", ["repository-read"]),
    verifiedHost("claude", ["duplicate-must-not-replace"]),
    verifiedHost("openclaw", ["native-delegation", "repository-read"]),
    verifiedHost("zcode", ["native-delegation", "repository-read"]),
    verifiedHost("unknown"),
    {
      effective_enabled: true,
      host: "hermes",
      execution_capabilities: {
        capabilities: "not-a-list",
        execution_host: "hermes",
        status: "native-installation-verified",
      },
    },
  ];
  assert.equal(harness.api.renderRouteHosts(), "openclaw");
  assert.deepEqual(
    harness.node("route-host").children.map((option) => option.value),
    ["openclaw", "zcode"],
  );
  assert.equal(harness.node("route-host").disabled, false);
  assert.equal(harness.node("route-button").disabled, false);
  assert.match(harness.node("route-host-help").textContent, /ambiguous duplicate host/i);

  harness.node("route-host").value = "openclaw";
  assert.equal(harness.api.renderRouteHosts(), "openclaw");
  assert.match(harness.node("route-button").title, /openclaw/i);

  harness.node("route-button").setAttribute("aria-busy", "true");
  harness.node("route-button").disabled = true;
  assert.equal(harness.api.renderRouteHosts(), "openclaw");
  assert.equal(harness.node("route-button").disabled, true);

  const optional = createAppHarness(() => {
    throw new Error("missing optional Route Lab labels do not fetch");
  });
  optional.missing("route-host-help");
  optional.missing("route-button");
  optional.api.state.master = { enabled: true, generation: 1 };
  optional.api.state.hosts = [verifiedHost("codex")];
  assert.equal(optional.api.renderRouteHosts(), "codex");
});

test("Route Lab UI refuses duplicate and oversized host inventories before POST", async () => {
  let calls = 0;
  const duplicate = createAppHarness(async () => {
    calls += 1;
    throw new Error("ambiguous host inventory must not reach Route Lab");
  });
  duplicate.api.state.master = { enabled: true, generation: 1 };
  duplicate.api.state.hosts = [verifiedHost("codex"), verifiedHost("codex")];
  duplicate.node("route-task").value = "Review this bounded host contract";

  assert.equal(duplicate.api.renderRouteHosts(), "");
  assert.equal(duplicate.node("route-button").disabled, true);
  assert.match(duplicate.node("route-host-help").textContent, /ambiguous duplicate host/i);
  await duplicate.api.runRoute();
  assert.equal(calls, 0);
  assert.match(duplicate.node("notice").textContent, /verified, enabled execution host/i);

  const oversized = createAppHarness(() => {
    throw new Error("oversized host inventory must not fetch");
  });
  oversized.api.state.master = { enabled: true, generation: 1 };
  oversized.api.state.hosts = [
    verifiedHost("codex"),
    ...Array.from({ length: 10 }, (_, index) => ({ host: `unknown-${index}` })),
  ];
  assert.equal(oversized.api.renderRouteHosts(), "");
  assert.equal(oversized.node("route-button").disabled, true);
  assert.match(oversized.node("route-host-help").textContent, /safe Route Lab bound/i);

  for (const [field, invalidValue] of [
    ["contract_version", "2"],
    ["source", "native-adapter-event"],
    ["evidence", [" duplicated evidence "]],
    ["capabilities", ["not-a-governed-native-capability"]],
  ]) {
    let malformedCalls = 0;
    const malformed = createAppHarness(async () => {
      malformedCalls += 1;
      throw new Error("malformed capability evidence must not reach Route Lab");
    });
    const host = verifiedHost("codex");
    host.execution_capabilities[field] = invalidValue;
    malformed.api.state.master = { enabled: true, generation: 1 };
    malformed.api.state.hosts = [host];
    malformed.node("route-task").value = "Reject malformed host evidence";
    assert.equal(malformed.api.renderRouteHosts(), "");
    assert.equal(malformed.node("route-button").disabled, true);
    await malformed.api.runRoute();
    assert.equal(malformedCalls, 0);
  }
});

test("owner settings surface materializes the ZCode adapter field", () => {
	const harness = createAppHarness(() => {
		throw new Error("owner surface setup does not fetch");
  });
  const grid = new FakeNode("adapter-grid");
  harness.missing("config-adapter-zcode");
  harness.select(".adapter-grid", [grid]);

	assert.equal(harness.api.configureOwnerSurface(), true);
  assert.equal(grid.children.length, 1);
  const [label] = grid.children;
  assert.equal(label.textContent, "ZCode");
  const [select] = label.children;
  assert.equal(select.id, "config-adapter-zcode");
  assert.equal(select.getAttribute("data-config-path"), "adapters.zcode.enabled");
  assert.deepEqual(
    select.children.map((option) => [option.value, option.textContent]),
    [["auto", "Auto"], ["true", "Enabled"], ["false", "Disabled"]],
  );
});

test("Route Lab renders authoritative host evidence and bounded eligibility rejections", () => {
  const harness = createAppHarness(() => {
    throw new Error("receipt rendering does not fetch");
  });
  harness.api.renderReceipt({
    eligibility: {
      capability_status: "native-installation-verified",
      eligible_count: 17,
      execution_host: "codex",
      rejection_count: 2,
      rejections: [
        { slug: "browser-specialist", reason: "missing_capabilities:browser-automation" },
        { slug: "linux-specialist", reason: "unsupported_tool_platform:windows" },
      ],
      truncated: true,
    },
    host_capability_receipt: {
      capabilities: ["repository-read", "test-execution"],
      execution_host: "codex",
      status: "native-installation-verified",
    },
    routing: {
      inference_mode: "inferred",
      provider_attempts: [
        {
          actual_model: "gpt-5.6-luna",
          latency_ms: 38187,
          model_group: "",
          model_receipt_source: "cli.explicit_model_argument",
          provider_name: "codex-subscription",
          provider_type: "cli",
          reason_code: "structured_response_applied",
          requested_model: "gpt-5.6-luna",
          stage: "planner",
          status: "applied",
        },
        {
          actual_model: "openai/gpt-5.6-mini",
          latency_ms: 27688,
          model_group: "task-agency-router",
          model_receipt_source: "response.body.model",
          provider_name: "agency-router",
          provider_type: "litellm",
          reason_code: "provider_response_contract_invalid",
          requested_model: "task-agency-router",
          stage: "recruiter",
          status: "rejected",
          validation_detail: "missing typed shortlist candidate",
        },
      ],
    },
    selected: [],
    signals: { selection: { status: "abstained" } },
  });

  const text = descendants(harness.node("route-result")).map((node) => node.textContent);
  assert.ok(text.includes("codex"));
  assert.ok(text.some((value) => /17 eligible · 2 rejected · bounded view/i.test(value)));
  assert.ok(text.some((value) => /browser-specialist: missing_capabilities/i.test(value)));
  assert.ok(text.includes("codex-subscription · cli"));
  assert.ok(text.includes("task-agency-router"));
  assert.ok(text.includes("openai/gpt-5.6-mini"));
  assert.ok(text.includes("response.body.model"));
  assert.ok(text.includes("27.69 s"));
  assert.ok(text.some((value) => /provider response contract invalid/i.test(value)));
  assert.ok(text.some((value) => /missing typed shortlist candidate/i.test(value)));
  assert.equal(harness.node("route-status").textContent, "ABSTAINED");

  harness.api.renderReceipt({
    eligibility: {
      eligible_count: 0,
      execution_host: "codex",
      rejection_count: 0,
      rejections: [],
      truncated: false,
    },
    host_capability_receipt: {
      execution_host: "codex",
      status: "native-installation-verified",
    },
    request_id: "<img src=x onerror=alert(1)>",
    selected: [],
    signals: { selection: { status: "abstained" } },
  });
  const emptyText = descendants(harness.node("route-result")).map((node) => node.textContent);
  assert.ok(emptyText.includes("0 eligible · 0 rejected"));
  assert.ok(emptyText.includes("native-installation-verified · 0 capabilities"));
  assert.ok(emptyText.includes("none: none"));
  assert.equal(emptyText.some((value) => value.includes("<img")), false);
});

test("bucketActivity returns a bounded empty series for absent or malformed data", () => {
  for (const activity of [undefined, null, {}, { routing: "bad", delegations: 42 }]) {
    const buckets = AgencyCharts.bucketActivity(activity, { now: NOW });
    assert.equal(buckets.length, 24);
    assert.ok(buckets.every((bucket) => bucket.routes === 0));
    assert.ok(buckets.every((bucket) => bucket.delegations === 0));
    assert.ok(buckets.every((bucket) => Number.isFinite(bucket.startMs)));
    assert.ok(buckets.every((bucket) => bucket.endMs > bucket.startMs));
  }

  assert.equal(
    AgencyCharts.bucketActivity({}, { now: NOW, bucketCount: 500 }).length,
    48,
  );
  const minimumWidth = AgencyCharts.bucketActivity(
    {},
    { now: NOW, bucketCount: 2, bucketMs: 1 },
  );
  assert.equal(minimumWidth[0].endMs - minimumWidth[0].startMs, 10_000);
});

test("charts.js preserves its legacy global fallback without weakening CommonJS exports", () => {
  const sandbox = { exports: {}, globalThis: undefined, module: { exports: {} } };
  vm.createContext(sandbox);
  new vm.Script(CHARTS_SOURCE, { filename: CHARTS_PATH }).runInContext(sandbox);

  assert.equal(typeof sandbox.module.exports.bucketActivity, "function");
  assert.equal(sandbox.AgencyCharts, sandbox.module.exports);
});

test("bucketActivity falls back safely for missing clocks and non-finite numeric timestamps", () => {
  const implicitNow = AgencyCharts.bucketActivity();
  assert.equal(implicitNow.length, 24);
  assert.ok(implicitNow.every((bucket) => Number.isFinite(bucket.startMs)));

  const invalidNow = AgencyCharts.bucketActivity({
    routing: [{ created_at: "" }, { created_at: Number.POSITIVE_INFINITY }],
  }, {
    now: Number.POSITIVE_INFINITY,
    bucketCount: 1,
    bucketMs: 10_000,
  });
  assert.equal(invalidNow.length, 1);
  assert.equal(invalidNow[0].routes, 0);
  assert.ok(Number.isFinite(invalidNow[0].startMs));
});

test("bucketActivity counts only valid in-window routing and delegation timestamps", () => {
  const activity = {
    routing: [
      { created_at: isoBefore(30_000) },
      { created_at: isoBefore(90_000) },
      { created_at: isoBefore(300_000) },
      { created_at: new Date(NOW + 1).toISOString() },
      { created_at: "not-a-date" },
      null,
    ],
    delegations: [
      { completed_at: isoBefore(15_000), started_at: "ignored" },
      { started_at: isoBefore(70_000) },
      { completed_at: "not-a-date", started_at: isoBefore(20_000) },
      { started_at: new Date(NOW + 60_000).toISOString() },
      {},
    ],
  };

  const buckets = AgencyCharts.bucketActivity(activity, {
    now: new Date(NOW),
    bucketCount: 4,
    bucketMs: 60_000,
  });

  assert.equal(buckets.length, 4);
  assert.equal(buckets.reduce((total, item) => total + item.routes, 0), 2);
  assert.equal(buckets.reduce((total, item) => total + item.delegations, 0), 2);
  assert.equal(buckets.at(-1).routes, 1);
  assert.equal(buckets.at(-1).delegations, 1);
});

test("bucketActivity remains deterministic for dense data and parseable now values", () => {
  const activity = {
    routing: Array.from({ length: 120 }, (_, index) => ({
      created_at: isoBefore((index % 12) * 10_000 + 1),
    })),
    delegations: Array.from({ length: 80 }, (_, index) => ({
      started_at: isoBefore((index % 8) * 15_000 + 1),
    })),
  };
  const options = {
    now: "2026-07-11T12:00:30.500Z",
    bucketCount: 12,
    bucketMs: 10_000,
  };

  const first = AgencyCharts.bucketActivity(activity, options);
  const second = AgencyCharts.bucketActivity(activity, options);

  assert.deepEqual(second, first);
  assert.equal(first.reduce((total, item) => total + item.routes, 0), 120);
  assert.equal(first.reduce((total, item) => total + item.delegations, 0), 80);
  assert.ok(first.every((bucket, index) => (
    index === 0 || bucket.startMs === first[index - 1].endMs
  )));
});

test("outcomeCounts classifies known outcomes and treats malformed statuses as unknown", () => {
  assert.deepEqual(AgencyCharts.outcomeCounts(), {
    success: 0,
    failed: 0,
    skipped: 0,
    unknown: 0,
    total: 0,
  });
  assert.deepEqual(AgencyCharts.outcomeCounts({ delegations: "bad" }), {
    success: 0,
    failed: 0,
    skipped: 0,
    unknown: 0,
    total: 0,
  });

  const counts = AgencyCharts.outcomeCounts({
    delegations: [
      { status: "success" },
      { status: "completed" },
      { status: "ok" },
      { status: "failed" },
      { status: "failure" },
      { status: "error" },
      { status: "cancelled" },
      { status: "timed_out" },
      { status: "timeout" },
      { status: "skipped" },
      { status: "blocked" },
      { status: "pending" },
      {},
      null,
    ],
  });
  assert.deepEqual(counts, { success: 3, failed: 6, skipped: 2, unknown: 3, total: 14 });
});

test("renderOutcomeChart exposes each non-empty segment to keyboard and assistive technology", () => {
  const root = svgHarness();
  const summary = { id: "outcome-summary", textContent: "" };
  AgencyCharts.renderOutcomeChart(root, summary, {
    delegations: [
      { status: "completed" },
      { status: "failed" },
      { status: "blocked" },
      { status: "something-new" },
    ],
  });

  const nodes = descendants(root);
  const segments = nodes.filter((node) => node.attributes?.get("role") === "img");
  assert.equal(segments.length, 4);
  assert.deepEqual(
    segments.map((node) => node.attributes.get("aria-label")),
    [
      "Completed: 1 (25.0%)",
      "Failed: 1 (25.0%)",
      "Skipped: 1 (25.0%)",
      "Unknown: 1 (25.0%)",
    ],
  );
  assert.ok(segments.every((node) => node.attributes.get("tabindex") === "0"));
});

test("renderActivityChart draws bounded series with readable axes and focusable observations", () => {
  const root = svgHarness();
  const summary = { id: "activity-summary", textContent: "" };
  const buckets = AgencyCharts.renderActivityChart(root, summary, {
    routing: [{ created_at: isoBefore(30_000) }, { created_at: isoBefore(90_000) }],
    delegations: [{ started_at: isoBefore(15_000), status: "completed" }],
  }, { now: NOW, bucketCount: 4, bucketMs: 60_000 });

  assert.equal(buckets.length, 4);
  assert.equal(root.dataset.routes, "2");
  assert.equal(root.dataset.delegations, "1");
  assert.match(summary.textContent, /2 observed routes · 1 delegation-event rows/i);
  const nodes = descendants(root);
  const axisLabels = nodes.filter((node) => node.attributes?.get("class")?.includes("axis-label"));
  assert.ok(axisLabels.some((node) => node.textContent === "0"));
  assert.ok(axisLabels.some((node) => node.textContent === "1"));
  const points = nodes.filter((node) => node.attributes?.get("data-chart-point") === "true");
  assert.equal(points.length, 3);
  assert.ok(points.every((node) => node.attributes.get("tabindex") === "0"));
  assert.ok(points.every((node) => node.attributes.get("aria-label")));
});

test("chart renderers support ambient documents, one-point windows, and empty outcomes", () => {
  const documentDescriptor = Object.getOwnPropertyDescriptor(globalThis, "document");
  const documentRef = { createElementNS: (_namespace, tag) => new FakeSvgNode(tag) };
  Object.defineProperty(globalThis, "document", {
    configurable: true,
    value: documentRef,
  });
  try {
    const activityRoot = new FakeSvgNode("activity-root");
    const buckets = AgencyCharts.renderActivityChart(activityRoot, null, {
      routing: [{ created_at: new Date(NOW).toISOString() }],
    }, { now: NOW, bucketCount: 1, bucketMs: 60_000 });
    assert.equal(buckets.length, 1);
    assert.equal(activityRoot.dataset.routes, "1");
    const activitySvg = activityRoot.children[0];
    assert.equal(activitySvg.attributes.get("role"), "group");
    assert.match(
      activitySvg.attributes.get("aria-describedby"),
      /^agency-chart-description-\d+$/,
    );

    const outcomeRoot = new FakeSvgNode("outcome-root");
    const counts = AgencyCharts.renderOutcomeChart(outcomeRoot, null, { delegations: [] });
    assert.deepEqual(counts, { success: 0, failed: 0, skipped: 0, unknown: 0, total: 0 });
    assert.equal(outcomeRoot.dataset.total, "0");
    assert.equal(
      descendants(outcomeRoot).filter((node) => node.attributes?.get("role") === "img").length,
      0,
    );
    assert.match(
      outcomeRoot.children[0].attributes.get("aria-describedby"),
      /^agency-chart-description-\d+$/,
    );
  } finally {
    if (documentDescriptor) {
      Object.defineProperty(globalThis, "document", documentDescriptor);
    } else {
      Reflect.deleteProperty(globalThis, "document");
    }
  }
});

test("pure chart helpers preserve hostile labels as inert input data", () => {
  const hostile = '<img src=x onerror="globalThis.compromised=true">';
  const activity = {
    routing: [{ created_at: isoBefore(1_000), selected_ids: [hostile] }],
    delegations: [
      { started_at: isoBefore(1_000), executed_worker_id: hostile },
      { started_at: isoBefore(1_000), status: hostile, executed_worker_id: hostile },
    ],
  };
  const before = structuredClone(activity);

  const buckets = AgencyCharts.bucketActivity(activity, {
    now: NOW,
    bucketCount: 1,
    bucketMs: 60_000,
  });
  const outcomes = AgencyCharts.outcomeCounts(activity);

  assert.deepEqual(activity, before);
  assert.equal(buckets[0].routes, 1);
  assert.equal(buckets[0].delegations, 2);
  assert.deepEqual(outcomes, { success: 0, failed: 0, skipped: 0, unknown: 2, total: 2 });
  assert.equal(globalThis.compromised, undefined);
});

test("retryDelay is deterministic, bounded, integer, and capped", () => {
  assert.equal(AgencyCharts.retryDelay(1, () => 0), 2_000);
  assert.equal(AgencyCharts.retryDelay(2, () => 0), 4_000);
  assert.equal(AgencyCharts.retryDelay(1, () => 1), 2_400);
  assert.equal(AgencyCharts.retryDelay(2, () => 1), 4_500);
  assert.equal(AgencyCharts.retryDelay(0, () => 0), 2_000);
  assert.equal(AgencyCharts.retryDelay(Number.NaN, () => 0), 2_000);
  assert.equal(AgencyCharts.retryDelay(1, () => -10), 2_000);
  assert.equal(AgencyCharts.retryDelay(1, () => 10), 2_400);
  assert.equal(AgencyCharts.retryDelay(1, 0.5), 2_200);
  assert.equal(AgencyCharts.retryDelay(1, Number.NaN), 2_000);
  assert.equal(AgencyCharts.retryDelay(1, () => { throw new Error("entropy unavailable"); }), 2_000);
  assert.equal(AgencyCharts.retryDelay(100, () => 0), 30_000);
  assert.equal(AgencyCharts.retryDelay(100, () => 1), 30_000);
  assert.ok(Number.isInteger(AgencyCharts.retryDelay(3, () => 0.314159)));
});

test("app.js renders hostile runtime labels as inert text across dashboard surfaces", () => {
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  const hostile = '<img src=x onerror="globalThis.compromised=true">';
  harness.api.state.overview = {
    capture_content: false,
    db_size_bytes: 1024,
    provider_health: [{
      failure_count: 1,
      latest_status: hostile,
      provider: hostile,
      success_count: 2,
      unknown_count: 0,
    }],
    recent: { delegations: 1, routing: 1 },
    retention_days: 30,
    roster_count: 1,
    status: "ok",
    wal_size_bytes: 512,
  };
  harness.api.state.hosts = [{
    current_native_root: true,
    discovered: true,
    effective_enabled: undefined,
    enabled: false,
    executable_discovered: true,
    host: hostile,
    inspection_status: "stale",
    maturity: "host-discovered",
    registered: true,
    runtime_enabled: true,
  }];
  harness.api.state.activity = {
    delegations: [{
      backend: hostile,
      host: hostile,
      id: "delegation-1",
      executed_worker_id: hostile,
      recommended_agent: "must-not-render-as-executor",
      started_at: "not-a-time",
      status: hostile,
    }],
    routing: [{
      created_at: "not-a-time",
      id: "routing-1",
      selected_ids: [hostile],
      source: hostile,
      status: hostile,
      trace_id: hostile,
    }],
  };

  harness.api.renderOverview();
  harness.api.renderHosts();
  harness.api.renderEvidence("routing");
  harness.api.renderReceipt({
    selected: [{ slug: hostile }],
    signals: { policy: { matched_actions: [hostile] } },
    status: hostile,
  });

  for (const root of [
    harness.node("overview-delegations"),
    harness.node("overview-hosts"),
    harness.node("provider-health"),
    harness.node("host-grid"),
    harness.node("evidence-body"),
    harness.node("route-result"),
  ]) {
    assert.ok(descendants(root).some((node) => node.textContent.includes(hostile)));
    assert.ok(descendants(root).every((node) => node.innerHTML === undefined));
  }
  assert.equal(harness.context.compromised, undefined);
});

test("delegation-event rows render only observed execution identity", () => {
  const harness = createAppHarness(() => {
    throw new Error("execution-identity rendering does not fetch");
  });
  harness.api.state.overview = {
    capture_content: false,
    recent: { delegations: 3, routing: 0 },
    retention_days: 30,
    status: "ok",
  };
  harness.api.state.activity = {
    delegations: [{
      backend: "native-task",
      executed_worker_id: "code-reviewer",
      executed_worker_kind: "specialist",
      host: "codex",
      id: "observed-event",
      native_run_id: "native-42",
      recommended_agent: "wrong-recommendation",
      started_at: isoBefore(1_000),
      status: "completed",
      work_unit_id: "recorded-unit",
    }, {
      backend: "legacy-tool",
      host: "claude",
      id: "recommendation-only-event",
      recommended_agent: "recommendation-only",
      started_at: isoBefore(2_000),
      status: "unknown",
    }, {
      backend: "legacy-tool",
      executed_worker_kind: "legacy-unverified-worker",
      host: "claude",
      id: "legacy-kind-only-event",
      recommended_agent: "legacy-recommendation",
      started_at: isoBefore(3_000),
      status: "completed",
    }],
  };

  harness.api.renderOverview();
  const overviewText = descendants(harness.node("overview-delegations"))
    .map((node) => node.textContent)
    .join("\n");
  assert.match(overviewText, /specialist · code-reviewer · run native-42/);
  assert.match(overviewText, /Not observed/);
  assert.doesNotMatch(overviewText, /wrong-recommendation|recommendation-only|legacy-recommendation|legacy-unverified-worker/);

  harness.api.renderEvidence("delegations");
  assert.deepEqual(
    harness.node("evidence-head").children[0].children.map((node) => node.textContent),
    ["Observed child", "Host", "Event state", "Host tool", "Recorded correlation ID", "Observed"],
  );
  const evidenceText = descendants(harness.node("evidence-body"))
    .map((node) => node.textContent)
    .join("\n");
  assert.match(evidenceText, /specialist · code-reviewer · run native-42/);
  assert.match(evidenceText, /Not observed/);
  assert.doesNotMatch(evidenceText, /wrong-recommendation|recommendation-only|legacy-recommendation|legacy-unverified-worker/);
  assert.match(harness.node("evidence-caption").textContent, /delegation-event row evidence/i);
  assert.match(harness.node("evidence-context").textContent, /recommendation is never presented as the executor/i);
});

test("app.js roster and empty evidence renderers expose actionable, scoped controls", async () => {
  const harness = createAppHarness(() => {
    throw new Error("render-only test does not fetch");
  });
  harness.api.state.roster = [
    {
      agent_slug: "security-reviewer",
      capabilities: ["security"],
      division: "review",
      enabled: true,
      name: "Security Reviewer",
    },
    { agent_slug: "generalist", capabilities: [], enabled: false },
    { agent_slug: "chief-of-staff", capabilities: [], enabled: true, protected: false },
  ];
  harness.api.state.rosterPage = {
    count: 3, total_count: 3, enabled_count: 2, disabled_count: 1, truncated: false,
  };
  harness.api.state.snapshots = [
    { activated: false, agent_count: 2, approved: false, created_at: null, snapshot_id: "pending" },
    { activated: false, agent_count: 2, approved: true, created_at: isoBefore(1_000), snapshot_id: "approved" },
    { activated: true, agent_count: 2, approved: true, created_at: isoBefore(2_000), snapshot_id: "active" },
  ];

  harness.api.renderRoster();
  assert.equal(harness.node("roster-count").textContent, "2 enabled · 3 total");
	const rosterNodes = descendants(harness.node("roster-grid"));
	assert.ok(rosterNodes.some((node) => node.textContent === "no capability tags"));
	assert.ok(rosterNodes.some((node) => node.className === "agent-card disabled"));
	const agentButtons = rosterNodes.filter((node) => node.type === "button");
	assert.deepEqual(agentButtons.map((node) => node.textContent), [
		"disable",
		"enable",
		"disable",
	]);
	assert.equal(agentButtons[0].disabled, false);
	assert.equal(agentButtons[1].disabled, false);
	assert.equal(agentButtons[2].disabled, false);
	assert.match(INDEX_SOURCE, /Agency steward is protected infrastructure/i);
	const snapshotNodes = descendants(harness.node("snapshot-list"));
	const snapshotButtons = snapshotNodes.filter((node) => node.type === "button");
	assert.deepEqual(snapshotButtons.map((node) => node.textContent), ["approve", "activate"]);
	assert.ok(snapshotButtons.every((node) => node.disabled === false));

  harness.api.state.activity = {};
  harness.api.renderEvidence("delegations");
  assert.equal(harness.node("evidence-head").children[0].children[0].getAttribute("scope"), "col");
  assert.match(
    harness.node("evidence-body").children[0].children[0].textContent,
    /no delegation-event row evidence/i,
  );
});

test("app.js model receipts show requested alias, LiteLLM router, and actual model separately", () => {
  const harness = createAppHarness(() => {
    throw new Error("render-only test does not fetch");
  });
  harness.api.state.activity = {
    receipts: [{
      ended_at: isoBefore(1_000),
      host: "litellm",
      model_group: "production-router",
      requested_model: "task-general",
      resolved_model: "gpt-5.6",
      resolved_provider: "openai",
      source: "litellm",
      status: "success",
    }],
  };

  harness.api.renderEvidence("receipts");

  assert.deepEqual(
    harness.node("evidence-head").children[0].children.map((node) => node.textContent),
    [
      "Requested",
      "LiteLLM router / model group",
      "Actual provider",
      "Actual model",
      "Host",
      "Status",
      "Source",
      "Ended",
    ],
  );
  const values = harness.node("evidence-body").children[0].children
    .map((node) => node.textContent || node.children[0]?.textContent);
  assert.deepEqual(values.slice(0, 4), [
    "task-general",
    "production-router",
    "openai",
    "gpt-5.6",
  ]);
});

test("app.js specialist evidence separates current turns from immutable history", () => {
  const harness = createAppHarness(() => {
    throw new Error("render-only test does not fetch");
  });
  harness.api.state.activity = {
    specialists: [
      {
        expired_at: null,
        id: "activation-current",
        loaded_at: isoBefore(1_000),
        session_id: "session-current",
        slug: "security-reviewer",
        state: "current",
        trace_id: "trace-current",
      },
      {
        expired_at: isoBefore(2_000),
        id: "activation-history",
        loaded_at: isoBefore(3_000),
        session_id: "session-history",
        slug: "code-reviewer",
        state: "historical",
        trace_id: "trace-history",
      },
    ],
    routing: [{
      created_at: isoBefore(500),
      fallback_applied: true,
      fallback_companion_ids: ["agents-orchestrator", "chief-of-staff"],
      id: "decision-fallback",
      selected_ids: ["agents-orchestrator", "chief-of-staff"],
      semantic_status: "abstained",
      source: "policy_fallback",
      status: "policy_fallback",
      trace_id: "trace-current",
    }, {
      created_at: isoBefore(250),
      fallback_applied: false,
      fallback_companion_ids: [],
      id: "decision-semantic",
      selected_ids: ["security-reviewer"],
      semantic_status: "selected",
      source: "computed",
      status: "selected",
      trace_id: "trace-semantic",
    }],
  };

  harness.api.renderEvidence();

  assert.match(harness.node("evidence-caption").textContent, /current-turn and historical/i);
  assert.match(harness.node("evidence-context").textContent, /1 current-turn activation · 1 historical activation/i);
  assert.deepEqual(
    harness.node("evidence-head").children[0].children.map((node) => node.textContent),
    ["Specialist", "Session", "Trace", "Evidence state", "Activated", "Expired"],
  );
  const activationRows = harness.node("evidence-body").children;
  assert.equal(activationRows[0].children[3].children[0].textContent, "Current turn");
  assert.match(activationRows[0].children[3].children[0].className, /activation-current/);
  assert.equal(activationRows[1].children[3].children[0].textContent, "Historical");
  assert.match(activationRows[1].children[3].children[0].className, /activation-historical/);

  harness.api.state.activity.specialists = [{
    id: "activation-malformed-state",
    loaded_at: isoBefore(4_000),
    session_id: "session-legacy",
    slug: "legacy-reviewer",
    state: "",
    trace_id: "",
  }];
  harness.api.renderEvidence();
  assert.equal(harness.node("evidence-body").children[0].children[3].children[0].textContent, "Historical");
  assert.match(harness.node("evidence-context").textContent, /0 current-turn activations · 1 historical activation/i);

  harness.api.state.activity.specialists = [];
  harness.api.renderEvidence();
  assert.match(harness.node("evidence-context").textContent, /0 current-turn activations · 0 historical activations/i);
  assert.match(
    harness.node("evidence-body").children[0].children[0].textContent,
    /no specialist activation evidence/i,
  );

  harness.api.renderEvidence("routing");
  const routingValues = descendants(harness.node("evidence-body")).map((node) => node.textContent);
  assert.ok(routingValues.includes("abstained"));
  assert.ok(routingValues.includes("policy_fallback"));
  assert.ok(routingValues.includes("Yes"));
  assert.ok(routingValues.includes("No"));
  assert.ok(routingValues.includes("agents-orchestrator, chief-of-staff"));
  assert.match(harness.node("evidence-context").textContent, /metadata-only runtime evidence/i);
});

test("evidence context is static prose and deduplicates live-render writes", () => {
  const contextTag = INDEX_SOURCE.match(/<p id="evidence-context"[^>]*>/)?.[0] || "";
  assert.doesNotMatch(contextTag, /role="status"|aria-live=/);

  const harness = createAppHarness(() => {
    throw new Error("render-only test does not fetch");
  });
  const context = harness.node("evidence-context");
  let rendered = "";
  let writes = 0;
  Object.defineProperty(context, "textContent", {
    configurable: true,
    get() { return rendered; },
    set(value) { rendered = String(value); writes += 1; },
  });

  harness.api.state.activity = { specialists: [] };
  harness.api.renderEvidence("specialists");
  harness.api.renderEvidence("specialists");
  assert.equal(writes, 1);

  harness.api.state.activity.specialists.push({ state: "current" });
  harness.api.renderEvidence("specialists");
  assert.equal(writes, 2);
});

test("app.js evidence tabs implement roving keyboard focus and labelled panels", () => {
  const harness = createAppHarness(() => {
    throw new Error("keyboard-only test does not fetch");
  });
  const tabList = new FakeNode("tab-list");
  const delegationTab = new FakeNode();
  delegationTab.classList.add("active");
  delegationTab.dataset.evidence = "delegations";
  delegationTab.parentElement = tabList;
  const routingTab = new FakeNode();
  routingTab.dataset.evidence = "routing";
  routingTab.parentElement = tabList;
  const panel = new FakeNode("evidence-panel");
  harness.node("evidence-body").closestNode = panel;
  harness.select(".subnav-item", [delegationTab, routingTab]);
  harness.api.state.activity = { delegations: [], routing: [] };

  harness.api.configureEvidenceTabs();
  assert.equal(tabList.getAttribute("role"), "tablist");
  assert.equal(panel.getAttribute("role"), "tabpanel");
  assert.equal(delegationTab.tabIndex, 0);
  assert.equal(routingTab.tabIndex, -1);

  let prevented = false;
  delegationTab.listeners.get("keydown")[0]({
    key: "ArrowRight",
    preventDefault() { prevented = true; },
  });
  assert.equal(prevented, true);
  assert.equal(delegationTab.getAttribute("aria-selected"), "false");
  assert.equal(routingTab.getAttribute("aria-selected"), "true");
  assert.equal(routingTab.focusCount, 1);
  assert.equal(panel.getAttribute("aria-labelledby"), routingTab.id);
  assert.match(harness.node("evidence-caption").textContent, /routing runtime evidence/i);
});

test("app UI honors reduced motion, canonical CSS, and live toggle semantics", () => {
  assert.equal((APP_CSS_SOURCE.match(/^:root\s*{/gm) || []).length, 1);
  assert.equal((APP_CSS_SOURCE.match(/@media\s*\(max-width:\s*980px\)/g) || []).length, 1);
  assert.equal((APP_CSS_SOURCE.match(/@media\s*\(max-width:\s*620px\)/g) || []).length, 1);
  assert.match(APP_CSS_SOURCE, /\[hidden\]\s*{[^}]*display:\s*none\s*!important;?[^}]*}/);
  assert.match(
    APP_CSS_SOURCE,
    /\.topbar-heading\s*{[^}]*flex:\s*1\s+1\s+280px;?[^}]*}/,
  );
  assert.match(
    APP_CSS_SOURCE,
    /@media\s*\(max-width:\s*720px\)[\s\S]*?\.topbar\s*{[^}]*flex-direction:\s*column;?[^}]*justify-content:\s*flex-start;?[^}]*}[\s\S]*?\.topbar-heading\s*{[^}]*flex:\s*0\s+0\s+auto;?[^}]*width:\s*100%;?[^}]*}/,
  );
  assert.match(
    APP_CSS_SOURCE,
    /\.topbar-heading h1\s*{[^}]*overflow-wrap:\s*anywhere;?[^}]*white-space:\s*normal;?/,
  );
  assert.doesNotMatch(APP_CSS_SOURCE, /\.topbar-heading h1\s*{[^}]*text-overflow:\s*ellipsis/);
  assert.match(APP_CSS_SOURCE, /\.button:disabled\s*{[^}]*cursor:\s*not-allowed;/);
  assert.match(
    APP_CSS_SOURCE,
    /\.button:disabled\[aria-busy="true"\],\s*\.button\.is-pending\s*{[^}]*cursor:\s*wait;?/,
  );
  const mutedDim = APP_CSS_SOURCE.match(/--muted-dim:\s*(#[0-9a-f]{6})/i)?.[1];
  assert.ok(mutedDim);
  const luminance = (color) => {
    const channels = [1, 3, 5].map((index) => Number.parseInt(color.slice(index, index + 2), 16) / 255);
    const linear = channels.map((value) => (
      value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
    ));
    return (0.2126 * linear[0]) + (0.7152 * linear[1]) + (0.0722 * linear[2]);
  };
  const contrast = (luminance(mutedDim) + 0.05) / (luminance("#0d1117") + 0.05);
  assert.ok(contrast >= 4.5, `muted small-text contrast was ${contrast.toFixed(2)}:1`);
  assert.doesNotMatch(APP_CSS_SOURCE, /main:focus\s*{[^}]*outline:\s*none/);
  assert.match(APP_CSS_SOURCE, /main:focus-visible\s*{[^}]*outline-offset:\s*-2px/);
  assert.match(APP_CSS_SOURCE, /scrollbar-width:\s*thin/);
  assert.match(APP_CSS_SOURCE, /\.rail::-webkit-scrollbar\s*{[^}]*height:\s*4px/);
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  const toggle = new harness.HTMLInputElement("live-toggle");
  toggle.type = "checkbox";
  harness.nodes.set("live-toggle", toggle);
  const metric = harness.node("metric-runtime");

  harness.context.window.matchMedia = () => ({ matches: true });
  harness.api.setMetric("metric-runtime", "Online");
  harness.api.setMetric("metric-runtime", "Offline");
  assert.equal(metric.classList.contains("is-updated"), false);

  harness.context.window.matchMedia = () => ({ matches: false });
  harness.api.setMetric("metric-runtime", "Online");
  assert.equal(metric.classList.contains("is-updated"), true);
  metric.listeners.get("animationend")[0]();
  assert.equal(metric.classList.contains("is-updated"), false);

  harness.api.state.live.enabled = false;
  harness.api.syncLiveToggle();
  assert.equal(toggle.getAttribute("aria-pressed"), "false");
  assert.equal(toggle.checked, false);
  harness.api.setLiveEnabled(true);
  assert.equal(toggle.getAttribute("aria-pressed"), "true");
  assert.equal(toggle.checked, true);
  assert.equal(harness.timers.tasks.get(harness.api.state.live.timer).delay, 0);
});

test("overview metric evidence renders explicit selection denominators and latency attribution", async () => {
  const calls = [];
  const harness = createAppHarness(async (path) => {
    calls.push(path);
    if (path === "/api/evidence/latency?limit=200") {
      return jsonResponse(200, routingLatencyPayload());
    }
    if (path === "/api/evidence/selections") {
      return jsonResponse(200, selectionDistributionPayload());
    }
    throw new Error(`unexpected metric request: ${path}`);
  });

  assert.equal(await harness.api.refreshMetricEvidence(), true);
  assert.deepEqual(calls, [
    "/api/evidence/latency?limit=200",
    "/api/evidence/selections",
  ]);
  assert.equal(harness.api.state.routingLatency.overall.p95_ms, 18_000);
  assert.equal(harness.api.state.selectionDistribution.decisions_with_selections, 202);
  assert.equal(harness.node("latency-budget-state").textContent, "OVER BUDGET");
  assert.equal(harness.node("latency-metric-p95").textContent, "18.0 s");
  assert.equal(harness.node("latency-metric-provider").textContent, "7.00 s");
  assert.match(harness.node("latency-evidence-context").textContent, /equality passes/i);
  assert.equal(harness.node("selection-metric-decisions").textContent, "202");
  assert.equal(harness.node("selection-metric-roster").textContent, "263");
  assert.match(harness.node("selection-evidence-context").textContent, /need not sum to 100%/i);
  assert.ok(
    descendants(harness.node("selection-chart"))
      .some((node) => node.textContent === "code-reviewer"),
  );
});

test("overview metric evidence keeps last-good data on partial failure and stays view scoped", async () => {
  let failLatency = false;
  let failSelections = false;
  let calls = 0;
  const harness = createAppHarness(async (path) => {
    calls += 1;
    if (path === "/api/evidence/latency?limit=200") {
      return failLatency
        ? jsonResponse(503, { error: "latency unavailable" })
        : jsonResponse(200, routingLatencyPayload());
    }
    if (path === "/api/evidence/selections") {
      return failSelections
        ? jsonResponse(503, { error: "selection evidence unavailable" })
        : jsonResponse(200, selectionDistributionPayload());
    }
    throw new Error(`unexpected metric request: ${path}`);
  });

  await harness.api.refreshMetricEvidence();
  const lastGoodLatency = harness.api.state.routingLatency;
  failLatency = true;
  await harness.api.refreshMetricEvidence();

  assert.equal(harness.api.state.routingLatency, lastGoodLatency);
  assert.equal(harness.api.state.metricEvidence.sources.latency.stale, true);
  assert.equal(harness.api.state.metricEvidence.sources.latency.unavailable, false);
  assert.match(harness.api.state.metricEvidence.sources.latency.error, /latency unavailable/i);
  assert.equal(harness.api.state.metricEvidence.sources.selections.stale, false);
  assert.match(harness.node("latency-budget-state").textContent, /^STALE · OVER BUDGET$/);
  assert.match(harness.node("latency-evidence-context").textContent, /retained prior evidence/i);

  const lastGoodSelections = harness.api.state.selectionDistribution;
  failLatency = false;
  failSelections = true;
  await harness.api.refreshMetricEvidence();
  assert.equal(harness.api.state.selectionDistribution, lastGoodSelections);
  assert.equal(harness.api.state.metricEvidence.sources.selections.stale, true);
  assert.equal(harness.api.state.metricEvidence.sources.selections.unavailable, false);
  assert.match(
    harness.api.state.metricEvidence.sources.selections.error,
    /selection evidence unavailable/i,
  );
  assert.equal(harness.node("selection-evidence-state").textContent, "STALE");
  assert.match(harness.node("selection-evidence-context").textContent, /retained prior evidence/i);
  const callsBeforeInactiveView = calls;
  harness.api.state.activeView = "routing";
  assert.equal(await harness.api.refreshMetricEvidence(), false);
  assert.equal(calls, callsBeforeInactiveView);
});

test("overview metric evidence distinguishes first-load unavailability for either source", async () => {
  for (const failedSource of ["latency", "selections"]) {
    const harness = createAppHarness(async (path) => {
      if (path === "/api/evidence/latency?limit=200") {
        return failedSource === "latency"
          ? jsonResponse(503, { error: "latency first-load failure" })
          : jsonResponse(200, routingLatencyPayload());
      }
      if (path === "/api/evidence/selections") {
        return failedSource === "selections"
          ? jsonResponse(503, { error: "selection first-load failure" })
          : jsonResponse(200, selectionDistributionPayload());
      }
      throw new Error(`unexpected metric request: ${path}`);
    });

    assert.equal(await harness.api.refreshMetricEvidence(), true);
    const failed = harness.api.state.metricEvidence.sources[failedSource];
    const current = harness.api.state.metricEvidence.sources[
      failedSource === "latency" ? "selections" : "latency"
    ];
    assert.equal(failed.stale, false);
    assert.equal(failed.unavailable, true);
    assert.equal(failed.sampledAt, null);
    assert.equal(current.stale, false);
    assert.equal(current.unavailable, false);
    assert.ok(current.sampledAt);
    const failedTag = harness.node(
      failedSource === "latency" ? "latency-budget-state" : "selection-evidence-state",
    );
    assert.equal(failedTag.textContent, "UNAVAILABLE");
    assert.equal(failedTag.dataset.state, "unavailable");
    assert.match(harness.node("metric-evidence-status").textContent, /unavailable/);
    assert.ok(harness.node("metric-evidence-status").textContent.length < 120);
  }
});

test("overview metric evidence treats empty observations as unknown rather than healthy", async () => {
  const emptySummary = { count: 0, min_ms: 0, p50_ms: 0, p95_ms: 0, max_ms: 0 };
  const harness = createAppHarness(async (path) => {
    if (path === "/api/evidence/latency?limit=200") {
      return jsonResponse(200, routingLatencyPayload({
        window: {
          kind: "most_recent_positive_latency_decisions",
          limit: 200,
          decision_count: 0,
        },
        over_budget: false,
        overall: emptySummary,
        split: {
          decisions: 0,
          unattributed_decisions: 0,
          provider_ms: emptySummary,
          derived_routing_remainder_ms: emptySummary,
          calls_per_decision: 0,
        },
        by_source: {},
        slowest: [],
      }));
    }
    if (path === "/api/evidence/selections") {
      return jsonResponse(200, selectionDistributionPayload({
        decisions_with_selections: 0,
        distinct_selected_specialists: 0,
        selection_occurrences: 0,
        top_10_selection_occurrences: 0,
        top_10_share_of_selection_occurrences: 0,
        top_specialists: [],
      }));
    }
    throw new Error(`unexpected metric request: ${path}`);
  });

  await harness.api.refreshMetricEvidence();
  assert.equal(harness.node("latency-budget-state").textContent, "UNKNOWN");
  assert.equal(harness.node("latency-budget-state").dataset.state, "unknown");
  assert.match(harness.node("latency-evidence-context").textContent, /no eligible routing evidence/i);
  assert.equal(harness.node("selection-evidence-state").textContent, "NO DATA");
  assert.match(harness.node("selection-evidence-context").textContent, /no selection-bearing decisions/i);
});

test("metric evidence rejects inconsistent projections and malformed apply snapshots", async () => {
  const duplicate = selectionDistributionPayload().top_specialists[0];
  const harness = createAppHarness(async (path) => {
    if (path === "/api/evidence/latency?limit=200") {
      return jsonResponse(200, routingLatencyPayload({ over_budget: false }));
    }
    if (path === "/api/evidence/selections") {
      return jsonResponse(200, selectionDistributionPayload({
        top_specialists: [duplicate, { ...duplicate }],
      }));
    }
    throw new Error(`unexpected invalid-metric request: ${path}`);
  });

  const snapshot = await harness.api.fetchMetricEvidence();
  assert.equal(snapshot.latency, null);
  assert.equal(snapshot.selections, null);
  assert.match(snapshot.errors.latency, /routing-latency evidence is invalid/i);
  assert.match(snapshot.errors.selections, /specialist-selection evidence is invalid/i);
  assert.throws(
    () => harness.api.applyMetricEvidence(null),
    /dashboard metric evidence is invalid/i,
  );
  assert.throws(
    () => harness.api.applyMetricEvidence({ errors: null }),
    /dashboard metric evidence is invalid/i,
  );
});

test("routing latency rejects the retired causal remainder field", async () => {
  const legacyLatency = routingLatencyPayload();
  legacyLatency.split.agency_ms = legacyLatency.split.derived_routing_remainder_ms;
  delete legacyLatency.split.derived_routing_remainder_ms;
  const harness = createAppHarness(async (path) => {
    if (path === "/api/evidence/latency?limit=200") {
      return jsonResponse(200, legacyLatency);
    }
    if (path === "/api/evidence/selections") {
      return jsonResponse(200, selectionDistributionPayload());
    }
    throw new Error(`unexpected legacy-metric request: ${path}`);
  });

  const snapshot = await harness.api.fetchMetricEvidence();
  assert.equal(snapshot.latency, null);
  assert.ok(snapshot.selections);
  assert.match(snapshot.errors.latency, /routing-latency evidence is invalid/i);
});

test("metric evidence renders bounded selection tails and equality-at-budget latency", async () => {
  const ranked = Array.from({ length: 12 }, (_, index) => ({
    slug: `specialist-${index + 1}`,
    decisions_containing_specialist: 12 - index,
    selection_occurrences: 12 - index,
    share_of_decisions_with_selections: (12 - index) / 20,
    share_of_selection_occurrences: (12 - index) / 100,
  }));
  const exactBudgetSummary = {
    count: 1,
    min_ms: 15_000,
    p50_ms: 15_000,
    p95_ms: 15_000,
    max_ms: 15_000,
  };
  const harness = createAppHarness(async (path) => {
    if (path === "/api/evidence/latency?limit=200") {
      return jsonResponse(200, routingLatencyPayload({
        window: {
          kind: "most_recent_positive_latency_decisions",
          limit: 200,
          decision_count: 1,
        },
        over_budget: false,
        overall: exactBudgetSummary,
        split: {
          decisions: 1,
          unattributed_decisions: 0,
          provider_ms: { count: 1, min_ms: 9_000, p50_ms: 9_000, p95_ms: 9_000, max_ms: 9_000 },
          derived_routing_remainder_ms: { count: 1, min_ms: 6_000, p50_ms: 6_000, p95_ms: 6_000, max_ms: 6_000 },
          calls_per_decision: 1,
        },
        by_source: {},
        slowest: [{
          source: "computed",
          latency_ms: 15_000,
          provider_ms: 18_000,
          provider_calls: 1,
          provider_timed_calls: 1,
          provider_unknown_calls: 0,
          created_at: "2026-08-12T00:00:00Z",
        }],
      }));
    }
    if (path === "/api/evidence/selections") {
      return jsonResponse(200, selectionDistributionPayload({
        decisions_with_selections: 20,
        distinct_selected_specialists: 15,
        selection_occurrences: 100,
        top_10_selection_occurrences: 80,
        top_10_share_of_selection_occurrences: 0.8,
        top_specialists: ranked,
        long_tail: {
          specialist_count: 3,
          decisions_containing_specialist: 2,
          share_of_decisions_with_selections: 0.1,
          selection_occurrences: 3,
          share_of_selection_occurrences: 0.03,
        },
        selection_bearing_decision_scan_limit: 20,
        selection_bearing_decision_scan_truncated: true,
      }));
    }
    throw new Error(`unexpected bounded-metric request: ${path}`);
  });

  assert.equal(await harness.api.refreshMetricEvidence(), true);
  assert.equal(harness.node("selection-tail-body").children.length, 3);
  const aggregateTailText = descendants(harness.node("selection-tail-body").children[2])
    .map((node) => node.textContent)
    .join(" ");
  assert.match(aggregateTailText, /beyond top 50/i);
  assert.match(harness.node("selection-evidence-context").textContent, /older retained evidence/i);
  assert.equal(harness.node("latency-budget-state").textContent, "WITHIN BUDGET");
  assert.match(harness.node("latency-evidence-context").textContent, /recorded total minus provider time/i);
  const emptySourceText = descendants(harness.node("latency-source-body"))
    .map((node) => node.textContent)
    .join(" ");
  assert.match(emptySourceText, /No eligible routing evidence/i);
  const slowestText = descendants(harness.node("latency-slowest-body"))
    .map((node) => node.textContent)
    .join(" ");
  assert.equal((slowestText.match(/unknown/g) || []).length, 2);
});

test("Vision Evidence validators reject inconsistent bounded projections", () => {
  const harness = createAppHarness(() => {
    throw new Error("validator tests do not fetch");
  });
  const clone = (value) => JSON.parse(JSON.stringify(value));

  assert.doesNotThrow(() => harness.api.validateChildDeliveryPayload(childDeliveryPayload()));
  const maximumTeam = childDeliveryPayload();
  maximumTeam.hosts[0].children[0].cards = Array.from({ length: 256 }, (_, index) => ({
    slug: `specialist-${index}`,
    version: "1",
    prompt_hash: "a".repeat(64),
  }));
  assert.doesNotThrow(() => harness.api.validateChildDeliveryPayload(maximumTeam));
  const impossibleChildCount = clone(childDeliveryPayload());
  impossibleChildCount.hosts[0].evidence_count = 2;
  assert.throws(
    () => harness.api.validateChildDeliveryPayload(impossibleChildCount),
    /child-delivery evidence is invalid/i,
  );
  const inconsistentChildTruncation = clone(childDeliveryPayload());
  inconsistentChildTruncation.hosts[0].detail_truncated = true;
  assert.throws(
    () => harness.api.validateChildDeliveryPayload(inconsistentChildTruncation),
    /child-delivery evidence is invalid/i,
  );

  assert.doesNotThrow(() => harness.api.validateRule8EvidencePayload(rule8EvidencePayload()));
  const historicalHost = clone(rule8EvidencePayload());
  historicalHost.withheld[0].host = "legacy-custom-host";
  assert.doesNotThrow(() => harness.api.validateRule8EvidencePayload(historicalHost));
  const invalidWindowHost = clone(rule8EvidencePayload());
  invalidWindowHost.window.host = "legacy-custom-host";
  assert.throws(
    () => harness.api.validateRule8EvidencePayload(invalidWindowHost),
    /Rule-8 evidence is invalid/i,
  );
  const filteredWindow = clone(rule8EvidencePayload());
  filteredWindow.window.host = "claude";
  filteredWindow.agency_blind[0].host = "claude";
  assert.doesNotThrow(() => harness.api.validateRule8EvidencePayload(filteredWindow));
  filteredWindow.agency_blind[0].host = "historical-other-host";
  assert.throws(
    () => harness.api.validateRule8EvidencePayload(filteredWindow),
    /Rule-8 evidence is invalid/i,
  );
  const wrongPartition = clone(rule8EvidencePayload());
  wrongPartition.withheld_statuses = ["response_invalid"];
  assert.throws(
    () => harness.api.validateRule8EvidencePayload(wrongPartition),
    /Rule-8 evidence is invalid/i,
  );

  assert.doesNotThrow(() => harness.api.validateHostWiringPayload(wiringEvidencePayload()));
  const malformedDigest = clone(wiringEvidencePayload());
  malformedDigest.hosts[0].wired_projection = "short";
  assert.throws(
    () => harness.api.validateHostWiringPayload(malformedDigest),
    /host-wiring evidence is invalid/i,
  );
  const inconsistentWiredFlag = clone(wiringEvidencePayload());
  inconsistentWiredFlag.hosts[0].wired = false;
  assert.throws(
    () => harness.api.validateHostWiringPayload(inconsistentWiredFlag),
    /host-wiring evidence is invalid/i,
  );
});

test("Vision Evidence renders three source contracts with accessible bounded freshness", async () => {
  const calls = [];
  const harness = createAppHarness(async (path) => {
    calls.push(path);
    if (path === "/api/evidence/children") return jsonResponse(200, childDeliveryPayload());
    if (path === "/api/evidence/rejections") return jsonResponse(200, rule8EvidencePayload());
    if (path === "/api/evidence/wiring") return jsonResponse(200, wiringEvidencePayload());
    throw new Error(`unexpected Vision Evidence request: ${path}`);
  });
  harness.api.configureOwnerSurface();
  harness.api.state.activeView = "evidence";

  assert.equal(await harness.api.refreshVisionEvidence(), true);
  assert.deepEqual(calls, [
    "/api/evidence/children",
    "/api/evidence/rejections",
    "/api/evidence/wiring",
  ]);
  assert.equal(harness.api.state.visionEvidence.loaded, true);
  assert.equal(harness.node("vision-children-state").textContent, "OBSERVED");
  assert.equal(harness.node("vision-rule8-state").textContent, "OBSERVED");
  assert.equal(harness.node("vision-wiring-state").textContent, "OBSERVED");
  assert.equal(
    harness.api.state.visionEvidence.sources.children.sampledAt,
    "2026-08-11T12:00:02+00:00",
  );
  assert.equal(
    harness.api.state.visionEvidence.sources.rejections.sampledAt,
    "2026-08-11T12:00:03+00:00",
  );
  assert.equal(
    harness.api.state.visionEvidence.sources.wiring.sampledAt,
    "2026-08-11T12:00:04+00:00",
  );
  assert.match(harness.node("vision-children-freshness").textContent, /^Source sampled /);
  assert.match(harness.node("vision-rule8-freshness").textContent, /^Source sampled /);
  assert.match(harness.node("vision-wiring-freshness").textContent, /^Source sampled /);
  assert.match(harness.node("vision-children-bounds").textContent, /16384 host-tree entries/i);
  assert.match(harness.node("vision-rule8-source").textContent, /not host execution or publication proof/i);
  const childItems = harness.node("vision-children-list").children;
  assert.ok(childItems.length > 0);
  assert.ok(childItems.every((item) => item.getAttribute("role") === "listitem"));
  const wiringText = descendants(harness.node("vision-wiring-list"))
    .map((node) => node.textContent)
    .join(" ");
  assert.match(wiringText, /aaaaaaaaaaaa…/);
  assert.doesNotMatch(wiringText, /a{64}/);
  assert.doesNotMatch(wiringText, /not installed/i);

  harness.api.state.selectionDistribution = selectionDistributionPayload();
  harness.api.state.routingLatency = routingLatencyPayload();
  harness.api.state.metricEvidence.sources.selections.sampledAt = "2026-08-11T12:00:01+00:00";
  harness.api.state.metricEvidence.sources.latency.sampledAt = "2026-08-11T12:00:00+00:00";
  harness.api.renderMetricEvidence();
  const selectionRows = harness.node("selection-chart").children;
  assert.ok(selectionRows.every((row) => row.getAttribute("role") === "listitem"));
  const barTrack = descendants(harness.node("selection-chart"))
    .find((node) => node.className === "selection-bar-track");
  assert.equal(barTrack.getAttribute("aria-hidden"), "true");
  assert.equal(barTrack.getAttribute("max"), "100");
  assert.equal(barTrack.getAttribute("value"), (146 / 202 * 100).toFixed(2));
  assert.equal(barTrack.getAttribute("style"), null);
  const selectionRenderer = RENDER_SOURCE.slice(
    RENDER_SOURCE.indexOf("function renderSelectionDistribution"),
    RENDER_SOURCE.indexOf("function renderRoutingLatency"),
  );
  assert.doesNotMatch(selectionRenderer, /setAttribute\("style"|\.style\./);
  assert.doesNotMatch(selectionRenderer, /selection-bar-fill/);
  assert.match(
    harness.node("metric-evidence-freshness").textContent,
    /Selection source sampled .* latency source sampled /,
  );

  assert.match(INDEX_SOURCE, /id="selection-chart"[^>]*role="list"/);
  assert.ok(INDEX_SOURCE.indexOf("vision-evidence-title") < INDEX_SOURCE.indexOf("AUTHORITATIVE EVENTS"));
  assert.match(INDEX_SOURCE, /id="vision-evidence-refresh"[^>]*>Refresh proof</);
  assert.match(APP_CSS_SOURCE, /\.vision-evidence-grid\{[^}]*grid-template-columns:repeat\(3/);
  assert.match(APP_CSS_SOURCE, /@media\(max-width:900px\)\{\.vision-evidence-grid\{grid-template-columns:1fr/);
  assert.match(
    APP_CSS_SOURCE,
    /\.vision-proof-row>\*,\.vision-proof-detail>\*,\.vision-proof-heading>\*\{[^}]*overflow-wrap:anywhere/,
  );
  assert.match(
    INDEX_SOURCE,
    /<span id="metric-evidence-status" class="sr-only" role="status" aria-live="polite" aria-atomic="true">/,
  );
  assert.match(
    INDEX_SOURCE,
    /<span id="vision-evidence-status" class="sr-only" role="status" aria-live="polite" aria-atomic="true">/,
  );
  for (const id of ["metric-evidence-status", "vision-evidence-status"]) {
    const region = harness.node(id);
    assert.ok(region.textContent.length < 140);
  }
  assert.equal(
    harness.node("metric-evidence-status").textContent,
    "Decision evidence: selection current; latency current.",
  );
  assert.equal(
    harness.node("vision-evidence-status").textContent,
    "Vision evidence: child delivery current; Rule 8 current; host wiring current.",
  );
});

test("Vision Evidence marks an initial source failure unavailable without stale evidence", async () => {
  const harness = createAppHarness(async (path) => {
    if (path === "/api/evidence/children") {
      return jsonResponse(503, { error: "child proof unavailable" });
    }
    if (path === "/api/evidence/rejections") return jsonResponse(200, rule8EvidencePayload());
    if (path === "/api/evidence/wiring") return jsonResponse(200, wiringEvidencePayload());
    throw new Error(`unexpected Vision Evidence request: ${path}`);
  });
  harness.api.configureOwnerSurface();
  harness.api.state.activeView = "evidence";

  assert.equal(await harness.api.refreshVisionEvidence(), true);
  const source = harness.api.state.visionEvidence.sources.children;
  assert.equal(source.stale, false);
  assert.equal(source.unavailable, true);
  assert.equal(source.sampledAt, null);
  assert.equal(harness.node("vision-children-state").textContent, "UNAVAILABLE");
  assert.equal(harness.node("vision-children-state").dataset.state, "unavailable");
  assert.match(harness.node("vision-children-freshness").textContent, /No validated source sample/);
  assert.equal(
    harness.node("vision-evidence-status").textContent,
    "Vision evidence: child delivery unavailable; Rule 8 current; host wiring current.",
  );
});

test("Vision Evidence empty states preserve bounded unknown semantics", async () => {
  const children = childDeliveryPayload();
  children.hosts = children.hosts.map((host) => ({
    ...host,
    artifact_candidates: 0,
    artifacts_scanned: 0,
    artifact_scan_truncated: false,
    evidence_count: 0,
    staffed_children: 0,
    correlated_staffed_children: 0,
    uncorrelated_staffed_children: 0,
    legacy_deliveries: 0,
    detail_truncated: false,
    children: [],
  }));
  const rejections = rule8EvidencePayload({
    window: {
      kind: "most_recent_matching_exceptional_runs",
      host: null,
      limit: 50,
      returned: 0,
    },
    counts: { matching_exceptional_runs: 0, withheld: 0, agency_blind: 0 },
    withheld: [],
    agency_blind: [],
  });
  const wiring = wiringEvidencePayload();
  wiring.hosts[0] = {
    ...wiring.hosts[0],
    status: "unavailable",
    wired: false,
    reason_code: "wired_missing",
    reason: "no wired hook command was observed at the measured location",
    wired_state: "missing",
    wired_projection: "",
    wired_path: "",
  };
  const harness = createAppHarness(async (path) => {
    if (path === "/api/evidence/children") return jsonResponse(200, children);
    if (path === "/api/evidence/rejections") return jsonResponse(200, rejections);
    if (path === "/api/evidence/wiring") return jsonResponse(200, wiring);
    throw new Error(`unexpected empty-evidence request: ${path}`);
  });
  harness.api.state.activeView = "evidence";
  await harness.api.refreshVisionEvidence();

  const childText = descendants(harness.node("vision-children-list"))
    .map((node) => node.textContent).join(" ");
  const rule8Text = descendants(harness.node("vision-rule8-list"))
    .map((node) => node.textContent).join(" ");
  const wiringText = descendants(harness.node("vision-wiring-list"))
    .map((node) => node.textContent).join(" ");
  assert.match(childText, /does not mean no children were started/i);
  assert.match(rule8Text, /This is not a health claim/i);
  assert.doesNotMatch(rule8Text, /healthy/i);
  assert.match(wiringText, /UNKNOWN/);
  assert.match(wiringText, /wiring state remains unknown/i);
  assert.doesNotMatch(wiringText, /not installed/i);
});

test("Vision Evidence retains last-good data only for a failed source", async () => {
  let failChildren = false;
  let generation = 0;
  const harness = createAppHarness(async (path) => {
    if (path === "/api/evidence/children") {
      return failChildren
        ? jsonResponse(503, { error: "child proof unavailable" })
        : jsonResponse(200, childDeliveryPayload());
    }
    if (path === "/api/evidence/rejections") {
      return jsonResponse(200, rule8EvidencePayload({
        sampled_at: `2026-08-11T12:01:0${generation}+00:00`,
      }));
    }
    if (path === "/api/evidence/wiring") {
      return jsonResponse(200, wiringEvidencePayload({
        sampled_at: `2026-08-11T12:02:0${generation}+00:00`,
      }));
    }
    throw new Error(`unexpected partial-evidence request: ${path}`);
  });
  harness.api.state.activeView = "evidence";
  await harness.api.refreshVisionEvidence();
  const children = harness.api.state.visionEvidence.children;
  const rejections = harness.api.state.visionEvidence.rejections;
  const wiring = harness.api.state.visionEvidence.wiring;
  const childSample = harness.api.state.visionEvidence.sources.children.sampledAt;

  failChildren = true;
  generation = 1;
  assert.equal(await harness.api.refreshVisionEvidence({ force: true }), true);
  assert.equal(harness.api.state.visionEvidence.children, children);
  assert.notEqual(harness.api.state.visionEvidence.rejections, rejections);
  assert.notEqual(harness.api.state.visionEvidence.wiring, wiring);
  assert.equal(harness.api.state.visionEvidence.sources.children.sampledAt, childSample);
  assert.equal(harness.api.state.visionEvidence.sources.children.stale, true);
  assert.match(harness.api.state.visionEvidence.sources.children.error, /child proof unavailable/i);
  assert.equal(harness.api.state.visionEvidence.sources.rejections.stale, false);
  assert.equal(harness.api.state.visionEvidence.sources.wiring.stale, false);
  assert.equal(harness.node("vision-children-state").textContent, "STALE");
  assert.match(harness.node("vision-children-freshness").textContent, /Last-good source sample/);
});

test("Vision Evidence request generations reject races and navigation restores busy state", async () => {
  const pending = [
    [deferred(), deferred(), deferred()],
    [deferred(), deferred(), deferred()],
    [deferred(), deferred(), deferred()],
  ];
  const calls = [];
  const harness = createAppHarness((path, options) => {
    const batch = Math.floor(calls.length / 3);
    const slot = calls.length % 3;
    calls.push({ path, signal: options.signal });
    return pending[batch][slot].promise;
  });
  harness.api.state.activeView = "evidence";
  const first = harness.api.refreshVisionEvidence();
  await Promise.resolve();
  const second = harness.api.refreshVisionEvidence({ force: true });
  await Promise.resolve();
  assert.ok(calls.slice(0, 3).every((call) => call.signal.aborted));
  [childDeliveryPayload({ sampled_at: "2026-08-11T12:10:00+00:00" }),
    rule8EvidencePayload({ sampled_at: "2026-08-11T12:10:01+00:00" }),
    wiringEvidencePayload({ sampled_at: "2026-08-11T12:10:02+00:00" })]
    .forEach((payload, index) => pending[1][index].resolve(jsonResponse(200, payload)));
  assert.equal(await second, true);
  pending[0][0].resolve(jsonResponse(200, childDeliveryPayload()));
  pending[0][1].resolve(jsonResponse(200, rule8EvidencePayload()));
  pending[0][2].resolve(jsonResponse(200, wiringEvidencePayload()));
  assert.equal(await first, false);
  assert.equal(
    harness.api.state.visionEvidence.sources.children.sampledAt,
    "2026-08-11T12:10:00+00:00",
  );

  const leaving = harness.api.refreshVisionEvidence({ force: true });
  await Promise.resolve();
  assert.equal(harness.node("vision-evidence-refresh").disabled, true);
  assert.equal(harness.node("vision-evidence-refresh").getAttribute("aria-busy"), "true");
  assert.equal(harness.api.cancelVisionEvidenceRequest(), true);
  harness.api.state.activeView = "routing";
  assert.ok(calls.slice(6, 9).every((call) => call.signal.aborted));
  assert.equal(harness.node("vision-evidence-refresh").disabled, false);
  assert.equal(harness.node("vision-evidence-refresh").getAttribute("aria-busy"), null);
  pending[2][0].resolve(jsonResponse(200, childDeliveryPayload()));
  pending[2][1].resolve(jsonResponse(200, rule8EvidencePayload()));
  pending[2][2].resolve(jsonResponse(200, wiringEvidencePayload()));
  assert.equal(await leaving, false);
});

test("Vision Evidence never joins the live poll", async () => {
  const calls = [];
  const harness = createAppHarness(async (path) => {
    calls.push(path);
    if (path === "/api/live?limit=100") {
      return jsonResponse(200, {
        schema_version: 1,
        revision: "evidence-live-only",
        sampled_at: "2026-08-11T12:20:00+00:00",
      });
    }
    throw new Error(`hot poll reached non-live endpoint: ${path}`);
  });
  harness.api.state.activeView = "evidence";
  await harness.api.runLivePoll();
  assert.deepEqual(calls, ["/api/live?limit=100"]);
  const liveFunction = LIVE_SOURCE.slice(
    LIVE_SOURCE.indexOf("async function fetchLiveSnapshot"),
    LIVE_SOURCE.indexOf("function applyLiveSnapshot"),
  );
  assert.doesNotMatch(liveFunction, /\/api\/evidence\/(children|rejections|wiring)/);
});

test("Evidence navigation waits for full refresh, loads once, and forced controls refetch", async () => {
  const initialLive = deferred();
  const initialControl = deferred();
  const calls = [];
  let liveCalls = 0;
  let controlCalls = 0;
  const harness = createAppHarness(async (path, options) => {
    calls.push({ path, signal: options?.signal });
    if (path === "/api/live?limit=100") {
      liveCalls += 1;
      return liveCalls === 1
        ? initialLive.promise
        : jsonResponse(200, { schema_version: 1, revision: `manual-${liveCalls}` });
    }
    if (path === "/api/control") {
      controlCalls += 1;
      return controlCalls === 1 ? initialControl.promise : jsonResponse(200, controlSnapshot());
    }
    if (path === "/api/evidence/children") return jsonResponse(200, childDeliveryPayload());
    if (path === "/api/evidence/rejections") return jsonResponse(200, rule8EvidencePayload());
    if (path === "/api/evidence/wiring") return jsonResponse(200, wiringEvidencePayload());
    if (path.startsWith("/api/update/status")) return jsonResponse(503, { error: "offline" });
    throw new Error(`unexpected navigation/full-refresh path: ${path}`);
  });
  harness.sessionValues.set("agency-dashboard-token", "session-token");
  const overviewNav = new FakeNode("nav-overview");
  overviewNav.classList.add("active");
  overviewNav.dataset.view = "overview";
  const evidenceNav = new FakeNode("nav-evidence");
  evidenceNav.dataset.view = "evidence";
  const routingNav = new FakeNode("nav-routing");
  routingNav.dataset.view = "routing";
  const overviewPanel = new FakeNode("view-overview");
  overviewPanel.dataset.viewPanel = "overview";
  const evidencePanel = new FakeNode("view-evidence");
  evidencePanel.dataset.viewPanel = "evidence";
  const routingPanel = new FakeNode("view-routing");
  routingPanel.dataset.viewPanel = "routing";
  harness.select(".nav-item", [overviewNav, evidenceNav, routingNav]);
  harness.select(".nav-item.active", [overviewNav]);
  harness.select(".view", [overviewPanel, evidencePanel, routingPanel]);
  harness.api.bindEvents();

  const connected = harness.api.connectFromLocation();
  await Promise.resolve();
  evidenceNav.listeners.get("click")[0]();
  assert.equal(harness.api.state.activeView, "evidence");
  assert.equal(calls.filter((call) => call.path.startsWith("/api/evidence/")).length, 0);
  assert.ok(calls.slice(0, 2).every((call) => !call.signal.aborted));
  initialLive.resolve(jsonResponse(200, { schema_version: 1, revision: "initial" }));
  initialControl.resolve(jsonResponse(200, controlSnapshot()));
  assert.equal(await connected, true);
  assert.equal(calls.filter((call) => call.path.startsWith("/api/evidence/")).length, 3);

  routingNav.listeners.get("click")[0]();
  evidenceNav.listeners.get("click")[0]();
  await Promise.resolve();
  assert.equal(calls.filter((call) => call.path.startsWith("/api/evidence/")).length, 3);

  harness.node("vision-evidence-refresh").listeners.get("click")[0]();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(calls.filter((call) => call.path.startsWith("/api/evidence/")).length, 6);

  await harness.node("refresh-button").listeners.get("click")[0]();
  assert.equal(calls.filter((call) => call.path.startsWith("/api/evidence/")).length, 9);

  routingNav.listeners.get("click")[0]();
  harness.node("vision-evidence-refresh").listeners.get("click")[0]();
  await harness.node("refresh-button").listeners.get("click")[0]();
  assert.equal(calls.filter((call) => call.path.startsWith("/api/evidence/")).length, 9);
});

test("app.js live snapshots are single-flight", async () => {
  const pending = deferred();
  const calls = [];
  const harness = createAppHarness((path, options) => {
    calls.push({ path, options });
    return pending.promise;
  });

  const first = harness.api.fetchLiveSnapshot();
  const second = harness.api.fetchLiveSnapshot();

  assert.equal(await second, null);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].path, "/api/live?limit=100");
  assert.equal(harness.api.state.live.inFlight, true);
  assert.equal(calls[0].options.signal.aborted, false);

  pending.resolve(jsonResponse(200, { schema_version: 1, revision: "single-flight" }));
  const result = await first;

  assert.equal(result.revision, "single-flight");
  assert.equal(harness.api.state.live.inFlight, false);
  assert.equal(harness.api.state.live.controller, null);
});

test("app.js validates live schemas, deduplicates revisions, and retries transient failures", async () => {
  const successHarness = createAppHarness(async () => jsonResponse(200, {
    activity: { delegations: [], routing: [] },
    overview: { status: "ok" },
    revision: "poll-success",
    sampled_at: "2026-07-11T12:00:30.500Z",
    schema_version: 1,
  }));
  assert.throws(
    () => successHarness.api.applyLiveSnapshot({ schema_version: 2 }),
    /unsupported live dashboard response/i,
  );
  await successHarness.api.runLivePoll();
  assert.equal(successHarness.api.state.live.revision, "poll-success");
  assert.equal(successHarness.node("connection-label").textContent, "Authenticated");
  assert.equal(successHarness.node("live-status").dataset.state, "live");
  assert.equal(
    successHarness.timers.tasks.get(successHarness.api.state.live.timer).delay,
    2500,
  );

  successHarness.api.state.live.chartWindow = -1;
  assert.equal(successHarness.api.applyLiveSnapshot({
    revision: "poll-success",
    sampled_at: "2026-07-11T12:01:30.500Z",
    schema_version: 1,
  }), false);
  assert.equal(successHarness.api.state.live.revision, "poll-success");

  const retryHarness = createAppHarness(async () => jsonResponse(500, {
    error: "temporary local service failure",
  }));
  await retryHarness.api.runLivePoll();
  assert.equal(retryHarness.api.state.live.failures, 1);
  assert.equal(retryHarness.node("connection-label").textContent, "Reconnecting");
  assert.equal(retryHarness.node("live-status").dataset.state, "retrying");
  assert.match(retryHarness.node("notice").textContent, /reconnects/i);
  assert.ok(retryHarness.timers.tasks.get(retryHarness.api.state.live.timer).delay >= 2000);
});

test("app.js rejects stale live generations and treats abort rejection as cancellation", async () => {
  const stalePending = deferred();
  let staleSignal;
  const staleHarness = createAppHarness((_path, options) => {
    staleSignal = options.signal;
    return stalePending.promise;
  });

  const staleRequest = staleHarness.api.fetchLiveSnapshot();
  const activeGeneration = staleHarness.api.state.live.generation;
  staleHarness.api.cancelLiveRequest();

  assert.equal(staleSignal.aborted, true);
  assert.ok(staleHarness.api.state.live.generation > activeGeneration);
  stalePending.resolve(jsonResponse(200, { schema_version: 1, revision: "stale" }));
  assert.equal(await staleRequest, null);
  assert.equal(staleHarness.api.state.live.inFlight, false);
  assert.equal(staleHarness.api.state.live.revision, "");

  let abortCalls = 0;
  let abortSignal;
  const abortHarness = createAppHarness((_path, options) => {
    abortCalls += 1;
    abortSignal = options.signal;
    return new Promise((_resolve, reject) => {
      options.signal.addEventListener("abort", () => {
        const error = new Error("request aborted");
        error.name = "AbortError";
        reject(error);
      }, { once: true });
    });
  });

  const poll = abortHarness.api.runLivePoll();
  abortHarness.api.cancelLiveRequest();
  await poll;

  assert.equal(abortCalls, 1);
  assert.equal(abortSignal.aborted, true);
  assert.equal(abortHarness.api.state.live.failures, 0);
  assert.equal(abortHarness.api.state.live.terminal, false);
  assert.equal(abortHarness.api.state.live.timer, null);
  assert.equal(abortHarness.api.state.live.inFlight, false);
});

test("app.js cancels stale full refresh generations before they can render", async () => {
  const requests = [];
  const harness = createAppHarness((path, options) => {
    const pending = deferred();
    requests.push({ path, signal: options.signal, pending });
    return pending.promise;
  });

  const refresh = harness.api.refreshAll();
  assert.equal(requests.length, 2);
  assert.deepEqual(
    requests.map((request) => request.path),
    ["/api/live?limit=100", "/api/control"],
  );
  const activeGeneration = harness.api.state.full.generation;

  harness.api.cancelFullRefresh();
  assert.ok(harness.api.state.full.generation > activeGeneration);
  assert.ok(requests.every((request) => request.signal.aborted));
  assert.equal(harness.node("refresh-button").disabled, false);

  requests.forEach((request) => request.pending.resolve(jsonResponse(200, {})));
  assert.equal(await refresh, false);
  assert.equal(harness.api.state.overview, null);
  assert.equal(harness.api.state.full.inFlight, false);
  assert.equal(harness.api.state.full.controller, null);
});

test("app.js initial refresh reuses the live fast path and preserves control-plane fields", async () => {
  const payloads = new Map([
    ["/api/live?limit=100", {
      schema_version: 1,
      revision: "initial-live",
      sampled_at: "2026-07-11T12:00:30.500Z",
      overview: {
        status: "ok",
        db_size_bytes: 2048,
        wal_size_bytes: 1024,
        recent: { routing: 3, delegations: 2 },
        provider_health: [],
      },
      activity: { delegations: [], routing: [] },
    }],
    ["/api/hosts", { hosts: [] }],
    ["/api/roster?limit=100", { agents: [{ agent_slug: "security-reviewer" }] }],
    ["/api/snapshots", { snapshots: [] }],
    ["/api/config", {
      revision: "config-revision",
      effective: { observability: { retention_days: 45, capture_content: true } },
      environment_overrides: {},
    }],
    ["/api/control", controlSnapshot({
      config: {
        revision: "config-revision",
        effective: { observability: { retention_days: 45, capture_content: true } },
        environment_overrides: {},
      },
      roster: { agents: [{ agent_slug: "security-reviewer" }] },
    })],
  ]);
  const calls = [];
  const harness = createAppHarness(async (path) => {
    calls.push(path);
    return jsonResponse(200, payloads.get(path));
  });

  assert.equal(await harness.api.refreshAll(), true);
  assert.deepEqual(calls, [
    "/api/live?limit=100",
    "/api/control",
  ]);
  assert.equal(harness.api.state.live.revision, "initial-live");
  assert.equal(harness.api.state.overview.roster_count, 1);
  assert.equal(harness.api.state.overview.retention_days, 45);
  assert.equal(harness.api.state.overview.capture_content, true);
  assert.equal(harness.api.state.config.revision, "config-revision");
  assert.equal(harness.api.state.pendingConfig.revision, "config-revision");
  assert.equal(harness.node("metric-runtime").textContent, "Online");
  assert.equal(harness.node("metric-roster").textContent, "1");
  assert.equal(harness.node("privacy-chip").textContent, "Redacted runtime content");
  assert.match(harness.node("window-label").textContent, /24 min window/i);

  harness.api.switchView("settings");
  assert.equal(harness.api.state.config.revision, "config-revision");
  assert.equal(harness.api.state.pendingConfig, null);
});

test("app.js control-plane refresh is single-flight and updates only current responses", async () => {
  const payloads = new Map([
    ["/api/hosts", { hosts: [{ host: "codex", discovered: true }] }],
    ["/api/roster?limit=100", { agents: [{ agent_slug: "reviewer" }, { agent_slug: "tester" }] }],
    ["/api/snapshots", { snapshots: [{ snapshot_id: "snapshot-1" }] }],
    ["/api/config", { effective: {}, revision: "control-config" }],
    ["/api/control", controlSnapshot({
      config: { effective: {}, revision: "control-config" },
      hosts: [{ host: "codex", discovered: true }],
      roster: { agents: [{ agent_slug: "reviewer" }, { agent_slug: "tester" }] },
      governance: { snapshots: [{ snapshot_id: "snapshot-1" }] },
    })],
  ]);
  const calls = [];
  const harness = createAppHarness(async (path) => {
    calls.push(path);
    return jsonResponse(200, payloads.get(path));
  });
  harness.api.state.activeView = "hosts";

  await harness.api.refreshControlPlane();
  assert.deepEqual(calls, ["/api/control"]);
  assert.equal(harness.api.state.hosts[0].host, "codex");
  assert.equal(harness.api.state.roster.length, 2);
  assert.equal(harness.api.state.overview.roster_count, 2);
  assert.equal(harness.api.state.control.inFlight, false);
  assert.equal(
    harness.timers.tasks.get(harness.api.state.control.timer).delay,
    15000,
  );
  assert.equal(harness.node("host-grid").children.length, 2);

  harness.api.state.control.inFlight = true;
  await harness.api.refreshControlPlane();
  assert.equal(calls.length, 1);
});

test("control refresh fails closed on missing or wrong-version contracts", async () => {
  for (const mode of ["missing", "wrong-schema"]) {
    const calls = [];
    const harness = createAppHarness(async (path) => {
      calls.push(path);
      assert.equal(path, "/api/control");
      return mode === "missing"
        ? jsonResponse(404, { error: "control endpoint unavailable" })
        : jsonResponse(200, { schema_version: "agency.dashboard.control.v2" });
    });
    harness.api.state.roster = [{ agent_slug: "last-good-agent" }];
    harness.api.state.control.revision = "last-good-control";

    await harness.api.refreshControlPlane();

    assert.deepEqual(calls, ["/api/control"], mode);
    assert.equal(harness.api.state.roster[0].agent_slug, "last-good-agent", mode);
    assert.equal(harness.api.state.control.revision, "last-good-control", mode);
    assert.equal(harness.api.state.control.stale, true, mode);
    assert.match(harness.node("notice").textContent, /retained the last good state/i);
  }
});

test("store identity drift stays visible and disables routing, roster, and host controls", async () => {
  const calls = [];
  const harness = createAppHarness(async (path) => {
    calls.push(path);
    if (path === "/api/control") {
      return jsonResponse(200, controlSnapshot({
        config: {
          effective: {},
          revision: "restart-config",
          service_binding: {
            store_path: "C:\\runtime\\active.db",
            desired_store_path: "C:\\runtime\\next.db",
            store_restart_required: true,
          },
        },
        restartRequired: true,
      }));
    }
    if (path === "/api/live?limit=100") {
      return jsonResponse(200, {
        activity: {},
        master: { enabled: true, generation: 4 },
        overview: { status: "ok" },
        revision: "restart-live",
        schema_version: 1,
      });
    }
    throw new Error(`restart-blocked refresh must not call ${path}`);
  });

  assert.equal(await harness.api.refreshAll(), true);
  assert.deepEqual(calls, ["/api/live?limit=100", "/api/control"]);
  assert.equal(harness.api.serviceRestartRequired(), true);
  assert.equal(harness.node("store-restart-banner").hidden, false);
  assert.match(harness.node("store-restart-paths").textContent, /active\.db/i);
  assert.match(harness.node("store-restart-paths").textContent, /next\.db/i);
  assert.equal(harness.node("route-button").disabled, true);
  assert.equal(harness.node("roster-search-slug").disabled, true);
  assert.equal(harness.node("roster-search-submit").disabled, true);
  assert.ok(harness.node("shell").classList.contains("store-restart-required"));

  const callsBeforeBlockedSearch = calls.length;
  assert.equal(await harness.api.applyRosterFilter("reviewer"), false);
  assert.equal(calls.length, callsBeforeBlockedSearch);
  await harness.api.refreshControlPlane();
  assert.deepEqual(calls, [
    "/api/live?limit=100",
    "/api/control",
    "/api/control",
  ]);

  harness.api.state.hosts = [{
    ...verifiedHost("codex"),
    runtime_control_generation: 1,
  }];
  harness.api.renderRouteHosts();
	harness.api.renderHosts();
	const hostButtons = descendants(harness.node("host-grid"))
		.filter((node) => node.type === "button");
	assert.equal(hostButtons.length, 2);
	assert.equal(hostButtons[0].textContent, "Restart required");
	assert.equal(hostButtons[0].disabled, true);
	assert.equal(hostButtons[0].listeners.size, 0);
	assert.equal(hostButtons[1].id, "uninstall-copy-button");

  harness.api.state.roster = [{
    agent_slug: "reviewer",
    capabilities: [],
    enabled: true,
    protected: false,
  }];
  harness.api.state.snapshots = [{
    activated: false,
    agent_count: 1,
    approved: false,
    snapshot_id: "snapshot-restart",
  }];
  harness.api.renderRoster();
  const rosterButtons = descendants(harness.node("roster-grid"))
    .filter((node) => node.type === "button");
	const snapshotButtons = descendants(harness.node("snapshot-list"))
		.filter((node) => node.type === "button");
	assert.equal(rosterButtons.length, 1);
	assert.equal(rosterButtons[0].disabled, true);
	assert.equal(rosterButtons[0].listeners.size, 0);
	assert.equal(snapshotButtons.length, 1);
	assert.equal(snapshotButtons[0].disabled, true);
	assert.equal(snapshotButtons[0].listeners.size, 0);

  const callsBeforeBlockedActions = calls.length;
  await harness.api.runRoute();
  assert.match(harness.node("notice").textContent, /restart the dashboard service/i);
  assert.equal(calls.length, callsBeforeBlockedActions);

  harness.api.state.master = { enabled: true, generation: 4 };
  harness.api.applyServiceBinding({
    service_binding: {
      store_path: "C:\\runtime\\next.db",
      desired_store_path: "C:\\runtime\\next.db",
      store_restart_required: false,
    },
  });
  assert.equal(harness.node("store-restart-banner").hidden, true);
  assert.equal(harness.node("route-button").disabled, false);
  assert.equal(harness.node("roster-search-slug").disabled, false);
  assert.equal(harness.node("shell").classList.contains("store-restart-required"), false);
});

test("store binding renders bounded fallbacks when paths or controls are unavailable", () => {
  const harness = createAppHarness(() => {
    throw new Error("binding projection does not fetch");
  });
  harness.missing("roster-search-slug");
  harness.api.state.master = { enabled: true, generation: 1 };

  assert.equal(harness.api.applyServiceBinding({
    service_binding: {
      store_path: null,
      desired_store_path: 42,
      store_restart_required: true,
    },
  }), true);

  assert.equal(
    harness.node("store-restart-paths").textContent,
    "Active: unknown · Configured: unknown",
  );
  assert.equal(harness.node("roster-search-submit").disabled, true);
  assert.equal(harness.node("roster-search-clear").disabled, true);
  assert.equal(harness.node("route-button").disabled, true);
});

test("late control and full-refresh responses cannot cross restart generations", async () => {
  let staleControl;
  staleControl = createAppHarness(async (path) => {
    assert.equal(path, "/api/control");
    staleControl.api.state.lifecycle.suspended = true;
    return jsonResponse(200, controlSnapshot());
  });
  await staleControl.api.refreshControlPlane();
  assert.equal(staleControl.api.state.hosts.length, 0);
  assert.equal(staleControl.api.state.control.inFlight, false);

  let staleRestart;
  staleRestart = createAppHarness(async (path) => {
    if (path === "/api/live?limit=100") {
      staleRestart.api.state.full.generation += 1;
      return jsonResponse(200, { revision: "obsolete-restart", schema_version: 1 });
    }
    if (path === "/api/control") return jsonResponse(200, controlSnapshot());
    throw new Error(`unexpected restart path ${path}`);
  });
  assert.equal(await staleRestart.api.refreshAll(), false);
  assert.equal(staleRestart.api.state.live.revision, "");

  let staleFull;
  staleFull = createAppHarness(async (path) => {
    if (path === "/api/control") {
      staleFull.api.state.full.generation += 1;
      return jsonResponse(200, controlSnapshot());
    }
    return jsonResponse(200, { revision: "obsolete-full", schema_version: 1 });
  });
  assert.equal(await staleFull.api.refreshAll(), false);
  assert.equal(staleFull.api.state.live.revision, "");
});

test("view-scoped intent wins deferred races with control and full refreshes", async () => {
  const newerOperations = {
    agents: [{ agent_slug: "newer-agent", capabilities: [], enabled: true }],
    config_revision: "test-config-revision",
    count: 1,
    enabled_count: 1,
    matched_count: 1,
    next_cursor: null,
    roster_revision: "newer-operation-revision",
    total_count: 1,
    truncated: false,
  };
  const staleOperations = {
    agents: [{ agent_slug: "stale-agent", capabilities: [], enabled: true }],
    config_revision: "stale-control",
    count: 1,
    enabled_count: 1,
    matched_count: 1,
    next_cursor: null,
    roster_revision: "stale-operation-revision",
    total_count: 1,
    truncated: false,
  };
  const staleSnapshot = controlSnapshot({
    config: { effective: {}, revision: "stale-control" },
    governance: {
      operations: staleOperations,
      reviews: { candidates: [] },
      snapshots: [],
    },
    roster: { agents: [], truncated: false },
  });

  const controlPending = deferred();
  const filterPending = deferred();
  const controlCalls = [];
  let controlOperationCalls = 0;
  const controlRace = createAppHarness((path, options) => {
    controlCalls.push({ path, signal: options.signal });
    if (path === "/api/control") return controlPending.promise;
    if (path.startsWith("/api/roster/operations")) {
      controlOperationCalls += 1;
      return controlOperationCalls === 1
        ? filterPending.promise
        : Promise.resolve(jsonResponse(200, staleOperations));
    }
    throw new Error(`unexpected control-race path ${path}`);
  });
  controlRace.api.state.activeView = "roster";
  const staleControl = controlRace.api.refreshControlPlane();
  await Promise.resolve();
  controlRace.node("roster-filter-query").value = "newer";
  const newerFilter = controlRace.api.applyOperationalFilters();
  assert.equal(controlCalls[0].signal.aborted, true);
  filterPending.resolve(jsonResponse(200, newerOperations));
  assert.equal(await newerFilter, true);
  controlPending.resolve(jsonResponse(200, staleSnapshot));
  await staleControl;
  assert.equal(controlRace.api.state.rosterOperations.agents[0].agent_slug, "newer-agent");
  assert.deepEqual(controlRace.api.state.rosterFilters, { query: "newer" });

  const livePending = deferred();
  const fullControlPending = deferred();
  const fullFilterPending = deferred();
  const fullCalls = [];
  let fullOperationCalls = 0;
  const fullRace = createAppHarness((path, options) => {
    fullCalls.push({ path, signal: options.signal });
    if (path === "/api/live?limit=100") return livePending.promise;
    if (path === "/api/control") return fullControlPending.promise;
    if (path.startsWith("/api/roster/operations")) {
      fullOperationCalls += 1;
      return fullOperationCalls === 1
        ? fullFilterPending.promise
        : Promise.resolve(jsonResponse(200, staleOperations));
    }
    throw new Error(`unexpected full-race path ${path}`);
  });
  fullRace.api.state.activeView = "roster";
  const staleFullRefresh = fullRace.api.refreshAll();
  await Promise.resolve();
  fullRace.node("roster-filter-query").value = "newer";
  const fullRaceFilter = fullRace.api.applyOperationalFilters();
  assert.ok(fullCalls.slice(0, 2).every((call) => call.signal.aborted));
  fullFilterPending.resolve(jsonResponse(200, newerOperations));
  assert.equal(await fullRaceFilter, true);
  livePending.resolve(jsonResponse(200, { revision: "stale-live", schema_version: 1 }));
  fullControlPending.resolve(jsonResponse(200, staleSnapshot));
  assert.equal(await staleFullRefresh, false);
  assert.equal(fullRace.api.state.rosterOperations.agents[0].agent_slug, "newer-agent");
  assert.deepEqual(fullRace.api.state.rosterFilters, { query: "newer" });
  assert.equal(fullRace.api.state.live.revision, "");
});

test("a newer view request aborts every globally invalidated scope and clears remediation busy state", async () => {
  const remediationPending = deferred();
  const rosterPending = deferred();
  const calls = [];
  const harness = createAppHarness((path, options) => {
    calls.push({ path, signal: options.signal });
    if (path.includes("pending_cursor")) return remediationPending.promise;
    if (path.startsWith("/api/roster/operations")) return rosterPending.promise;
    throw new Error(`unexpected cross-view path ${path}`);
  });
  harness.api.state.rosterReview = {
    remediation_attempts: [{ event_id: "pending-1" }],
    next_remediation_pending_cursor: "pending-1",
    remediation_pending_has_more: true,
  };

  const olderRemediation = harness.api.loadMoreRemediation("pending");
  await Promise.resolve();
  assert.equal(harness.node("review-pending-more").disabled, true);
  assert.equal(harness.node("review-pending-more").getAttribute("aria-busy"), "true");

  const newerRoster = harness.api.applyOperationalFilters();
  await Promise.resolve();
  assert.equal(calls[0].signal.aborted, true);
  assert.equal(harness.api.state.requests.remediation.controller, null);
  assert.notEqual(harness.api.state.requests.operationalRoster.controller, null);
  assert.equal(harness.node("review-pending-more").disabled, false);
  assert.equal(harness.node("review-pending-more").getAttribute("aria-busy"), null);

  rosterPending.resolve(jsonResponse(200, {
    agents: [{ agent_slug: "newer-agent", capabilities: [], enabled: true }],
    config_revision: "test-config-revision",
    next_cursor: null,
    roster_revision: "newer-roster-revision",
    truncated: false,
  }));
  assert.equal(await newerRoster, true);
  remediationPending.resolve(jsonResponse(200, {
    remediation_attempts: [{ event_id: "stale-pending" }],
    next_remediation_pending_cursor: "",
    remediation_pending_has_more: false,
  }));
  assert.equal(await olderRemediation, false);
  assert.deepEqual(
    harness.api.state.rosterReview.remediation_attempts.map((item) => item.event_id),
    ["pending-1"],
  );
  assert.ok(Object.values(harness.api.state.requests).every((request) => !request.controller));
  assert.ok([...harness.timers.tasks.values()].some((task) => task.delay === 0));
});

test("app.js routing lab posts bounded tasks and reconciles live evidence", async () => {
  const calls = [];
  const harness = createAppHarness(async (path, options) => {
    calls.push({ path, options });
    if (path === "/api/route") {
      return jsonResponse(200, {
        request_id: options.headers.get("X-Agency-Request-ID"),
        selected: [{ slug: "security-reviewer" }],
        signals: { policy: { matched_actions: ["review"] } },
        status: "selected",
      });
    }
    if (path === "/api/live?limit=100") {
      return jsonResponse(200, {
        activity: { delegations: [], routing: [] },
        overview: { status: "ok" },
        revision: "after-route",
        schema_version: 1,
      });
    }
    throw new Error(`unexpected path ${path}`);
  });

  await harness.api.runRoute();
  assert.match(harness.node("notice").textContent, /enter a task/i);
  assert.equal(calls.length, 0);

  harness.node("route-task").value = "Review this service";
  await harness.api.runRoute();
  assert.match(harness.node("notice").textContent, /verified, enabled execution host/i);
  assert.equal(calls.length, 0);

  harness.api.state.master = { enabled: true, generation: 1 };
  harness.api.state.hosts = [verifiedHost("codex")];
  harness.api.renderRouteHosts();
  harness.node("route-task").value = "  Review this service  ";
  harness.node("route-session").value = " dashboard-lab ";
  await harness.api.runRoute();
  assert.equal(calls.length, 2);
  const body = JSON.parse(calls[0].options.body);
  assert.deepEqual(body, {
    host: "codex",
    limit: 12,
    session_id: "dashboard-lab",
    task: "Review this service",
  });
  assert.equal(harness.node("route-status").textContent, "SELECTED");
  assert.ok(
    descendants(harness.node("route-result"))
      .some((node) => node.textContent === "security-reviewer"),
  );
  assert.ok(
    descendants(harness.node("route-result"))
      .some((node) => node.textContent === calls[0].options.headers.get("X-Agency-Request-ID")),
  );
  assert.equal(harness.api.state.live.revision, "after-route");
  assert.equal(harness.node("route-button").disabled, false);
  assert.equal(harness.node("route-button").getAttribute("aria-busy"), null);
});

test("app.js binds lifecycle controls for live pause, page cleanup, and late fragments", () => {
  const harness = createAppHarness(() => {
    throw new Error("registered listeners are not allowed to fetch in this test");
  });
  const overviewNav = new FakeNode("nav-overview");
  overviewNav.classList.add("active");
  overviewNav.dataset.view = "overview";
  const overviewPanel = new FakeNode("view-overview");
  overviewPanel.dataset.viewPanel = "overview";
  harness.select(".nav-item", [overviewNav]);
  harness.select(".view", [overviewPanel]);

  harness.api.bindEvents();
  assert.equal(harness.documentListeners.get("visibilitychange").length, 1);
  assert.equal(harness.windowListeners.get("hashchange").length, 1);
  assert.equal(harness.windowListeners.get("pagehide").length, 1);
  assert.equal(harness.windowListeners.get("pageshow").length, 1);

  harness.node("live-toggle").listeners.get("click")[0]();
  assert.equal(harness.api.state.live.enabled, false);
  assert.equal(harness.node("live-status").dataset.state, "paused");

  harness.api.state.clockTimer = harness.timers.set(() => {}, 1000);
  harness.windowListeners.get("pagehide")[0]();
  assert.equal(harness.api.state.clockTimer, null);
  assert.equal(harness.api.state.live.timer, null);
  assert.equal(harness.api.state.control.timer, null);
  assert.equal(harness.api.state.full.inFlight, false);
});

test("app.js executes bound navigation, provider, workforce, hash, and startup callbacks", async () => {
  const calls = [];
  const harness = createAppHarness(async (path) => {
    calls.push(path);
    if (path.startsWith("/api/workforce")) {
      return jsonResponse(200, {
        collection_revision: "workers-v1",
        counts: {},
        hiring_cases: [],
        truncated: false,
        workers: [],
      });
    }
    if (path.startsWith("/api/hiring")) {
      return jsonResponse(200, {
        collection_revision: "hiring-v1",
        hiring_cases: [],
        truncated: false,
      });
    }
    return jsonResponse(200, { models: [] });
  });
  const overviewNav = new FakeNode("nav-overview");
  overviewNav.classList.add("active");
  overviewNav.dataset.view = "overview";
  const workforceNav = new FakeNode("nav-workforce");
  workforceNav.dataset.view = "workforce";
  const overviewPanel = new FakeNode("view-overview");
  overviewPanel.dataset.viewPanel = "overview";
  const workforcePanel = new FakeNode("view-workforce");
  workforcePanel.dataset.viewPanel = "workforce";
  harness.select(".nav-item", [overviewNav, workforceNav]);
  harness.select(".nav-item.active", [overviewNav]);
  harness.select(".view", [overviewPanel, workforcePanel]);

  assert.equal(await harness.api.start(), false);
  overviewNav.listeners.get("click")[0]();
  workforceNav.listeners.get("click")[0]();
  harness.node("provider-builder-type").listeners.get("change")[0]();
  harness.node("provider-builder-transport").listeners.get("change")[0]();
  harness.windowListeners.get("hashchange")[0]();
  await new Promise((resolve) => setImmediate(resolve));
  await new Promise((resolve) => setImmediate(resolve));

  assert.equal(harness.api.state.activeView, "workforce");
  assert.ok(calls.some((path) => path.startsWith("/api/workforce")));
  assert.ok(calls.some((path) => path.startsWith("/api/hiring")));
});

test("Route Lab and worker-detail failures remain visible and lifecycle bounded", async () => {
  const emptyWorkerEvidence = {
    events: [],
    hiring_cases: [],
    lineage: [],
    outcomes: [],
  };
  const routeHarness = createAppHarness(async () => {
    throw new Error("route transport unavailable");
  });
  routeHarness.api.state.master = { enabled: true, generation: 1 };
  routeHarness.api.state.hosts = [verifiedHost("codex")];
  routeHarness.api.renderRouteHosts();
  routeHarness.node("route-task").value = "Review the service";
  routeHarness.node("route-host").value = "codex";

  await routeHarness.api.runRoute();
  assert.equal(routeHarness.node("route-status").textContent, "FAILED");
  assert.match(routeHarness.node("notice").textContent, /route transport unavailable/i);
  assert.match(
    routeHarness.node("notice").textContent,
    /Request ID 00000000-0000-4000-8000-000000000001/,
  );
  assert.equal(routeHarness.node("route-button").disabled, false);
  const noticeTimer = [...routeHarness.timers.tasks.values()]
    .find((task) => task.delay === 6000);
  assert.ok(noticeTimer);
  noticeTimer.callback();
  assert.equal(routeHarness.node("notice").hidden, true);

  const workerHarness = createAppHarness(async (path) => {
    if (path.includes("worker=worker-one")) {
      return jsonResponse(200, {
        detail: {
          worker: { agent_slug: "worker-one", revision: 1, worker_id: "worker-one-id" },
          ...emptyWorkerEvidence,
        },
      });
    }
    throw new Error("worker detail unavailable");
  });
  await workerHarness.api.selectWorker("");
  await workerHarness.api.selectWorker("worker-one");
  assert.equal(workerHarness.api.state.selectedWorkerDetail.worker.agent_slug, "worker-one");
  assert.throws(
    () => workerHarness.api.validateWorkerDetailResponse({
      detail: {
        worker: { agent_slug: "worker-two", revision: 1, worker_id: "worker-two-id" },
        ...emptyWorkerEvidence,
      },
    }, "worker-one"),
    /did not match the requested governed worker/i,
  );
  for (const agentSlug of ["WORKER-ONE", " worker-one ", 7]) {
    assert.throws(
      () => workerHarness.api.validateWorkerDetailResponse({
        detail: {
          worker: { agent_slug: agentSlug, revision: 1, worker_id: "worker-one-id" },
          ...emptyWorkerEvidence,
        },
      }, "worker-one"),
      /did not match the requested governed worker/i,
    );
  }
  assert.throws(
    () => workerHarness.api.validateWorkerDetailResponse({
      detail: {
        worker: {
          agent_slug: "worker-one",
          revision: Number.MAX_SAFE_INTEGER + 1,
          worker_id: "worker-one-id",
        },
        ...emptyWorkerEvidence,
      },
    }, "worker-one"),
    /did not match the requested governed worker/i,
  );
  assert.throws(
    () => workerHarness.api.validateWorkerDetailResponse({
      detail: {
        worker: { agent_slug: "worker-one", revision: 1, worker_id: "worker-one-id" },
        events: [],
        hiring_cases: [],
        lineage: [],
      },
    }, "worker-one"),
    /invalid evidence collection/i,
  );
  assert.throws(
    () => workerHarness.api.validateWorkerDetailResponse({
      detail: {
        worker: { agent_slug: "worker-one", revision: 1, worker_id: "worker-one-id" },
        ...emptyWorkerEvidence,
        outcomes: {},
      },
    }, "worker-one"),
    /invalid evidence collection/i,
  );
  await workerHarness.api.selectWorker("worker-two");
  assert.match(workerHarness.node("notice").textContent, /worker detail unavailable/i);
});

test("app.js keeps inactive views out of the live render path and hides panels semantically", () => {
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  const overviewNav = new FakeNode("nav-overview");
  overviewNav.dataset.view = "overview";
  overviewNav.classList.add("active");
  const hostsNav = new FakeNode("nav-hosts");
  hostsNav.dataset.view = "hosts";
  const overviewPanel = new FakeNode("view-overview");
  overviewPanel.dataset.viewPanel = "overview";
  const hostsPanel = new FakeNode("view-hosts");
  hostsPanel.dataset.viewPanel = "hosts";
  harness.select(".nav-item", [overviewNav, hostsNav]);
  harness.select(".view", [overviewPanel, hostsPanel]);

  harness.api.switchView("hosts");
  assert.equal(harness.api.state.activeView, "hosts");
  assert.equal(overviewPanel.hidden, true);
  assert.equal(overviewPanel.getAttribute("aria-hidden"), "true");
  assert.equal(hostsPanel.hidden, false);
  assert.equal(hostsPanel.getAttribute("aria-hidden"), "false");
  assert.equal(hostsNav.getAttribute("aria-current"), "page");

  harness.node("metric-runtime").textContent = "not-rendered";
  harness.api.state.activeView = "routing";
  assert.equal(harness.api.applyLiveSnapshot({
    schema_version: 1,
    revision: "background-live",
    sampled_at: "2026-07-11T12:01:30.500Z",
    overview: { status: "ok" },
    activity: { delegations: [], routing: [] },
  }), true);
  assert.equal(harness.node("metric-runtime").textContent, "not-rendered");

  harness.api.state.activeView = "overview";
  harness.api.renderActiveView();
  assert.equal(harness.node("metric-runtime").textContent, "Online");
});

test("app.js marks malformed configuration JSON invalid and clears the error after correction", () => {
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  const providers = new FakeNode("config-providers");
  providers.dataset.configPath = "providers";
  providers.dataset.valueType = "json";
  providers.labels = [{ textContent: "Provider array" }];
  providers.value = "{";
  harness.nodes.set("config-providers", providers);
  harness.select("[data-config-path]", [providers]);
  harness.api.state.configBaseline.set("providers", "[]");

  harness.api.updateConfigDirtyState();
  assert.equal(providers.getAttribute("aria-invalid"), "true");
  assert.match(providers.validationMessage, /valid JSON/i);
  assert.equal(harness.node("config-save-button").disabled, true);
  assert.match(harness.node("config-change-count").textContent, /valid JSON/i);

  providers.value = "[]";
  harness.api.updateConfigDirtyState();
  assert.equal(providers.getAttribute("aria-invalid"), null);
  assert.equal(providers.validationMessage, "");
  assert.equal(harness.api.state.configDirty, false);
});

test("app.js pauses while hidden, resumes visibly, and gates BFCache restoration", () => {
  const harness = createAppHarness(() => {
    throw new Error("timers must not perform a fetch in this deterministic test");
  });
  harness.api.scheduleLive(500);
  harness.api.scheduleControlRefresh(750);
  harness.api.scheduleUpdateRefresh(900);
  assert.notEqual(harness.api.state.live.timer, null);
  assert.notEqual(harness.api.state.control.timer, null);
  assert.notEqual(harness.api.state.updateRequest.timer, null);

  harness.document.visibilityState = "hidden";
  harness.api.handleVisibilityChange();
  assert.equal(harness.api.state.live.timer, null);
  assert.equal(harness.api.state.control.timer, null);
  assert.equal(harness.api.state.updateRequest.timer, null);
  assert.equal(harness.node("live-status").dataset.state, "paused");
  assert.match(harness.node("live-status").textContent, /hidden/i);

  harness.document.visibilityState = "visible";
  harness.api.handleVisibilityChange();
  assert.equal(
    harness.timers.tasks.get(harness.api.state.live.timer).delay,
    0,
  );
  assert.equal(
    harness.timers.tasks.get(harness.api.state.control.timer).delay,
    0,
  );
  assert.equal(
    harness.timers.tasks.get(harness.api.state.updateRequest.timer).delay,
    0,
  );
  assert.notEqual(harness.api.state.clockTimer, null);
  assert.equal(harness.node("live-status").dataset.state, "connecting");

  harness.api.cancelLiveRequest();
  harness.api.cancelControlRequest();
  harness.api.cancelUpdateRequest();
  harness.node("refresh-button").disabled = true;
  harness.api.handlePageShow({ persisted: false });
  assert.equal(harness.node("refresh-button").disabled, true);
  assert.equal(harness.api.state.live.timer, null);
  assert.equal(harness.api.state.control.timer, null);
  assert.equal(harness.api.state.updateRequest.timer, null);

  harness.api.state.live.enabled = false;
  harness.api.handlePageShow({ persisted: true });
  assert.equal(harness.node("refresh-button").disabled, false);
  assert.equal(harness.api.state.live.timer, null);
  assert.equal(harness.api.state.control.timer, null);
  assert.equal(
    harness.timers.tasks.get(harness.api.state.updateRequest.timer).delay,
    0,
  );

  harness.api.state.live.enabled = true;
  harness.api.state.live.terminal = true;
  harness.api.handlePageShow({ persisted: true });
  assert.equal(harness.api.state.live.timer, null);
  assert.equal(harness.api.state.control.timer, null);
  assert.equal(
    harness.timers.tasks.get(harness.api.state.updateRequest.timer).delay,
    0,
  );

  harness.api.state.live.terminal = false;
  harness.node("refresh-button").disabled = true;
  harness.api.handlePageShow({ persisted: true });
  assert.equal(harness.node("refresh-button").disabled, false);
  assert.equal(
    harness.timers.tasks.get(harness.api.state.live.timer).delay,
    0,
  );
  assert.equal(
    harness.timers.tasks.get(harness.api.state.control.timer).delay,
    0,
  );
});

test("app.js treats 401 and 403 live responses as terminal", async (testContext) => {
  for (const status of [401, 403]) {
    await testContext.test(`HTTP ${status}`, async () => {
      let calls = 0;
      const harness = createAppHarness(async () => {
        calls += 1;
        return jsonResponse(status, { error: "authentication required" });
      });

      await harness.api.runLivePoll();

      assert.equal(calls, 1);
      assert.equal(harness.api.state.live.terminal, true);
      assert.equal(harness.api.state.live.inFlight, false);
      assert.equal(harness.api.state.live.controller, null);
      assert.equal(harness.api.state.live.timer, null);
      assert.equal(harness.node("connection-label").textContent, "Token expired");
      assert.equal(harness.node("live-status").dataset.state, "expired");
      assert.match(harness.node("live-status").textContent, /access expired/i);
      assert.match(harness.node("live-announcer").textContent, /access expired/i);
      assert.equal(harness.node("notice").hidden, false);
      assert.match(harness.node("notice").textContent, /token expired/i);
      assert.match(
        harness.node("notice").textContent,
        /Request ID 00000000-0000-4000-8000-000000000001/,
      );

      harness.api.scheduleLive(0);
      await harness.api.runLivePoll();
      assert.equal(harness.api.state.live.timer, null);
      assert.equal(calls, 1);
    });
  }
});

test("app.js covers fallback helpers and forward modal focus trapping", async () => {
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  const plain = new FakeNode("plain");
  plain.value = "unchanged";
  assert.equal(harness.api.readConfigControl(plain), "unchanged");
  assert.equal(harness.api.evidenceRowKey("opaque", 7), "row:7");
  assert.equal(harness.api.activeEvidenceKind(), "specialists");

  const activeTab = new FakeNode("receipts-tab");
  activeTab.dataset.evidence = "receipts";
  harness.select(".subnav-item.active", [activeTab]);
  assert.equal(harness.api.activeEvidenceKind(), "receipts");

  const first = new FakeNode("first");
  const last = new FakeNode("last");
  harness.node("confirmation-modal").queryNodes = [first, last];
  const cancelled = harness.api.requestConfirmation("CONFIRM", "Confirm it.");
  harness.document.activeElement = last;
  let prevented = false;
  harness.api.handleModalKeyboard({
    key: "Tab",
    preventDefault() { prevented = true; },
    shiftKey: false,
  });
  assert.equal(prevented, true);
  assert.equal(first.focusCount, 1);
  harness.api.finishConfirmation(false);
  assert.equal(await cancelled, false);

  harness.node("config-provider-secret-index").value = "";
  harness.node("config-provider-secret").value = "new-secret";
  assert.throws(
    () => harness.api.collectConfigChanges(),
    /select a provider before changing its direct key/i,
  );
});

test("app.js reconnects from stored credentials and surfaces missing tokens", async () => {
  const payloads = new Map([
    ["/api/live?limit=100", {
      activity: {},
      overview: { status: "ok" },
      revision: "connected",
      schema_version: 1,
    }],
    ["/api/hosts", { hosts: [] }],
    ["/api/roster?limit=100", emptyRosterPage("connected-roster", "config")],
    ["/api/snapshots", emptyGovernancePage("connected-snapshots")],
    ["/api/config", { effective: {}, revision: "config" }],
    ["/api/control", controlSnapshot({
      config: { effective: {}, revision: "config" },
    })],
  ]);
  const connected = createAppHarness(async (path) => jsonResponse(200, payloads.get(path)));
  connected.sessionValues.set("agency-dashboard-token", "stored-token");
  connected.api.showNotice("Connecting");
  await connected.api.connectFromLocation();
  assert.equal(connected.api.state.token, "stored-token");
  assert.equal(connected.node("notice").hidden, true);
  assert.equal(connected.node("connection-label").textContent, "Authenticated");

  let calls = 0;
  const missing = createAppHarness(async () => {
    calls += 1;
    return jsonResponse(500, {});
  });
  await missing.api.connectFromLocation();
  assert.equal(calls, 0);
  assert.equal(missing.node("connection-label").textContent, "Token required");
  assert.match(missing.node("notice").textContent, /no active access token/i);
});

test("a secondary evidence 401 remains visible after the primary connection succeeds", async (testContext) => {
  for (const activeView of ["overview", "evidence"]) {
    await testContext.test(activeView, async () => {
      const calls = [];
      const harness = createAppHarness(async (path) => {
        calls.push(path);
        if (path === "/api/live?limit=100") {
          return jsonResponse(200, {
            activity: {},
            overview: { status: "ok" },
            revision: `connected-${activeView}`,
            schema_version: 1,
          });
        }
        if (path === "/api/control") {
          return jsonResponse(200, controlSnapshot({
            config: { effective: {}, revision: `config-${activeView}` },
          }));
        }
        if (path === "/api/evidence/latency?limit=200") {
          return jsonResponse(401, { error: "metric token expired" });
        }
        if (path === "/api/evidence/selections") {
          return jsonResponse(200, selectionDistributionPayload());
        }
        if (path === "/api/evidence/children") {
          return jsonResponse(401, { error: "Vision token expired" });
        }
        if (path === "/api/evidence/rejections") {
          return jsonResponse(200, rule8EvidencePayload());
        }
        if (path === "/api/evidence/wiring") {
          return jsonResponse(200, wiringEvidencePayload());
        }
        throw new Error(`unexpected secondary-auth path: ${path}`);
      });
      harness.sessionValues.set("agency-dashboard-token", "stored-token");
      harness.api.state.activeView = activeView;
      harness.api.showNotice("Connecting");

      assert.equal(await harness.api.connectFromLocation(), true);
      assert.equal(harness.api.state.live.terminal, true);
      assert.equal(harness.node("connection-label").textContent, "Token expired");
      assert.equal(harness.node("notice").hidden, false);
      assert.match(harness.node("notice").textContent, /token expired/i);
      assert.match(
        harness.node("notice").textContent,
        /Request ID 00000000-0000-4000-8000-000000000001/,
      );
      assert.ok(calls.some((path) => path.startsWith("/api/evidence/")));
    });
  }
});

test("app.js omits retired dependency graphs and renders roster control refreshes", () => {
  const harness = createAppHarness(() => {
    throw new Error("render-only test does not fetch");
  });
  harness.api.renderReceipt({
    selected: [],
  });
  assert.equal(
    descendants(harness.node("route-result"))
      .some((node) => /dependency graph|run independently|work units/i.test(node.textContent)),
    false,
  );

  harness.api.state.activeView = "roster";
  harness.api.state.roster = [{ agent_slug: "reviewer", capabilities: [] }];
  harness.api.renderActiveControlView();
  assert.equal(harness.node("roster-count").textContent, "1 enabled · 1 total");
});

test("app.js handles control-plane and full-refresh error classes", async () => {
  const terminal = createAppHarness(async () => jsonResponse(401, { error: "expired" }));
  await terminal.api.refreshControlPlane();
  assert.equal(terminal.api.state.live.terminal, true);
  assert.equal(terminal.node("connection-label").textContent, "Token expired");

  const aborted = createAppHarness(async () => {
    const error = new Error("cancelled");
    error.name = "AbortError";
    throw error;
  });
  assert.equal(await aborted.api.refreshAll(), false);
  assert.equal(aborted.node("connection-label").textContent, "");

  const unavailable = createAppHarness(async () => {
    throw new Error("network unavailable");
  });
  assert.equal(await unavailable.api.refreshAll(), undefined);
  assert.equal(unavailable.node("connection-label").textContent, "Control data stale");
  assert.match(unavailable.node("notice").textContent, /control refresh failed/i);
  assert.match(unavailable.node("notice").textContent, /request id/i);
  await assert.rejects(
    unavailable.api.refreshAll({ surfaceErrors: false }),
    /network unavailable/i,
  );

  const fullTerminal = createAppHarness(async () => jsonResponse(403, { error: "forbidden" }));
  assert.equal(await fullTerminal.api.refreshAll(), undefined);
  assert.equal(fullTerminal.api.state.live.terminal, true);
});

test("app.js reports post-mutation reconciliation failures without hiding success", async () => {
  const transient = createAppHarness(async () => jsonResponse(503, { error: "live unavailable" }));
  await transient.api.reconcileRuntimeEvidence("Mutation completed.");
  assert.match(transient.node("notice").textContent, /mutation completed.*could not refresh/i);

  const terminal = createAppHarness(async () => jsonResponse(401, { error: "expired" }));
  await terminal.api.reconcileRuntimeEvidence("Mutation completed.");
  assert.equal(terminal.api.state.live.terminal, true);
  assert.match(terminal.node("notice").textContent, /token expired/i);

  const allTransient = createAppHarness(async () => jsonResponse(503, { error: "control unavailable" }));
  await allTransient.api.reconcileAll("Roster updated.");
  assert.match(allTransient.node("notice").textContent, /roster updated.*could not refresh/i);

  const allTerminal = createAppHarness(async () => jsonResponse(403, { error: "expired" }));
  await allTerminal.api.reconcileAll("Host updated.");
  assert.equal(allTerminal.api.state.live.terminal, true);
  assert.match(allTerminal.node("notice").textContent, /token expired/i);
});

test("app.js supports every evidence-tab keyboard command", () => {
  const harness = createAppHarness(() => {
    throw new Error("keyboard-only test does not fetch");
  });
  const tabList = new FakeNode("tab-list");
  const tabs = ["delegations", "routing", "receipts"].map((kind, index) => {
    const tab = new FakeNode();
    tab.dataset.evidence = kind;
    tab.parentElement = tabList;
    if (index === 1) tab.classList.add("active");
    return tab;
  });
  harness.select(".subnav-item", tabs);
  harness.api.state.activity = { delegations: [], receipts: [], routing: [] };
  harness.api.configureEvidenceTabs();

  const invoke = (tab, key) => {
    let prevented = false;
    tab.listeners.get("keydown")[0]({ key, preventDefault() { prevented = true; } });
    return prevented;
  };
  assert.equal(invoke(tabs[1], "ArrowLeft"), true);
  assert.equal(tabs[0].focusCount, 1);
  assert.equal(invoke(tabs[1], "ArrowUp"), true);
  assert.equal(invoke(tabs[1], "ArrowDown"), true);
  assert.equal(invoke(tabs[1], "Home"), true);
  assert.equal(invoke(tabs[1], "End"), true);
  assert.equal(tabs[2].focusCount, 2);
  assert.equal(invoke(tabs[1], "Enter"), true);
  assert.equal(invoke(tabs[1], " "), true);
  assert.equal(invoke(tabs[1], "Escape"), false);
});

test("app.js exercises defensive configuration and optional-DOM branches", () => {
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  harness.api.finishConfirmation(false);
  harness.node("confirmation-modal").hidden = true;
  assert.equal(harness.api.modalFocusable().length, 0);
  harness.api.handleModalKeyboard({ key: "Tab", preventDefault() {} });
  harness.api.state.confirmation = { phrase: "x", resolve() {}, returnFocus: null };
  harness.api.handleModalKeyboard({ key: "A", preventDefault() {} });
  harness.node("confirmation-modal").hidden = false;
  harness.node("confirmation-modal").queryNodes = [];
  harness.api.handleModalKeyboard({ key: "Tab", preventDefault() {} });
  harness.api.finishConfirmation(false);

  const integer = new FakeNode("worker-count");
  integer.dataset.valueType = "integer";
  integer.value = "bad";
  assert.throws(() => harness.api.readConfigControl(integer), /worker-count/i);
  const number = new FakeNode("ratio");
  number.dataset.valueType = "number";
  number.value = "NaN";
  assert.throws(() => harness.api.readConfigControl(number), /ratio/i);
  const json = new FakeNode("metadata");
  json.dataset.valueType = "json";
  json.value = "{";
  assert.throws(() => harness.api.readConfigControl(json), /metadata/i);

  const boolean = new FakeNode("boolean");
  boolean.dataset.valueType = "boolean";
  harness.api.writeConfigControl(boolean, true);
  assert.equal(boolean.checked, true);
  const genericJson = new FakeNode("generic-json");
  genericJson.dataset.valueType = "json";
  harness.api.writeConfigControl(genericJson, null);
  assert.equal(genericJson.value, "[]");
  const nullableString = new FakeNode("nullable-string");
  harness.api.writeConfigControl(nullableString, null);
  assert.equal(nullableString.value, "");

  const clearOperations = [];
  harness.api.appendSecretOperation(clearOperations, "judge.api_key", "", true);
  assert.deepEqual(JSON.parse(JSON.stringify(clearOperations)), [{
    action: "clear", op: "secret", path: "judge.api_key",
  }]);

  const providers = new FakeNode("config-providers");
  providers.dataset.configPath = "providers";
  providers.dataset.valueType = "json";
  providers.value = "[{}]";
  harness.nodes.set("config-providers", providers);
  harness.api.syncProviderSecretOptions();
  assert.equal(harness.node("config-provider-secret-index").options[0].textContent, "Provider 1");

  assert.equal(harness.api.applyConfigSnapshot(null), false);
  harness.api.state.activeView = "settings";
  harness.api.state.configDirty = true;
  harness.api.state.config = {};
  harness.api.state.pendingConfig = { revision: "same" };
  assert.equal(harness.api.applyConfigSnapshot({ revision: "same", effective: {} }), false);

  const first = new FakeNode("first-control");
  first.dataset.configPath = "first";
  first.value = "changed";
  const second = new FakeNode("second-control");
  second.dataset.configPath = "second";
  second.value = "changed";
  harness.select("[data-config-path]", [first, second]);
  harness.api.state.configBaseline = new Map([["first", '"old"'], ["second", '"old"']]);
  harness.api.updateConfigDirtyState();
  assert.match(harness.node("config-change-count").textContent, /2 unsaved changes/i);

  harness.select("[data-config-path]", []);
  harness.api.renderConfig({ config: {}, environment_overrides: [], revision: null });
  assert.equal(harness.node("config-revision").textContent, "NEW FILE");
  assert.equal(harness.node("config-override-count").textContent, "NO OVERRIDES");
  assert.match(harness.node("config-path").textContent, /bundled defaults/i);

  harness.api.switchView("unrecognized");
  assert.equal(harness.node("view-title").textContent, "Agency Runtime");
  harness.missing("missing-metric");
  harness.api.setMetric("missing-metric", "ignored");
  harness.context.AgencyCharts = undefined;
  harness.api.renderCharts();
  harness.missing("live-toggle");
  harness.api.syncLiveToggle();
});

test("app.js renders sparse and changing runtime evidence defensively", () => {
  const harness = createAppHarness(() => {
    throw new Error("render-only test does not fetch");
  });
  harness.api.state.activeView = "evidence";
  const tab = new FakeNode("routing-tab");
  tab.dataset.evidence = "routing";
  harness.select(".subnav-item.active", [tab]);
  harness.api.state.activity = { routing: [] };
  harness.api.renderActiveView();
  harness.api.state.activeView = "roster";
  harness.api.renderActiveView();
  harness.api.state.activeView = "overview";
  harness.api.state.overview = null;
  harness.api.renderActiveControlView();
  harness.api.state.overview = {};
  harness.api.renderActiveControlView();

  assert.match(harness.api.evidenceRowKey({}, 3), /^trace:3$/);
  harness.api.state.overview = {
    provider_health: [{ failure_count: 0, provider: "local", success_count: 0, unknown_count: 1 }],
  };
  harness.api.state.hosts = [{ host: "codex", runtime_enabled: false }];
  harness.api.state.activity = {
    delegations: [{ started_at: null }],
  };
  harness.api.state.evidenceKeys.set("overview", new Set(["old"]));
  harness.api.renderOverview();
  assert.equal(harness.node("metric-runtime").textContent, "Unknown");
  assert.ok(harness.node("overview-delegations").children[0].classList.contains("is-new"));
  assert.ok(
    descendants(harness.node("overview-delegations"))
      .some((node) => node.textContent === "Not observed"),
  );

  harness.api.state.hosts = [
    { executable_discovered: false, host: "absent", runtime_enabled: false },
    { executable_discovered: true, host: "unknown", inspection_status: "complete" },
    { executable_discovered: true, host: "enabled", inspection_status: "complete", runtime_control_generation: 0, runtime_enabled: true },
    { executable_discovered: true, host: "disabled", inspection_status: "complete", runtime_control_generation: 0, runtime_enabled: false },
  ];
	harness.api.renderHosts();
	const buttons = descendants(harness.node("host-grid")).filter((node) => node.type === "button");
	assert.deepEqual(buttons.map((node) => node.textContent), [
		"State unknown",
		"Disable",
		"Enable",
		"Copy uninstall preview",
	]);
	assert.equal(buttons[0].disabled, true);
	assert.equal(buttons[1].disabled, false);
	assert.equal(buttons[2].disabled, false);

  harness.api.state.activity = {
    finalizations: [{ action: "", missing: [], trace_id: "new" }],
  };
  harness.api.state.evidenceKeys.set("finalizations", new Set(["old"]));
  harness.api.renderEvidence("finalizations");
  const evidenceRow = harness.node("evidence-body").children[0];
  assert.equal(evidenceRow.classList.contains("is-new"), true);
  assert.ok(descendants(evidenceRow).some((node) => node.textContent === "—"));

  harness.api.renderReceipt({
    provider: "fallback-provider",
    selected: [{ agent_slug: "agent-two" }, { id: "agent-three" }, {}],
    signals: {
      selection: { provider: "judge", status: "ranked" },
      work_units: { units: [{ id: "unit" }] },
    },
  });
  assert.equal(harness.node("route-status").textContent, "RANKED");

  harness.api.updateLastSync("invalid");
  assert.equal(harness.node("last-sync").textContent, "Sync time unavailable");
  harness.api.updateLastSync();
  assert.match(harness.node("last-sync").textContent, /last sync/i);
});

test("app.js covers nested confirmations and final parsing fallbacks", async () => {
  const harness = createAppHarness(async () => jsonResponse(418, {}));

  const first = harness.api.requestConfirmation("FIRST", "First operation.");
  const second = harness.api.requestConfirmation("SECOND", "Second operation.");
  assert.equal(await first, false);
  harness.api.finishConfirmation(false);
  assert.equal(await second, false);

  harness.api.state.confirmation = { phrase: "x", resolve() {}, returnFocus: null };
  harness.node("confirmation-modal").hidden = false;
  harness.api.handleModalKeyboard({ key: "A", preventDefault() {} });
  harness.api.finishConfirmation(false);

  await assert.rejects(harness.api.api("/teapot"), /HTTP 418/);
  const number = new FakeNode("ratio");
  number.dataset.valueType = "number";
  number.labels = [{ textContent: "" }];
  number.value = "NaN";
  assert.throws(() => harness.api.readConfigControl(number), /ratio/i);
});

test("app.js covers sparse configuration and chart payload fallbacks", () => {
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  harness.select("[data-config-path]", []);
  harness.api.renderConfig({});
  assert.equal(harness.node("config-revision").textContent, "NEW FILE");
  harness.api.renderConfig({ effective: {}, environment_overrides: ["one", "two"] });
  assert.equal(harness.node("config-override-count").textContent, "2 ENV OVERRIDES");

  harness.api.state.activeView = "settings";
  harness.api.state.configDirty = true;
  harness.api.state.config = {};
  harness.api.state.pendingConfig = {};
  assert.equal(harness.api.applyConfigSnapshot({ revision: "new", effective: {} }), false);

  harness.context.AgencyCharts = {
    renderActivityChart: () => [],
    renderOutcomeChart: () => ({ failed: 0, skipped: 0, success: 0, unknown: 0 }),
  };
  harness.api.state.live.sampledAt = "invalid";
  harness.api.renderCharts();
  assert.match(harness.node("window-label").textContent, /^0 min window/);

  harness.api.state.overview = null;
  harness.api.renderOverview();
  assert.equal(harness.node("metric-runtime").textContent, "Unknown");
  harness.api.state.roster = [{ agent_slug: "no-capabilities-field" }];
  harness.api.state.snapshots = [];
  harness.api.renderRoster();
  assert.ok(
    descendants(harness.node("roster-grid"))
      .some((node) => node.textContent === "no capability tags"),
  );
});

test("app.js covers sparse receipts and live snapshots", () => {
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  harness.api.renderReceipt({});
  assert.equal(
    descendants(harness.node("route-result"))
      .some((node) => /delegation work units|dependency graph/i.test(node.textContent)),
    false,
  );
  harness.api.renderReceipt({
    signals: { delegation: {}, work_units: {} },
    work_units: {},
  });
  assert.equal(harness.node("route-status").textContent, "COMPLETE");
  harness.api.renderReceipt({
		signals: { delegation: { work_units: { units: [{ id: "first-path" }] } } },
	});
	assert.equal(
		descendants(harness.node("route-result"))
			.some((node) => node.textContent.includes("first-path")),
		false,
	);

  harness.api.state.activeView = "routing";
  assert.equal(harness.api.applyLiveSnapshot({ schema_version: 1 }), true);
  assert.equal(harness.api.state.live.revision, "");
  assert.deepEqual(JSON.parse(JSON.stringify(harness.api.state.activity)), {});
  assert.deepEqual(JSON.parse(JSON.stringify(harness.api.state.overview)), {});

  harness.api.state.activeView = "overview";
  harness.api.state.live.chartWindow = 1;
  assert.equal(harness.api.applyLiveSnapshot({
    revision: "",
    sampled_at: "invalid",
    schema_version: 1,
  }), false);
});

test("app.js covers cancellation, stale control responses, and fallback retry", async () => {
  const retry = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  retry.context.AgencyCharts = undefined;
  retry.api.handleLiveFailure(new Error("offline"));
  assert.equal(retry.timers.tasks.get(retry.api.state.live.timer).delay, 2000);

  const livePending = deferred();
  const staleLive = createAppHarness(() => livePending.promise);
  const poll = staleLive.api.runLivePoll();
  staleLive.api.state.live.generation += 1;
  livePending.resolve(jsonResponse(200, { revision: "stale", schema_version: 1 }));
  await poll;
  assert.equal(staleLive.api.state.live.revision, "");
  assert.equal(staleLive.api.state.live.timer, null);

  const activeControl = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  const controller = new AbortController();
  activeControl.api.state.control.controller = controller;
  activeControl.api.cancelControlRequest();
  assert.equal(controller.signal.aborted, true);

  const requests = [];
  const staleControl = createAppHarness(() => {
    const pending = deferred();
    requests.push(pending);
    return pending.promise;
  });
  const refresh = staleControl.api.refreshControlPlane();
  staleControl.api.cancelControlRequest();
  requests.forEach((pending) => pending.resolve(jsonResponse(200, {})));
  await refresh;
  assert.equal(staleControl.api.state.control.timer, null);

  const sparseControl = createAppHarness(async () => jsonResponse(200, {}));
  await sparseControl.api.refreshControlPlane();
  assert.equal(sparseControl.api.state.hosts.length, 0);
  assert.equal(sparseControl.api.state.roster.length, 0);
  assert.equal(sparseControl.api.state.snapshots.length, 0);

  const hiddenClock = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  hiddenClock.document.visibilityState = "hidden";
  hiddenClock.api.updateLocalClock();
  assert.equal(hiddenClock.api.state.clockTimer, null);
});

test("app.js rejects sparse collection payloads while paused and preserves last-good state", async () => {
  const payloads = new Map([
    ["/api/live?limit=100", { schema_version: 1 }],
    ["/api/hosts", {}],
    ["/api/roster?limit=100", {}],
    ["/api/snapshots", {}],
    ["/api/config", { config: {} }],
  ]);
  const harness = createAppHarness(async (path) => jsonResponse(200, payloads.get(path)));
  harness.api.state.live.enabled = false;
  harness.api.setLiveStatus("Live updates paused", "paused");
  harness.api.state.hosts = [{ host: "last-good-host" }];
  harness.api.state.roster = [{ agent_slug: "last-good-agent" }];
  harness.api.state.snapshots = [{ snapshot_id: "last-good-snapshot" }];
  assert.equal(await harness.api.refreshAll(), undefined);
  assert.equal(harness.api.state.hosts[0].host, "last-good-host");
  assert.equal(harness.api.state.roster[0].agent_slug, "last-good-agent");
  assert.equal(harness.api.state.snapshots[0].snapshot_id, "last-good-snapshot");
  assert.equal(harness.node("live-status").textContent, "Live updates paused");
  assert.equal(harness.node("live-status").dataset.state, "paused");

  const emptyConfigPayloads = new Map(payloads);
  emptyConfigPayloads.set("/api/config", {});
  emptyConfigPayloads.set("/api/roster?limit=100", emptyRosterPage("empty-config-roster"));
  emptyConfigPayloads.set("/api/snapshots", emptyGovernancePage("empty-config-snapshots"));
  emptyConfigPayloads.set("/api/control", controlSnapshot({
    config: { effective: {}, revision: "empty-config" },
  }));
  const emptyConfig = createAppHarness(async (path) => (
    jsonResponse(200, emptyConfigPayloads.get(path))
  ));
  assert.equal(await emptyConfig.api.refreshAll(), true);
  assert.equal(emptyConfig.api.state.overview.capture_content, false);
  assert.equal(emptyConfig.api.state.overview.retention_days, undefined);
  assert.equal(emptyConfig.api.state.overview.roster_count, 0);
});

test("app.js rejects null governance without replacing the last-good control state", async () => {
  const malformed = controlSnapshot();
  malformed.governance = null;
  const harness = createAppHarness(async (path) => {
    assert.equal(path, "/api/control");
    return jsonResponse(200, malformed);
  });
  harness.api.state.hosts = [{ host: "last-good-host" }];
  harness.api.state.roster = [{ agent_slug: "last-good-agent" }];
  harness.api.state.snapshots = [{ snapshot_id: "last-good-snapshot" }];
  harness.api.state.rosterReview = {
    candidates: [{ candidate: { id: "last-good-review" } }],
  };

  await harness.api.refreshControlPlane();

  assert.deepEqual(harness.api.state.hosts, [{ host: "last-good-host" }]);
  assert.deepEqual(harness.api.state.roster, [{ agent_slug: "last-good-agent" }]);
  assert.deepEqual(harness.api.state.snapshots, [{ snapshot_id: "last-good-snapshot" }]);
  assert.deepEqual(harness.api.state.rosterReview, {
    candidates: [{ candidate: { id: "last-good-review" } }],
  });
  assert.equal(harness.api.state.control.stale, true);
  assert.match(harness.node("notice").textContent, /retained the last good state/i);
});

test("ES-module bootstrap and lifecycle teardown are deterministic", async () => {
  const harness = createAppHarness(() => {
    throw new Error("teardown must abort before fetching");
  });
  const nav = new FakeNode("nav-overview");
  nav.classList.add("active");
  nav.dataset.view = "overview";
  const panel = new FakeNode("view-overview");
  panel.dataset.viewPanel = "overview";
  const tab = new FakeNode("evidence-tab");
  tab.classList.add("active");
  tab.dataset.evidence = "delegations";
  harness.select(".nav-item", [nav]);
  harness.select(".nav-item.active", [nav]);
  harness.select(".view", [panel]);
  harness.select(".subnav-item", [tab]);

  assert.equal(harness.api.bindEvents(), true);
  assert.equal(harness.api.bindEvents(), false);
  harness.api.configureEvidenceTabs();
  assert.equal(nav.listeners.get("click").length, 1);
  assert.equal(tab.listeners.get("click").length, 1);

  harness.api.showNotice("clean me up");
  const metric = harness.node("metric-runtime");
  harness.api.markUpdated(metric);
  harness.api.markUpdated(metric);
  assert.equal(metric.listeners.get("animationend").length, 1);
  const confirmation = harness.api.requestConfirmation("CLOSE", "Close safely.");
  const mutation = harness.api.beginMutation();

  assert.equal(harness.api.destroy(), true);
  assert.equal(await confirmation, false);
  assert.equal(mutation.signal.aborted, true);
  assert.equal(harness.api.showNotice.timer, null);
  assert.equal(metric.listeners.get("animationend").length, 0);
  assert.equal(harness.documentListeners.get("visibilitychange").length, 0);
  assert.equal(harness.windowListeners.get("hashchange").length, 0);
  assert.equal(harness.api.finishMutation(mutation), false);
  assert.equal(harness.api.destroy(), false);
  assert.equal(await harness.api.start(), false);

  assert.equal(bootstrappedDashboard.state.lifecycle.destroyed, true);
});

test("connection and reconciliation generations reject stale async completions", async () => {
  const pendingRequests = [];
  const connected = createAppHarness((path) => {
    const pending = deferred();
    pendingRequests.push({ path, pending });
    return pending.promise;
  });
  connected.sessionValues.set("agency-dashboard-token", "stored-token");
  const connecting = connected.api.connectFromLocation();
  await Promise.resolve();
  connected.api.state.lifecycle.suspended = true;
  const payloads = new Map([
    ["/api/live?limit=100", { activity: {}, overview: {}, revision: "stale", schema_version: 1 }],
    ["/api/hosts", { hosts: [] }],
    ["/api/roster?limit=100", { agents: [] }],
    ["/api/snapshots", { snapshots: [] }],
    ["/api/config", { effective: {}, revision: "stale-config" }],
  ]);
  pendingRequests.forEach(({ path, pending }) => pending.resolve(jsonResponse(200, payloads.get(path))));
  assert.equal(await connecting, false);
  assert.equal(connected.node("connection-label").textContent, "");

  const rejected = deferred();
  const failed = createAppHarness(() => rejected.promise);
  failed.sessionValues.set("agency-dashboard-token", "stored-token");
  const staleFailure = failed.api.connectFromLocation();
  await Promise.resolve();
  failed.api.state.lifecycle.destroyed = true;
  rejected.reject(new Error("obsolete connection"));
  assert.equal(await staleFailure, false);
  assert.equal(failed.node("notice").textContent, "");

  const destroyedConnection = createAppHarness(() => {
    throw new Error("a missing token must fail before fetching");
  });
  destroyedConnection.api.state.lifecycle.destroyed = true;
  assert.equal(await destroyedConnection.api.connectFromLocation(), false);
  assert.equal(destroyedConnection.node("notice").textContent, "");

  const livePending = deferred();
  const live = createAppHarness(() => livePending.promise);
  const refreshing = live.api.refreshRuntimeEvidence();
  live.api.cancelLiveRequest();
  livePending.resolve(jsonResponse(200, { revision: "obsolete", schema_version: 1 }));
  assert.equal(await refreshing, false);
  assert.equal(live.api.state.live.revision, "");
  assert.equal(live.node("connection-label").textContent, "");

  live.api.state.lifecycle.destroyed = true;
  assert.equal(await live.api.reconcileRuntimeEvidence("ignored"), false);
  live.api.state.lifecycle.destroyed = false;
  live.api.state.lifecycle.suspended = true;
  assert.equal(await live.api.reconcileAll("ignored"), false);

  const reconcilePending = deferred();
  const staleReconcile = createAppHarness(() => reconcilePending.promise);
  const reconciling = staleReconcile.api.reconcileRuntimeEvidence("completed");
  staleReconcile.api.state.lifecycle.suspended = true;
  reconcilePending.reject(new Error("late failure"));
  assert.equal(await reconciling, false);
  assert.equal(staleReconcile.node("notice").textContent, "completed");
});

test("paged roster metadata drives global counts and accessible truncation disclosure", async () => {
  const hostileCursor = 'page/<img src=x onerror="compromised=true">';
  const harness = createAppHarness(() => {
    throw new Error("paged roster projection does not fetch");
  });
  assert.equal(
    harness.api.validateExactRosterLookup({
      agents: [{ agent_slug: "security-reviewer" }],
      filter_slug: "security-reviewer",
    }, "security-reviewer").filter_slug,
    "security-reviewer",
  );
  assert.throws(
    () => harness.api.validateExactRosterLookup({
      agents: [{ agent_slug: "wrong-agent" }],
      filter_slug: "security-reviewer",
    }, "security-reviewer"),
    /did not match the requested agent/i,
  );
  for (const filterSlug of ["SECURITY-REVIEWER", " security-reviewer ", 7]) {
    assert.throws(
      () => harness.api.validateExactRosterLookup({
        agents: [{ agent_slug: "security-reviewer" }],
        filter_slug: filterSlug,
      }, "security-reviewer"),
      /did not match the requested agent/i,
    );
  }
  for (const agentSlug of ["SECURITY-REVIEWER", " security-reviewer ", 7]) {
    assert.throws(
      () => harness.api.validateExactRosterLookup({
        agents: [{ agent_slug: agentSlug }],
        filter_slug: "security-reviewer",
      }, "security-reviewer"),
      /did not match the requested agent/i,
    );
  }
  harness.api.applyRosterPage({
    agents: [
      { agent_slug: "first", capabilities: [] },
      { agent_slug: "second", capabilities: [] },
    ],
    count: 2,
    total_count: 6,
    enabled_count: 4,
    disabled_count: 2,
    limit: 2,
    truncated: true,
    next_cursor: hostileCursor,
  });
  harness.api.state.overview = { roster_count: 4 };
  harness.api.renderOverview();
  assert.deepEqual(harness.api.state.rosterPage, {
    agents: harness.api.state.roster,
    count: 2,
    total_count: 6,
    enabled_count: 4,
    disabled_count: 2,
    limit: 2,
    truncated: true,
    next_cursor: hostileCursor,
  });
  assert.equal(harness.api.state.overview.roster_count, 4);
  assert.equal(harness.node("metric-roster").textContent, "4");

  harness.api.state.activeView = "roster";
  harness.api.renderRoster();
  const pageStatus = harness.node("roster-page-status");
  assert.equal(harness.node("roster-count").textContent, "4 enabled · 6 total");
  assert.equal(pageStatus.hidden, false);
  assert.match(pageStatus.textContent, /showing 2 of 6 governed specialists/i);
  assert.match(pageStatus.textContent, /4 are not shown/i);
  assert.match(pageStatus.textContent, /find any specialist by its exact agent slug/i);
  assert.equal(pageStatus.textContent.includes("<img"), false);
  assert.equal(harness.node("roster-search-clear").hidden, true);
  assert.equal(harness.context.compromised, undefined);

  harness.api.applyRosterPage({
    agents: [{ agent_slug: "only", capabilities: [] }],
    count: 1,
    total_count: 1,
    limit: 50,
    truncated: false,
    next_cursor: null,
  });
  harness.api.renderRoster();
  assert.equal(harness.node("roster-count").textContent, "1 enabled · 1 total");
  assert.equal(pageStatus.hidden, true);
  assert.equal(pageStatus.textContent, "");

  harness.api.applyRosterPage({
    agents: [{ agent_slug: "first", capabilities: [] }],
    count: 1,
    total_count: 3,
    limit: 1,
    truncated: true,
  });
  harness.api.renderRoster();
  assert.match(pageStatus.textContent, /exact agent slug/i);

  harness.api.applyRosterPage({
    agents: [],
    count: 0,
    total_count: 2,
    limit: 0,
    truncated: true,
    next_cursor: "empty-page",
  });
  harness.api.renderRoster();
  assert.match(pageStatus.textContent, /showing 0 of 2/i);

  harness.api.state.rosterFilter = "missing-agent";
  harness.api.renderRoster();
  assert.match(pageStatus.textContent, /no governed specialist matches missing-agent/i);
  assert.equal(harness.node("roster-search-clear").hidden, false);
  harness.api.state.rosterFilter = "";

  assert.deepEqual(harness.api.applyRosterPage({
    agents: "invalid",
    count: -1,
    total_count: -2,
    limit: 0,
    truncated: "true",
    next_cursor: 7,
  }), {
    agents: [],
    count: 0,
    total_count: 0,
    enabled_count: 0,
    disabled_count: 0,
    limit: 0,
    truncated: false,
    next_cursor: null,
  });
  assert.deepEqual(harness.api.applyRosterPage(), {
    agents: [],
    count: 0,
    total_count: 0,
    enabled_count: 0,
    disabled_count: 0,
    limit: 0,
    truncated: false,
    next_cursor: null,
  });

  const optionalStatus = createAppHarness(() => {
    throw new Error("rendering roster metadata does not fetch");
  });
  optionalStatus.missing("roster-page-status");
  optionalStatus.api.state.roster = [];
  optionalStatus.api.renderRoster();
  assert.equal(optionalStatus.node("roster-count").textContent, "0 enabled · 0 total");
});

test("collection completion fails closed on missing initial cursor or revision", async () => {
  const calls = [];
  const harness = createAppHarness(async (path) => {
    calls.push(path);
    return jsonResponse(200, {
      collection_revision: "revision-1",
      next_cursor: null,
      truncated: false,
      workers: [{ agent_slug: "worker-two" }],
    });
  });
  const options = {
    basePath: "/api/workforce?limit=200",
    itemField: "workers",
    revisionField: "collection_revision",
  };

  await assert.rejects(
    harness.api.completeCollection({
      collection_revision: "revision-1",
      truncated: true,
      workers: [],
    }, options),
    /invalid next cursor/i,
  );
  await assert.rejects(
    harness.api.completeCollection({
      next_cursor: "cursor-1",
      truncated: true,
      workers: [],
    }, options),
    /omitted its paging revision/i,
  );
  assert.equal(calls.length, 0);

  const completed = await harness.api.completeCollection({
    collection_revision: "revision-1",
    next_cursor: "cursor-1",
    truncated: true,
    workers: [{ agent_slug: "worker-one" }],
  }, options);
  assert.equal(calls[0], "/api/workforce?limit=200&after=cursor-1");
  assert.deepEqual(
    completed.workers.map((worker) => worker.agent_slug),
    ["worker-one", "worker-two"],
  );
  assert.equal(completed.truncated, false);
  assert.equal(completed.pages_loaded, 2);

  const changed = createAppHarness(async () => jsonResponse(200, {
    collection_revision: "revision-2",
    next_cursor: null,
    truncated: false,
    workers: [],
  }));
  await assert.rejects(
    changed.api.completeCollection({
      collection_revision: "revision-1",
      next_cursor: "cursor-1",
      truncated: true,
      workers: [],
    }, options),
    /changed while it was being paged/i,
  );

  for (const [page, message] of [
    [null, /invalid page/i],
    [[], /invalid page/i],
    [{
      collection_revision: "revision-1", next_cursor: null, truncated: false, workers: {},
    }, /invalid items/i],
    [{
      collection_revision: "revision-1", next_cursor: null, truncated: "false", workers: [],
    }, /invalid truncation flag/i],
    [{ next_cursor: null, truncated: false, workers: [] }, /paging revision/i],
    [{
      collection_revision: "revision-1", next_cursor: "A-noncanonical-slug", truncated: true, workers: [],
    }, /invalid next cursor/i],
    [{
      collection_revision: "revision-1", next_cursor: "x".repeat(129), truncated: true, workers: [],
    }, /invalid next cursor/i],
    [{
      collection_revision: "revision-1", next_cursor: "unexpected", truncated: false, workers: [],
    }, /unexpected next cursor/i],
  ]) {
    await assert.rejects(harness.api.completeCollection(page, options), message);
  }
  for (const cursor of [
    "invalid=padding",
    "x".repeat(1025),
    encodedCursor("wrong.v1", "time", "id"),
  ]) {
    await assert.rejects(
      harness.api.completeCollection({
        collection_revision: "revision-1",
        next_cursor: cursor,
        truncated: true,
        workers: [],
      }, { ...options, cursorContract: "encoded", cursorKind: "hiring.v1" }),
      /invalid next cursor/i,
    );
  }
  const hiringCursor = encodedCursor("hiring.v1", "2026-07-26T12:00:00Z", "case-1");
  const encodedHarness = createAppHarness(async () => jsonResponse(200, {
    collection_revision: "hiring-revision-1",
    hiring_cases: [{ id: "case-2" }],
    next_cursor: null,
    truncated: false,
  }));
  const completedHiring = await encodedHarness.api.completeCollection({
    collection_revision: "hiring-revision-1",
    hiring_cases: [{ id: "case-1" }],
    next_cursor: hiringCursor,
    truncated: true,
  }, {
    basePath: "/api/hiring?limit=200",
    cursorContract: "encoded",
    cursorKind: "hiring.v1",
    itemField: "hiring_cases",
    revisionField: "collection_revision",
  });
  assert.deepEqual(completedHiring.hiring_cases.map((item) => item.id), ["case-1", "case-2"]);
});

test("workforce and hiring retain last-good data independently", async () => {
  let mode = "baseline";
  const workforceFails = createAppHarness(async (path) => {
    if (path.startsWith("/api/workforce")) {
      if (mode === "workforce-fails") {
        return jsonResponse(200, workforceCollection([], { workers: "not-an-array" }));
      }
      return jsonResponse(200, workforceCollection(
        [{ agent_slug: "last-good-worker", state: "employee" }],
        { counts: { employee: 1 } },
      ));
    }
    return jsonResponse(200, hiringCollection([
      hiringCaseSummary(mode === "baseline" ? "last-good-case" : "new-hiring-case"),
    ]));
  });
  workforceFails.api.state.activeView = "workforce";
  assert.equal(await workforceFails.api.refreshWorkforce(), true);
  const workforceSampledAt = workforceFails.api.state.workforceSources.workforce.lastGoodAt;
  mode = "workforce-fails";
  assert.equal(await workforceFails.api.refreshWorkforce(), true);
  assert.deepEqual(
    workforceFails.api.state.workforce.map((worker) => worker.agent_slug),
    ["last-good-worker"],
  );
  assert.deepEqual(workforceFails.api.state.workforceCounts, { employee: 1 });
  assert.deepEqual(
    workforceFails.api.state.hiring.map((item) => item.id),
    ["new-hiring-case"],
  );
  assert.deepEqual(workforceFails.api.state.workforceSources.workforce, {
    status: "stale",
    error: "The workers collection returned invalid items.",
    lastGoodAt: workforceSampledAt,
  });
  assert.equal(workforceFails.api.state.workforceSources.hiring.status, "current");
  assert.match(workforceFails.node("workforce-count").textContent, /STALE/);
  assert.match(
    descendants(workforceFails.node("workforce-grid")).map((node) => node.textContent).join(" "),
    /retaining the last-good sample/i,
  );
  assert.match(workforceFails.node("hiring-count").textContent, /CURRENT/);

  mode = "baseline";
  const hiringFails = createAppHarness(async (path) => {
    if (path.startsWith("/api/workforce")) {
      return jsonResponse(200, workforceCollection([
        { agent_slug: mode === "baseline" ? "baseline-worker" : "new-workforce-worker" },
      ]));
    }
    if (mode === "hiring-fails") {
      return jsonResponse(200, hiringCollection([], { hiring_cases: "not-an-array" }));
    }
    return jsonResponse(200, hiringCollection([hiringCaseSummary("last-good-hiring")]));
  });
  hiringFails.api.state.activeView = "workforce";
  assert.equal(await hiringFails.api.refreshWorkforce(), true);
  const hiringSampledAt = hiringFails.api.state.workforceSources.hiring.lastGoodAt;
  mode = "hiring-fails";
  assert.equal(await hiringFails.api.refreshWorkforce(), true);
  assert.deepEqual(
    hiringFails.api.state.workforce.map((worker) => worker.agent_slug),
    ["new-workforce-worker"],
  );
  assert.deepEqual(hiringFails.api.state.hiring.map((item) => item.id), ["last-good-hiring"]);
  assert.equal(hiringFails.api.state.workforceSources.workforce.status, "current");
  assert.deepEqual(hiringFails.api.state.workforceSources.hiring, {
    status: "stale",
    error: "The hiring_cases collection returned invalid items.",
    lastGoodAt: hiringSampledAt,
  });
  assert.match(hiringFails.node("hiring-count").textContent, /STALE/);
  assert.match(hiringFails.node("hiring-page-status").textContent, /retaining the last-good sample/i);
});

test("first-load source failures stay unavailable while validated empty peers stay current", async () => {
  const invalidWorkforce = createAppHarness(async (path) => jsonResponse(
    200,
    path.startsWith("/api/workforce")
      ? workforceCollection([], { workers: "not-an-array" })
      : hiringCollection([]),
  ));
  invalidWorkforce.api.state.activeView = "workforce";
  assert.equal(await invalidWorkforce.api.refreshWorkforce(), true);
  assert.equal(invalidWorkforce.api.state.workforceSources.workforce.status, "unavailable");
  assert.equal(invalidWorkforce.api.state.workforceSources.hiring.status, "current");
  assert.match(invalidWorkforce.node("workforce-count").textContent, /UNAVAILABLE/);
  assert.match(
    descendants(invalidWorkforce.node("workforce-grid"))
      .map((node) => node.textContent).join(" "),
    /unavailable; no validated sample/i,
  );
  assert.match(
    descendants(invalidWorkforce.node("hiring-list"))
      .map((node) => node.textContent).join(" "),
    /No hiring cases match the committed source filters/i,
  );

  const invalidHiring = createAppHarness(async (path) => jsonResponse(
    200,
    path.startsWith("/api/workforce")
      ? workforceCollection([])
      : hiringCollection([], { hiring_cases: "not-an-array" }),
  ));
  invalidHiring.api.state.activeView = "workforce";
  assert.equal(await invalidHiring.api.refreshWorkforce(), true);
  assert.equal(invalidHiring.api.state.workforceSources.workforce.status, "current");
  assert.equal(invalidHiring.api.state.workforceSources.hiring.status, "unavailable");
  assert.match(
    descendants(invalidHiring.node("workforce-grid"))
      .map((node) => node.textContent).join(" "),
    /No governed workers are installed yet/i,
  );
  assert.match(invalidHiring.node("hiring-count").textContent, /UNAVAILABLE/);
  assert.match(invalidHiring.node("hiring-page-status").textContent, /no validated sample/i);

  const emptyCurrent = createAppHarness(async (path) => jsonResponse(
    200,
    path.startsWith("/api/workforce") ? workforceCollection([]) : hiringCollection([]),
  ));
  emptyCurrent.api.state.activeView = "workforce";
  assert.equal(await emptyCurrent.api.refreshWorkforce(), true);
  assert.equal(emptyCurrent.api.state.workforceSources.workforce.status, "current");
  assert.equal(emptyCurrent.api.state.workforceSources.hiring.status, "current");
  assert.match(emptyCurrent.node("workforce-count").textContent, /CURRENT/);
  assert.match(emptyCurrent.node("hiring-count").textContent, /CURRENT/);
});

test("roster paging rejects activation-policy changes under a stable Store generation", async () => {
  const first = controlSnapshot({
    config: { revision: "config-revision-a" },
    roster: {
      agents: [{ agent_slug: "alpha-reviewer" }],
      config_revision: "config-revision-a",
      next_cursor: "alpha-reviewer",
      roster_revision: "stable-roster-generation",
      truncated: true,
    },
  });
  const harness = createAppHarness(async (path) => {
    if (path === "/api/control") return jsonResponse(200, first);
    if (path === "/api/roster?limit=200&after=alpha-reviewer") {
      return jsonResponse(200, {
        agents: [{ agent_slug: "beta-reviewer" }],
        config_revision: "config-revision-b",
        next_cursor: null,
        roster_revision: "stable-roster-generation",
        truncated: false,
      });
    }
    throw new Error(`unexpected activation-continuity path ${path}`);
  });

  await assert.rejects(
    harness.api.fetchControlSnapshot(),
    /changed while it was being paged/i,
  );

  const mismatchedInitial = createAppHarness(async (path) => {
    if (path === "/api/control") {
      return jsonResponse(200, controlSnapshot({
        config: { revision: "config-revision-a" },
        roster: { config_revision: "config-revision-b" },
      }));
    }
    throw new Error(`unexpected control-continuity path ${path}`);
  });
  await assert.rejects(
    mismatchedInitial.api.fetchControlSnapshot(),
    /did not match the control snapshot/i,
  );
});

test("roster search markup permits the normalization performed before lookup", () => {
  const searchInput = INDEX_SOURCE.match(/<input id="roster-search-slug"[^>]*>/)?.[0] || "";
  assert.doesNotMatch(searchInput, /\s(?:pattern|minlength)=/);
  assert.match(searchInput, /maxlength="256"/);
  assert.match(searchInput, /aria-describedby="roster-search-help"/);

  const harness = createAppHarness(() => {
    throw new Error("normalization-only test does not fetch");
  });
  assert.equal(harness.api.normalizeRosterFilter("  Security-Reviewer  "), "security-reviewer");
});

test("roster search rolls back failed lookups and refuses inactive lifecycles", async () => {
  let calls = 0;
  const harness = createAppHarness(async () => {
    calls += 1;
    return jsonResponse(503, { error: "lookup unavailable" });
  });
  harness.api.state.activeView = "roster";
  harness.api.state.rosterFilter = "current-agent";
  harness.api.state.rosterFilterCommitted = "current-agent";
  harness.node("roster-search-slug").value = "current-agent";

  assert.equal(await harness.api.applyRosterFilter("target-agent"), false);
  assert.equal(harness.api.state.rosterFilter, "current-agent");
  assert.equal(harness.node("roster-search-slug").value, "current-agent");
  assert.match(harness.node("notice").textContent, /control refresh failed/i);
  assert.match(harness.node("notice").textContent, /request id/i);
  assert.ok(calls > 0);

  const callsAfterFailure = calls;
  harness.api.state.lifecycle.destroyed = true;
  assert.equal(await harness.api.applyRosterFilter("target-agent"), false);
  harness.api.state.lifecycle.destroyed = false;
  harness.api.state.lifecycle.suspended = true;
  assert.equal(await harness.api.applyRosterFilter("target-agent"), false);
  assert.equal(calls, callsAfterFailure);
});

test("a stale roster search cannot roll back a newer successful search", async () => {
  const staleLive = deferred();
  let firstLiveSignal;
  let liveCalls = 0;
  let filterALookups = 0;
  const harness = createAppHarness((path, options) => {
    if (path === "/api/live?limit=100") {
      liveCalls += 1;
      if (liveCalls === 1) {
        firstLiveSignal = options.signal;
        return staleLive.promise;
      }
      return Promise.resolve(jsonResponse(200, {
        revision: "filter-b-live",
        schema_version: 1,
      }));
    }
    if (path === "/api/control") {
      return Promise.resolve(jsonResponse(200, controlSnapshot()));
    }
    if (path === "/api/agents/lookup?slug=filter-a") {
      filterALookups += 1;
      return Promise.resolve(jsonResponse(200, {
        ...emptyRosterPage("filter-a-revision"),
        agents: [{ agent_slug: "filter-a", capabilities: [], enabled: true }],
        filter_slug: "filter-a",
      }));
    }
    if (path === "/api/agents/lookup?slug=filter-b") {
      return Promise.resolve(jsonResponse(200, {
        ...emptyRosterPage("filter-b-revision"),
        agents: [{ agent_slug: "filter-b", capabilities: [], enabled: true }],
        filter_slug: "filter-b",
      }));
    }
    throw new Error(`unexpected roster-filter race path ${path}`);
  });

  const staleA = harness.api.applyRosterFilter("filter-a");
  for (let index = 0; index < 20 && filterALookups === 0; index += 1) {
    await Promise.resolve();
  }
  assert.equal(filterALookups, 1);

  const newerB = harness.api.applyRosterFilter("filter-b");
  assert.equal(firstLiveSignal.aborted, true);
  assert.equal(await newerB, true);
  assert.equal(harness.api.state.rosterFilter, "filter-b");
  assert.equal(harness.api.state.rosterFilterCommitted, "filter-b");
  assert.equal(harness.node("roster-search-slug").value, "filter-b");
  assert.equal(harness.api.state.roster[0].agent_slug, "filter-b");

  staleLive.resolve(jsonResponse(200, {
    revision: "filter-a-live",
    schema_version: 1,
  }));
  assert.equal(await staleA, false);
  assert.equal(harness.api.state.rosterFilter, "filter-b");
  assert.equal(harness.api.state.rosterFilterCommitted, "filter-b");
  assert.equal(harness.node("roster-search-slug").value, "filter-b");
  assert.equal(harness.api.state.roster[0].agent_slug, "filter-b");
});

test("a failed current roster search restores committed data instead of a pending intent", async () => {
  const staleLive = deferred();
  let liveCalls = 0;
  let filterALookups = 0;
  const harness = createAppHarness((path) => {
    if (path === "/api/live?limit=100") {
      liveCalls += 1;
      return liveCalls === 1
        ? staleLive.promise
        : Promise.resolve(jsonResponse(200, {
          revision: "filter-b-live",
          schema_version: 1,
        }));
    }
    if (path === "/api/control") {
      return Promise.resolve(jsonResponse(200, controlSnapshot()));
    }
    if (path === "/api/agents/lookup?slug=filter-a") {
      filterALookups += 1;
      return Promise.resolve(jsonResponse(200, {
        ...emptyRosterPage("filter-a-revision"),
        agents: [{ agent_slug: "filter-a", capabilities: [], enabled: true }],
        filter_slug: "filter-a",
      }));
    }
    if (path === "/api/agents/lookup?slug=filter-b") {
      return Promise.resolve(jsonResponse(503, { error: "filter B unavailable" }));
    }
    throw new Error(`unexpected committed-filter race path ${path}`);
  });
  harness.api.state.rosterFilter = "filter-c";
  harness.api.state.rosterFilterCommitted = "filter-c";
  harness.api.state.roster = [{ agent_slug: "filter-c", capabilities: [], enabled: true }];
  harness.api.state.rosterPage = {
    count: 1,
    disabled_count: 0,
    enabled_count: 1,
    next_cursor: null,
    total_count: 1,
    truncated: false,
  };
  harness.node("roster-search-slug").value = "filter-c";

  const staleA = harness.api.applyRosterFilter("filter-a");
  for (let index = 0; index < 20 && filterALookups === 0; index += 1) {
    await Promise.resolve();
  }
  assert.equal(filterALookups, 1);

  assert.equal(await harness.api.applyRosterFilter("filter-b"), false);
  assert.equal(harness.api.state.rosterFilter, "filter-c");
  assert.equal(harness.api.state.rosterFilterCommitted, "filter-c");
  assert.equal(harness.node("roster-search-slug").value, "filter-c");
  assert.equal(harness.api.state.roster[0].agent_slug, "filter-c");

  staleLive.resolve(jsonResponse(200, {
    revision: "filter-a-live",
    schema_version: 1,
  }));
  assert.equal(await staleA, false);
  assert.equal(harness.api.state.rosterFilter, "filter-c");
  assert.equal(harness.api.state.rosterFilterCommitted, "filter-c");
  assert.equal(harness.node("roster-search-slug").value, "filter-c");
  assert.equal(harness.api.state.roster[0].agent_slug, "filter-c");
});

test("operational roster intent supersedes a pending exact search in either response order", async () => {
  for (const responseOrder of ["exact-first", "operational-first"]) {
    const staleLive = deferred();
    const operationalPage = deferred();
    let filterALookups = 0;
    const harness = createAppHarness((path) => {
      if (path === "/api/live?limit=100") return staleLive.promise;
      if (path === "/api/control") {
        return Promise.resolve(jsonResponse(200, controlSnapshot()));
      }
      if (path === "/api/agents/lookup?slug=filter-a") {
        filterALookups += 1;
        return Promise.resolve(jsonResponse(200, {
          ...emptyRosterPage("filter-a-revision"),
          agents: [{ agent_slug: "filter-a", capabilities: [], enabled: true }],
          filter_slug: "filter-a",
        }));
      }
      if (path === "/api/roster/operations?limit=100") return operationalPage.promise;
      throw new Error(`unexpected operational-filter race path ${path}`);
    });
    harness.api.state.rosterFilter = "filter-c";
    harness.api.state.rosterFilterCommitted = "filter-c";
    harness.api.state.roster = [{ agent_slug: "filter-c", capabilities: [], enabled: true }];
    harness.node("roster-search-slug").value = "filter-c";

    const staleA = harness.api.applyRosterFilter("filter-a");
    for (let index = 0; index < 20 && filterALookups === 0; index += 1) {
      await Promise.resolve();
    }
    assert.equal(filterALookups, 1, responseOrder);

    const newerOperational = harness.api.applyOperationalFilters();
    assert.equal(harness.api.state.rosterFilter, "filter-c", responseOrder);
    assert.equal(harness.node("roster-search-slug").value, "filter-c", responseOrder);
    if (responseOrder === "exact-first") {
      staleLive.resolve(jsonResponse(200, {
        revision: "filter-a-live",
        schema_version: 1,
      }));
      assert.equal(await staleA, false, responseOrder);
      operationalPage.resolve(jsonResponse(200, {
        agents: [{ agent_slug: "operational-b", capabilities: [], enabled: true }],
        config_revision: "test-config-revision",
        next_cursor: null,
        roster_revision: "operational-b-revision",
        truncated: false,
      }));
      assert.equal(await newerOperational, true, responseOrder);
    } else {
      operationalPage.resolve(jsonResponse(200, {
        agents: [{ agent_slug: "operational-b", capabilities: [], enabled: true }],
        config_revision: "test-config-revision",
        next_cursor: null,
        roster_revision: "operational-b-revision",
        truncated: false,
      }));
      assert.equal(await newerOperational, true, responseOrder);
      staleLive.resolve(jsonResponse(200, {
        revision: "filter-a-live",
        schema_version: 1,
      }));
      assert.equal(await staleA, false, responseOrder);
    }

    assert.equal(harness.api.state.rosterFilter, "", responseOrder);
    assert.equal(harness.api.state.rosterFilterCommitted, "", responseOrder);
    assert.equal(harness.node("roster-search-slug").value, "", responseOrder);
    assert.equal(
      harness.api.state.rosterOperations.agents[0].agent_slug,
      "operational-b",
      responseOrder,
    );
  }
});

test("a failed operational roster intent restores the committed exact roster", async () => {
  const staleLive = deferred();
  const operationalPage = deferred();
  let filterALookups = 0;
  const harness = createAppHarness((path) => {
    if (path === "/api/live?limit=100") return staleLive.promise;
    if (path === "/api/control") {
      return Promise.resolve(jsonResponse(200, controlSnapshot()));
    }
    if (path === "/api/agents/lookup?slug=filter-a") {
      filterALookups += 1;
      return Promise.resolve(jsonResponse(200, {
        ...emptyRosterPage("filter-a-revision"),
        agents: [{ agent_slug: "filter-a", capabilities: [], enabled: true }],
        filter_slug: "filter-a",
      }));
    }
    if (path === "/api/roster/operations?limit=100") return operationalPage.promise;
    throw new Error(`unexpected failed-operational-filter path ${path}`);
  });
  harness.api.state.rosterFilter = "filter-c";
  harness.api.state.rosterFilterCommitted = "filter-c";
  harness.api.state.roster = [{ agent_slug: "filter-c", capabilities: [], enabled: true }];
  harness.node("roster-search-slug").value = "filter-c";

  const staleA = harness.api.applyRosterFilter("filter-a");
  for (let index = 0; index < 20 && filterALookups === 0; index += 1) {
    await Promise.resolve();
  }
  assert.equal(filterALookups, 1);

  const failedOperational = harness.api.applyOperationalFilters();
  assert.equal(harness.api.state.rosterFilter, "filter-c");
  operationalPage.resolve(jsonResponse(503, { error: "operational B unavailable" }));
  assert.equal(await failedOperational, false);
  assert.equal(harness.api.state.rosterFilter, "filter-c");
  assert.equal(harness.api.state.rosterFilterCommitted, "filter-c");
  assert.equal(harness.node("roster-search-slug").value, "filter-c");
  assert.equal(harness.api.state.roster[0].agent_slug, "filter-c");

  staleLive.resolve(jsonResponse(200, {
    revision: "filter-a-live",
    schema_version: 1,
  }));
  assert.equal(await staleA, false);
  assert.equal(harness.api.state.rosterFilter, "filter-c");
  assert.equal(harness.api.state.rosterFilterCommitted, "filter-c");
  assert.equal(harness.node("roster-search-slug").value, "filter-c");
  assert.equal(harness.api.state.roster[0].agent_slug, "filter-c");
});

test("same-revision live snapshots render only when master state changes visibly", () => {
  const harness = createAppHarness(() => {
    throw new Error("same-revision rendering does not fetch");
  });
  harness.api.state.live.revision = "same-revision";
  harness.api.state.overview = { status: "ok", recent: {} };
  harness.api.applyMasterState({ enabled: true, generation: 1 });

  assert.equal(harness.api.applyLiveSnapshot({
    schema_version: 1,
    revision: "same-revision",
    sampled_at: "2026-07-16T12:00:00Z",
    overview: {},
    activity: {},
    master: { enabled: false, generation: 2 },
  }), true);
  assert.equal(harness.node("master-label").textContent, "Agency off");

  assert.equal(harness.api.applyLiveSnapshot({
    schema_version: 1,
    revision: "same-revision",
    sampled_at: "2026-07-16T12:00:01Z",
    overview: {},
    activity: {},
    master: { enabled: true, generation: 3 },
  }, { render: false }), true);
  assert.equal(harness.api.state.master.enabled, true);
});

test("Route Lab reconciles a server-side master bypass without rendering a receipt", async () => {
  for (const message of ["Agency was disabled concurrently.", ""]) {
    const disabledMaster = {
      schema_version: 1,
      enabled: false,
      generation: 2,
      updated_at: "2026-07-16T12:00:00Z",
      source: "dashboard",
    };
    const harness = createAppHarness(async (path) => {
      assert.equal(path, "/api/route");
      return jsonResponse(200, {
        bypassed: true,
        master: disabledMaster,
        message,
        status: "disabled",
      });
    });
    harness.api.applyMasterState({ ...disabledMaster, enabled: true, generation: 1 });
    harness.node("route-task").value = "Review this change";
    harness.node("route-host").value = "codex";

    await harness.api.runRoute();

    assert.equal(harness.api.state.master.enabled, false);
    assert.equal(harness.node("route-status").textContent, "BYPASSED");
    assert.match(
      harness.node("notice").textContent,
      message ? /disabled concurrently/i : /routing was bypassed/i,
    );
  }
});

test("Route Lab performs no request while Agency is globally bypassed", async () => {
  let calls = 0;
  const harness = createAppHarness(async () => {
    calls += 1;
    throw new Error("routing must not be requested");
  });
  harness.api.applyMasterState({
    schema_version: 1,
    enabled: false,
    generation: 3,
    updated_at: "2026-07-16T12:00:00Z",
    source: "dashboard",
  });
  harness.node("route-task").value = "Review this change";

  await harness.api.runRoute();

  assert.equal(calls, 0);
  assert.equal(harness.node("route-status").textContent, "BYPASSED");
  assert.match(harness.node("notice").textContent, /enable the master switch/i);
});

test("master control markup and motion treatment preserve accessibility", () => {
  const master = INDEX_SOURCE.match(/<button id="master-toggle"[^>]*>/)?.[0] || "";
  assert.match(master, /type="button"/);
  assert.match(master, /aria-label="Agency master state loading"/);
  assert.match(master, /data-state="loading"/);
  assert.match(master, /\sdisabled/);
  assert.doesNotMatch(master, /aria-pressed=/);
  assert.match(master, /aria-describedby="master-summary"/);
  const route = INDEX_SOURCE.match(/<button id="route-button"[^>]*>/)?.[0] || "";
  assert.match(route, /aria-disabled="true"/);
  assert.match(route, /\sdisabled/);
  assert.match(INDEX_SOURCE, /id="runtime-paused-banner"[^>]*role="status"[^>]*aria-live="polite"/);
  assert.match(APP_CSS_SOURCE, /\.master-control\[aria-pressed="false"\]/);
  assert.match(APP_CSS_SOURCE, /\.master-control\[data-state="loading"\]/);
  assert.match(APP_CSS_SOURCE, /\.agency-paused \.route-form/);
  assert.match(APP_CSS_SOURCE, /@media\s*\(prefers-reduced-motion:\s*reduce\)/);
});

test("operational dashboard renders governed roster, quarantine, and inference evidence", () => {
  const harness = createAppHarness(() => {
    throw new Error("render-only operational test does not fetch");
  });
  harness.node("roster-filter-division").value = "engineering";
  harness.node("roster-filter-authority").value = "obsolete";
  harness.missing("roster-filter-tool");
  harness.api.state.overview = {
    capture_content: false,
    db_size_bytes: 1,
    inference: {
      configured: true,
      failure_count: 2,
      provider_chain: [
        {
          order: 1,
          name: "production-router",
          type: "litellm",
          requested_model: "balanced",
          router: "balanced-group",
          configuration_ready: true,
          observed_receipt: {
            actual_provider: "anthropic",
            actual_model: "claude-production",
          },
        },
        {
          order: 2,
          name: "direct-fallback",
          configuration_ready: false,
          observed_receipt: {},
        },
      ],
      recent_failures: [
        {
          kind: "model_receipt",
          requested_model: "balanced",
          router: "balanced-group",
          actual_provider: "anthropic",
          actual_model: "claude-production",
          status: "failed",
          recorded_at: isoBefore(1_000),
        },
        {
          kind: "routing",
          provider: "production-router",
          status: "degraded",
          trace_id: "trace-safe",
          created_at: isoBefore(2_000),
        },
        {
          kind: "preflight_failure",
          status: "preflight_failed",
          stage: "routing",
          reason_code: "workforce_inference_failed",
          invariant_code: "native_plan_scope_invalid",
          exception_category: "timeout",
          provider_attempts: [{ status: "failed" }],
          staffing_reason_codes: ["selected_agent_budget_exceeded"],
          hiring_reason_codes: ["gap_evidence_not_hireable"],
          host: "codex",
          trace_id: "trace-preflight",
          recorded_at: isoBefore(3_000),
        },
        { kind: "model_receipt" },
        { kind: "routing" },
      ],
      state: "degraded",
    },
    provider_health: [],
    recent: {},
    retention_days: 30,
    roster_count: 2,
    status: "ok",
    wal_size_bytes: 0,
  };
  harness.api.renderOverview();
  assert.equal(harness.node("inference-state").textContent, "DEGRADED");
  assert.equal(harness.node("provider-failure-count").textContent, "2");
  const providerText = descendants(harness.node("provider-health"))
    .map((node) => node.textContent).join(" ");
  assert.match(providerText, /Router \/ model group: balanced-group/);
  assert.match(providerText, /Observed actual: anthropic \/ claude-production/);
  assert.match(providerText, /config gap/);
  const failureText = descendants(harness.node("provider-failures"))
    .map((node) => node.textContent).join(" ");
  assert.match(failureText, /Actual: anthropic \/ claude-production/);
  assert.match(failureText, /Trace: trace-safe/);
  assert.match(failureText, /routing · workforce_inference_failed/);
  assert.match(failureText, /Host: codex · timeout/);
  assert.match(failureText, /Trace: trace-preflight · 1 provider attempt/);
  assert.match(failureText, /Staffing: selected_agent_budget_exceeded/);
  assert.match(failureText, /Hiring: gap_evidence_not_hireable/);
  assert.match(failureText, /unidentified model · failed/);
  assert.match(failureText, /routing inference · degraded/);

  harness.api.state.overview.inference = {
    configured: true,
    provider_chain: [],
    recent_failures: [],
    state: "unknown",
  };
  harness.api.renderOverview();
  assert.match(
    harness.node("provider-health").children[0].textContent,
    /configured inference has no provider-chain projection/i,
  );

  harness.api.state.rosterFilters = { host: "codex" };
  harness.api.state.rosterOperations = {
    agents: [
      {
        agent_slug: "security-reviewer",
        name: "Security Reviewer",
        division: "engineering",
        capabilities: ["security"],
        enabled: true,
        authority: "review",
        audit_status: "approved",
        source_revision: "source-2",
        source_content_hash: "source-hash",
        audit_revision: "audit-2",
        context_mode: "isolated_only",
        supported_hosts: ["codex"],
        supported_platforms: ["windows", "linux"],
        required_tools: ["git"],
        conflicts_with: ["unsafe-agent"],
        requires: ["chief-of-staff"],
        revision_history: [{
          version: "2.0.0",
          audit_status: "approved",
          created_at: isoBefore(3_000),
        }],
      },
      {
        agent_slug: "plain-agent",
        capabilities: [],
        enabled: false,
      },
      {
        agent_slug: "sparse-audited-agent",
        capabilities: [],
        enabled: true,
        audit_status: "failed",
        content_hash: "fallback-content-hash",
      },
      {
        agent_slug: "sparse-history-agent",
        capabilities: [],
        enabled: true,
        authority: "advise",
        revision_history: [{}],
      },
    ],
    count: 4,
    matched_count: 4,
    total_count: 4,
    enabled_count: 3,
    truncated: false,
    facets: {
      divisions: ["engineering"],
      capabilities: ["security"],
      authorities: ["review"],
      hosts: ["codex"],
      platforms: ["linux", "windows"],
      tools: ["git"],
    },
  };
  harness.api.state.rosterReview = {
    queue_count: 3,
    upstream: {
      packaged_source_revision: "upstream-42",
      remote_freshness: "unverified",
      state: "review_pending",
    },
    candidates: [
      {
        candidate: {
          name: "Security Reviewer",
          slug: "security-reviewer",
          source_revision: "source-3",
          content_hash: "candidate-hash",
        },
        active: { source_revision: "source-2", content_hash: "active-hash" },
        change: "changed",
        changed_fields: ["capabilities"],
        latest_audit: {
          verdict: "passed",
          inference_status: "passed",
          findings: [{ severity: "warning", code: "review-change" }, {}],
        },
      },
      { candidate: {}, latest_audit: {}, changed_fields: [] },
      {},
    ],
    remediation_attempts: [
      {
        slug: "quarantined-specialist",
        created_at: "2026-07-11T11:58:00Z",
        receipt: {
          original_hash: "original-safe-hash",
          proposal_hash: "proposal-safe-hash",
          attempted_rule_ids: ["encoding-v1", "semantic-v1"],
          matched_rule_id: "encoding-v1",
          status: "proposal_pending_review",
          next_action: "review_deterministic_proposal_and_semantic_projection",
        },
      },
    ],
    remediation_history: [
      {
        slug: "repaired-specialist",
        original_hash: "raw-hash",
        candidate_hash: "candidate-hash",
        source_hash: "raw-hash",
        candidate_id: "candidate-42",
        resolution: "remediated_candidate",
        audit_policy_current: false,
        created_at: "2026-07-11T11:59:00Z",
      },
    ],
    remediation_count: 2,
    remediation_history_count: 3,
    remediation_stale_resolution_count: 1,
    remediation_unvalidated_resolution_count: 2,
    remediation_pending_has_more: true,
    remediation_history_has_more: true,
    next_remediation_pending_cursor: "pending-cursor",
    next_remediation_history_cursor: "history-cursor",
  };
  harness.api.renderRoster();
  assert.match(harness.node("roster-page-status").textContent, /active operational filters/i);
  assert.equal(harness.node("roster-filter-division").value, "engineering");
  assert.equal(harness.node("roster-filter-authority").value, "");
  const rosterText = descendants(harness.node("roster-grid"))
    .map((node) => node.textContent).join(" ");
  assert.match(rosterText, /Contract, compatibility & history/);
  assert.match(rosterText, /unsafe-agent/);
  assert.match(rosterText, /2\.0\.0/);
  const reviewText = descendants(harness.node("review-list"))
    .map((node) => node.textContent).join(" ");
  assert.match(reviewText, /Candidate revision/);
  assert.match(reviewText, /warning · review-change/);
  assert.match(reviewText, /unknown · finding/);
  assert.match(reviewText, /No audit findings recorded/);
  assert.match(reviewText, /quarantined-specialist/);
  assert.match(reviewText, /remediation attempt · non-executable/);
  assert.match(reviewText, /original-safe-hash/);
  assert.match(reviewText, /proposal-safe-hash/);
  assert.match(reviewText, /encoding-v1, semantic-v1/);
  assert.match(reviewText, /review_deterministic_proposal_and_semantic_projection/);
  assert.match(reviewText, /2026-07-11T11:58:00Z/);
  assert.match(reviewText, /cannot activate an agent/);
  assert.match(reviewText, /repaired-specialist/);
  assert.match(reviewText, /repair provenance · immutable history/);
  assert.match(reviewText, /historical policy/);
  assert.equal(harness.node("review-count").textContent, "3");
  assert.match(harness.node("review-page-status").textContent, /1 of 2 pending repairs/);
  assert.match(harness.node("review-page-status").textContent, /1 of 3 resolved repairs/);
  assert.match(
    harness.node("review-page-status").textContent,
    /1 stale signed resolution was reopened for review/,
  );
  assert.match(
    harness.node("review-page-status").textContent,
    /2 unvalidated resolution records remain quarantined/,
  );
  assert.equal(
    harness.node("review-page-status").dataset.unvalidatedResolutionCount,
    "2",
  );
  assert.equal(harness.node("review-page-status").dataset.staleResolutionCount, "1");
  assert.equal(harness.node("review-page-status").classList.contains("failed"), true);
  assert.equal(harness.node("review-pending-more").hidden, false);
  assert.equal(harness.node("review-history-more").hidden, false);
  const [remediationCard] = descendants(harness.node("review-list"))
    .filter((node) => node.className.includes("remediation-card"));
  assert.equal(
    remediationCard.getAttribute("aria-label"),
    "Remediation attempt for quarantined-specialist",
  );
  const [remediationGuard] = descendants(remediationCard)
    .filter((node) => node.className === "remediation-guard");
  assert.equal(remediationGuard.getAttribute("role"), "note");
  assert.match(harness.node("upstream-status").textContent, /upstream-42/);

  harness.api.state.rosterFilters = null;
  harness.api.renderRoster();
  harness.api.state.rosterFilters = { host: "codex" };
  delete harness.api.state.rosterOperations.matched_count;
  harness.api.state.rosterReview.upstream = { packaged_source_revision: "upstream-minimal" };
  harness.api.renderRoster();
  assert.match(harness.node("roster-page-status").textContent, /showing 4 of 4 specialists/i);
  assert.match(harness.node("upstream-status").textContent, /remote freshness unverified/i);
  assert.match(harness.node("upstream-status").textContent, /status unknown/i);

  harness.api.state.rosterReview = {
    candidates: [],
    remediation_attempts: [{
      slug: "unknown-remediation",
      receipt: { attempted_rule_ids: [] },
    }, {}],
  };
  harness.api.renderRoster();
  assert.equal(harness.node("review-count").textContent, "2");
  const remediationOnlyText = descendants(harness.node("review-list"))
    .map((node) => node.textContent).join(" ");
  assert.match(remediationOnlyText, /unknown-remediation/);
  assert.match(remediationOnlyText, /none generated/);
  assert.match(remediationOnlyText, /manual review required/);
  assert.doesNotMatch(remediationOnlyText, /No candidates .* await review/);

  harness.api.state.rosterReview = { candidates: [], remediation_attempts: [] };
  harness.api.renderRoster();
  assert.equal(harness.node("review-count").textContent, "0");
  assert.equal(
    harness.node("review-list").children[0].textContent,
    "No candidates, remediation attempts, or repair history are available.",
  );

  harness.api.state.rosterFilter = "exact-agent";
  harness.api.state.roster = [{ agent_slug: "exact-agent", capabilities: [] }];
  harness.api.state.rosterPage = {
    count: 1, total_count: 1, enabled_count: 1, truncated: false,
  };
  harness.api.renderRoster();
  assert.equal(harness.node("roster-filter-division").children.length, 2);

  const optional = createAppHarness(() => {
    throw new Error("optional review nodes do not fetch");
  });
  optional.missing("review-list");
  optional.missing("upstream-status");
  optional.missing("inference-state");
  optional.missing("provider-failure-count");
  optional.missing("provider-failures");
  optional.api.state.overview = {
    inference: { provider_chain: [], recent_failures: [] },
    provider_health: [], recent: {}, status: "ok",
  };
  optional.api.renderOverview();
  optional.api.renderRoster();
});

test("remediation queue controls page pending and history independently", async () => {
  const calls = [];
  const harness = createAppHarness(async (path) => {
    calls.push(path);
    if (path.includes("history_cursor")) {
      return jsonResponse(200, {
        remediation_revision: "remediation-revision-1",
        remediation_attempts: [],
        remediation_history: [{ event_id: "history-2", slug: "second-resolution" }],
        remediation_unvalidated_resolution_count: 0,
        remediation_pending_has_more: false,
        remediation_history_has_more: false,
        next_remediation_pending_cursor: "",
        next_remediation_history_cursor: "",
      });
    }
    return jsonResponse(200, {
      remediation_revision: "remediation-revision-1",
      remediation_attempts: [{
        event_id: "pending-2",
        slug: "second-repair",
        receipt: { attempted_rule_ids: [] },
      }],
      remediation_history: [],
      remediation_unvalidated_resolution_count: 1,
      remediation_pending_has_more: false,
      remediation_history_has_more: true,
      next_remediation_pending_cursor: "",
      next_remediation_history_cursor: "history-1",
    });
  });
  harness.api.state.rosterReview = {
    remediation_revision: "remediation-revision-1",
    candidates: [],
    remediation_attempts: [{
      event_id: "pending-1",
      slug: "first-repair",
      receipt: { attempted_rule_ids: [] },
    }],
    remediation_history: [{ event_id: "history-1", slug: "resolved-repair" }],
    remediation_count: 2,
    remediation_history_count: 2,
    remediation_unvalidated_resolution_count: 0,
    remediation_pending_has_more: true,
    remediation_history_has_more: true,
    next_remediation_pending_cursor: "pending-1",
    next_remediation_history_cursor: "history-1",
    limit: 1,
  };

  harness.api.bindEvents();
  assert.equal(
    await harness.node("review-pending-more").listeners.get("click")[0](),
    true,
  );
  assert.equal(
    calls[0],
    "/api/roster/reviews?limit=1&pending_cursor=pending-1",
  );
  assert.deepEqual(
    harness.api.state.rosterReview.remediation_attempts.map((item) => item.event_id),
    ["pending-1", "pending-2"],
  );
  assert.equal(harness.api.state.rosterReview.remediation_history.length, 1);
  assert.equal(
    harness.api.state.rosterReview.remediation_unvalidated_resolution_count,
    1,
  );
  assert.equal(harness.node("review-pending-more").hidden, true);
  assert.equal(harness.node("review-history-more").hidden, false);
  assert.equal(
    await harness.node("review-history-more").listeners.get("click")[0](),
    true,
  );
  assert.equal(
    calls[1],
    "/api/roster/reviews?limit=1&history_cursor=history-1",
  );
  assert.deepEqual(
    harness.api.state.rosterReview.remediation_history.map((item) => item.event_id),
    ["history-1", "history-2"],
  );
  assert.equal(harness.api.state.rosterReview.remediation_history_has_more, false);
  await assert.rejects(
    harness.api.loadMoreRemediation("unknown"),
    /must be pending or history/,
  );

  const failed = createAppHarness(async () => jsonResponse(503, { error: "review unavailable" }));
  failed.api.state.rosterReview = {
    remediation_attempts: [],
    next_remediation_pending_cursor: "pending-error",
    limit: 1,
  };
  assert.equal(await failed.api.loadMoreRemediation("pending"), false);
  assert.match(failed.node("notice").textContent, /review unavailable/);

  const empty = createAppHarness(() => {
    throw new Error("empty remediation pages do not fetch");
  });
  empty.api.state.rosterReview = null;
  assert.equal(await empty.api.loadMoreRemediation("pending"), false);
  empty.api.state.lifecycle.suspended = true;
  assert.equal(await empty.api.loadMoreRemediation("pending"), false);

  const lateResponse = deferred();
  const late = createAppHarness(async () => lateResponse.promise);
  late.api.state.rosterReview = {
    remediation_attempts: [],
    next_remediation_pending_cursor: "pending-late",
  };
  const latePage = late.api.loadMoreRemediation("pending");
  await Promise.resolve();
  late.api.state.lifecycle.suspended = true;
  lateResponse.resolve(jsonResponse(200, { remediation_attempts: [] }));
  assert.equal(await latePage, false);

  const malformed = createAppHarness(async () => jsonResponse(200, {
    remediation_revision: "remediation-malformed",
    remediation_attempts: "invalid",
    remediation_unvalidated_resolution_count: "invalid",
    next_remediation_pending_cursor: null,
  }));
  malformed.api.state.rosterReview = {
    remediation_revision: "remediation-malformed",
    remediation_attempts: "invalid",
    remediation_unvalidated_resolution_count: 4,
    next_remediation_pending_cursor: "pending-malformed",
  };
  assert.equal(await malformed.api.loadMoreRemediation("pending"), true);
  assert.deepEqual(malformed.api.state.rosterReview.remediation_attempts, []);
  assert.equal(
    malformed.api.state.rosterReview.remediation_unvalidated_resolution_count,
    4,
  );

  const changed = createAppHarness(async () => jsonResponse(200, {
    remediation_revision: "remediation-new",
    remediation_attempts: [{ event_id: "pending-new" }],
    next_remediation_pending_cursor: "",
  }));
  changed.api.state.rosterReview = {
    remediation_revision: "remediation-old",
    remediation_attempts: [{ event_id: "pending-old" }],
    next_remediation_pending_cursor: "pending-old",
  };
  assert.equal(await changed.api.loadMoreRemediation("pending"), false);
  assert.deepEqual(
    changed.api.state.rosterReview.remediation_attempts.map((item) => item.event_id),
    ["pending-old"],
  );
  assert.match(changed.node("notice").textContent, /collection changed/);

  const optional = createAppHarness(() => {
    throw new Error("optional remediation controls do not fetch");
  });
  optional.missing("review-history-more");
  optional.api.state.rosterReview = {
    candidates: [],
    remediation_attempts: [],
    remediation_history: [{}],
    remediation_pending_has_more: false,
    remediation_history_has_more: true,
    next_remediation_history_cursor: "history-optional",
  };
  optional.api.renderRoster();
  assert.match(
    descendants(optional.node("review-list")).map((node) => node.textContent).join(" "),
    /unknown/,
  );
});

test("queued control refresh preserves the remediation extent already loaded by the operator", async () => {
  const firstReviewPage = {
    candidates: [],
    collection_revision: "review-revision-1",
    remediation_revision: "remediation-revision-1",
    limit: 1,
    next_cursor: null,
    next_remediation_history_cursor: "",
    next_remediation_pending_cursor: "pending-1",
    remediation_attempts: [{ event_id: "pending-1", slug: "first-repair" }],
    remediation_history: [],
    remediation_history_has_more: false,
    remediation_pending_has_more: true,
    truncated: false,
  };
  const snapshot = controlSnapshot({ governance: {
    operations: { agents: [] },
    reviews: firstReviewPage,
    snapshots: [],
  } });
  const harness = createAppHarness(async (path) => {
    if (path.includes("pending_cursor")) {
      return jsonResponse(200, {
        remediation_revision: "remediation-revision-1",
        remediation_attempts: [{ event_id: "pending-2", slug: "second-repair" }],
        remediation_history: [],
        remediation_history_has_more: false,
        remediation_pending_has_more: false,
        next_remediation_history_cursor: "",
        next_remediation_pending_cursor: "",
      });
    }
    if (path === "/api/control") return jsonResponse(200, snapshot);
    throw new Error(`unexpected remediation extent path ${path}`);
  });
  harness.api.state.rosterReview = structuredClone(firstReviewPage);

  assert.equal(await harness.api.loadMoreRemediation("pending"), true);
  assert.deepEqual(
    harness.api.state.rosterReview.remediation_attempts.map((item) => item.event_id),
    ["pending-1", "pending-2"],
  );
  const scheduled = [...harness.timers.tasks.entries()]
    .find(([, task]) => task.delay === 0);
  assert.ok(scheduled);
  harness.timers.tasks.delete(scheduled[0]);
  await scheduled[1].callback();

  assert.deepEqual(
    harness.api.state.rosterReview.remediation_attempts.map((item) => item.event_id),
    ["pending-1", "pending-2"],
  );
  assert.equal(harness.api.state.rosterReview.next_remediation_pending_cursor, "");
  assert.equal(harness.api.state.rosterReview.remediation_pending_has_more, false);
});

test("automatic review refresh invalidates stale paged history when a repair reopens", async () => {
  const firstReviewPage = {
    candidates: [],
    collection_revision: "review-revision-1",
    remediation_revision: "remediation-revision-before-reopen",
    limit: 1,
    next_cursor: null,
    next_remediation_history_cursor: "history-current",
    next_remediation_pending_cursor: "",
    remediation_attempts: [],
    remediation_history: [{
      event_id: "history-current",
      queue_event_id: "queue-current",
      slug: "current-resolution",
    }],
    remediation_history_count: 2,
    remediation_history_has_more: true,
    remediation_pending_has_more: false,
    truncated: false,
  };
  const refreshedReviewPage = {
    ...firstReviewPage,
    remediation_revision: "remediation-revision-after-reopen",
    next_remediation_history_cursor: "",
    remediation_attempts: [{
      event_id: "queue-reopened",
      slug: "reopened-repair",
      receipt: { attempted_rule_ids: [] },
    }],
    remediation_count: 1,
    remediation_history: [firstReviewPage.remediation_history[0]],
    remediation_history_count: 1,
    remediation_history_has_more: false,
  };
  const snapshot = controlSnapshot({ governance: {
    operations: { agents: [] },
    reviews: refreshedReviewPage,
    snapshots: [],
  } });
  const harness = createAppHarness(async (path) => {
    if (path.includes("history_cursor")) {
      return jsonResponse(200, {
        remediation_revision: "remediation-revision-before-reopen",
        remediation_attempts: [],
        remediation_history: [{
          event_id: "history-reopened",
          queue_event_id: "queue-reopened",
          slug: "reopened-repair",
        }],
        remediation_history_has_more: false,
        remediation_pending_has_more: false,
        next_remediation_history_cursor: "",
        next_remediation_pending_cursor: "",
      });
    }
    if (path === "/api/control") return jsonResponse(200, snapshot);
    throw new Error(`unexpected remediation invalidation path ${path}`);
  });
  harness.api.state.rosterReview = structuredClone(firstReviewPage);

  assert.equal(await harness.api.loadMoreRemediation("history"), true);
  assert.deepEqual(
    harness.api.state.rosterReview.remediation_history.map((item) => item.event_id),
    ["history-current", "history-reopened"],
  );
  harness.api.applyGovernanceSnapshot({
    operations: { agents: [] },
    reviews: structuredClone(refreshedReviewPage),
    snapshots: [],
  });
  harness.api.renderRoster();

  assert.deepEqual(
    harness.api.state.rosterReview.remediation_attempts.map((item) => item.event_id),
    ["queue-reopened"],
  );
  assert.deepEqual(
    harness.api.state.rosterReview.remediation_history.map((item) => item.event_id),
    ["history-current"],
  );
  const rendered = descendants(harness.node("review-list"))
    .map((node) => node.textContent)
    .join(" ");
  assert.match(rendered, /reopened-repair remediation attempt/);
  assert.doesNotMatch(rendered, /reopened-repair repair provenance/);

  harness.api.state.rosterReview.remediation_history.push({
    event_id: "history-corrupt-overlap",
    queue_event_id: "queue-reopened",
    slug: "reopened-repair",
  });
  harness.api.renderRoster();
  assert.equal(harness.node("review-page-status").dataset.remediationOverlapCount, "1");
  assert.match(harness.node("review-page-status").textContent, /conflicting history row was suppressed/);
});

test("operational roster filters are bounded, reversible, and lifecycle safe", async () => {
  const calls = [];
  const response = {
    agents: [], count: 0, matched_count: 0, total_count: 0, enabled_count: 0,
    config_revision: "test-config-revision",
    next_cursor: null, roster_revision: "filtered-roster-revision",
    truncated: false, facets: {},
  };
  const harness = createAppHarness(async (path) => {
    calls.push(path);
    return jsonResponse(200, response);
  });
  harness.node("roster-filter-query").value = "  secure review  ";
  harness.node("roster-filter-host").value = "codex";
  harness.missing("roster-filter-tool");
  let prevented = false;
  assert.equal(await harness.api.applyOperationalFilters({
    preventDefault() { prevented = true; },
  }), true);
  assert.equal(prevented, true);
  assert.equal(calls[0], "/api/roster/operations?limit=100&query=secure+review&host=codex");
  assert.deepEqual(harness.api.state.rosterFilters, { query: "secure review", host: "codex" });
  assert.equal(harness.api.operationalRosterPath({ platform: "linux" }), "/api/roster/operations?limit=100&platform=linux");

  assert.equal(await harness.api.clearOperationalFilters(), true);
  assert.equal(harness.node("roster-filter-query").value, "");
  assert.equal(harness.node("roster-filter-host").value, "");
  assert.equal(calls.at(-1), "/api/roster/operations?limit=100");
  assert.deepEqual(harness.api.applyGovernanceSnapshot({
    snapshots: [{ snapshot_id: "safe" }], operations: response, reviews: { candidates: [] },
  }), {
    snapshots: [{ snapshot_id: "safe" }], operations: response, reviews: { candidates: [] },
  });
  assert.deepEqual(harness.api.applyGovernanceSnapshot({ snapshots: "invalid" }).snapshots, []);

  harness.api.state.serviceBinding = { store_restart_required: true };
  assert.equal(await harness.api.applyOperationalFilters(), false);
  assert.match(harness.node("notice").textContent, /restart the dashboard service/i);
  harness.api.state.serviceBinding = { store_restart_required: false };
  harness.api.state.lifecycle.destroyed = true;
  assert.equal(await harness.api.applyOperationalFilters(), false);
  harness.api.state.lifecycle.destroyed = false;
  harness.api.state.lifecycle.suspended = true;
  assert.equal(await harness.api.applyOperationalFilters(), false);

  const pending = deferred();
  const late = createAppHarness(() => pending.promise);
  const applying = late.api.applyOperationalFilters();
  late.api.state.lifecycle.suspended = true;
  pending.resolve(jsonResponse(200, response));
  assert.equal(await applying, false);

  const failed = createAppHarness(async () => jsonResponse(503, { error: "filter unavailable" }));
  assert.equal(await failed.api.applyOperationalFilters(), false);
  assert.match(failed.node("notice").textContent, /filter unavailable/i);
});

test("operational dashboard markup and accessibility policies stay discoverable", () => {
  for (const id of [
    "inference-state", "provider-failures", "roster-operations-form",
    "roster-filter-division", "roster-filter-capability", "roster-filter-authority",
    "roster-filter-host", "roster-filter-platform", "roster-filter-tool",
    "review-list", "upstream-status", "hiring-filter-type",
    "hiring-approver-identity", "hiring-approver-help",
  ]) assert.match(INDEX_SOURCE, new RegExp(`id="${id}"`));
  for (const path of [
    "workforce.mode", "workforce.provider",
    "workforce.max_work_units", "workforce.max_selected_per_unit",
    "workforce.max_selected_total", "workforce.max_hires_per_turn",
    "workforce.daily_hire_alert_threshold", "workforce.hiring_repair_budget",
    "workforce.amend_overlap_threshold", "workforce.auto_promote_successes",
  ]) assert.match(INDEX_SOURCE, new RegExp(`data-config-path="${path.replaceAll(".", "\\.")}"`));
  for (const retiredPath of [
    "workforce.planner_model", "workforce.recruiter_model",
    "workforce.hiring_model", "workforce.critic_model",
    "workforce.max_hires_per_task", "workforce.max_hires_per_day",
  ]) assert.doesNotMatch(
    INDEX_SOURCE,
    new RegExp(`data-config-path="${retiredPath.replaceAll(".", "\\.")}"`),
  );
  for (const retiredId of [
    "workforce-model-options", "workforce-model-refresh", "workforce-model-status",
  ]) assert.doesNotMatch(INDEX_SOURCE, new RegExp(`id="${retiredId}"`));
  assert.match(INDEX_SOURCE, /<label for="config-workforce-provider">Fallback provider<\/label>/);
  assert.match(
    INDEX_SOURCE,
    /id="config-workforce-max-units"[^>]*min="1"[^>]*max="16"/,
  );
  assert.match(INDEX_SOURCE, /Inference accepts at most 16 staffing needs per request/i);
  assert.match(INDEX_SOURCE, /INFERENCE \+ VERIFICATION/);
  assert.doesNotMatch(INDEX_SOURCE, /DETERMINISTIC \+ JUDGE/);
  assert.match(INDEX_SOURCE, /bounded delegation-event rows/i);
  assert.doesNotMatch(INDEX_SOURCE, /recorded host-native child events|recorded native-child/i);
  assert.match(
    INDEX_SOURCE,
    /id="hiring-approver-identity"[^>]*maxlength="128"[^>]*aria-describedby="hiring-approver-help"/,
  );
  assert.match(INDEX_SOURCE, /Dashboard authentication proves authority, not human identity/i);
  assert.match(APP_CSS_SOURCE, /\.roster-filter-grid/);
  assert.match(APP_CSS_SOURCE, /\.review-card/);
  assert.match(APP_CSS_SOURCE, /\.remediation-card/);
  assert.match(APP_CSS_SOURCE, /\.remediation-guard/);
  assert.match(APP_CSS_SOURCE, /\.provider-chain-row/);
  assert.match(APP_CSS_SOURCE, /\.update-banner/);
  assert.match(APP_CSS_SOURCE, /@media\s*\(forced-colors:\s*active\)/);
  assert.match(APP_CSS_SOURCE, /@media\s*\(prefers-reduced-motion:\s*reduce\)/);
});

function updateContractPayload() {
  const installed = {
    package_version: "0.1.0", build_identity: `0.1.0+g${"a".repeat(12)}`,
    source_revision: "a".repeat(40), source_branch: "main", source_dirty: false,
    install_kind: "source-checkout", official_repository: true,
  };
  return {
    schema_version: "agency.dashboard.update.v1",
    installed,
    release: {
      schema_version: "agency.update.v1", installed,
      selector: { kind: "channel", value: "release", ref: "latest", key: "channel:release" },
      checked: true, cache_hit: true, stale: false, checking: false,
      checked_at: "1970-01-01T00:16:40+00:00",
      status: "update_available", update_available: true, error: null,
      command: "agency upgrade --channel release",
      target: {
        kind: "release", label: "v0.2.0", version: "0.2.0", ref: "v0.2.0",
        commit_sha: "b".repeat(40), published_at: "2026-07-28T00:00:00Z",
        url: "https://github.com/Holeshot-Software-LLC/agency-runtime/releases/tag/v0.2.0",
      },
    },
    main: {
      schema_version: "agency.update.v1", installed,
      selector: { kind: "channel", value: "main", ref: "main", key: "channel:main" },
      checked: true, cache_hit: true, stale: false, checking: false,
      checked_at: "1970-01-01T00:16:40+00:00",
      status: "different_target", update_available: null, error: null,
      command: "agency upgrade --channel main",
      target: {
        kind: "main", label: "main", version: null, ref: "main",
        commit_sha: "c".repeat(40), published_at: null,
        url: `https://github.com/Holeshot-Software-LLC/agency-runtime/commit/${"c".repeat(40)}`,
      },
    },
    recommended: "release",
    checking: false,
  };
}

test("dashboard update surface traces authenticated status to a fixed attended command", async () => {
  const calls = [];
  const payload = updateContractPayload();
  const harness = createAppHarness(async (path) => {
    calls.push(path);
    return jsonResponse(200, payload);
  });

  assert.equal(await harness.api.refreshUpdateStatus(), true);
  assert.deepEqual(calls, ["/api/update"]);
  assert.equal(harness.node("update-banner").dataset.state, "available");
  assert.equal(harness.node("update-title").textContent, "Agency update available");
  assert.equal(harness.node("update-command").textContent, "agency upgrade --channel release");
  assert.equal(harness.node("update-copy-button").hidden, false);
  assert.equal(harness.node("update-link").href, payload.release.target.url);

  const copied = [];
  harness.context.window.navigator = { clipboard: { writeText: async (value) => copied.push(value) } };
  harness.api.bindEvents();
  await harness.node("update-copy-button").listeners.get("click")[0]();
  assert.deepEqual(copied, ["agency upgrade --channel release"]);
  assert.match(harness.node("notice").textContent, /owner-controlled terminal/);

  harness.context.window.navigator = {};
  await harness.node("update-copy-button").listeners.get("click")[0]();
  assert.match(harness.node("notice").textContent, /select the displayed command/i);

  harness.context.window.navigator = {
    clipboard: { writeText: async () => { throw new Error("clipboard denied"); } },
  };
  await harness.node("update-copy-button").listeners.get("click")[0]();
  assert.match(harness.node("notice").textContent, /select the displayed command/i);
});

test("dashboard update surface rejects cross-field and target-identity mismatches", () => {
  const harness = createAppHarness(() => {
    throw new Error("direct projection must not fetch");
  });
  assert.throws(
    () => harness.api.applyUpdateStatus({ schema_version: "agency.dashboard.update.v0" }),
    /Unsupported Agency update response/,
  );

  const impossibleMain = updateContractPayload();
  impossibleMain.release.status = "current";
  impossibleMain.release.update_available = false;
  impossibleMain.recommended = "main";
  impossibleMain.main.status = "update_available";
  impossibleMain.main.update_available = true;
  assert.throws(() => harness.api.applyUpdateStatus(impossibleMain), /invalid/i);

  const mismatchedFlag = updateContractPayload();
  mismatchedFlag.release.status = "current";
  assert.throws(() => harness.api.applyUpdateStatus(mismatchedFlag), /invalid/i);

  const mismatchedCommitUrl = updateContractPayload();
  mismatchedCommitUrl.main.target.url = `https://github.com/Holeshot-Software-LLC/agency-runtime/commit/${"d".repeat(40)}`;
  assert.throws(() => harness.api.applyUpdateStatus(mismatchedCommitUrl), /invalid/i);

  const mismatchedReleaseUrl = updateContractPayload();
  mismatchedReleaseUrl.release.target.url = "https://github.com/Holeshot-Software-LLC/agency-runtime/releases/tag/v9.9.9";
  assert.throws(() => harness.api.applyUpdateStatus(mismatchedReleaseUrl), /invalid/i);
  assert.match(LIVE_SOURCE, /api\("\/api\/update"/);
  assert.match(LIVE_SOURCE, /safeUpdateTargetUrl/);
});

async function acceptOwnerConfirmation(harness, pending, phrase) {
  await Promise.resolve();
  assert.equal(harness.api.state.confirmation?.phrase, phrase);
  harness.node("confirmation-input").value = phrase;
  harness.api.finishConfirmation(true);
  await pending;
}

test("owner dashboard controls dispatch confirmed revision-bound mutations", async () => {
  const calls = [];
  const mutationPaths = new Set([
    "/api/agents/toggle",
    "/api/config",
    "/api/hiring/approve",
    "/api/hosts/toggle",
    "/api/maintenance/trim",
    "/api/roster/action",
    "/api/runtime/toggle",
    "/api/workforce/action",
  ]);
  const harness = createAppHarness(async (path, options = {}) => {
    calls.push({ path, options });
    if (path === "/api/live?limit=100") {
      return jsonResponse(200, {
        activity: {},
        master: {
          enabled: false,
          generation: 8,
          schema_version: 1,
          source: "dashboard",
          updated_at: "2026-07-30T12:00:00Z",
        },
        overview: { status: "ok" },
        revision: `owner-live-${calls.length}`,
        sampled_at: "2026-07-30T12:00:00Z",
        schema_version: 1,
      });
    }
    if (path === "/api/control") {
      return jsonResponse(200, controlSnapshot({
        config: {
          effective: { observability: { capture_content: false, retention_days: 31 } },
          revision: "owner-control-config",
        },
      }));
    }
    if (path === "/api/config") {
      return jsonResponse(200, {
        effective: { observability: { capture_content: false, retention_days: 31 } },
        restart_required_paths: [],
        revision: "owner-saved-config",
      });
    }
    if (path === "/api/maintenance/trim") {
      return jsonResponse(200, { db_size_after_bytes: 1536 });
    }
    if (path === "/api/runtime/toggle") {
      return jsonResponse(200, {
        changed: true,
        master: {
          enabled: false,
          generation: 8,
          schema_version: 1,
          source: "dashboard",
          updated_at: "2026-07-30T12:00:00Z",
        },
        ok: true,
      });
    }
    if (mutationPaths.has(path)) return jsonResponse(200, { ok: true });
    throw new Error(`unexpected owner dashboard request: ${path}`);
  });

  const retention = new FakeNode("config-retention");
  retention.dataset.configPath = "observability.retention_days";
  retention.dataset.valueType = "integer";
  retention.labels = [{ textContent: "Runtime retention days" }];
  retention.value = "31";
  harness.nodes.set("config-retention", retention);
  harness.select("[data-config-path]", [retention]);
  harness.api.state.config = { revision: "owner-original-config" };
  harness.api.state.configBaseline.set("observability.retention_days", "30");
  await acceptOwnerConfirmation(
    harness,
    harness.api.saveConfig({ preventDefault() {} }),
    "SAVE CONFIG",
  );

  harness.node("trim-confirm").value = "TRIM RUNTIME DATA";
  harness.node("trim-days").value = "45";
  await harness.api.trimRuntime();

  await acceptOwnerConfirmation(
    harness,
    harness.api.rosterAction("approve", "snapshot-owner"),
    "APPROVE snapshot-owner",
  );
  await acceptOwnerConfirmation(
    harness,
    harness.api.toggleHost("codex", false, 4),
    "DISABLE codex",
  );

  harness.api.state.controlConfigRevision = "owner-agent-revision";
  await acceptOwnerConfirmation(
    harness,
    harness.api.toggleAgent("code-reviewer", false),
    "DISABLE code-reviewer",
  );

  harness.api.state.master = {
    enabled: true,
    generation: 7,
    schema_version: 1,
    source: "dashboard",
    updated_at: "2026-07-30T11:59:00Z",
  };
  await acceptOwnerConfirmation(
    harness,
    harness.api.toggleMaster(false),
    "DISABLE AGENCY",
  );

  harness.node("workforce-action-kind").value = "suspend";
  harness.node("workforce-action-worker").value = "typescript-application-engineer";
  harness.node("workforce-action-target").value = "";
  harness.node("workforce-action-reason").value = "Owner reviewed current evidence.";
  harness.node("workforce-action-revision").value = "3";
  await acceptOwnerConfirmation(
    harness,
    harness.api.workforceAction({ preventDefault() {} }),
    "SUSPEND typescript-application-engineer",
  );

  harness.node("hiring-approver-identity").value = "  Lucas Owner  ";
  await acceptOwnerConfirmation(
    harness,
    harness.api.hiringApprove("hiring-owner-1"),
    "APPROVE hiring-owner-1",
  );

  const mutations = calls.filter(({ path }) => mutationPaths.has(path));
  assert.deepEqual(mutations.map(({ path }) => path), [
    "/api/config",
    "/api/maintenance/trim",
    "/api/roster/action",
    "/api/hosts/toggle",
    "/api/agents/toggle",
    "/api/runtime/toggle",
    "/api/workforce/action",
    "/api/hiring/approve",
  ]);
  const bodies = Object.fromEntries(
    mutations.map(({ path, options }) => [path, JSON.parse(options.body)]),
  );
  assert.deepEqual(bodies["/api/config"], {
    confirmations: ["SAVE CONFIG"],
    expected_revision: "owner-original-config",
    operations: [{
      op: "set",
      path: "observability.retention_days",
      value: 31,
    }],
  });
  assert.deepEqual(bodies["/api/maintenance/trim"], {
    confirm: "TRIM RUNTIME DATA",
    older_than_days: 45,
    vacuum: false,
  });
  assert.deepEqual(bodies["/api/roster/action"], {
    action: "approve",
    confirm: "APPROVE snapshot-owner",
    snapshot_id: "snapshot-owner",
  });
  assert.deepEqual(bodies["/api/hosts/toggle"], {
    confirm: "DISABLE codex",
    enabled: false,
    expected_generation: 4,
    host: "codex",
  });
  assert.deepEqual(bodies["/api/agents/toggle"], {
    confirm: "DISABLE code-reviewer",
    enabled: false,
    expected_revision: "owner-agent-revision",
    slug: "code-reviewer",
  });
  assert.deepEqual(bodies["/api/runtime/toggle"], {
    confirm: "DISABLE AGENCY",
    enabled: false,
    expected_generation: 7,
  });
  assert.deepEqual(bodies["/api/workforce/action"], {
    action: "suspend",
    confirm: "SUSPEND typescript-application-engineer",
    expected_revision: 3,
    into: "",
    reason: "Owner reviewed current evidence.",
    worker: "typescript-application-engineer",
  });
  assert.deepEqual(bodies["/api/hiring/approve"], {
    approved_by: "Lucas Owner",
    case_id: "hiring-owner-1",
    confirm: "APPROVE hiring-owner-1",
  });
});

test("hiring approval rejects missing or oversized audit identity before confirmation or POST", async () => {
  const calls = [];
  const harness = createAppHarness(async (path) => {
    calls.push(path);
    return jsonResponse(200, { ok: true });
  });
  harness.node("hiring-approver-identity").value = " \t\n ";

  assert.equal(await harness.api.hiringApprove("case-needs-owner"), undefined);
  assert.equal(harness.api.state.confirmation, null);
  assert.deepEqual(calls, []);
  assert.match(harness.node("notice").textContent, /approver audit identity/i);

  harness.node("hiring-approver-identity").value = "é".repeat(65);
  assert.equal(await harness.api.hiringApprove("case-needs-owner"), undefined);
  assert.equal(harness.api.state.confirmation, null);
  assert.deepEqual(calls, []);
  assert.match(harness.node("notice").textContent, /valid approver audit identity/i);
});

test("authenticated dashboard exposes the owner control surface and mutation request client", () => {
	const mutationEndpoints = [
		"/api/agents/toggle",
    "/api/config\"",
    "/api/hiring/approve",
    "/api/hosts/toggle",
    "/api/maintenance/trim",
    "/api/roster/action",
		"/api/runtime/toggle",
		"/api/workforce/action",
	];
	for (const endpoint of mutationEndpoints) assert.ok(ACTIONS_SOURCE.includes(endpoint));
	for (const callback of ["toggleAgent", "toggleHost", "rosterAction"]) {
		assert.match(RENDER_SOURCE, new RegExp(`callbacks\\.${callback}`));
	}
	assert.match(APP_SOURCE, /actions\.hiringApprove/);
	for (const id of ["trim-button", "trim-confirm", "trim-days"]) {
		assert.match(INDEX_SOURCE, new RegExp(`id="${id}"`));
	}
	assert.match(INDEX_SOURCE, /Trim runtime data/);
	assert.match(INDEX_SOURCE, /dashboard and CLI use the same validated configuration writer/i);

	const harness = createAppHarness(() => {
		throw new Error("owner surface setup does not fetch");
	});
	const configControls = [new FakeNode("config-input"), new FakeNode("config-select")];
  harness.select(
    "#config-form input, #config-form select, #config-form textarea, #config-form button",
    configControls,
  );
	harness.node("privacy-chip").textContent = "Metadata only";
	assert.equal(harness.api.bindEvents(), true);
	for (const name of [
		"trimRuntime", "saveConfig", "rosterAction", "toggleAgent", "toggleHost",
		"toggleMaster", "workforceAction", "hiringApprove",
	]) assert.equal(typeof harness.api[name], "function");
	for (const id of [
		"provider-builder-save", "provider-builder-remove",
		"config-reset-button", "trim-button",
	]) {
		assert.equal(harness.node(id).disabled, false);
		assert.equal(harness.node(id).hidden, false);
		assert.ok(harness.node(id).listeners.size > 0);
	}
	assert.ok(harness.node("config-form").listeners.get("submit")?.length > 0);
	assert.ok(harness.node("workforce-action-form").listeners.get("submit")?.length > 0);
	assert.ok(harness.node("confirmation-accept").listeners.get("click")?.length > 0);
	assert.ok(harness.node("confirmation-cancel").listeners.get("click")?.length > 0);
	for (const control of configControls) assert.equal(control.disabled, false);
	assert.equal(harness.node("master-toggle").disabled, false);
	assert.ok(harness.node("master-toggle").listeners.get("click")?.length > 0);
	assert.equal(harness.node("privacy-chip").textContent, "Runtime metadata only");
	harness.api.renderConfig({
    effective: {},
    environment_overrides: [],
		path: "C:/Users/test/.agency-runtime/agency.yaml",
		revision: "config-revision-after-refresh",
	});
	assert.equal(harness.node("config-change-count").textContent, "No unsaved changes");
	assert.equal(harness.node("config-save-button").disabled, true);
	harness.node("config-providers").value = JSON.stringify([{ name: "owner-provider" }]);
	harness.api.syncProviderSecretOptions();
	assert.equal(harness.node("config-provider-secret-index").options[0].textContent, "owner-provider");

	harness.api.applyMasterState({
    schema_version: 1,
    enabled: true,
    generation: 4,
		updated_at: "2026-07-26T00:00:00Z",
		source: "test",
	});
	assert.equal(harness.node("master-toggle").disabled, false);
	assert.equal(
		harness.node("master-toggle").attributes.get("aria-label"),
		"Disable Agency Runtime globally",
	);
});
