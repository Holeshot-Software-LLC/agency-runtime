import { createActionController } from "./dashboard-actions.js";
import { createConfigController } from "./dashboard-config.js";
import { APIError, createCore } from "./dashboard-core.js";
import { createLiveController } from "./dashboard-live.js";
import { createRenderer } from "./dashboard-render.js";

export function createDashboard(runtime = globalThis) {
	const core = createCore(runtime);
	const { document, window, state, byId, listen } = core;
	const config = createConfigController(core);
	const renderer = createRenderer(core, config);
	const live = createLiveController(core, config, renderer);
	const actions = createActionController(core, config, renderer, live);

	async function connectFromLocation() {
		const generation = ++state.connection.generation;
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
		live.cancelUpdateRequest();
		live.cancelFullRefresh();
		live.cancelMutationRequests();
		live.cancelViewRequests();
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
		live.scheduleUpdateRefresh(0);
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
		live.scheduleUpdateRefresh(0);
		if (!state.live.enabled || state.live.terminal) return;
		live.scheduleLive(0);
		live.scheduleControlRefresh(0);
	}

	function destroy() {
		if (state.lifecycle.destroyed) return false;
		state.lifecycle.destroyed = true;
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

	function configureReadOnlySurface() {
		state.surfaceReadOnly = true;
		const manualProviderModel = byId("provider-builder-model");
		if (manualProviderModel && !manualProviderModel.getAttribute("aria-label")) {
			manualProviderModel.setAttribute(
				"aria-label",
				"Manual provider model or router alias",
			);
		}
		if (!byId("config-adapter-zcode")) {
			const adapterGrid = document.querySelector(".adapter-grid");
			if (adapterGrid) {
				const label = document.createElement("label");
				const select = document.createElement("select");
				label.setAttribute("for", "config-adapter-zcode");
				label.textContent = "ZCode";
				select.id = "config-adapter-zcode";
				select.setAttribute("data-config-path", "adapters.zcode.enabled");
				[
					["auto", "Auto"],
					["true", "Enabled"],
					["false", "Disabled"],
				].forEach(([value, text]) => {
					const option = document.createElement("option");
					option.value = value;
					option.textContent = text;
					select.append(option);
				});
				label.append(select);
				adapterGrid.append(label);
			}
		}
		const hiddenMutationControls = [
			"provider-builder-save",
			"provider-builder-remove",
			"config-reset-button",
			"config-save-button",
			"workforce-action-submit",
		];
		hiddenMutationControls.forEach((id) => {
			const control = byId(id);
			if (!control) return;
			control.disabled = true;
			control.hidden = true;
			control.setAttribute("aria-hidden", "true");
		});
		const master = byId("master-toggle");
		if (master) {
			master.disabled = true;
			master.setAttribute("aria-disabled", "true");
		}
		const workforceForm = byId("workforce-action-form");
		if (workforceForm) workforceForm.hidden = true;
		const confirmation = byId("confirmation-modal");
		if (confirmation) confirmation.hidden = true;
		const configForm = byId("config-form");
		if (configForm) configForm.setAttribute("aria-label", "Effective configuration (read-only)");
		const privacy = byId("privacy-chip");
		if (privacy?.textContent === "Metadata only") privacy.textContent = "Runtime metadata only";
		document.querySelectorAll(
			"#config-form input, #config-form select, #config-form textarea, #config-form button",
		).forEach((control) => {
			control.disabled = true;
		});
		const changeCount = byId("config-change-count");
		if (changeCount) changeCount.textContent = "Read-only monitoring";
		return true;
	}

	async function copyAttendedCommand(commandValue, successMessage) {
		const command = String(commandValue || "").trim();
		if (!command) return false;
		try {
			if (typeof window.navigator?.clipboard?.writeText !== "function") {
				throw new Error("clipboard unavailable");
			}
			await window.navigator.clipboard.writeText(command);
			core.showNotice(successMessage);
			return true;
		} catch {
			core.showNotice("Copy was unavailable. Select the displayed command manually.", true);
			return false;
		}
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
		configureReadOnlySurface();
		listen(byId("refresh-button"), "click", async () => {
			await live.refreshAll();
			void live.refreshUpdateStatus();
		});
		live.ensureUpdateSurface();
		listen(byId("update-copy-button"), "click", () => copyAttendedCommand(
			byId("update-command")?.textContent,
			"Upgrade command copied. Review it in an owner-controlled terminal.",
		));
		listen(byId("host-grid"), "click", (event) => {
			if (event.target?.id !== "uninstall-copy-button") return false;
			return copyAttendedCommand(
				event.target.dataset.command,
				"Uninstall preview copied. Run it in an owner-controlled terminal.",
			);
		});
		listen(byId("route-button"), "click", actions.runRoute);
		listen(byId("route-host"), "change", renderer.renderRouteHosts);
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
		const workforceGrid = byId("workforce-grid");
		if (workforceGrid) {
			listen(workforceGrid, "click", (event) => {
				const card = event.target?.closest?.("[data-worker]");
				const slug = String(card?.dataset?.worker || "");
				if (slug) void actions.selectWorker(slug);
			});
		}
		const hiringList = byId("hiring-list");
		if (hiringList) {
			listen(hiringList, "click", (event) => {
				const control = event.target?.closest?.("[data-hiring-evidence-case]");
				const caseId = String(control?.dataset?.hiringEvidenceCase || "");
				if (caseId && !control.disabled) void live.loadHiringEvidence(caseId);
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
		const liveToggle = byId("live-toggle");
		if (liveToggle) {
			state.live.enabled = liveToggle.getAttribute("aria-pressed") !== "false";
			live.syncLiveToggle();
			listen(liveToggle, "click", () => setLiveEnabled(!state.live.enabled));
		}
		listen(document, "visibilitychange", handleVisibilityChange);
		listen(window, "pagehide", handlePageHide);
		listen(window, "pageshow", handlePageShow);
		// Some launchers attach the fragment after DOMContentLoaded. Reconnect
		// without retaining the token in browser history or a stale async render.
		listen(window, "hashchange", () => {
			if (core.hasTokenFragment()) void connectFromLocation();
		});
		renderer.switchView(document.querySelector(".nav-item.active")?.dataset.view || "overview");
		return true;
	}

	async function start() {
		if (state.lifecycle.destroyed) return false;
		bindEvents();
		live.updateLocalClock();
		const connected = await connectFromLocation();
		if (connected) void live.refreshUpdateStatus();
		return connected;
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
		configureReadOnlySurface,
		start,
		destroy,
	};
	listen(document, "DOMContentLoaded", start, { once: true });
	return dashboard;
}

export const bootstrappedDashboard = createDashboard(globalThis);
