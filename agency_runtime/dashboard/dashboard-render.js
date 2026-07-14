"use strict";

const EVIDENCE_COLUMNS = {
  delegations: [["recommended_agent", "Agent"], ["host", "Host"], ["status", "Status"], ["backend", "Backend"], ["work_unit_id", "Work unit"], ["started_at", "Started"]],
  routing: [["trace_id", "Trace"], ["id", "Decision"], ["status", "Status"], ["source", "Source"], ["selected_ids", "Selected"], ["created_at", "Created"]],
  receipts: [["resolved_model", "Resolved model"], ["resolved_provider", "Provider"], ["host", "Host"], ["status", "Status"], ["source", "Source"], ["ended_at", "Ended"]],
  runs: [["trace_id", "Trace"], ["session_id", "Session"], ["host", "Host"], ["status", "Status"], ["started_at", "Started"], ["ended_at", "Ended"]],
  finalizations: [["trace_id", "Trace"], ["host", "Host"], ["action", "Action"], ["missing", "Missing"], ["created_at", "Created"]],
};

export function createRenderer(core, config, callbacks) {
  const {
    runtime,
    document,
    window,
    state,
    byId,
    el,
    formatBytes,
    formatTime,
    hostState,
    hostLocation,
    truthLabel,
    listen,
  } = core;
  const animationListeners = new Map();
  const configuredTabs = new WeakSet();

  function reducedMotionPreferred() {
    return typeof window.matchMedia === "function"
      && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  }

  function markUpdated(node, className = "is-updated") {
    if (!node || reducedMotionPreferred()) return;
    const previous = animationListeners.get(node);
    if (previous) {
      node.removeEventListener("animationend", previous.listener);
      node.classList.remove(previous.className);
    }
    node.classList.remove(className);
    void node.offsetWidth;
    node.classList.add(className);
    const finished = () => {
      node.classList.remove(className);
      if (animationListeners.get(node)?.listener === finished) animationListeners.delete(node);
    };
    animationListeners.set(node, { className, listener: finished });
    node.addEventListener("animationend", finished, { once: true });
  }

  function disposeAnimations() {
    animationListeners.forEach(({ className, listener }, node) => {
      node.removeEventListener("animationend", listener);
      node.classList.remove(className);
    });
    animationListeners.clear();
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
    const charts = runtime.AgencyCharts;
    if (!charts) return;
    const buckets = charts.renderActivityChart(
      byId("activity-chart"),
      byId("activity-chart-summary"),
      state.activity,
      { now: state.live.sampledAt || Date.now(), bucketCount: 24, bucketMs: 60000 },
    );
    const outcomes = charts.renderOutcomeChart(
      byId("outcome-chart"),
      byId("outcome-chart-summary"),
      state.activity,
    );
    const sampled = Date.parse(state.live.sampledAt || "");
    state.live.chartWindow = Number.isFinite(sampled) ? Math.floor(sampled / 60000) : null;
    const bucketMinutes = buckets.length
      ? Math.round((buckets.length * (buckets[0].endMs - buckets[0].startMs)) / 60000)
      : 0;
    const sampledLabel = Number.isFinite(sampled)
      ? new Date(sampled).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
      : "pending";
    const windowLabel = byId("window-label");
    if (windowLabel) {
      windowLabel.textContent = `${bucketMinutes} min window · sampled ${sampledLabel}`;
      windowLabel.title = `Bounded runtime evidence sampled at ${sampledLabel}`;
    }
    [
      ["outcome-success", outcomes.success],
      ["outcome-failed", outcomes.failed],
      ["outcome-skipped", outcomes.skipped],
      ["outcome-unknown", outcomes.unknown],
    ].forEach(([id, value]) => {
      const node = byId(id);
      if (node) node.textContent = String(value);
    });
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

  function emptyRow(columns, message) {
    const tr = el("tr");
    const td = el("td", "", message);
    td.colSpan = columns;
    tr.append(td);
    return tr;
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

    const tbody = byId("overview-delegations");
    tbody.replaceChildren();
    const previousOverviewKeys = state.evidenceKeys.get("overview") || new Set();
    const nextOverviewKeys = new Set();
    (state.activity.delegations || []).slice(0, 12).forEach((row, index) => {
      const tr = el("tr");
      const key = evidenceRowKey(row, index);
      nextOverviewKeys.add(key);
      if (previousOverviewKeys.size && !previousOverviewKeys.has(key)) tr.classList.add("is-new");
      [row.recommended_agent || "unassigned", row.host || "unknown"].forEach((value) => {
        tr.append(el("td", "", value));
      });
      const status = el("span", `status ${row.status || ""}`, row.status || "unknown");
      const statusCell = el("td");
      statusCell.append(status);
      tr.append(statusCell);
      tr.append(el("td", "", row.backend || "—"), el("td", "", formatTime(row.started_at)));
      tbody.append(tr);
    });
    state.evidenceKeys.set("overview", nextOverviewKeys);
    if (!tbody.children.length) tbody.append(emptyRow(5, "No delegation evidence yet."));

    const hostStack = byId("overview-hosts");
    hostStack.replaceChildren();
    state.hosts.forEach((host) => {
      const row = el("div", "host-row");
      const current = hostState(host);
      const copy = el("div");
      copy.append(el("strong", "", host.host), el("small", "", hostLocation(host)));
      row.append(copy, el("span", `host-state ${current}`, current));
      hostStack.append(row);
    });

    const providerStack = byId("provider-health");
    providerStack.replaceChildren();
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
    if (!providerStack.children.length) {
      providerStack.append(el("div", "empty-compact", "No provider receipts observed."));
    }
    renderCharts();
  }

  function renderHosts() {
    const grid = byId("host-grid");
    grid.replaceChildren();
    state.hosts.forEach((host) => {
      const card = el("article", "host-card");
      const heading = el("div", "host-row");
      const current = hostState(host);
      heading.append(el("strong", "", host.host), el("span", `host-state ${current}`, current));
      card.append(heading, el("small", "", hostLocation(host)));
      const tags = el("div", "token-list");
      tags.append(el("span", "token", truthLabel(host.registered, "registered", "not registered", "registration unknown")));
      tags.append(el("span", "token", truthLabel(host.enabled, "native enabled", "native disabled", "native enablement unknown")));
      tags.append(el("span", "token", host.runtime_enabled === false ? "runtime off" : "runtime on"));
      tags.append(el("span", "token", truthLabel(host.effective_enabled, "effective", "inactive", "effective state unverified")));
      tags.append(el("span", "token", host.maturity || "unverified"));
      card.append(tags);
      if (host.executable_discovered === true) {
        const actions = el("div", "card-actions");
        const inspectionCurrent = !host.inspection_status || host.inspection_status === "complete";
        const directionKnown = inspectionCurrent && typeof host.runtime_enabled === "boolean";
        const enabled = host.runtime_enabled === true;
        const label = directionKnown
          ? (enabled ? "Disable" : "Enable")
          : (!inspectionCurrent ? "Inspection stale" : "State unknown");
        const button = el("button", `button compact ${enabled ? "danger" : "solid"}`, label);
        button.type = "button";
        button.disabled = !directionKnown;
        if (directionKnown) {
          button.addEventListener("click", () => callbacks.toggleHost(host.host, !enabled));
        } else {
          button.title = "A current host inspection is required before this action is available.";
        }
        actions.append(button);
        card.append(actions);
      }
      grid.append(card);
    });
  }

  function renderRoster() {
    const grid = byId("roster-grid");
    grid.replaceChildren();
    const pageCount = Number.isInteger(state.rosterPage?.count)
      ? state.rosterPage.count
      : state.roster.length;
    const totalCount = Number.isInteger(state.rosterPage?.total_count)
      ? state.rosterPage.total_count
      : pageCount;
    const truncated = state.rosterPage?.truncated === true;
    byId("roster-count").textContent = truncated
      ? `${pageCount} / ${totalCount}`
      : String(totalCount);
    const pageStatus = byId("roster-page-status");
    if (pageStatus) {
      pageStatus.hidden = !truncated;
      if (truncated) {
        const remaining = Math.max(0, totalCount - pageCount);
        const cursor = state.rosterPage?.next_cursor;
        const limit = state.rosterPage?.limit || pageCount;
        const continuation = cursor
          ? `/api/roster?after=${encodeURIComponent(cursor)}&limit=${limit}`
          : "/api/roster when next_cursor is available";
        pageStatus.textContent = `Showing ${pageCount} of ${totalCount} active specialists; ${remaining} are not shown on this page. Continue with ${continuation}.`;
      } else pageStatus.textContent = "";
    }
    state.roster.forEach((agent) => {
      const card = el("article", "agent-card");
      card.append(
        el("strong", "", agent.name || agent.agent_slug),
        el("small", "", `${agent.agent_slug} · ${agent.division || "unassigned"}`),
      );
      const tags = el("div", "token-list");
      (agent.capabilities || []).slice(0, 4).forEach((value) => {
        tags.append(el("span", "token", value));
      });
      if (!tags.children.length) tags.append(el("span", "token", "no capability tags"));
      card.append(tags);
      grid.append(card);
    });
    const list = byId("snapshot-list");
    list.replaceChildren();
    state.snapshots.forEach((snapshot) => {
      const row = el("div", "stack-item");
      const copy = el("div");
      copy.append(
        el("strong", "", snapshot.snapshot_id),
        el("small", "", `${snapshot.agent_count || 0} agents · ${formatTime(snapshot.created_at)}`),
      );
      const status = snapshot.activated ? "activated" : snapshot.approved ? "approved" : "pending";
      const controls = el("div", "card-actions");
      controls.append(el("span", `host-state ${snapshot.activated ? "verified" : ""}`, status));
      if (!snapshot.activated) {
        const action = snapshot.approved ? "activate" : "approve";
        const button = el("button", "button compact ghost", action);
        button.type = "button";
        button.addEventListener("click", () => callbacks.rosterAction(action, snapshot.snapshot_id));
        controls.append(button);
      }
      row.append(copy, controls);
      list.append(row);
    });
    if (!list.children.length) list.append(el("div", "empty-state", "No roster snapshots."));
  }

  function renderEvidence(kind = "delegations") {
    const columns = EVIDENCE_COLUMNS[kind];
    const label = kind.endsWith("s") ? kind.slice(0, -1) : kind;
    const head = byId("evidence-head");
    const body = byId("evidence-body");
    head.replaceChildren();
    body.replaceChildren();
    const caption = byId("evidence-caption");
    if (caption) caption.textContent = `${label[0].toUpperCase()}${label.slice(1)} runtime evidence`;
    const trh = el("tr");
    columns.forEach(([, columnLabel]) => {
      const heading = el("th", "", columnLabel);
      heading.setAttribute("scope", "col");
      trh.append(heading);
    });
    head.append(trh);
    const previousKeys = state.evidenceKeys.get(kind) || new Set();
    const nextKeys = new Set();
    (state.activity[kind] || []).forEach((row, index) => {
      const tr = el("tr");
      const key = evidenceRowKey(row, index);
      nextKeys.add(key);
      if (previousKeys.size && !previousKeys.has(key)) tr.classList.add("is-new");
      columns.forEach(([columnKey]) => {
        let value = row[columnKey];
        if (Array.isArray(value)) value = value.join(", ") || "—";
        if (columnKey.endsWith("_at") || columnKey === "created_at") value = formatTime(value);
        const td = el("td");
        if (columnKey === "status" || columnKey === "action") {
          td.append(el("span", `status ${value || ""}`, value || "—"));
        } else td.textContent = value || "—";
        tr.append(td);
      });
      body.append(tr);
    });
    state.evidenceKeys.set(kind, nextKeys);
    if (!body.children.length) body.append(emptyRow(columns.length, `No ${label} evidence yet.`));
  }

  function renderReceipt(receipt) {
    const root = byId("route-result");
    root.className = "receipt";
    root.replaceChildren();
    const selected = (receipt.selected || [])
      .map((item) => item.slug || item.agent_slug || item.id)
      .filter(Boolean);
    const workUnits = receipt.signals?.delegation?.work_units?.units
      || receipt.signals?.work_units?.units
      || receipt.work_units?.units
      || [];
    const blocks = [
      ["Status", receipt.status || receipt.signals?.selection?.status || "unknown"],
      ["Selected specialists", selected.length ? selected : ["abstained"]],
      ["Policy actions", receipt.signals?.policy?.matched_actions || []],
      ["Work units", workUnits],
      ["Decision source", receipt.signals?.selection?.provider || receipt.provider || "deterministic"],
    ];
    blocks.forEach(([label, value]) => {
      const block = el("div", "receipt-block");
      block.append(el("span", "", label));
      if (Array.isArray(value)) {
        const list = el("div", "token-list");
        (value.length ? value : ["none"]).forEach((item) => {
          list.append(el("span", "token", typeof item === "string" ? item : JSON.stringify(item)));
        });
        block.append(list);
      } else block.append(el("p", "", value));
      root.append(block);
    });
    const graph = receipt.delegation_graph || {};
    const graphNodes = Array.isArray(graph.nodes) ? graph.nodes : [];
    const graphEdges = Array.isArray(graph.edges) ? graph.edges : [];
    const graphBlock = el("div", "receipt-block dependency-graph");
    graphBlock.append(el("span", "", "Delegation dependency graph"));
    if (!graphNodes.length) {
      graphBlock.append(el("p", "", "No delegation work units detected."));
    } else {
      const nodes = el("div", "dependency-nodes");
      graphNodes.forEach((node) => {
        const item = el("div", "dependency-node");
        item.append(el("strong", "", node.id), el("small", "", node.description));
        nodes.append(item);
      });
      graphBlock.append(nodes);
      const edges = el("div", "dependency-edges");
      if (graphEdges.length) {
        graphEdges.forEach((edge) => {
          edges.append(el("small", "", `${edge.from} → ${edge.to} · ${edge.reason}`));
        });
      } else {
        edges.append(el("small", "", "No dependency edges; detected units can run independently."));
      }
      graphBlock.append(edges);
    }
    root.append(graphBlock);
    byId("route-status").textContent = String(
      receipt.status || receipt.signals?.selection?.status || "complete",
    ).toUpperCase();
  }

  function activeEvidenceKind() {
    return document.querySelector(".subnav-item.active")?.dataset.evidence || "delegations";
  }

  function renderActiveView() {
    if (state.activeView === "overview" && state.overview) renderOverview();
    else if (state.activeView === "evidence") renderEvidence(activeEvidenceKind());
    else if (state.activeView === "hosts") renderHosts();
    else if (state.activeView === "roster") renderRoster();
  }

  function renderActiveControlView() {
    if (state.activeView === "overview" && state.overview) renderOverview();
    else if (state.activeView === "hosts") renderHosts();
    else if (state.activeView === "roster") renderRoster();
  }

  function switchView(name) {
    state.activeView = name;
    document.querySelectorAll(".nav-item").forEach((node) => {
      const active = node.dataset.view === name;
      node.classList.toggle("active", active);
      if (active) node.setAttribute("aria-current", "page");
      else node.removeAttribute("aria-current");
    });
    document.querySelectorAll(".view").forEach((node) => {
      const active = node.dataset.viewPanel === name;
      node.classList.toggle("active", active);
      node.hidden = !active;
      node.setAttribute("aria-hidden", String(!active));
    });
    const titles = {
      overview: "Runtime overview",
      routing: "Routing lab",
      evidence: "Evidence ledger",
      roster: "Roster governance",
      hosts: "Host integrations",
      settings: "Settings & retention",
    };
    byId("view-title").textContent = titles[name] || "Agency Runtime";
    if (name === "settings" && state.pendingConfig && !state.configDirty) {
      config.renderConfig(state.pendingConfig);
    }
    renderActiveView();
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
      if (configuredTabs.has(node)) return;
      configuredTabs.add(node);
      listen(node, "click", () => activateEvidenceTab(node));
      listen(node, "keydown", (event) => {
        let target = null;
        if (event.key === "ArrowRight" || event.key === "ArrowDown") {
          target = tabs[(index + 1) % tabs.length];
        } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
          target = tabs[(index - 1 + tabs.length) % tabs.length];
        } else if (event.key === "Home") target = tabs[0];
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

  return {
    reducedMotionPreferred,
    markUpdated,
    disposeAnimations,
    setMetric,
    renderCharts,
    renderOverview,
    emptyRow,
    renderHosts,
    renderRoster,
    renderEvidence,
    renderReceipt,
    renderActiveView,
    renderActiveControlView,
    evidenceRowKey,
    activeEvidenceKind,
    switchView,
    activateEvidenceTab,
    configureEvidenceTabs,
  };
}
