"use strict";

const state = {
  token: "",
  overview: null,
  activity: {},
  hosts: [],
  roster: [],
  snapshots: [],
  config: null,
  configBaseline: new Map(),
  configDirty: false,
  pendingConfig: null,
  confirmation: null,
  evidenceKeys: new Map(),
  metricValues: new Map(),
  clockTimer: null,
  live: {
    enabled: true,
    terminal: false,
    timer: null,
    controller: null,
    inFlight: false,
    generation: 0,
    failures: 0,
    revision: "",
    sampledAt: null,
    chartWindow: null,
  },
  control: {
    timer: null,
    controller: null,
    inFlight: false,
  },
  full: {
    controller: null,
    inFlight: false,
    generation: 0,
  },
};

const LIVE_INTERVAL_MS = 2500;
const CONTROL_INTERVAL_MS = 15000;

function byId(id) { return document.getElementById(id); }
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined && text !== null) node.textContent = String(text);
  return node;
}
function formatBytes(value) {
  const bytes = Number(value || 0);
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 ** 2).toFixed(1)} MB`;
}
function formatTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? String(value) : date.toLocaleString();
}
function showNotice(message, error = false) {
  const notice = byId("notice");
  notice.textContent = message;
  notice.className = error ? "notice error" : "notice";
  notice.hidden = false;
  window.clearTimeout(showNotice.timer);
  showNotice.timer = window.setTimeout(() => { notice.hidden = true; }, 6000);
}

function requestConfirmation(phrase, message) {
  if (state.confirmation) finishConfirmation(false);
  return new Promise((resolve) => {
    const activeElement = document.activeElement;
    state.confirmation = {
      phrase,
      resolve,
      returnFocus: activeElement instanceof HTMLElement ? activeElement : null,
    };
    byId("confirmation-title").textContent = "Confirm this operation";
    byId("confirmation-message").textContent = message;
    byId("confirmation-phrase").textContent = phrase;
    byId("confirmation-input").value = "";
    byId("confirmation-error").hidden = true;
    byId("confirmation-modal").hidden = false;
    const shell = document.querySelector(".shell");
    if (shell) shell.inert = true;
    byId("confirmation-input").focus();
  });
}

function finishConfirmation(accepted) {
  const pending = state.confirmation;
  if (!pending) return;
  if (accepted && byId("confirmation-input").value !== pending.phrase) {
    byId("confirmation-error").hidden = false;
    byId("confirmation-input").focus();
    return;
  }
  state.confirmation = null;
  byId("confirmation-modal").hidden = true;
  byId("confirmation-input").value = "";
  const shell = document.querySelector(".shell");
  if (shell) shell.inert = false;
  if (pending.returnFocus?.isConnected) pending.returnFocus.focus();
  pending.resolve(accepted);
}

function modalFocusable() {
  const modal = byId("confirmation-modal");
  if (!modal || modal.hidden) return [];
  return [...modal.querySelectorAll(
    'button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
  )].filter((node) => !node.hidden);
}

function handleModalKeyboard(event) {
  if (!state.confirmation || byId("confirmation-modal")?.hidden) return;
  if (event.key === "Escape") {
    event.preventDefault();
    finishConfirmation(false);
    return;
  }
  if (event.key !== "Tab") return;
  const focusable = modalFocusable();
  if (!focusable.length) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}
function hostState(host) {
  if (host.inspection_status && host.inspection_status !== "complete") {
    return "inspection-" + host.inspection_status;
  }
  return String(host.maturity || host.state || (host.discovered ? "host-discovered" : "absent"));
}
function truthLabel(value, yes, no, unknown) {
  if (value === true) return yes;
  if (value === false) return no;
  return unknown;
}
function hostLocation(host) {
  if (host.executable) return host.executable;
  if (host.native_root_exists === true && host.native_root) return host.native_root;
  if (host.current_native_root === true) return "Current native payload detected";
  return "Not discovered";
}

class APIError extends Error {
  constructor(message, status, retryAfter = null) {
    super(message);
    this.name = "APIError";
    this.status = status;
    this.retryAfter = retryAfter;
  }
}

async function api(path, options = {}) {
  const headers = { Authorization: `Bearer ${state.token}`, ...(options.headers || {}) };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  const response = await fetch(path, {
    ...options,
    headers,
    cache: "no-store",
    credentials: "omit",
  });
  let payload;
  try { payload = await response.json(); } catch { payload = { error: `HTTP ${response.status}` }; }
  if (!response.ok) {
    throw new APIError(
      payload.error || `HTTP ${response.status}`,
      response.status,
      response.headers.get("Retry-After"),
    );
  }
  return payload;
}

function installToken() {
  const hash = new URLSearchParams(window.location.hash.slice(1));
  const incoming = hash.get("token");
  if (incoming) sessionStorage.setItem("agency-dashboard-token", incoming);
  state.token = incoming || sessionStorage.getItem("agency-dashboard-token") || "";
  if (window.location.hash) history.replaceState(null, "", window.location.pathname);
  if (!state.token) throw new Error("This dashboard URL has no active access token. Run `agency dashboard service open` or restart `agency dashboard`.");
}

function nestedValue(root, path) {
  return path.split(".").reduce((value, part) => (
    value !== null && value !== undefined && Object.hasOwn(value, part) ? value[part] : undefined
  ), root);
}

function stableValue(value) {
  if (Array.isArray(value)) return value.map(stableValue);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stableValue(value[key])]));
  }
  return value;
}

function comparable(value) {
  return JSON.stringify(stableValue(value));
}

function readConfigControl(node) {
  const kind = node.dataset.valueType || "string";
  if (kind === "boolean") return node.checked;
  if (kind === "integer") {
    const value = Number(node.value);
    if (!Number.isInteger(value)) throw new Error(`${node.labels?.[0]?.textContent || node.id} must be an integer.`);
    return value;
  }
  if (kind === "number") {
    const value = Number(node.value);
    if (!Number.isFinite(value)) throw new Error(`${node.labels?.[0]?.textContent || node.id} must be a finite number.`);
    return value;
  }
  if (kind === "json") {
    try { return JSON.parse(node.value); }
    catch { throw new Error(`${node.labels?.[0]?.textContent || node.id} must contain valid JSON.`); }
  }
  if (node.dataset.nullable === "true" && !node.value.trim()) return null;
  return node.value;
}

function writeConfigControl(node, value) {
  const kind = node.dataset.valueType || "string";
  if (kind === "boolean") node.checked = value === true;
  else if (kind === "json") {
    const safeValue = node.dataset.configPath === "providers" && Array.isArray(value)
      ? value.map(({ api_key: _secret, ...provider }) => provider)
      : value;
    node.value = JSON.stringify(safeValue ?? [], null, 2);
  }
  else node.value = value ?? "";
}

function configControls() {
  return [...document.querySelectorAll("[data-config-path]")];
}

function collectConfigChanges() {
  const operations = [];
  configControls().forEach((node) => {
    const path = node.dataset.configPath;
    const value = readConfigControl(node);
    if (comparable(value) !== state.configBaseline.get(path)) operations.push({ op: "set", path, value });
  });
  appendSecretOperation(
    operations,
    "judge.api_key",
    byId("config-judge-secret").value,
    byId("config-judge-secret-clear").checked,
  );
  appendSecretOperation(
    operations,
    "adapters.litellm.api_key",
    byId("config-litellm-secret").value,
    byId("config-litellm-secret-clear").checked,
  );
  const providerIndex = byId("config-provider-secret-index").value;
  const providerSecret = byId("config-provider-secret").value;
  const clearProviderSecret = byId("config-provider-secret-clear").checked;
  if ((providerSecret || clearProviderSecret) && providerIndex === "") {
    throw new Error("Select a provider before changing its direct key.");
  }
  if (providerIndex !== "") {
    appendSecretOperation(
      operations,
      `providers.${providerIndex}.api_key`,
      providerSecret,
      clearProviderSecret,
    );
  }
  return operations;
}

function appendSecretOperation(operations, path, value, clear) {
  if (value && clear) throw new Error(`Choose either a new value or clear for ${path}, not both.`);
  if (value) operations.push({ op: "secret", path, action: "replace", value });
  if (clear) operations.push({ op: "secret", path, action: "clear" });
}

function syncProviderSecretOptions() {
  const select = byId("config-provider-secret-index");
  const selected = select.value;
  let providers = [];
  try { providers = JSON.parse(byId("config-providers").value); }
  catch { providers = []; }
  select.replaceChildren();
  if (!Array.isArray(providers) || !providers.length) {
    const option = el("option", "", "No configured providers");
    option.value = "";
    select.append(option);
    select.disabled = true;
    return;
  }
  select.disabled = false;
  providers.forEach((provider, index) => {
    const option = el("option", "", provider?.name || `Provider ${index + 1}`);
    option.value = String(index);
    select.append(option);
  });
  select.value = [...select.options].some((option) => option.value === selected)
    ? selected
    : "0";
}

function updateConfigDirtyState() {
  syncProviderSecretOptions();
  let operations = [];
  try { operations = collectConfigChanges(); }
  catch (error) {
    state.configDirty = true;
    byId("config-change-count").textContent = error.message;
    byId("config-save-button").disabled = true;
    return;
  }
  const count = operations.length;
  state.configDirty = count > 0;
  const pending = state.pendingConfig ? " · newer configuration available; reset to load it" : "";
  byId("config-change-count").textContent = count
    ? `${count} unsaved change${count === 1 ? "" : "s"}${pending}`
    : `No unsaved changes${pending}`;
  byId("config-save-button").disabled = count === 0;
}

function renderConfig(snapshot) {
  const effective = snapshot.effective || snapshot.config || {};
  state.config = snapshot;
  state.pendingConfig = null;
  configControls().forEach((node) => writeConfigControl(node, nestedValue(effective, node.dataset.configPath)));
  byId("config-judge-secret").value = "";
  byId("config-judge-secret-clear").checked = false;
  byId("config-litellm-secret").value = "";
  byId("config-litellm-secret-clear").checked = false;
  byId("config-provider-secret").value = "";
  byId("config-provider-secret-clear").checked = false;
  syncProviderSecretOptions();
  state.configBaseline = new Map(configControls().map((node) => [
    node.dataset.configPath,
    comparable(readConfigControl(node)),
  ]));
  byId("config-output").textContent = JSON.stringify(effective, null, 2);
  byId("config-path").textContent = snapshot.path || "Bundled defaults; the next save creates the user config.";
  const revision = String(snapshot.revision || "missing");
  byId("config-revision").textContent = revision === "missing" ? "NEW FILE" : revision.slice(0, 10);
  const rawOverrides = snapshot.environment_overrides || {};
  const overrides = Array.isArray(rawOverrides) ? rawOverrides : Object.keys(rawOverrides);
  byId("config-override-count").textContent = overrides.length ? `${overrides.length} ENV OVERRIDE${overrides.length === 1 ? "" : "S"}` : "NO OVERRIDES";
  updateConfigDirtyState();
}

function applyConfigSnapshot(snapshot, { force = false } = {}) {
  if (!snapshot) return false;
  const currentRevision = String(state.config?.revision || "missing");
  const nextRevision = String(snapshot.revision || "missing");
  if (!force && state.configDirty) {
    if (currentRevision !== nextRevision) {
      const pendingRevision = String(state.pendingConfig?.revision || "");
      state.pendingConfig = snapshot;
      updateConfigDirtyState();
      if (pendingRevision !== nextRevision) {
        showNotice("Configuration changed outside this dashboard. Your unsaved edits were preserved.", true);
      }
    }
    return false;
  }
  renderConfig(snapshot);
  return true;
}

function switchView(name) {
  document.querySelectorAll(".nav-item").forEach((node) => {
    const active = node.dataset.view === name;
    node.classList.toggle("active", active);
    if (active) node.setAttribute("aria-current", "page");
    else node.removeAttribute("aria-current");
  });
  document.querySelectorAll(".view").forEach((node) => node.classList.toggle("active", node.dataset.viewPanel === name));
  const titles = { overview: "Runtime overview", routing: "Routing lab", evidence: "Evidence ledger", roster: "Roster governance", hosts: "Host integrations", settings: "Settings & retention" };
  byId("view-title").textContent = titles[name] || "Agency Runtime";
}

function reducedMotionPreferred() {
  return typeof window.matchMedia === "function"
    && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

function markUpdated(node, className = "is-updated") {
  if (!node || reducedMotionPreferred()) return;
  node.classList.remove(className);
  void node.offsetWidth;
  node.classList.add(className);
  node.addEventListener("animationend", () => node.classList.remove(className), { once: true });
}

function setMetric(id, value) {
  const node = byId(id);
  if (!node) return;
  const rendered = String(value);
  const previous = state.metricValues.get(id);
  node.textContent = rendered;
  state.metricValues.set(id, rendered);
  if (previous !== undefined && previous !== rendered) markUpdated(node);
}

function renderCharts() {
  const charts = globalThis.AgencyCharts;
  if (!charts) return;
  charts.renderActivityChart(
    byId("activity-chart"),
    byId("activity-chart-summary"),
    state.activity,
    { now: state.live.sampledAt || Date.now(), bucketCount: 24, bucketMs: 60000 },
  );
  charts.renderOutcomeChart(
    byId("outcome-chart"),
    byId("outcome-chart-summary"),
    state.activity,
  );
  const sampled = Date.parse(state.live.sampledAt || "");
  state.live.chartWindow = Number.isFinite(sampled) ? Math.floor(sampled / 60000) : null;
}

function evidenceRowKey(row, index) {
  if (row && typeof row === "object") {
    return String(
      row.id
      || `${row.trace_id || "trace"}:${row.work_unit_id || row.created_at || row.started_at || index}`,
    );
  }
  return `row:${index}`;
}

function renderOverview() {
  const data = state.overview || {};
  setMetric("metric-runtime", data.status === "ok" ? "Online" : "Unknown");
  setMetric("metric-roster", data.roster_count ?? "—");
  setMetric("metric-routing", data.recent?.routing ?? "—");
  setMetric("metric-delegations", data.recent?.delegations ?? "—");
  setMetric("metric-store", formatBytes((data.db_size_bytes || 0) + (data.wal_size_bytes || 0)));
  byId("setting-capture").textContent = data.capture_content ? "Opt-in enabled" : "Disabled";
  byId("setting-retention").textContent = `${data.retention_days || 30} days`;
  byId("privacy-chip").textContent = data.capture_content ? "Redacted content" : "Metadata only";
  const trimDays = byId("trim-days");
  if (trimDays && trimDays.dataset.dirty !== "true") {
    trimDays.value = data.retention_days || 30;
  }

  const tbody = byId("overview-delegations"); tbody.replaceChildren();
  const previousOverviewKeys = state.evidenceKeys.get("overview") || new Set();
  const nextOverviewKeys = new Set();
  (state.activity.delegations || []).slice(0, 12).forEach((row, index) => {
    const tr = el("tr");
    const key = evidenceRowKey(row, index);
    nextOverviewKeys.add(key);
    if (previousOverviewKeys.size && !previousOverviewKeys.has(key)) tr.classList.add("is-new");
    [row.recommended_agent || "unassigned", row.host || "unknown"].forEach((value) => tr.append(el("td", "", value)));
    const status = el("span", `status ${row.status || ""}`, row.status || "unknown");
    const statusCell = el("td"); statusCell.append(status); tr.append(statusCell);
    tr.append(el("td", "", row.backend || "—"), el("td", "", formatTime(row.started_at)));
    tbody.append(tr);
  });
  state.evidenceKeys.set("overview", nextOverviewKeys);
  if (!tbody.children.length) tbody.append(emptyRow(5, "No delegation evidence yet."));

  const hostStack = byId("overview-hosts"); hostStack.replaceChildren();
  state.hosts.forEach((host) => {
    const row = el("div", "host-row");
    const current = hostState(host);
    const copy = el("div"); copy.append(el("strong", "", host.host), el("small", "", hostLocation(host)));
    row.append(copy, el("span", `host-state ${current}`, current)); hostStack.append(row);
  });

  const providerStack = byId("provider-health"); providerStack.replaceChildren();
  (data.provider_health || []).forEach((provider) => {
    const row = el("div", "provider-row");
    const copy = el("div");
    copy.append(
      el("strong", "", provider.provider),
      el("small", "", `${provider.success_count} successful · ${provider.failure_count} failed · ${provider.unknown_count} unknown`),
    );
    const latest = String(provider.latest_status || "unknown").toLowerCase();
    row.append(copy, el("span", `status ${latest}`, latest));
    providerStack.append(row);
  });
  if (!providerStack.children.length) providerStack.append(el("div", "empty-compact", "No provider receipts observed."));
  renderCharts();
}

function emptyRow(columns, message) {
  const tr = el("tr"); const td = el("td", "", message); td.colSpan = columns; tr.append(td); return tr;
}

function renderHosts() {
  const grid = byId("host-grid"); grid.replaceChildren();
  state.hosts.forEach((host) => {
    const card = el("article", "host-card");
    const heading = el("div", "host-row");
    const current = hostState(host);
    heading.append(el("strong", "", host.host), el("span", `host-state ${current}`, current));
    card.append(heading, el("small", "", hostLocation(host)));
    const tags = el("div", "token-list");
    tags.append(el("span", "token", truthLabel(host.registered, "registered", "not registered", "registration unknown")));
    tags.append(el("span", "token", truthLabel(host.enabled, "enabled", "disabled", "enablement unknown")));
    tags.append(el("span", "token", host.maturity || "unverified"));
    card.append(tags);
    if (host.executable_discovered === true) {
      const actions = el("div", "card-actions");
      const inspectionCurrent = !host.inspection_status || host.inspection_status === "complete";
      const directionKnown = inspectionCurrent && host.registered === true && typeof host.enabled === "boolean";
      const enabled = host.enabled === true;
      const label = directionKnown
        ? (enabled ? "Disable" : "Enable")
        : (!inspectionCurrent ? "Inspection stale" : (host.registered === false ? "Not registered" : "State unknown"));
      const button = el("button", `button compact ${enabled ? "danger" : "solid"}`, label);
      button.type = "button";
      button.disabled = !directionKnown;
      if (directionKnown) button.addEventListener("click", () => toggleHost(host.host, !enabled));
      else button.title = "A native inventory must prove registration and current enablement before this action is available.";
      actions.append(button); card.append(actions);
    }
    grid.append(card);
  });
}

function renderRoster() {
  const grid = byId("roster-grid"); grid.replaceChildren();
  byId("roster-count").textContent = state.roster.length;
  state.roster.forEach((agent) => {
    const card = el("article", "agent-card");
    card.append(el("strong", "", agent.name || agent.agent_slug), el("small", "", `${agent.agent_slug} · ${agent.division || "unassigned"}`));
    const tags = el("div", "token-list");
    (agent.capabilities || []).slice(0, 4).forEach((value) => tags.append(el("span", "token", value)));
    if (!tags.children.length) tags.append(el("span", "token", "no capability tags"));
    card.append(tags); grid.append(card);
  });
  const list = byId("snapshot-list"); list.replaceChildren();
  state.snapshots.forEach((snapshot) => {
    const row = el("div", "stack-item");
    const copy = el("div"); copy.append(el("strong", "", snapshot.snapshot_id), el("small", "", `${snapshot.agent_count || 0} agents · ${formatTime(snapshot.created_at)}`));
    const status = snapshot.activated ? "activated" : snapshot.approved ? "approved" : "pending";
    const controls = el("div", "card-actions");
    controls.append(el("span", `host-state ${snapshot.activated ? "verified" : ""}`, status));
    if (!snapshot.activated) {
      const action = snapshot.approved ? "activate" : "approve";
      const button = el("button", "button compact ghost", action);
      button.type = "button";
      button.addEventListener("click", () => rosterAction(action, snapshot.snapshot_id));
      controls.append(button);
    }
    row.append(copy, controls);
    list.append(row);
  });
  if (!list.children.length) list.append(el("div", "empty-state", "No roster snapshots."));
}

const evidenceColumns = {
  delegations: [["recommended_agent", "Agent"], ["host", "Host"], ["status", "Status"], ["backend", "Backend"], ["work_unit_id", "Work unit"], ["started_at", "Started"]],
  routing: [["trace_id", "Trace"], ["id", "Decision"], ["status", "Status"], ["source", "Source"], ["selected_ids", "Selected"], ["created_at", "Created"]],
  receipts: [["resolved_model", "Resolved model"], ["resolved_provider", "Provider"], ["host", "Host"], ["status", "Status"], ["source", "Source"], ["ended_at", "Ended"]],
  runs: [["trace_id", "Trace"], ["session_id", "Session"], ["host", "Host"], ["status", "Status"], ["started_at", "Started"], ["ended_at", "Ended"]],
  finalizations: [["trace_id", "Trace"], ["host", "Host"], ["action", "Action"], ["missing", "Missing"], ["created_at", "Created"]],
};
function renderEvidence(kind = "delegations") {
  const columns = evidenceColumns[kind];
  const head = byId("evidence-head"); const body = byId("evidence-body"); head.replaceChildren(); body.replaceChildren();
  const trh = el("tr"); columns.forEach(([, label]) => trh.append(el("th", "", label))); head.append(trh);
  const previousKeys = state.evidenceKeys.get(kind) || new Set();
  const nextKeys = new Set();
  (state.activity[kind] || []).forEach((row, index) => {
    const tr = el("tr");
    const key = evidenceRowKey(row, index);
    nextKeys.add(key);
    if (previousKeys.size && !previousKeys.has(key)) tr.classList.add("is-new");
    columns.forEach(([key]) => {
      let value = row[key];
      if (Array.isArray(value)) value = value.join(", ") || "—";
      if (key.endsWith("_at") || key === "created_at") value = formatTime(value);
      const td = el("td");
      if (key === "status" || key === "action") td.append(el("span", `status ${value || ""}`, value || "—")); else td.textContent = value || "—";
      tr.append(td);
    });
    body.append(tr);
  });
  state.evidenceKeys.set(kind, nextKeys);
  if (!body.children.length) body.append(emptyRow(columns.length, `No ${kind} evidence yet.`));
}

function renderReceipt(receipt) {
  const root = byId("route-result"); root.className = "receipt"; root.replaceChildren();
  const selected = (receipt.selected || []).map((item) => item.slug || item.agent_slug || item.id).filter(Boolean);
  const blocks = [
    ["Status", receipt.status || receipt.signals?.selection?.status || "unknown"],
    ["Selected specialists", selected.length ? selected : ["abstained"]],
    ["Policy actions", receipt.signals?.policy?.matched_actions || []],
    ["Work units", receipt.signals?.delegation?.work_units?.units || receipt.signals?.work_units?.units || receipt.work_units?.units || []],
    ["Decision source", receipt.signals?.selection?.provider || receipt.provider || "deterministic"],
  ];
  blocks.forEach(([label, value]) => {
    const block = el("div", "receipt-block"); block.append(el("span", "", label));
    if (Array.isArray(value)) {
      const list = el("div", "token-list");
      (value.length ? value : ["none"]).forEach((item) => {
        list.append(el("span", "token", typeof item === "string" ? item : JSON.stringify(item)));
      });
      block.append(list);
    } else block.append(el("p", "", value));
    root.append(block);
  });
  const graph = receipt.delegation_graph || { nodes: [], edges: [] };
  const graphBlock = el("div", "receipt-block dependency-graph");
  graphBlock.append(el("span", "", "Delegation dependency graph"));
  if (!(graph.nodes || []).length) {
    graphBlock.append(el("p", "", "No delegation work units detected."));
  } else {
    const nodes = el("div", "dependency-nodes");
    (graph.nodes || []).forEach((node) => {
      const item = el("div", "dependency-node");
      item.append(el("strong", "", node.id), el("small", "", node.description));
      nodes.append(item);
    });
    graphBlock.append(nodes);
    const edges = el("div", "dependency-edges");
    if ((graph.edges || []).length) {
      (graph.edges || []).forEach((edge) => edges.append(el("small", "", `${edge.from} → ${edge.to} · ${edge.reason}`)));
    } else {
      edges.append(el("small", "", "No dependency edges; detected units can run independently."));
    }
    graphBlock.append(edges);
  }
  root.append(graphBlock);
  byId("route-status").textContent = String(receipt.status || receipt.signals?.selection?.status || "complete").toUpperCase();
}

function activeEvidenceKind() {
  return document.querySelector(".subnav-item.active")?.dataset.evidence || "delegations";
}

function setConnection(connected, label) {
  document.querySelector(".rail-foot")?.classList.toggle("connected", connected);
  if (byId("connection-label")) byId("connection-label").textContent = label;
}

function setLiveStatus(label, stateName, { announce = false } = {}) {
  const status = byId("live-status");
  if (status) {
    status.textContent = label;
    status.dataset.state = stateName;
  }
  if (announce && state.live.statusText !== label && byId("live-announcer")) {
    byId("live-announcer").textContent = label;
  }
  state.live.statusText = label;
}

function updateLastSync(sampledAt) {
  const parsed = new Date(sampledAt || Date.now());
  const rendered = Number.isNaN(parsed.valueOf())
    ? "Sync time unavailable"
    : `Last sync ${parsed.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}`;
  if (byId("last-sync")) byId("last-sync").textContent = rendered;
}

function updateLocalClock() {
  window.clearTimeout(state.clockTimer);
  state.clockTimer = null;
  if (document.visibilityState === "hidden") return;
  const now = new Date();
  const clock = byId("local-clock");
  if (clock) {
    clock.dateTime = now.toISOString();
    clock.textContent = now.toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  }
  const delay = Math.max(100, 1020 - (Date.now() % 1000));
  state.clockTimer = window.setTimeout(updateLocalClock, delay);
}

function syncLiveToggle() {
  const toggle = byId("live-toggle");
  if (!toggle) return;
  toggle.setAttribute("aria-pressed", String(state.live.enabled));
  if (toggle instanceof HTMLInputElement && toggle.type === "checkbox") {
    toggle.checked = state.live.enabled;
  }
}

function cancelLiveRequest() {
  state.live.generation += 1;
  window.clearTimeout(state.live.timer);
  state.live.timer = null;
  const controller = state.live.controller;
  state.live.controller = null;
  state.live.inFlight = false;
  if (controller) controller.abort();
}

function liveCanRun() {
  return state.live.enabled
    && !state.live.terminal
    && document.visibilityState !== "hidden";
}

function scheduleLive(delay = LIVE_INTERVAL_MS) {
  window.clearTimeout(state.live.timer);
  state.live.timer = null;
  if (!liveCanRun()) return;
  state.live.timer = window.setTimeout(runLivePoll, Math.max(0, delay));
}

async function fetchLiveSnapshot() {
  if (state.live.inFlight) return null;
  const controller = new AbortController();
  const generation = state.live.generation + 1;
  state.live.generation = generation;
  state.live.controller = controller;
  state.live.inFlight = true;
  try {
    const payload = await api("/api/live?limit=100", { signal: controller.signal });
    return generation === state.live.generation ? payload : null;
  } finally {
    if (state.live.controller === controller) {
      state.live.controller = null;
      state.live.inFlight = false;
    }
  }
}

function applyLiveSnapshot(payload) {
  if (!payload || payload.schema_version !== 1) {
    throw new Error("Unsupported live dashboard response.");
  }
  state.live.sampledAt = payload.sampled_at || new Date().toISOString();
  updateLastSync(state.live.sampledAt);
  if (payload.revision === state.live.revision) {
    const sampled = Date.parse(state.live.sampledAt);
    const chartWindow = Number.isFinite(sampled) ? Math.floor(sampled / 60000) : null;
    if (chartWindow !== state.live.chartWindow) renderCharts();
    return false;
  }
  state.live.revision = String(payload.revision || "");
  state.overview = { ...(state.overview || {}), ...(payload.overview || {}) };
  state.activity = payload.activity || {};
  renderOverview();
  renderEvidence(activeEvidenceKind());
  return true;
}

function terminalLiveFailure(error) {
  return error instanceof APIError && (error.status === 401 || error.status === 403);
}

function handleLiveFailure(error) {
  if (error?.name === "AbortError") return;
  if (terminalLiveFailure(error)) {
    state.live.terminal = true;
    cancelLiveRequest();
    setConnection(false, "Token expired");
    setLiveStatus("Access expired · reopen from the CLI", "expired", { announce: true });
    showNotice("The dashboard token expired. Run `agency dashboard service open` to reconnect.", true);
    return;
  }
  state.live.failures += 1;
  const retry = globalThis.AgencyCharts?.retryDelay
    ? globalThis.AgencyCharts.retryDelay(state.live.failures)
    : Math.min(30000, 2000 * (2 ** Math.min(state.live.failures - 1, 4)));
  setConnection(false, "Reconnecting");
  setLiveStatus(`Reconnecting in ${Math.ceil(retry / 1000)}s`, "retrying", { announce: state.live.failures === 1 });
  if (state.live.failures === 1) showNotice("Live updates paused while the dashboard reconnects.", true);
  scheduleLive(retry);
}

async function runLivePoll() {
  state.live.timer = null;
  if (!liveCanRun() || state.live.inFlight) return;
  try {
    const payload = await fetchLiveSnapshot();
    if (!payload) return;
    applyLiveSnapshot(payload);
    state.live.failures = 0;
    setConnection(true, "Authenticated");
    setLiveStatus("Live · authenticated", "live", { announce: true });
    scheduleLive(LIVE_INTERVAL_MS);
  } catch (error) {
    handleLiveFailure(error);
  }
}

function cancelControlRequest() {
  window.clearTimeout(state.control.timer);
  state.control.timer = null;
  const controller = state.control.controller;
  state.control.controller = null;
  state.control.inFlight = false;
  if (controller) controller.abort();
}

function cancelFullRefresh() {
  state.full.generation += 1;
  const controller = state.full.controller;
  state.full.controller = null;
  state.full.inFlight = false;
  if (controller) controller.abort();
}

function scheduleControlRefresh(delay = CONTROL_INTERVAL_MS) {
  window.clearTimeout(state.control.timer);
  state.control.timer = null;
  if (!state.live.enabled || document.visibilityState === "hidden" || state.live.terminal) return;
  state.control.timer = window.setTimeout(refreshControlPlane, Math.max(0, delay));
}

async function refreshControlPlane() {
  state.control.timer = null;
  if (state.control.inFlight || document.visibilityState === "hidden") return;
  const controller = new AbortController();
  state.control.controller = controller;
  state.control.inFlight = true;
  try {
    const [hosts, roster, snapshots, config] = await Promise.all([
      api("/api/hosts", { signal: controller.signal }),
      api("/api/roster", { signal: controller.signal }),
      api("/api/snapshots", { signal: controller.signal }),
      api("/api/config", { signal: controller.signal }),
    ]);
    if (state.control.controller !== controller) return;
    state.hosts = hosts.hosts || [];
    state.roster = roster.agents || [];
    state.snapshots = snapshots.snapshots || [];
    state.overview = { ...(state.overview || {}), roster_count: state.roster.length };
    applyConfigSnapshot(config);
    renderOverview();
    renderHosts();
    renderRoster();
  } catch (error) {
    if (error?.name !== "AbortError" && terminalLiveFailure(error)) handleLiveFailure(error);
  } finally {
    if (state.control.controller === controller) {
      state.control.controller = null;
      state.control.inFlight = false;
      scheduleControlRefresh();
    }
  }
}

async function refreshAll({ surfaceErrors = true } = {}) {
  cancelFullRefresh();
  const controller = new AbortController();
  const generation = state.full.generation + 1;
  state.full.generation = generation;
  state.full.controller = controller;
  state.full.inFlight = true;
  byId("refresh-button").disabled = true;
  cancelLiveRequest();
  cancelControlRequest();
  try {
    const [overview, activity, hosts, roster, snapshots, config] = await Promise.all([
      api("/api/overview", { signal: controller.signal }),
      api("/api/activity?limit=100", { signal: controller.signal }),
      api("/api/hosts", { signal: controller.signal }),
      api("/api/roster", { signal: controller.signal }),
      api("/api/snapshots", { signal: controller.signal }),
      api("/api/config", { signal: controller.signal }),
    ]);
    if (generation !== state.full.generation || state.full.controller !== controller) return false;
    state.overview = overview;
    state.activity = activity;
    state.hosts = hosts.hosts || [];
    state.roster = roster.agents || [];
    state.snapshots = snapshots.snapshots || [];
    state.live.revision = "";
    state.live.sampledAt = new Date().toISOString();
    applyConfigSnapshot(config);
    setConnection(true, "Authenticated");
    setLiveStatus(state.live.enabled ? "Live · authenticated" : "Live updates paused", state.live.enabled ? "live" : "paused");
    updateLastSync(state.live.sampledAt);
    renderOverview(); renderHosts(); renderRoster(); renderEvidence(activeEvidenceKind());
    return true;
  } catch (error) {
    if (error?.name === "AbortError") return false;
    setConnection(false, "Unavailable");
    if (terminalLiveFailure(error)) handleLiveFailure(error);
    else if (surfaceErrors) showNotice(error.message, true);
    if (!surfaceErrors) throw error;
  } finally {
    if (state.full.controller === controller) {
      state.full.controller = null;
      state.full.inFlight = false;
      byId("refresh-button").disabled = false;
      scheduleLive(LIVE_INTERVAL_MS);
      scheduleControlRefresh();
    }
  }
}

async function refreshRuntimeEvidence() {
  cancelLiveRequest();
  try {
    const payload = await fetchLiveSnapshot();
    if (payload) applyLiveSnapshot(payload);
    state.live.failures = 0;
    setConnection(true, "Authenticated");
    setLiveStatus("Live · authenticated", "live");
  } finally {
    scheduleLive(LIVE_INTERVAL_MS);
  }
}

function pauseForMutation() {
  cancelFullRefresh();
  cancelLiveRequest();
  cancelControlRequest();
  byId("refresh-button").disabled = true;
}

function resumeAfterMutation() {
  if (!state.full.inFlight) byId("refresh-button").disabled = false;
  scheduleLive(LIVE_INTERVAL_MS);
  scheduleControlRefresh();
}

async function reconcileRuntimeEvidence(successMessage) {
  showNotice(successMessage);
  try {
    await refreshRuntimeEvidence();
  } catch (error) {
    if (terminalLiveFailure(error)) handleLiveFailure(error);
    else showNotice(`${successMessage} The live view could not refresh: ${error.message}`, true);
  }
}

async function reconcileAll(successMessage) {
  showNotice(successMessage);
  try {
    await refreshAll({ surfaceErrors: false });
  } catch (error) {
    if (!terminalLiveFailure(error)) {
      showNotice(`${successMessage} The dashboard view could not refresh: ${error.message}`, true);
    }
  }
}

async function runRoute() {
  const task = byId("route-task").value.trim();
  if (!task) return showNotice("Enter a task before running the routing lab.", true);
  byId("route-button").disabled = true; byId("route-status").textContent = "RUNNING";
  pauseForMutation();
  try {
    const result = await api("/api/route", { method: "POST", body: JSON.stringify({ task, session_id: byId("route-session").value.trim(), limit: 12 }) });
    renderReceipt(result);
    await reconcileRuntimeEvidence("Routing receipt completed.");
  } catch (error) { showNotice(error.message, true); byId("route-status").textContent = "FAILED"; }
  finally { byId("route-button").disabled = false; resumeAfterMutation(); }
}

async function trimRuntime() {
  const confirm = byId("trim-confirm").value;
  if (confirm !== "TRIM RUNTIME DATA") return showNotice("Enter the exact confirmation phrase.", true);
  const days = Number(byId("trim-days").value);
  if (!Number.isInteger(days) || days < 1 || days > 3650) {
    return showNotice("Older than days must be an integer from 1 through 3650.", true);
  }
  byId("trim-button").disabled = true;
  pauseForMutation();
  try {
    const result = await api("/api/maintenance/trim", { method: "POST", body: JSON.stringify({ confirm, older_than_days: days, vacuum: false }) });
    byId("trim-confirm").value = "";
    delete byId("trim-days").dataset.dirty;
    await reconcileAll(`Runtime evidence trimmed. Database is ${formatBytes(result.db_size_after_bytes)}.`);
  } catch (error) { showNotice(error.message, true); }
  finally { byId("trim-button").disabled = false; resumeAfterMutation(); }
}

function requiredConfigConfirmations(operations) {
  const confirmations = ["SAVE CONFIG"];
  if (operations.some((operation) => operation.op === "secret")) confirmations.push("SAVE SENSITIVE CONFIG");
  const profile = operations.find((operation) => operation.path === "profile");
  if (profile?.value === "local-only") confirmations.push("APPLY LOCAL-ONLY PROFILE");
  const capture = operations.find((operation) => operation.path === "observability.capture_content");
  if (capture?.value === true) confirmations.push("ENABLE CONTENT CAPTURE");
  return confirmations;
}

async function saveConfig(event) {
  event.preventDefault();
  let operations;
  try { operations = collectConfigChanges(); }
  catch (error) { return showNotice(error.message, true); }
  if (!operations.length) return;

  const confirmations = [];
  for (const phrase of requiredConfigConfirmations(operations)) {
    const accepted = await requestConfirmation(
      phrase,
      "Configuration changes are validated and written to your user configuration file.",
    );
    if (!accepted) return showNotice("Configuration save cancelled.", true);
    confirmations.push(phrase);
  }

  byId("config-save-button").disabled = true;
  pauseForMutation();
  try {
    const result = await api("/api/config", {
      method: "POST",
      body: JSON.stringify({
        expected_revision: state.config?.revision || "missing",
        operations,
        confirmations,
      }),
    });
    renderConfig(result);
    const restarts = result.restart_required_paths || [];
    const savedMessage = restarts.length
      ? `Configuration saved. Restart required for: ${restarts.join(", ")}.`
      : "Configuration saved and active.";
    await reconcileRuntimeEvidence(savedMessage);
  } catch (error) {
    showNotice(error.message, true);
    updateConfigDirtyState();
  } finally {
    resumeAfterMutation();
  }
}

async function rosterAction(action, snapshotId) {
  const expected = `${action.toUpperCase()} ${snapshotId}`;
  const accepted = await requestConfirmation(
    expected,
    `This will ${action} roster snapshot ${snapshotId}.`,
  );
  if (!accepted) return showNotice("Roster action cancelled.", true);
  pauseForMutation();
  try {
    await api("/api/roster/action", { method: "POST", body: JSON.stringify({ action, snapshot_id: snapshotId, confirm: expected }) });
    await reconcileAll(`Snapshot ${snapshotId} ${action}d.`);
  } catch (error) { showNotice(error.message, true); }
  finally { resumeAfterMutation(); }
}

async function toggleHost(host, enabled) {
  const expected = `${enabled ? "ENABLE" : "DISABLE"} ${host}`;
  const accepted = await requestConfirmation(
    expected,
    "This changes native host state. The host may require a restart.",
  );
  if (!accepted) return showNotice("Host action cancelled.", true);
  pauseForMutation();
  try {
    await api("/api/hosts/toggle", { method: "POST", body: JSON.stringify({ host, enabled, confirm: expected }) });
    await reconcileAll(`${host} ${enabled ? "enabled" : "disabled"}. Restart the host to finish activation.`);
  } catch (error) { showNotice(error.message, true); }
  finally { resumeAfterMutation(); }
}

function activateEvidenceTab(node, { focus = false } = {}) {
  const tabs = [...document.querySelectorAll(".subnav-item")];
  tabs.forEach((item) => {
    const active = item === node;
    item.classList.toggle("active", active);
    item.setAttribute("aria-selected", String(active));
    item.tabIndex = active ? 0 : -1;
  });
  const panel = byId("evidence-body")?.closest(".table-wrap");
  if (panel && node.id) panel.setAttribute("aria-labelledby", node.id);
  renderEvidence(node.dataset.evidence);
  if (focus) node.focus();
}

function configureEvidenceTabs() {
  const tabs = [...document.querySelectorAll(".subnav-item")];
  if (!tabs.length) return;
  tabs[0].parentElement?.setAttribute("role", "tablist");
  const panel = byId("evidence-body")?.closest(".table-wrap");
  if (panel) {
    panel.id ||= "evidence-ledger-panel";
    panel.setAttribute("role", "tabpanel");
  }
  tabs.forEach((node, index) => {
    node.id ||= `evidence-tab-${node.dataset.evidence || index}`;
    node.setAttribute("role", "tab");
    node.setAttribute("aria-controls", panel?.id || "evidence-ledger-panel");
    const active = node.classList.contains("active");
    node.setAttribute("aria-selected", String(active));
    node.tabIndex = active ? 0 : -1;
    node.addEventListener("click", () => activateEvidenceTab(node));
    node.addEventListener("keydown", (event) => {
      let target = null;
      if (event.key === "ArrowRight" || event.key === "ArrowDown") target = tabs[(index + 1) % tabs.length];
      else if (event.key === "ArrowLeft" || event.key === "ArrowUp") target = tabs[(index - 1 + tabs.length) % tabs.length];
      else if (event.key === "Home") target = tabs[0];
      else if (event.key === "End") target = tabs[tabs.length - 1];
      else if (event.key === "Enter" || event.key === " ") target = node;
      if (!target) return;
      event.preventDefault();
      activateEvidenceTab(target, { focus: true });
    });
  });
  const active = tabs.find((node) => node.getAttribute("aria-selected") === "true") || tabs[0];
  if (panel && active?.id) {
    panel.setAttribute("aria-labelledby", active.id);
    panel.tabIndex = 0;
  }
}

function setLiveEnabled(enabled) {
  state.live.enabled = Boolean(enabled);
  syncLiveToggle();
  if (!state.live.enabled) {
    cancelLiveRequest();
    cancelControlRequest();
    setLiveStatus("Live updates paused", "paused", { announce: true });
    return;
  }
  state.live.terminal = false;
  state.live.failures = 0;
  setLiveStatus("Connecting live updates", "connecting", { announce: true });
  scheduleLive(0);
  scheduleControlRefresh(0);
}

function handleVisibilityChange() {
  if (document.visibilityState === "hidden") {
    window.clearTimeout(state.clockTimer);
    state.clockTimer = null;
    cancelLiveRequest();
    cancelControlRequest();
    if (state.live.enabled && !state.live.terminal) {
      setLiveStatus("Paused while this tab is hidden", "paused");
    }
    return;
  }
  updateLocalClock();
  if (state.live.enabled && !state.live.terminal) {
    setLiveStatus("Syncing live activity", "connecting");
    scheduleLive(0);
    scheduleControlRefresh(0);
  }
}

function handlePageShow(event) {
  if (!event.persisted) return;
  if (!state.full.inFlight) byId("refresh-button").disabled = false;
  updateLocalClock();
  if (!state.live.enabled || state.live.terminal) return;
  scheduleLive(0);
  scheduleControlRefresh(0);
}

function bindEvents() {
  document.querySelectorAll(".nav-item").forEach((node) => node.addEventListener("click", () => switchView(node.dataset.view)));
  configureEvidenceTabs();
  byId("refresh-button").addEventListener("click", refreshAll);
  byId("route-button").addEventListener("click", runRoute);
  byId("trim-button").addEventListener("click", trimRuntime);
  byId("trim-days").addEventListener("input", () => {
    byId("trim-days").dataset.dirty = "true";
  });
  byId("config-form").addEventListener("submit", saveConfig);
  byId("config-form").addEventListener("input", updateConfigDirtyState);
  byId("config-form").addEventListener("change", updateConfigDirtyState);
  byId("config-reset-button").addEventListener("click", () => {
    const snapshot = state.pendingConfig || state.config;
    if (snapshot) renderConfig(snapshot);
  });
  byId("confirmation-cancel").addEventListener("click", () => finishConfirmation(false));
  byId("confirmation-accept").addEventListener("click", () => finishConfirmation(true));
  byId("confirmation-input").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      finishConfirmation(true);
    } else if (event.key === "Escape") {
      event.preventDefault();
      finishConfirmation(false);
    }
  });
  document.addEventListener("keydown", handleModalKeyboard);
  const liveToggle = byId("live-toggle");
  if (liveToggle) {
    state.live.enabled = liveToggle.getAttribute("aria-pressed") !== "false";
    syncLiveToggle();
    liveToggle.addEventListener("click", () => setLiveEnabled(!state.live.enabled));
  }
  document.addEventListener("visibilitychange", handleVisibilityChange);
  window.addEventListener("pagehide", () => {
    window.clearTimeout(state.clockTimer);
    state.clockTimer = null;
    cancelLiveRequest();
    cancelControlRequest();
    cancelFullRefresh();
  });
  window.addEventListener("pageshow", handlePageShow);
  switchView(document.querySelector(".nav-item.active")?.dataset.view || "overview");
}

document.addEventListener("DOMContentLoaded", async () => {
  bindEvents();
  updateLocalClock();
  try { installToken(); await refreshAll(); } catch (error) { showNotice(error.message, true); byId("connection-label").textContent = "Token required"; }
});
