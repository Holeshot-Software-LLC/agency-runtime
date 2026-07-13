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
    if (payload.revision === state.live.revision) {
      const sampled = Date.parse(state.live.sampledAt);
      const chartWindow = Number.isFinite(sampled) ? Math.floor(sampled / 60000) : null;
      if (
        render
        && state.activeView === "overview"
        && chartWindow !== state.live.chartWindow
      ) renderer.renderCharts();
      return false;
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
      limit: pageInteger(payload.limit, count, 1),
      truncated: payload.truncated === true,
      next_cursor: typeof payload.next_cursor === "string" ? payload.next_cursor : null,
    };
    state.roster = agents;
    state.rosterPage = rosterPage;
    return rosterPage;
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
      const [hosts, roster, snapshots, configSnapshot] = await Promise.all([
        api("/api/hosts", { signal: controller.signal }),
        api("/api/roster", { signal: controller.signal }),
        api("/api/snapshots", { signal: controller.signal }),
        api("/api/config", { signal: controller.signal }),
      ]);
      if (state.control.controller !== controller || state.lifecycle.suspended) return;
      state.hosts = hosts.hosts || [];
      const rosterPage = applyRosterPage(roster);
      state.snapshots = snapshots.snapshots || [];
      state.overview = { ...(state.overview || {}), roster_count: rosterPage.total_count };
      config.applyConfigSnapshot(configSnapshot);
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
      const [live, hosts, roster, snapshots, configSnapshot] = await Promise.all([
        api("/api/live?limit=100", { signal: controller.signal }),
        api("/api/hosts", { signal: controller.signal }),
        api("/api/roster", { signal: controller.signal }),
        api("/api/snapshots", { signal: controller.signal }),
        api("/api/config", { signal: controller.signal }),
      ]);
      if (
        generation !== state.full.generation
        || state.full.controller !== controller
        || state.lifecycle.suspended
      ) return false;
      state.hosts = hosts.hosts || [];
      const rosterPage = applyRosterPage(roster);
      state.snapshots = snapshots.snapshots || [];
      const effective = configSnapshot.effective || configSnapshot.config || {};
      state.overview = {
        roster_count: rosterPage.total_count,
        retention_days: nestedValue(effective, "observability.retention_days"),
        capture_content: nestedValue(effective, "observability.capture_content") === true,
      };
      state.activity = {};
      state.live.revision = "";
      config.applyConfigSnapshot(configSnapshot);
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
    refreshControlPlane,
    refreshAll,
    refreshRuntimeEvidence,
    reconcileRuntimeEvidence,
    reconcileAll,
  };
}
