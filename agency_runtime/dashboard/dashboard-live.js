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
    renderPreservingInteraction,
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
            ? "Agency Runtime is enabled (read-only monitoring)"
            : "Agency Runtime is disabled (read-only monitoring)",
      );
      toggle.dataset.state = !known ? "loading" : enabled ? "enabled" : "disabled";
      toggle.disabled = true;
      toggle.setAttribute("aria-disabled", "true");
      toggle.title = known
        ? `Generation ${master.generation} · ${enabled ? "Agency is active" : "Agency is bypassed"} · read-only`
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
    state.control.generation += 1;
    window.clearTimeout(state.control.timer);
    state.control.timer = null;
    const controller = state.control.controller;
    state.control.controller = null;
    state.control.inFlight = false;
    if (controller) controller.abort();
  }

  function beginViewRequest(name) {
    const request = state.requests[name];
    if (!request) throw new Error(`Unknown dashboard request scope: ${name}`);
    request.generation += 1;
    request.controller?.abort();
    request.controller = new AbortController();
    return { controller: request.controller, generation: request.generation };
  }

  function viewRequestIsCurrent(name, request) {
    const current = state.requests[name];
    return !state.lifecycle.destroyed
      && !state.lifecycle.suspended
      && !request.controller.signal.aborted
      && current?.controller === request.controller
      && current.generation === request.generation;
  }

  function finishViewRequest(name, request) {
    const current = state.requests[name];
    if (current?.controller !== request.controller) return false;
    current.controller = null;
    return true;
  }

  function cancelViewRequests() {
    Object.values(state.requests).forEach((request) => {
      request.generation += 1;
      request.controller?.abort();
      request.controller = null;
    });
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
      if (masterChanged && render) renderPreservingInteraction(renderer.renderActiveView);
      return masterChanged;
    }
    state.live.revision = String(payload.revision || "");
    state.overview = { ...(state.overview || {}), ...(payload.overview || {}) };
    state.activity = payload.activity || {};
    state.activityCollections = payload.activity_collections || {};
    if (render) renderPreservingInteraction(renderer.renderActiveView);
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

  async function completeCollection(
    initial,
    {
      basePath,
      itemField,
      revisionField,
      signal,
      maximumPages = 100,
      cursorParameter = "after",
    },
  ) {
    if (!initial || typeof initial !== "object") return initial || {};
    const rows = Array.isArray(initial[itemField]) ? [...initial[itemField]] : [];
    const revision = String(initial[revisionField] || "");
    let cursor = initial.truncated === true ? String(initial.next_cursor || "") : "";
    const seenCursors = new Set();
    let pageCount = 1;
    while (cursor) {
      if (pageCount >= maximumPages || seenCursors.has(cursor)) {
        throw new Error(`The ${itemField} collection exceeded its safe paging boundary.`);
      }
      seenCursors.add(cursor);
      const separator = basePath.includes("?") ? "&" : "?";
      const page = await api(
        `${basePath}${separator}${cursorParameter}=${encodeURIComponent(cursor)}`,
        { signal },
      );
      if (revision && String(page[revisionField] || "") !== revision) {
        throw new Error(`The ${itemField} collection changed while it was being paged.`);
      }
      rows.push(...(Array.isArray(page[itemField]) ? page[itemField] : []));
      cursor = page.truncated === true ? String(page.next_cursor || "") : "";
      if (page.truncated === true && !cursor) {
        throw new Error(`The ${itemField} collection omitted its next cursor.`);
      }
      pageCount += 1;
    }
    return {
      ...initial,
      [itemField]: rows,
      count: rows.length,
      page_count: rows.length,
      truncated: false,
      next_cursor: null,
      pages_loaded: pageCount,
    };
  }

  async function completeRosterPage(initial, signal) {
    if (state.rosterFilter || initial?.truncated !== true) return initial;
    return completeCollection(initial, {
      basePath: "/api/roster?limit=200",
      itemField: "agents",
      revisionField: "roster_revision",
      signal,
    });
  }

  async function completeGovernanceSnapshot(initial, signal) {
    if (!initial || typeof initial !== "object") return initial || {};
    const withSnapshots = await completeCollection(initial, {
      basePath: "/api/snapshots?limit=200",
      itemField: "snapshots",
      revisionField: "collection_revision",
      signal,
    });
    const reviews = await completeCollection(withSnapshots.reviews || {}, {
      basePath: "/api/roster/reviews?limit=100",
      itemField: "candidates",
      revisionField: "collection_revision",
      cursorParameter: "candidate_cursor",
      signal,
    });
    return { ...withSnapshots, reviews };
  }

  async function fetchWorkforceCollections(signal) {
    const [workforceFirst, hiringFirst] = await Promise.all([
      api("/api/workforce?limit=200", { signal }),
      api("/api/hiring?limit=200", { signal }),
    ]);
    const [workforce, hiring] = await Promise.all([
      completeCollection(workforceFirst, {
        basePath: "/api/workforce?limit=200",
        itemField: "workers",
        revisionField: "collection_revision",
        signal,
      }),
      completeCollection(hiringFirst, {
        basePath: "/api/hiring?limit=200",
        itemField: "hiring_cases",
        revisionField: "collection_revision",
        signal,
      }),
    ]);
    return { workforce, hiring };
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

  async function fetchOperationalRoster(filters, signal) {
    const first = await api(operationalRosterPath(filters), { signal });
    return completeCollection(first, {
      basePath: operationalRosterPath(filters),
      itemField: "agents",
      revisionField: "roster_revision",
      signal,
    });
  }

  async function applyOperationalFilters(event) {
    event?.preventDefault?.();
    if (config.serviceRestartRequired()) {
      showNotice("Restart the dashboard service before filtering the roster.", true);
      return false;
    }
    if (state.lifecycle.destroyed || state.lifecycle.suspended) return false;
    const filters = operationalFilterValues();
    const request = beginViewRequest("operationalRoster");
    try {
      const payload = await fetchOperationalRoster(filters, request.controller.signal);
      if (!viewRequestIsCurrent("operationalRoster", request)) return false;
      state.rosterFilters = filters;
      state.rosterOperations = payload;
      state.rosterFilter = "";
      if (byId("roster-search-slug")) byId("roster-search-slug").value = "";
      renderPreservingInteraction(renderer.renderRoster);
      return true;
    } catch (error) {
      if (error?.name !== "AbortError" && viewRequestIsCurrent("operationalRoster", request)) {
        showNotice(error.message, true);
      }
      return false;
    } finally {
      finishViewRequest("operationalRoster", request);
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
    const request = beginViewRequest("remediation");
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
      const payload = await api(`/api/roster/reviews?${query.toString()}`, {
        signal: request.controller.signal,
      });
      if (viewRequestIsCurrent("remediation", request)) {
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
        renderPreservingInteraction(renderer.renderRoster);
        loaded = true;
      }
    } catch (error) {
      if (error?.name !== "AbortError" && viewRequestIsCurrent("remediation", request)) {
        showNotice(error.message, true);
      }
    }
    if (button && viewRequestIsCurrent("remediation", request)) {
      button.disabled = false;
      button.removeAttribute("aria-busy");
    }
    finishViewRequest("remediation", request);
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

  async function legacyControlSnapshot(signal) {
    const configSnapshot = await api("/api/config", { signal });
    if (configSnapshot?.service_binding?.store_restart_required === true) {
      return {
        schema_version: "agency.dashboard.control.legacy",
        config: configSnapshot,
        service_binding: configSnapshot.service_binding,
        restart_required: true,
        control_revision: "legacy-unversioned",
      };
    }
    const [hosts, rosterFirst, governance] = await Promise.all([
      api("/api/hosts", { signal }),
      api(rosterRequestPath(), { signal }),
      api("/api/snapshots", { signal }),
    ]);
    const roster = await completeRosterPage(rosterFirst, signal);
    return {
      schema_version: "agency.dashboard.control.legacy",
      config: configSnapshot,
      hosts: hosts.hosts || [],
      master: hosts.master,
      roster,
      governance: await completeGovernanceSnapshot(governance, signal),
      service_binding: configSnapshot.service_binding,
      restart_required: false,
      control_revision: "legacy-unversioned",
    };
  }

  async function fetchControlSnapshot(signal) {
    let snapshot;
    try {
      snapshot = await api("/api/control", { signal });
    } catch (error) {
      if (error?.name === "AbortError") throw error;
      if (!(error instanceof APIError) || ![0, 404].includes(error.status)) throw error;
      return legacyControlSnapshot(signal);
    }
    if (snapshot?.schema_version !== "agency.dashboard.control.v1") {
      if (
        signal?.aborted
        || state.lifecycle.destroyed
        || state.lifecycle.suspended
      ) throw new runtime.DOMException("Aborted", "AbortError");
      return legacyControlSnapshot(signal);
    }
    if (!snapshot.restart_required) {
      snapshot.roster = await completeRosterPage(snapshot.roster, signal);
      snapshot.governance = await completeGovernanceSnapshot(
        snapshot.governance,
        signal,
      );
      if (state.rosterFilter) {
        snapshot.roster = await api(rosterRequestPath(), { signal });
      }
      if (Object.keys(state.rosterFilters || {}).length) {
        snapshot.governance = {
          ...(snapshot.governance || {}),
          operations: await fetchOperationalRoster(state.rosterFilters, signal),
        };
      }
    }
    return snapshot;
  }

  function setControlFresh(snapshot) {
    state.control.revision = String(snapshot.control_revision || "legacy-unversioned");
    state.control.sampledAt = snapshot.sampled_at || new Date().toISOString();
    state.control.stale = false;
    state.control.errorRequestId = "";
    const shell = document.querySelector(".shell");
    if (shell) shell.dataset.controlState = "fresh";
  }

  function markControlStale(error) {
    state.control.stale = true;
    state.control.errorRequestId = String(error?.requestId || "");
    const shell = document.querySelector(".shell");
    if (shell) shell.dataset.controlState = "stale";
    setConnection(false, "Control data stale");
    const revision = state.control.revision
      ? ` Last good revision ${state.control.revision.slice(0, 12)}.`
      : " No complete control revision has loaded.";
    const request = state.control.errorRequestId
      ? ` Request ID ${state.control.errorRequestId}.`
      : "";
    showNotice(`Control refresh failed; retained the last good state.${revision}${request}`, true);
  }

  function applyControlSnapshot(snapshot, { render = true } = {}) {
    if (!snapshot || typeof snapshot !== "object") {
      throw new Error("Dashboard control response is invalid.");
    }
    if (!snapshot.config || typeof snapshot.config !== "object") {
      throw new Error("Dashboard control response omitted configuration.");
    }
    const restartRequired = snapshot.restart_required === true
      || snapshot.config.service_binding?.store_restart_required === true;
    if (
      !restartRequired
      && (
        !Array.isArray(snapshot.hosts)
        || !snapshot.roster
        || typeof snapshot.roster !== "object"
        || !snapshot.governance
        || typeof snapshot.governance !== "object"
      )
    ) {
      throw new Error("Dashboard control response is incomplete.");
    }
    config.applyConfigSnapshot(snapshot.config);
    setControlFresh(snapshot);
    if (restartRequired || config.serviceRestartRequired()) {
      if (render) renderPreservingInteraction(renderer.renderActiveControlView);
      return true;
    }
    state.hosts = snapshot.hosts;
    applyMasterState(snapshot.master);
    const rosterPage = applyRosterPage(snapshot.roster);
    applyGovernanceSnapshot(snapshot.governance);
    state.overview = { ...(state.overview || {}), roster_count: rosterPage.enabled_count };
    if (render) renderPreservingInteraction(renderer.renderActiveControlView);
    return true;
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
    const generation = state.control.generation + 1;
    state.control.generation = generation;
    state.control.controller = controller;
    state.control.inFlight = true;
    try {
      const [snapshot, workforce] = await Promise.all([
        fetchControlSnapshot(controller.signal),
        state.activeView === "workforce"
          ? fetchWorkforceCollections(controller.signal)
          : Promise.resolve(null),
      ]);
      if (
        state.control.controller !== controller
        || state.control.generation !== generation
        || state.lifecycle.suspended
      ) return;
      applyControlSnapshot(snapshot, { render: false });
      if (workforce) commitWorkforceCollections(workforce, { render: false });
      renderPreservingInteraction(renderer.renderActiveControlView);
    } catch (error) {
      if (
        state.control.controller === controller
        && !state.lifecycle.destroyed
        && !state.lifecycle.suspended
        && error?.name !== "AbortError"
      ) {
        if (terminalLiveFailure(error)) handleLiveFailure(error);
        else markControlStale(error);
      }
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
      const [live, control, workforce] = await Promise.all([
        api("/api/live?limit=100", { signal: controller.signal }),
        fetchControlSnapshot(controller.signal),
        state.activeView === "workforce"
          ? fetchWorkforceCollections(controller.signal)
          : Promise.resolve(null),
      ]);
      if (
        generation !== state.full.generation
        || state.full.controller !== controller
        || state.lifecycle.suspended
      ) return false;
      applyControlSnapshot(control, { render: false });
      if (workforce) commitWorkforceCollections(workforce, { render: false });
      const effective = control.config.effective || control.config.config || {};
      state.overview = {
        ...(state.overview || {}),
        roster_count: state.rosterPage?.enabled_count ?? state.overview?.roster_count,
        retention_days: nestedValue(effective, "observability.retention_days"),
        capture_content: nestedValue(effective, "observability.capture_content") === true,
      };
      state.activity = {};
      state.live.revision = "";
      applyLiveSnapshot(live, { render: false });
      if (control.restart_required || config.serviceRestartRequired()) {
        setConnection(true, "Restart required");
        setLiveStatus("Service restart required", "paused", { announce: true });
      } else {
        setConnection(true, "Authenticated");
        setLiveStatus(
          state.live.enabled ? "Live · authenticated" : "Live updates paused",
          state.live.enabled ? "live" : "paused",
        );
      }
      renderPreservingInteraction(renderer.renderActiveView);
      return true;
    } catch (error) {
      if (error?.name === "AbortError") return false;
      if (state.lifecycle.destroyed || state.lifecycle.suspended) return false;
      setConnection(false, "Unavailable");
      if (terminalLiveFailure(error)) handleLiveFailure(error);
      else if (surfaceErrors) markControlStale(error);
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
    if (signal) {
      const collections = await fetchWorkforceCollections(signal);
      if (signal.aborted || state.lifecycle.destroyed || state.lifecycle.suspended) return false;
      commitWorkforceCollections(collections, { render: true });
      return true;
    }
    const request = beginViewRequest("workforce");
    try {
      const collections = await fetchWorkforceCollections(request.controller.signal);
      if (!viewRequestIsCurrent("workforce", request)) return false;
      commitWorkforceCollections(collections, { render: true });
      return true;
    } catch (error) {
      if (error?.name !== "AbortError" && viewRequestIsCurrent("workforce", request)) {
        showNotice(error.message, true);
      }
      return false;
    } finally {
      finishViewRequest("workforce", request);
    }
  }

  function commitWorkforceCollections({ workforce, hiring }, { render = true } = {}) {
    state.workforce = Array.isArray(workforce?.workers) ? workforce.workers : [];
    state.workforceCounts = workforce?.counts || {};
    const { workers: _workers, ...workforcePage } = workforce || {};
    state.workforcePage = workforcePage;
    state.hiring = Array.isArray(hiring?.hiring_cases) ? hiring.hiring_cases : [];
    const { hiring_cases: _cases, ...hiringPage } = hiring || {};
    state.hiringPage = hiringPage;
    if (render && state.activeView === "workforce") {
      renderPreservingInteraction(renderer.renderWorkforce);
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
    syncMasterControl,
    applyMasterState,
    cancelLiveRequest,
    cancelControlRequest,
    beginViewRequest,
    viewRequestIsCurrent,
    finishViewRequest,
    cancelFullRefresh,
    cancelMutationRequests,
    cancelViewRequests,
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
    completeCollection,
    fetchControlSnapshot,
    applyControlSnapshot,
    markControlStale,
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
