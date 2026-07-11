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
  confirmation: null,
};

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
  if (state.confirmation) state.confirmation.resolve(false);
  return new Promise((resolve) => {
    state.confirmation = { phrase, resolve };
    byId("confirmation-title").textContent = "Confirm this operation";
    byId("confirmation-message").textContent = message;
    byId("confirmation-phrase").textContent = phrase;
    byId("confirmation-input").value = "";
    byId("confirmation-error").hidden = true;
    byId("confirmation-modal").hidden = false;
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
  pending.resolve(accepted);
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

async function api(path, options = {}) {
  const headers = { Authorization: `Bearer ${state.token}`, ...(options.headers || {}) };
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  const response = await fetch(path, { ...options, headers });
  let payload;
  try { payload = await response.json(); } catch { payload = { error: `HTTP ${response.status}` }; }
  if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
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
    byId("config-change-count").textContent = error.message;
    byId("config-save-button").disabled = true;
    return;
  }
  const count = operations.length;
  byId("config-change-count").textContent = count ? `${count} unsaved change${count === 1 ? "" : "s"}` : "No unsaved changes";
  byId("config-save-button").disabled = count === 0;
}

function renderConfig(snapshot) {
  const effective = snapshot.effective || snapshot.config || {};
  state.config = snapshot;
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

function switchView(name) {
  document.querySelectorAll(".nav-item").forEach((node) => node.classList.toggle("active", node.dataset.view === name));
  document.querySelectorAll(".view").forEach((node) => node.classList.toggle("active", node.dataset.viewPanel === name));
  const titles = { overview: "Runtime overview", routing: "Routing lab", evidence: "Evidence ledger", roster: "Roster governance", hosts: "Host integrations", settings: "Settings & retention" };
  byId("view-title").textContent = titles[name] || "Agency Runtime";
}

function renderOverview() {
  const data = state.overview || {};
  byId("metric-runtime").textContent = data.status === "ok" ? "Online" : "Unknown";
  byId("metric-roster").textContent = data.roster_count ?? "—";
  byId("metric-routing").textContent = data.recent?.routing ?? "—";
  byId("metric-delegations").textContent = data.recent?.delegations ?? "—";
  byId("metric-store").textContent = formatBytes((data.db_size_bytes || 0) + (data.wal_size_bytes || 0));
  byId("setting-capture").textContent = data.capture_content ? "Opt-in enabled" : "Disabled";
  byId("setting-retention").textContent = `${data.retention_days || 30} days`;
  byId("privacy-chip").textContent = data.capture_content ? "Redacted content" : "Metadata only";
  byId("trim-days").value = data.retention_days || 30;

  const tbody = byId("overview-delegations"); tbody.replaceChildren();
  (state.activity.delegations || []).slice(0, 12).forEach((row) => {
    const tr = el("tr");
    [row.recommended_agent || "unassigned", row.host || "unknown"].forEach((value) => tr.append(el("td", "", value)));
    const status = el("span", `status ${row.status || ""}`, row.status || "unknown");
    const statusCell = el("td"); statusCell.append(status); tr.append(statusCell);
    tr.append(el("td", "", row.backend || "—"), el("td", "", formatTime(row.started_at)));
    tbody.append(tr);
  });
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
  (state.activity[kind] || []).forEach((row) => {
    const tr = el("tr");
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

async function refreshAll() {
  byId("refresh-button").disabled = true;
  try {
    const [overview, activity, hosts, roster, snapshots, config] = await Promise.all([
      api("/api/overview"), api("/api/activity?limit=100"), api("/api/hosts"), api("/api/roster"), api("/api/snapshots"), api("/api/config"),
    ]);
    state.overview = overview; state.activity = activity; state.hosts = hosts.hosts || []; state.roster = roster.agents || []; state.snapshots = snapshots.snapshots || [];
    renderConfig(config);
    document.querySelector(".rail-foot").classList.add("connected"); byId("connection-label").textContent = "Authenticated";
    renderOverview(); renderHosts(); renderRoster(); renderEvidence(document.querySelector(".subnav-item.active").dataset.evidence);
  } catch (error) {
    document.querySelector(".rail-foot").classList.remove("connected"); byId("connection-label").textContent = "Unavailable"; showNotice(error.message, true);
  } finally { byId("refresh-button").disabled = false; }
}

async function refreshRuntimeEvidence() {
  const [overview, activity] = await Promise.all([
    api("/api/overview"),
    api("/api/activity?limit=100"),
  ]);
  state.overview = overview;
  state.activity = activity;
  renderOverview();
  renderEvidence(document.querySelector(".subnav-item.active").dataset.evidence);
}

async function runRoute() {
  const task = byId("route-task").value.trim();
  if (!task) return showNotice("Enter a task before running the routing lab.", true);
  byId("route-button").disabled = true; byId("route-status").textContent = "RUNNING";
  try {
    const result = await api("/api/route", { method: "POST", body: JSON.stringify({ task, session_id: byId("route-session").value.trim(), limit: 12 }) });
    renderReceipt(result);
    await refreshRuntimeEvidence();
  } catch (error) { showNotice(error.message, true); byId("route-status").textContent = "FAILED"; }
  finally { byId("route-button").disabled = false; }
}

async function trimRuntime() {
  const confirm = byId("trim-confirm").value;
  if (confirm !== "TRIM RUNTIME DATA") return showNotice("Enter the exact confirmation phrase.", true);
  const days = Number(byId("trim-days").value);
  if (!Number.isInteger(days) || days < 1 || days > 3650) {
    return showNotice("Older than days must be an integer from 1 through 3650.", true);
  }
  byId("trim-button").disabled = true;
  try {
    const result = await api("/api/maintenance/trim", { method: "POST", body: JSON.stringify({ confirm, older_than_days: days, vacuum: false }) });
    byId("trim-confirm").value = ""; showNotice(`Runtime evidence trimmed. Database is ${formatBytes(result.db_size_after_bytes)}.`); await refreshAll();
  } catch (error) { showNotice(error.message, true); }
  finally { byId("trim-button").disabled = false; }
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
    showNotice(restarts.length
      ? `Configuration saved. Restart required for: ${restarts.join(", ")}.`
      : "Configuration saved and active.");
    await refreshRuntimeEvidence();
  } catch (error) {
    showNotice(error.message, true);
    updateConfigDirtyState();
  }
}

async function rosterAction(action, snapshotId) {
  const expected = `${action.toUpperCase()} ${snapshotId}`;
  const accepted = await requestConfirmation(
    expected,
    `This will ${action} roster snapshot ${snapshotId}.`,
  );
  if (!accepted) return showNotice("Roster action cancelled.", true);
  try {
    await api("/api/roster/action", { method: "POST", body: JSON.stringify({ action, snapshot_id: snapshotId, confirm: expected }) });
    showNotice(`Snapshot ${snapshotId} ${action}d.`); await refreshAll();
  } catch (error) { showNotice(error.message, true); }
}

async function toggleHost(host, enabled) {
  const expected = `${enabled ? "ENABLE" : "DISABLE"} ${host}`;
  const accepted = await requestConfirmation(
    expected,
    "This changes native host state. The host may require a restart.",
  );
  if (!accepted) return showNotice("Host action cancelled.", true);
  try {
    await api("/api/hosts/toggle", { method: "POST", body: JSON.stringify({ host, enabled, confirm: expected }) });
    showNotice(`${host} ${enabled ? "enabled" : "disabled"}. Restart the host to finish activation.`); await refreshAll();
  } catch (error) { showNotice(error.message, true); }
}

function bindEvents() {
  document.querySelectorAll(".nav-item").forEach((node) => node.addEventListener("click", () => switchView(node.dataset.view)));
  document.querySelectorAll(".subnav-item").forEach((node) => node.addEventListener("click", () => {
    document.querySelectorAll(".subnav-item").forEach((item) => item.classList.toggle("active", item === node)); renderEvidence(node.dataset.evidence);
  }));
  byId("refresh-button").addEventListener("click", refreshAll);
  byId("route-button").addEventListener("click", runRoute);
  byId("trim-button").addEventListener("click", trimRuntime);
  byId("config-form").addEventListener("submit", saveConfig);
  byId("config-form").addEventListener("input", updateConfigDirtyState);
  byId("config-form").addEventListener("change", updateConfigDirtyState);
  byId("config-reset-button").addEventListener("click", () => {
    if (state.config) renderConfig(state.config);
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
}

document.addEventListener("DOMContentLoaded", async () => {
  bindEvents();
  try { installToken(); await refreshAll(); } catch (error) { showNotice(error.message, true); byId("connection-label").textContent = "Token required"; }
});
