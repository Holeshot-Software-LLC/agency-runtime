"use strict";

import { APIError, CONTROL_INTERVAL_MS, LIVE_INTERVAL_MS } from "./dashboard-core.js";

export function createLiveController(core, config, renderer) {
  const {
    runtime,
    document,
    window,
    AbortController,
    state,
    byId,
    api,
    showNotice,
    nestedValue,
  } = core;
  const AGENT_SLUG_PATTERN = /^[a-z0-9][a-z0-9._-]{1,127}$/;

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
    if (
      state.lifecycle.destroyed
      || state.lifecycle.suspended
      || document.visibilityState === "hidden"
    ) return;
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
    if (toggle instanceof core.HTMLInputElement && toggle.type === "checkbox") {
      toggle.checked = state.live.enabled;
    }
  }

  function syncMasterControl() {
    const master = state.master;
    const known = Boolean(master);
    const enabled = known ? master.enabled === true : null;
    const toggle = byId("master-toggle");
    if (toggle) {
      if (known) toggle.setAttribute("aria-pressed", String(enabled));
      else toggle.removeAttribute("aria-pressed");
      toggle.setAttribute(
        "aria-label",
        !known
          ? "Agency master state loading"
          : enabled
            ? "Disable Agency Runtime globally"
            : "Enable Agency Runtime globally",
      );
      toggle.dataset.state = !known ? "loading" : enabled ? "enabled" : "disabled";
      if (toggle.getAttribute("aria-busy") !== "true") toggle.disabled = !known;
      toggle.title = known
        ? `Generation ${master.generation} · ${enabled ? "Agency is active" : "Agency is bypassed"}`
        : "Loading Agency master state";
    }
    if (byId("master-label")) {
      byId("master-label").textContent = !known
        ? "Agency status"
        : enabled
          ? "Agency on"
          : "Agency off";
    }
    if (byId("master-generation")) {
      byId("master-generation").textContent = known ? `GEN ${master.generation}` : "LOADING";
    }
    if (byId("master-summary")) {
      byId("master-summary").textContent = !known
        ? "Loading Agency master state."
        : enabled
          ? "Agency routing, delegation, and evidence shaping are active."
          : "Agency is bypassed. Dashboard status and configuration remain available.";
    }
    if (byId("runtime-paused-banner")) {
      byId("runtime-paused-banner").hidden = !known || enabled;
    }
    const shell = document.querySelector(".shell");
    shell?.classList.toggle("agency-paused", known && !enabled);
    if (shell) shell.dataset.agencyState = !known ? "loading" : enabled ? "enabled" : "disabled";
    const routeButton = byId("route-button");
    const routeHost = byId("route-host");
    const storeRestartRequired = config.serviceRestartRequired();
    const routeHostAvailable = Boolean(routeHost?.value);
    if (routeHost) {
      routeHost.disabled = !known || !enabled || storeRestartRequired || !routeHostAvailable;
    }
    if (routeButton && routeButton.getAttribute("aria-busy") !== "true") {
      routeButton.disabled = !known || !enabled || storeRestartRequired || !routeHostAvailable;
      routeButton.setAttribute("aria-disabled", String(routeButton.disabled));
      routeButton.title = storeRestartRequired
        ? "Restart the dashboard service to use Route Lab."
        : !known
        ? "Loading Agency master state"
        : enabled && routeHostAvailable
          ? `Run a routing explanation for ${routeHost.value}`
          : enabled
            ? "A verified and enabled execution host is required"
          : "Enable Agency Runtime to use Route Lab";
    }
    if (known && !enabled && byId("route-status")) {
      byId("route-status").textContent = "BYPASSED";
    } else if (known && enabled && byId("route-status")?.textContent === "BYPASSED") {
      byId("route-status").textContent = "IDLE";
    }
  }

  function applyMasterState(master) {
    if (master === undefined || master === null) return false;
    if (
      typeof master !== "object"
      || typeof master.enabled !== "boolean"
      || !Number.isInteger(master.generation)
      || master.generation < 0
    ) {
      throw new Error("Unsupported Agency master-state response.");
    }
    if (
      state.master
      && Number.isInteger(state.master.generation)
      && master.generation < state.master.generation
    ) return false;
    const changed = !state.master
      || state.master.enabled !== master.enabled
      || state.master.generation !== master.generation;
    state.master = { ...master };
    syncMasterControl();
    return changed;
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
    const wasInFlight = state.full.inFlight;
    state.full.controller = null;
    state.full.inFlight = false;
    if (controller) controller.abort();
    if (wasInFlight) byId("refresh-button").disabled = false;
  }

  function cancelMutationRequests() {
    const hadActiveMutations = state.mutation.active > 0;
    state.mutation.controllers.forEach((controller) => controller.abort());
    state.mutation.controllers.clear();
    state.mutation.active = 0;
    if (hadActiveMutations) byId("refresh-button").disabled = false;
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

  function beginMutation() {
    pauseForMutation();
    const controller = new AbortController();
    state.mutation.controllers.add(controller);
    state.mutation.active += 1;
    return controller;
  }

  function mutationIsCurrent(controller) {
    return !state.lifecycle.destroyed
      && !state.lifecycle.suspended
      && !controller.signal.aborted
      && state.mutation.controllers.has(controller);
  }

  function finishMutation(controller) {
    if (!state.mutation.controllers.delete(controller)) return false;
    state.mutation.active = Math.max(0, state.mutation.active - 1);
    if (state.mutation.active === 0) resumeAfterMutation();
    return true;
  }

  function liveCanRun() {
    return state.live.enabled
      && !state.live.terminal
      && !state.lifecycle.destroyed
      && !state.lifecycle.suspended
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

  function applyLiveSnapshot(payload, { render = true } = {}) {
    if (!payload || payload.schema_version !== 1) {
      throw new Error("Unsupported live dashboard response.");
    }
    state.live.sampledAt = payload.sampled_at || new Date().toISOString();
    updateLastSync(state.live.sampledAt);
    const masterChanged = applyMasterState(payload.master);
    if (payload.revision === state.live.revision) {
      const sampled = Date.parse(state.live.sampledAt);
      const chartWindow = Number.isFinite(sampled) ? Math.floor(sampled / 60000) : null;
      if (
        render
        && state.activeView === "overview"
        && chartWindow !== state.live.chartWindow
      ) renderer.renderCharts();
      if (masterChanged && render) renderer.renderActiveView();
      return masterChanged;
    }
    state.live.revision = String(payload.revision || "");
    state.overview = { ...(state.overview || {}), ...(payload.overview || {}) };
    state.activity = payload.activity || {};
    if (render) renderer.renderActiveView();
    return true;
  }

  function terminalLiveFailure(error) {
    return error instanceof APIError && (error.status === 401 || error.status === 403);
  }

  function handleLiveFailure(error) {
    if (error?.name === "AbortError" || state.lifecycle.destroyed) return;
    if (terminalLiveFailure(error)) {
      state.live.terminal = true;
      cancelLiveRequest();
      setConnection(false, "Token expired");
      setLiveStatus("Access expired · reopen from the CLI", "expired", { announce: true });
      showNotice(
        "The dashboard token expired. Run `agency dashboard service open` to reconnect.",
        true,
      );
      return;
    }
    state.live.failures += 1;
    const retry = runtime.AgencyCharts?.retryDelay
      ? runtime.AgencyCharts.retryDelay(state.live.failures)
      : Math.min(30000, 2000 * (2 ** Math.min(state.live.failures - 1, 4)));
    setConnection(false, "Reconnecting");
    setLiveStatus(
      `Reconnecting in ${Math.ceil(retry / 1000)}s`,
      "retrying",
      { announce: state.live.failures === 1 },
    );
    if (state.live.failures === 1) {
      showNotice("Live updates paused while the dashboard reconnects.", true);
    }
    scheduleLive(retry);
  }

  async function runLivePoll() {
    state.live.timer = null;
    if (!liveCanRun() || state.live.inFlight) return;
    try {
      const payload = await fetchLiveSnapshot();
      if (!payload || !liveCanRun()) return;
      applyLiveSnapshot(payload);
      state.live.failures = 0;
      setConnection(true, "Authenticated");
      setLiveStatus("Live · authenticated", "live", { announce: true });
      scheduleLive(LIVE_INTERVAL_MS);
    } catch (error) {
      handleLiveFailure(error);
    }
  }

  function scheduleControlRefresh(delay = CONTROL_INTERVAL_MS) {
    window.clearTimeout(state.control.timer);
    state.control.timer = null;
    if (!liveCanRun()) return;
    state.control.timer = window.setTimeout(refreshControlPlane, Math.max(0, delay));
  }

  function pageInteger(value, fallback, minimum = 0) {
    return Number.isInteger(value) && value >= minimum ? value : fallback;
  }

  function applyRosterPage(payload = {}) {
    const agents = Array.isArray(payload.agents) ? payload.agents : [];
    const count = pageInteger(payload.count, agents.length);
    const rosterPage = {
      agents,
      count,
      total_count: pageInteger(payload.total_count, count),
      enabled_count: pageInteger(payload.enabled_count, count),
      disabled_count: pageInteger(payload.disabled_count, 0),
      limit: pageInteger(payload.limit, count, 1),
      truncated: payload.truncated === true,
      next_cursor: typeof payload.next_cursor === "string" ? payload.next_cursor : null,
    };
    state.roster = agents;
    state.rosterPage = rosterPage;
    return rosterPage;
  }

  function applyGovernanceSnapshot(payload = {}) {
    state.snapshots = Array.isArray(payload.snapshots) ? payload.snapshots : [];
    if (payload.operations && typeof payload.operations === "object") {
      state.rosterOperations = payload.operations;
    }
    if (payload.reviews && typeof payload.reviews === "object") {
      state.rosterReview = payload.reviews;
    }
    return {
      operations: state.rosterOperations,
      reviews: state.rosterReview,
      snapshots: state.snapshots,
    };
  }

  function operationalFilterValues() {
    const fields = ["query", "division", "capability", "authority", "host", "platform", "tool"];
    return Object.fromEntries(fields.flatMap((field) => {
      const value = String(byId(`roster-filter-${field}`)?.value || "").trim();
      return value ? [[field, value]] : [];
    }));
  }

  function operationalRosterPath(filters = {}) {
    const query = new URLSearchParams({ limit: "100", ...filters });
    return `/api/roster/operations?${query.toString()}`;
  }

  async function applyOperationalFilters(event) {
    event?.preventDefault?.();
    if (config.serviceRestartRequired()) {
      showNotice("Restart the dashboard service before filtering the roster.", true);
      return false;
    }
    if (state.lifecycle.destroyed || state.lifecycle.suspended) return false;
    const filters = operationalFilterValues();
    try {
      const payload = await api(operationalRosterPath(filters));
      if (state.lifecycle.destroyed || state.lifecycle.suspended) return false;
      state.rosterFilters = filters;
      state.rosterOperations = payload;
      state.rosterFilter = "";
      if (byId("roster-search-slug")) byId("roster-search-slug").value = "";
      renderer.renderRoster();
      return true;
    } catch (error) {
      showNotice(error.message, true);
      return false;
    }
  }

  function clearOperationalFilters() {
    ["query", "division", "capability", "authority", "host", "platform", "tool"]
      .forEach((field) => {
        const control = byId(`roster-filter-${field}`);
        if (control) control.value = "";
      });
    return applyOperationalFilters();
  }

  async function loadMoreRemediation(kind) {
    if (!["pending", "history"].includes(kind)) {
      throw new Error("Remediation page kind must be pending or history.");
    }
    if (state.lifecycle.destroyed || state.lifecycle.suspended) return false;
    const current = state.rosterReview || {};
    const cursorField = kind === "pending"
      ? "next_remediation_pending_cursor"
      : "next_remediation_history_cursor";
    const cursor = String(current[cursorField] || "");
    if (!cursor) return false;
    const button = byId(`review-${kind}-more`);
    if (button) {
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
    }
    let loaded = false;
    try {
      const query = new URLSearchParams({
        limit: String(pageInteger(current.limit, 25, 1)),
        [`${kind}_cursor`]: cursor,
      });
      const payload = await api(`/api/roster/reviews?${query.toString()}`);
      if (!state.lifecycle.destroyed && !state.lifecycle.suspended) {
        const itemField = kind === "pending" ? "remediation_attempts" : "remediation_history";
        const existing = Array.isArray(current[itemField]) ? current[itemField] : [];
        const incoming = Array.isArray(payload[itemField]) ? payload[itemField] : [];
        const seen = new Set(existing.map((item) => item?.event_id).filter(Boolean));
        const merged = [
          ...existing,
          ...incoming.filter((item) => !item?.event_id || !seen.has(item.event_id)),
        ];
        const next = {
          ...current,
          [itemField]: merged,
          [cursorField]: String(payload[cursorField] || ""),
          remediation_unvalidated_resolution_count: Number.isInteger(
            payload.remediation_unvalidated_resolution_count,
          )
            ? payload.remediation_unvalidated_resolution_count
            : current.remediation_unvalidated_resolution_count,
        };
        if (kind === "pending") {
          next.remediation_pending_has_more = payload.remediation_pending_has_more === true;
        } else {
          next.remediation_history_has_more = payload.remediation_history_has_more === true;
        }
        state.rosterReview = next;
        renderer.renderRoster();
        loaded = true;
      }
    } catch (error) {
      showNotice(error.message, true);
    }
    if (button) {
      button.disabled = false;
      button.removeAttribute("aria-busy");
    }
    return loaded;
  }

  function rosterRequestPath() {
    return state.rosterFilter
      ? `/api/agents/lookup?slug=${encodeURIComponent(state.rosterFilter)}`
      : "/api/roster?limit=100";
  }

  function normalizeRosterFilter(value) {
    const slug = String(value || "").trim().toLowerCase();
    if (slug && !AGENT_SLUG_PATTERN.test(slug)) {
      throw new Error("Agent slug must use 2-128 letters, digits, dots, underscores, or dashes.");
    }
    return slug;
  }

  async function applyRosterFilter(value) {
    if (config.serviceRestartRequired()) {
      showNotice("Restart the dashboard service before searching the roster.", true);
      return false;
    }
    let slug;
    try {
      slug = normalizeRosterFilter(value);
    } catch (error) {
      showNotice(error.message, true);
      return false;
    }
    if (state.lifecycle.destroyed || state.lifecycle.suspended) return false;
    const previous = state.rosterFilter;
    state.rosterFilter = slug;
    byId("roster-search-slug").value = slug;
    const refreshed = await refreshAll();
    if (!refreshed && !state.lifecycle.destroyed && !state.lifecycle.suspended) {
      state.rosterFilter = previous;
      byId("roster-search-slug").value = previous;
      renderer.renderRoster();
    }
    return refreshed === true;
  }

  function searchRoster(event) {
    event.preventDefault();
    return applyRosterFilter(byId("roster-search-slug").value);
  }

  function clearRosterSearch() {
    return applyRosterFilter("");
  }

  async function refreshControlPlane() {
    state.control.timer = null;
    if (
      state.control.inFlight
      || state.lifecycle.destroyed
      || state.lifecycle.suspended
      || document.visibilityState === "hidden"
    ) return;
    const controller = new AbortController();
    state.control.controller = controller;
    state.control.inFlight = true;
    try {
      const configSnapshot = await api("/api/config", { signal: controller.signal });
      if (state.control.controller !== controller || state.lifecycle.suspended) return;
      config.applyConfigSnapshot(configSnapshot);
      if (config.serviceRestartRequired()) {
        renderer.renderActiveControlView();
        return;
      }
      const [hosts, roster, snapshots] = await Promise.all([
        api("/api/hosts", { signal: controller.signal }),
        api(rosterRequestPath(), { signal: controller.signal }),
        api("/api/snapshots", { signal: controller.signal }),
      ]);
      if (state.control.controller !== controller || state.lifecycle.suspended) return;
      state.hosts = hosts.hosts || [];
      applyMasterState(hosts.master);
      const rosterPage = applyRosterPage(roster);
      applyGovernanceSnapshot(snapshots);
      if (state.activeView === "workforce") await refreshWorkforce({ signal: controller.signal });
      state.overview = { ...(state.overview || {}), roster_count: rosterPage.enabled_count };
      renderer.renderActiveControlView();
    } catch (error) {
      if (
        state.control.controller === controller
        && !state.lifecycle.destroyed
        && !state.lifecycle.suspended
        && error?.name !== "AbortError"
        && terminalLiveFailure(error)
      ) handleLiveFailure(error);
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
      const configSnapshot = await api("/api/config", { signal: controller.signal });
      if (
        generation !== state.full.generation
        || state.full.controller !== controller
        || state.lifecycle.suspended
      ) return false;
      config.applyConfigSnapshot(configSnapshot);
      if (config.serviceRestartRequired()) {
        const live = await api("/api/live?limit=100", { signal: controller.signal });
        if (
          generation !== state.full.generation
          || state.full.controller !== controller
          || state.lifecycle.suspended
        ) return false;
        applyLiveSnapshot(live, { render: false });
        setConnection(true, "Restart required");
        setLiveStatus("Service restart required", "paused", { announce: true });
        renderer.renderActiveView();
        return true;
      }
      const [live, hosts, roster, snapshots] = await Promise.all([
        api("/api/live?limit=100", { signal: controller.signal }),
        api("/api/hosts", { signal: controller.signal }),
        api(rosterRequestPath(), { signal: controller.signal }),
        api("/api/snapshots", { signal: controller.signal }),
      ]);
      if (
        generation !== state.full.generation
        || state.full.controller !== controller
        || state.lifecycle.suspended
      ) return false;
      state.hosts = hosts.hosts || [];
      applyMasterState(hosts.master);
      const rosterPage = applyRosterPage(roster);
      applyGovernanceSnapshot(snapshots);
      if (state.activeView === "workforce") await refreshWorkforce({ signal: controller.signal });
      const effective = configSnapshot.effective || configSnapshot.config || {};
      state.overview = {
        roster_count: rosterPage.enabled_count,
        retention_days: nestedValue(effective, "observability.retention_days"),
        capture_content: nestedValue(effective, "observability.capture_content") === true,
      };
      state.activity = {};
      state.live.revision = "";
      applyLiveSnapshot(live, { render: false });
      setConnection(true, "Authenticated");
      setLiveStatus(
        state.live.enabled ? "Live · authenticated" : "Live updates paused",
        state.live.enabled ? "live" : "paused",
      );
      renderer.renderActiveView();
      return true;
    } catch (error) {
      if (error?.name === "AbortError") return false;
      if (state.lifecycle.destroyed || state.lifecycle.suspended) return false;
      setConnection(false, "Unavailable");
      if (terminalLiveFailure(error)) handleLiveFailure(error);
      else if (surfaceErrors) showNotice(error.message, true);
      if (!surfaceErrors) throw error;
    } finally {
      if (state.full.controller === controller) {
        state.full.controller = null;
        state.full.inFlight = false;
        if (!state.lifecycle.destroyed) byId("refresh-button").disabled = false;
        scheduleLive(LIVE_INTERVAL_MS);
        scheduleControlRefresh();
      }
    }
  }

  async function refreshRuntimeEvidence() {
    cancelLiveRequest();
    try {
      const payload = await fetchLiveSnapshot();
      if (!payload || state.lifecycle.destroyed || state.lifecycle.suspended) return false;
      applyLiveSnapshot(payload);
      state.live.failures = 0;
      setConnection(true, "Authenticated");
      setLiveStatus("Live · authenticated", "live");
      return true;
    } finally {
      scheduleLive(LIVE_INTERVAL_MS);
    }
  }

  async function refreshWorkforce({ signal } = {}) {
    const [workforce, hiring] = await Promise.all([
      api("/api/workforce?limit=1000", { signal }),
      api("/api/hiring?limit=100", { signal }),
    ]);
    if (state.lifecycle.destroyed || state.lifecycle.suspended) return false;
    state.workforce = workforce.workers || [];
    state.workforceCounts = workforce.counts || {};
    state.hiring = hiring.hiring_cases || [];
    if (state.activeView === "workforce") renderer.renderWorkforce();
    return true;
  }

  async function reconcileRuntimeEvidence(successMessage) {
    if (state.lifecycle.destroyed || state.lifecycle.suspended) return false;
    showNotice(successMessage);
    try {
      await refreshRuntimeEvidence();
    } catch (error) {
      if (state.lifecycle.destroyed || state.lifecycle.suspended) return false;
      if (terminalLiveFailure(error)) handleLiveFailure(error);
      else showNotice(`${successMessage} The live view could not refresh: ${error.message}`, true);
    }
    return true;
  }

  async function reconcileAll(successMessage) {
    if (state.lifecycle.destroyed || state.lifecycle.suspended) return false;
    showNotice(successMessage);
    try {
      await refreshAll({ surfaceErrors: false });
    } catch (error) {
      if (!terminalLiveFailure(error)) {
        showNotice(`${successMessage} The dashboard view could not refresh: ${error.message}`, true);
      }
    }
    return true;
  }

  return {
    setConnection,
    setLiveStatus,
    updateLastSync,
    updateLocalClock,
    syncLiveToggle,
    syncMasterControl,
    applyMasterState,
    cancelLiveRequest,
    cancelControlRequest,
    cancelFullRefresh,
    cancelMutationRequests,
    pauseForMutation,
    resumeAfterMutation,
    beginMutation,
    mutationIsCurrent,
    finishMutation,
    liveCanRun,
    scheduleLive,
    fetchLiveSnapshot,
    applyLiveSnapshot,
    terminalLiveFailure,
    handleLiveFailure,
    runLivePoll,
    scheduleControlRefresh,
    applyRosterPage,
    applyGovernanceSnapshot,
    operationalFilterValues,
    operationalRosterPath,
    applyOperationalFilters,
    clearOperationalFilters,
    loadMoreRemediation,
    rosterRequestPath,
    normalizeRosterFilter,
    applyRosterFilter,
    searchRoster,
    clearRosterSearch,
    refreshControlPlane,
    refreshAll,
    refreshRuntimeEvidence,
    refreshWorkforce,
    reconcileRuntimeEvidence,
    reconcileAll,
  };
}
