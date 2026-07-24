"use strict";
import { createActionController } from "./dashboard-actions.js";
import { createConfigController } from "./dashboard-config.js";
import { APIError, createCore } from "./dashboard-core.js";
import { createLiveController } from "./dashboard-live.js";
import { createRenderer } from "./dashboard-render.js";
export function createDashboard(runtime = globalThis) {
  const core = createCore(runtime);
  const { document, window, state, byId, listen } = core;
  const config = createConfigController(core);
  let actions;
  const renderer = createRenderer(core, config, {
    rosterAction: (...args) => actions.rosterAction(...args),
    toggleAgent: (...args) => actions.toggleAgent(...args),
    toggleHost: (...args) => actions.toggleHost(...args),
    selectWorker: (...args) => actions.selectWorker(...args),
    hiringApprove: (...args) => actions.hiringApprove(...args),
  });
  const live = createLiveController(core, config, renderer);
  actions = createActionController(core, config, renderer, live);
  async function connectFromLocation() {
    const generation = state.connection.generation + 1;
    state.connection.generation = generation;
    try {
      core.installToken();
      state.live.terminal = false;
      const refreshed = await live.refreshAll();
      if (
        generation !== state.connection.generation
        || state.lifecycle.destroyed
        || state.lifecycle.suspended
      ) return false;
      if (refreshed) core.clearNotice();
      return refreshed;
    } catch (error) {
      if (generation !== state.connection.generation || state.lifecycle.destroyed) return false;
      core.showNotice(error.message, true);
      byId("connection-label").textContent = "Token required";
      return false;
    }
  }
  function setLiveEnabled(enabled) {
    state.live.enabled = Boolean(enabled);
    live.syncLiveToggle();
    if (!state.live.enabled) {
      live.cancelLiveRequest();
      live.cancelControlRequest();
      live.setLiveStatus("Live updates paused", "paused", { announce: true });
      return;
    }
    state.live.terminal = false;
    state.live.failures = 0;
    live.setLiveStatus("Connecting live updates", "connecting", { announce: true });
    live.scheduleLive(0);
    live.scheduleControlRefresh(0);
  }
  function suspendRuntime() {
    state.lifecycle.suspended = true;
    window.clearTimeout(state.clockTimer);
    state.clockTimer = null;
    live.cancelLiveRequest();
    live.cancelControlRequest();
    live.cancelFullRefresh();
    live.cancelMutationRequests();
  }
  function handleVisibilityChange() {
    if (document.visibilityState === "hidden") {
      suspendRuntime();
      if (state.live.enabled && !state.live.terminal) {
        live.setLiveStatus("Paused while this tab is hidden", "paused");
      }
      return;
    }
    state.lifecycle.suspended = false;
    live.updateLocalClock();
    if (state.live.enabled && !state.live.terminal) {
      live.setLiveStatus("Syncing live activity", "connecting");
      live.scheduleLive(0);
      live.scheduleControlRefresh(0);
    }
  }
  function handlePageShow(event) {
    if (!event.persisted || state.lifecycle.destroyed) return;
    state.lifecycle.suspended = false;
    if (!state.full.inFlight) byId("refresh-button").disabled = false;
    live.updateLocalClock();
    if (!state.live.enabled || state.live.terminal) return;
    live.scheduleLive(0);
    live.scheduleControlRefresh(0);
  }
  function destroy() {
    if (state.lifecycle.destroyed) return false;
    state.lifecycle.destroyed = true;
    state.lifecycle.suspended = true;
    state.connection.generation += 1;
    suspendRuntime();
    core.disposeCore();
    renderer.disposeAnimations();
    core.disposeListeners();
    state.lifecycle.bound = false;
    return true;
  }
  function handlePageHide(event = {}) {
    suspendRuntime();
    if (!event.persisted) destroy();
  }
  function bindEvents() {
    if (state.lifecycle.bound || state.lifecycle.destroyed) return false;
    state.lifecycle.bound = true;
    document.querySelectorAll(".nav-item").forEach((node) => {
      listen(node, "click", () => {
        renderer.switchView(node.dataset.view);
        if (node.dataset.view === "workforce") {
          void live.refreshWorkforce().catch((error) => core.showNotice(error.message, true));
        }
      });
    });
    renderer.configureEvidenceTabs();
    listen(byId("refresh-button"), "click", live.refreshAll);
    listen(byId("route-button"), "click", actions.runRoute);
    listen(byId("route-host"), "change", renderer.renderRouteHosts);
    listen(byId("trim-button"), "click", actions.trimRuntime);
    listen(byId("roster-search-form"), "submit", live.searchRoster);
    listen(byId("roster-search-clear"), "click", live.clearRosterSearch);
    const operationalFilters = byId("roster-operations-form");
    if (operationalFilters) listen(operationalFilters, "submit", live.applyOperationalFilters);
    const clearOperationalFilters = byId("roster-filter-clear");
    if (clearOperationalFilters) {
      listen(clearOperationalFilters, "click", live.clearOperationalFilters);
    }
    const pendingRemediation = byId("review-pending-more");
    if (pendingRemediation) {
      listen(pendingRemediation, "click", () => live.loadMoreRemediation("pending"));
    }
    const remediationHistory = byId("review-history-more");
    if (remediationHistory) {
      listen(remediationHistory, "click", () => live.loadMoreRemediation("history"));
    }
    listen(byId("trim-days"), "input", () => {
      byId("trim-days").dataset.dirty = "true";
    });
    listen(byId("config-form"), "submit", actions.saveConfig);
    const workforceActionForm = byId("workforce-action-form");
    if (workforceActionForm) listen(workforceActionForm, "submit", actions.workforceAction);
    listen(byId("config-form"), "input", config.updateConfigDirtyState);
    listen(byId("config-form"), "change", config.updateConfigDirtyState);
    const providerSave = byId("provider-builder-save");
    if (providerSave) {
      listen(providerSave, "click", () => {
        try {
          const provider = config.upsertProviderDraft();
          core.showNotice(
            `Provider ${provider.name} staged with model/router ${provider.model || "default"}.`,
          );
        } catch (error) {
          core.showNotice(error.message, true);
        }
      });
    }
    const providerType = byId("provider-builder-type");
    const providerTransport = byId("provider-builder-transport");
    const providerModelSelect = byId("provider-builder-model-select");
    const providerModelRefresh = byId("provider-builder-model-refresh");
    if (providerType) {
      listen(providerType, "change", () => {
        config.syncProviderTimeoutRecommendation();
        config.syncProviderReasoningEffortOptions();
        void config.loadProviderModels();
      });
    }
    if (providerTransport) listen(providerTransport, "change", () => {
      config.syncProviderReasoningEffortOptions();
      void config.loadProviderModels();
    });
    if (providerModelSelect) listen(providerModelSelect, "change", config.syncProviderModelInput);
    if (providerModelRefresh) {
      listen(providerModelRefresh, "click", () => { void config.loadProviderModels({ refresh: true }); });
    }
    const workforceProvider = byId("config-workforce-provider");
    const workforceModelRefresh = byId("workforce-model-refresh");
    if (workforceProvider) {
      listen(workforceProvider, "change", () => { void config.loadWorkforceModels(); });
    }
    if (workforceModelRefresh) {
      listen(workforceModelRefresh, "click", () => {
        void config.loadWorkforceModels({ refresh: true });
      });
    }
    const providerRemove = byId("provider-builder-remove");
    if (providerRemove) {
      listen(providerRemove, "click", () => {
        try {
          config.removeSelectedProvider();
          core.showNotice("Provider removal staged.");
        } catch (error) {
          core.showNotice(error.message, true);
        }
      });
    }
    listen(byId("config-reset-button"), "click", () => {
      const snapshot = state.pendingConfig || state.config;
      if (snapshot) config.renderConfig(snapshot);
    });
    listen(byId("confirmation-cancel"), "click", () => core.finishConfirmation(false));
    listen(byId("confirmation-accept"), "click", () => core.finishConfirmation(true));
    listen(byId("confirmation-input"), "keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        core.finishConfirmation(true);
      } else if (event.key === "Escape") {
        event.preventDefault();
        core.finishConfirmation(false);
      }
    });
    listen(document, "keydown", core.handleModalKeyboard);
    const liveToggle = byId("live-toggle");
    if (liveToggle) {
      state.live.enabled = liveToggle.getAttribute("aria-pressed") !== "false";
      live.syncLiveToggle();
      listen(liveToggle, "click", () => setLiveEnabled(!state.live.enabled));
    }
    const masterToggle = byId("master-toggle");
    if (masterToggle) {
      listen(masterToggle, "click", () => actions.toggleMaster(state.master?.enabled === false));
    }
    listen(document, "visibilitychange", handleVisibilityChange);
    listen(window, "pagehide", handlePageHide);
    listen(window, "pageshow", handlePageShow);
    listen(window, "hashchange", () => { void connectFromLocation(); });
    renderer.switchView(document.querySelector(".nav-item.active")?.dataset.view || "overview");
    return true;
  }
  async function start() {
    if (state.lifecycle.destroyed) return false;
    bindEvents();
    live.updateLocalClock();
    return connectFromLocation();
  }
  const dashboard = {
    ...core,
    ...config,
    ...renderer,
    ...live,
    ...actions,
    APIError,
    connectFromLocation,
    setLiveEnabled,
    suspendRuntime,
    handleVisibilityChange,
    handlePageShow,
    handlePageHide,
    bindEvents,
    start,
    destroy,
  };
  listen(document, "DOMContentLoaded", start, { once: true });
  return dashboard;
}
export const bootstrappedDashboard = createDashboard(globalThis);
