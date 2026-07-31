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

	function configureOwnerSurface() {
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
		const configForm = byId("config-form");
		if (configForm) configForm.setAttribute("aria-label", "Agency Runtime configuration");
		const privacy = byId("privacy-chip");
		if (privacy?.textContent === "Metadata only") privacy.textContent = "Runtime metadata only";
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
		configureOwnerSurface();
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
		listen(byId("trim-button"), "click", actions.trimRuntime);
		listen(byId("trim-days"), "input", () => {
			byId("trim-days").dataset.dirty = "true";
		});
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
				const approval = event.target?.closest?.("[data-hiring-approve-case]");
				const approvalCaseId = String(approval?.dataset?.hiringApproveCase || "");
				if (approvalCaseId && !approval.disabled) {
					void actions.hiringApprove(approvalCaseId);
					return;
				}
				const control = event.target?.closest?.("[data-hiring-evidence-case]");
				const caseId = String(control?.dataset?.hiringEvidenceCase || "");
				if (caseId && !control.disabled) void live.loadHiringEvidence(caseId);
			});
		}
		listen(byId("config-form"), "submit", actions.saveConfig);
		listen(byId("config-form"), "input", config.updateConfigDirtyState);
		listen(byId("config-form"), "change", config.updateConfigDirtyState);
		const workforceActionForm = byId("workforce-action-form");
		if (workforceActionForm) listen(workforceActionForm, "submit", actions.workforceAction);
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
		configureOwnerSurface,
		start,
		destroy,
	};
	listen(document, "DOMContentLoaded", start, { once: true });
	return dashboard;
}

export const bootstrappedDashboard = createDashboard(globalThis);
