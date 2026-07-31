import {
	APIError,
	CONTROL_INTERVAL_MS,
	HIRING_EVIDENCE_DOCUMENTS,
	isRecord,
	LIVE_INTERVAL_MS,
	withRequestId,
} from "./dashboard-core.js";

const UPDATE_STATUS_FLAGS = new Map([
	["unchecked", null],
	["unavailable", null],
	["unknown", null],
	["current", false],
	["newer_installed", false],
	["local_changes", false],
	["different_target", null],
	["update_available", true],
]);
const RELEASE_VERSION_PATTERN = /^(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)\.(?:0|[1-9]\d*)(?:(?:a|b|rc)(?:0|[1-9]\d*))?$/;
const UPDATE_REF_PATTERN = /^[0-9A-Za-z][0-9A-Za-z._+/-]{0,127}$/;
const FULL_SHA_PATTERN = /^[0-9a-f]{40}$/;

function safeUpdateText(value, limit) {
	return typeof value === "string" && value.length > 0 && value.length <= limit
		&& value.trim() === value && !/[\u0000-\u001f\u007f]/.test(value);
}

export function safeUpdateTargetUrl(value, target, channel) {
	if (typeof value !== "string" || !isRecord(target)) return "";
	if (channel === "main") {
		const prefix = "https://github.com/Holeshot-Software-LLC/agency-runtime/commit/";
		return FULL_SHA_PATTERN.test(target.commit_sha) && value === `${prefix}${target.commit_sha}`
			? value : "";
	}
	const prefix = "https://github.com/Holeshot-Software-LLC/agency-runtime/releases/tag/";
	return UPDATE_REF_PATTERN.test(target.label)
		&& !target.label.includes("..") && !target.label.includes("//")
		&& !target.label.includes("@{") && !target.label.endsWith("/")
		&& value === `${prefix}${target.label}` ? value : "";
}

function validateUpdateChannel(status, channel, installed) {
	const expectedCommand = `agency upgrade --channel ${channel}`;
	const expectedSelectorRef = channel === "release" ? "latest" : "main";
	if (
		!isRecord(status)
		|| status.schema_version !== "agency.update.v1"
		|| !UPDATE_STATUS_FLAGS.has(status.status)
		|| status.update_available !== UPDATE_STATUS_FLAGS.get(status.status)
		|| status.command !== expectedCommand
		|| typeof status.checked !== "boolean"
		|| typeof status.cache_hit !== "boolean"
		|| typeof status.stale !== "boolean"
		|| typeof status.checking !== "boolean"
		|| status.checked !== (status.status !== "unchecked")
		|| (status.checked && !safeUpdateText(status.checked_at, 64))
		|| (!status.checked && status.checked_at !== null)
		|| (status.error !== null && !safeUpdateText(status.error, 512))
		|| !isRecord(status.installed)
		|| status.installed.build_identity !== installed.build_identity
		|| !isRecord(status.selector)
		|| status.selector.kind !== "channel"
		|| status.selector.value !== channel
		|| status.selector.ref !== expectedSelectorRef
		|| status.selector.key !== `channel:${channel}`
		|| (channel === "main" && ["newer_installed", "update_available"].includes(status.status))
	) return false;

	const targetRequired = !["unchecked", "unavailable"].includes(status.status);
	if (targetRequired !== isRecord(status.target)) return false;
	if (!targetRequired) return status.target === null;
	const target = status.target;
	if (
		!safeUpdateText(target.label, 128)
		|| !FULL_SHA_PATTERN.test(target.commit_sha)
		|| !safeUpdateTargetUrl(target.url, target, channel)
		|| (target.published_at !== null && !safeUpdateText(target.published_at, 64))
	) return false;
	if (channel === "main") {
		return target.kind === "main" && target.label === "main" && target.ref === "main"
			&& target.version === null && target.published_at === null;
	}
	return target.kind === "release" && target.ref === target.label
		&& (target.version === null || RELEASE_VERSION_PATTERN.test(target.version));
}

export function validateUpdateStatusPayload(payload) {
	if (!isRecord(payload) || payload.schema_version !== "agency.dashboard.update.v1") {
		throw new Error("Unsupported Agency update response.");
	}
	const installed = payload.installed;
	if (
		!isRecord(installed)
		|| !safeUpdateText(installed.package_version, 64)
		|| !safeUpdateText(installed.build_identity, 160)
		|| typeof payload.checking !== "boolean"
		|| !validateUpdateChannel(payload.release, "release", installed)
		|| !validateUpdateChannel(payload.main, "main", installed)
		|| payload.checking !== (payload.release.checking || payload.main.checking)
		|| payload.recommended !== (payload.release.update_available === true ? "release" : "main")
	) throw new Error("Agency update response is invalid.");
	return payload;
}

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
	const COLLECTION_CURSOR_PATTERN = /^[A-Za-z0-9_-]{1,1024}$/;
	const COLLECTION_PAGE_ITEM_LIMIT = 200;
	const lifecycleInactive = () => state.lifecycle.destroyed || state.lifecycle.suspended;

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
			lifecycleInactive()
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
			toggle.setAttribute("aria-disabled", String(toggle.disabled));
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
			!isRecord(master)
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

	function cancelUpdateRequest() {
		state.updateRequest.generation += 1;
		window.clearTimeout(state.updateRequest.timer);
		state.updateRequest.timer = null;
		state.updateRequest.controller?.abort();
		state.updateRequest.controller = null;
		state.updateRequest.inFlight = false;
		state.updateRequest.attempts = 0;
	}

	function ensureUpdateSurface() {
		let banner = byId("update-banner");
		if (banner) return banner;
		banner = document.createElement("aside");
		banner.id = "update-banner";
		banner.className = "update-banner";
		banner.hidden = true;
		banner.setAttribute("role", "status");
		banner.setAttribute("aria-live", "polite");

		const copy = document.createElement("span");
		copy.className = "update-copy";
		const title = document.createElement("strong");
		title.id = "update-title";
		const detail = document.createElement("small");
		detail.id = "update-detail";
		const command = document.createElement("code");
		command.id = "update-command";
		copy.append(title, detail, command);

		const actions = document.createElement("span");
		actions.className = "update-actions";
		const link = document.createElement("a");
		link.id = "update-link";
		link.className = "button ghost";
		link.target = "_blank";
		link.rel = "noopener noreferrer";
		link.textContent = "View target";
		link.hidden = true;
		const copyButton = document.createElement("button");
		copyButton.id = "update-copy-button";
		copyButton.className = "button solid";
		copyButton.type = "button";
		copyButton.textContent = "Copy command";
		copyButton.hidden = true;
		actions.append(link, copyButton);
		banner.append(copy, actions);
		byId("notice")?.insertAdjacentElement?.("afterend", banner);
		return banner;
	}

	function applyUpdateStatus(payload) {
		validateUpdateStatusPayload(payload);
		state.update = payload;
		renderUpdateStatus();
		return true;
	}

	function renderUpdateStatus() {
		const banner = ensureUpdateSurface();
		const payload = state.update;
		if (!banner || !payload) return false;
		const release = payload.release;
		const main = payload.main;
		const selected = release.update_available === true
			? release
			: main.update_available === true
				? main
				: release.checked && !release.error
					? release
					: main;
		const available = selected.update_available === true;
		const checking = payload.checking === true;
		banner.hidden = false;
		banner.dataset.state = available ? "available" : checking ? "checking" : "current";
		byId("update-title").textContent = available
			? "Agency update available"
			: checking
				? "Checking Agency updates"
				: "Agency version";
		const target = isRecord(selected.target) ? selected.target : null;
		const targetLabel = target?.label ? ` · ${target.label}` : "";
		byId("update-detail").textContent = `${payload.installed.build_identity}${targetLabel} · ${selected.status}`;
		byId("update-command").textContent = available ? selected.command : "";
		byId("update-command").hidden = !available;
		const channel = selected === release ? "release" : "main";
		const targetUrl = safeUpdateTargetUrl(target?.url, target, channel);
		const link = byId("update-link");
		link.hidden = !targetUrl;
		if (targetUrl) link.href = targetUrl;
		else link.removeAttribute("href");
		byId("update-copy-button").hidden = !available;
		return true;
	}

	function scheduleUpdateRefresh(delay = 1500) {
		window.clearTimeout(state.updateRequest.timer);
		state.updateRequest.timer = null;
		if (lifecycleInactive() || state.updateRequest.attempts >= 5) return;
		state.updateRequest.timer = window.setTimeout(refreshUpdateStatus, delay);
	}

	async function refreshUpdateStatus() {
		if (lifecycleInactive() || state.updateRequest.inFlight) return false;
		const controller = new AbortController();
		const generation = state.updateRequest.generation + 1;
		state.updateRequest.generation = generation;
		state.updateRequest.controller = controller;
		state.updateRequest.inFlight = true;
		try {
			const payload = await api("/api/update", { signal: controller.signal });
			if (
				controller.signal.aborted
				|| generation !== state.updateRequest.generation
				|| lifecycleInactive()
			) return false;
			applyUpdateStatus(payload);
			if (payload.checking === true) {
				state.updateRequest.attempts += 1;
				scheduleUpdateRefresh();
			} else {
				state.updateRequest.attempts = 0;
			}
			return true;
		} catch (error) {
			if (error?.name !== "AbortError") {
				state.updateRequest.attempts += 1;
				if (state.updateRequest.attempts < 3) scheduleUpdateRefresh(3000);
			}
			return false;
		} finally {
			if (state.updateRequest.controller === controller) {
				state.updateRequest.controller = null;
				state.updateRequest.inFlight = false;
			}
		}
	}

	function clearRemediationBusyState() {
		for (const kind of ["pending", "history"]) {
			const button = byId(`review-${kind}-more`);
			if (!button) continue;
			button.disabled = false;
			if (typeof button.removeAttribute === "function") button.removeAttribute("aria-busy");
			else button.setAttribute?.("aria-busy", "false");
		}
	}

	function clearHiringEvidenceBusyState() {
		state.hiringEvidenceLoadingCaseId = "";
		(document.querySelectorAll?.("[data-hiring-evidence-case]") || []).forEach((button) => {
			button.disabled = false;
			if (typeof button.removeAttribute === "function") button.removeAttribute("aria-busy");
			else button.setAttribute?.("aria-busy", "false");
		});
	}

	function abortViewRequests() {
		Object.values(state.requests).forEach((request) => {
			request.generation += 1;
			request.controller?.abort();
			request.controller = null;
		});
		clearRemediationBusyState();
		clearHiringEvidenceBusyState();
	}

	function beginViewRequest(name) {
		const request = state.requests[name];
		if (!request) throw new Error(`Unknown dashboard request scope: ${name}`);
		cancelFullRefresh();
		cancelControlRequest();
		state.commit.generation += 1;
		abortViewRequests();
		request.controller = new AbortController();
		return {
			controller: request.controller,
			generation: request.generation,
			commitGeneration: state.commit.generation,
		};
	}

	function viewRequestIsCurrent(name, request) {
		const current = state.requests[name];
		return !lifecycleInactive()
			&& !request.controller.signal.aborted
			&& current?.controller === request.controller
			&& current.generation === request.generation
			&& state.commit.generation === request.commitGeneration;
	}

	function finishViewRequest(name, request) {
		const current = state.requests[name];
		if (current?.controller !== request.controller) return false;
		current.controller = null;
		if (!Object.values(state.requests).some((item) => item.controller)) {
			scheduleControlRefresh(0);
		}
		return true;
	}

	function cancelViewRequests() {
		state.commit.generation += 1;
		abortViewRequests();
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
		return !lifecycleInactive()
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
			&& !lifecycleInactive()
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
				withRequestId(
					"The dashboard token expired. Run `agency dashboard service open` to reconnect.",
					error?.requestId,
				),
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
			showNotice(withRequestId(
				"Live updates paused while the dashboard reconnects.",
				error?.requestId,
			), true);
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

	function encodedCollectionCursorIsValid(value, kind, fields) {
		if (!COLLECTION_CURSOR_PATTERN.test(value) || typeof kind !== "string" || !kind) return false;
		const decode = runtime.atob || globalThis.atob;
		const encode = runtime.btoa || globalThis.btoa;
		if (typeof decode !== "function" || typeof encode !== "function") return false;
		try {
			const base64 = value.replace(/-/g, "+").replace(/_/g, "/");
			const padding = (4 - (value.length % 4)) % 4;
			const payload = JSON.parse(decode(base64 + "=".repeat(padding)));
			if (
				!Array.isArray(payload)
				|| payload.length !== fields + 1
				|| payload[0] !== kind
				|| payload.slice(1).some((item) => typeof item !== "string" || !item)
			) return false;
			return encode(JSON.stringify(payload))
				.replace(/\+/g, "-")
				.replace(/\//g, "_")
				.replace(/=+$/, "") === value;
		} catch {
			return false;
		}
	}

	function collectionCursorIsValid(value, contract, kind, fields) {
		if (typeof value !== "string") return false;
		if (contract === "slug") return AGENT_SLUG_PATTERN.test(value);
		if (contract === "encoded") return encodedCollectionCursorIsValid(value, kind, fields);
		throw new Error(`Unknown dashboard collection cursor contract: ${contract}`);
	}

	function validateCollectionPage(page, {
		itemField,
		revisionField,
		continuityField = "",
		cursorContract,
		cursorFields,
		cursorKind,
	}) {
		if (!isRecord(page)) {
			throw new Error(`The ${itemField} collection returned an invalid page.`);
		}
		if (!Array.isArray(page[itemField]) || page[itemField].length > COLLECTION_PAGE_ITEM_LIMIT) {
			throw new Error(`The ${itemField} collection returned invalid items.`);
		}
		if (typeof page.truncated !== "boolean") {
			throw new Error(`The ${itemField} collection returned an invalid truncation flag.`);
		}
		if (typeof page[revisionField] !== "string" || !page[revisionField].trim()) {
			throw new Error(`The ${itemField} collection omitted its paging revision.`);
		}
		if (continuityField && (
			typeof page[continuityField] !== "string"
			|| !page[continuityField].trim()
		)) throw new Error(`The ${itemField} collection omitted its continuity revision.`);
		if (page.truncated) {
			if (!collectionCursorIsValid(
				page.next_cursor,
				cursorContract,
				cursorKind,
				cursorFields,
			)) {
				throw new Error(`The ${itemField} collection returned an invalid next cursor.`);
			}
		} else if (page.next_cursor !== null) {
			throw new Error(`The ${itemField} collection returned an unexpected next cursor.`);
		}
		return page;
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
			cursorContract = "slug",
			cursorFields = 2,
			cursorKind = "",
			continuityField = "",
			expectedContinuity,
		},
	) {
		const pageContract = {
			itemField,
			revisionField,
			cursorContract,
			cursorFields,
			cursorKind,
			continuityField,
		};
		validateCollectionPage(initial, pageContract);
		if (
			expectedContinuity !== undefined
			&& initial[continuityField] !== expectedContinuity
		) throw new Error(`The ${itemField} collection did not match the control snapshot.`);
		const rows = [...initial[itemField]];
		const revision = initial[revisionField];
		const continuity = initial[continuityField];
		let cursor = initial.truncated ? initial.next_cursor : "";
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
			validateCollectionPage(page, pageContract);
			if (page[revisionField] !== revision) {
				throw new Error(`The ${itemField} collection changed while it was being paged.`);
			}
			if (continuityField && page[continuityField] !== continuity) {
				throw new Error(`The ${itemField} collection changed while it was being paged.`);
			}
			rows.push(...page[itemField]);
			cursor = page.truncated ? page.next_cursor : "";
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

	async function completeRosterPage(
		initial,
		signal,
		basePath = "/api/roster?limit=200",
		expectedConfigRevision,
	) {
		return completeCollection(initial, {
			basePath,
			itemField: "agents",
			revisionField: "roster_revision",
			continuityField: "config_revision",
			expectedContinuity: expectedConfigRevision,
			signal,
		});
	}

	async function completeGovernanceSnapshot(initial, signal) {
		if (!isRecord(initial)) {
			throw new Error("The governance collection returned an invalid page.");
		}
		const withSnapshots = await completeCollection(initial, {
			basePath: "/api/snapshots?limit=200",
			itemField: "snapshots",
			revisionField: "collection_revision",
			signal,
			cursorContract: "encoded",
			cursorKind: "roster-snapshots.v1",
		});
		const reviews = await completeCollection(withSnapshots.reviews || {}, {
			basePath: "/api/roster/reviews?limit=100",
			itemField: "candidates",
			revisionField: "collection_revision",
			cursorParameter: "candidate_cursor",
			signal,
			cursorContract: "encoded",
			cursorKind: "roster-reviews.v1",
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
				cursorContract: "encoded",
				cursorKind: "hiring.v1",
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

	function remediationRowsMatchPrefix(firstPage, loaded) {
		if (!Array.isArray(firstPage) || !Array.isArray(loaded) || firstPage.length > loaded.length) {
			return false;
		}
		return firstPage.every((item, index) => (
			typeof item?.event_id === "string"
			&& item.event_id
			&& item.event_id === loaded[index]?.event_id
		));
	}

	function remediationProjectionIsStable(next, current) {
		const nextRevision = typeof next?.remediation_revision === "string"
			? next.remediation_revision.trim()
			: "";
		const currentRevision = typeof current?.remediation_revision === "string"
			? current.remediation_revision.trim()
			: "";
		return Boolean(nextRevision && currentRevision && nextRevision === currentRevision);
	}

	function preserveRemediationExtent(next, current, kind) {
		if (state.remediationExtent[kind] !== true) return;
		const itemField = kind === "pending" ? "remediation_attempts" : "remediation_history";
		const cursorField = kind === "pending"
			? "next_remediation_pending_cursor"
			: "next_remediation_history_cursor";
		const hasMoreField = kind === "pending"
			? "remediation_pending_has_more"
			: "remediation_history_has_more";
		const firstPage = next[itemField];
		const loaded = current?.[itemField];
		if (
			!remediationProjectionIsStable(next, current)
			|| !remediationRowsMatchPrefix(firstPage, loaded)
		) {
			state.remediationExtent[kind] = false;
			return;
		}
		const seen = new Set(firstPage.map((item) => item.event_id));
		next[itemField] = [
			...firstPage,
			...loaded.filter((item) => !seen.has(item.event_id)),
		];
		next[cursorField] = current[cursorField];
		next[hasMoreField] = current[hasMoreField] === true;
	}

	function applyGovernanceSnapshot(payload = {}) {
		state.snapshots = Array.isArray(payload.snapshots) ? payload.snapshots : [];
		if (isRecord(payload.operations)) {
			state.rosterOperations = payload.operations;
		}
		if (isRecord(payload.reviews)) {
			const reviews = { ...payload.reviews };
			preserveRemediationExtent(reviews, state.rosterReview, "pending");
			preserveRemediationExtent(reviews, state.rosterReview, "history");
			state.rosterReview = reviews;
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

	async function fetchOperationalRoster(filters, signal, expectedConfigRevision) {
		const first = await api(operationalRosterPath(filters), { signal });
		return completeCollection(first, {
			basePath: operationalRosterPath(filters),
			itemField: "agents",
			revisionField: "roster_revision",
			continuityField: "config_revision",
			expectedContinuity: expectedConfigRevision,
			signal,
		});
	}

	async function applyOperationalFilters(event) {
		event?.preventDefault?.();
		if (config.serviceRestartRequired()) {
			showNotice("Restart the dashboard service before filtering the roster.", true);
			return false;
		}
		if (lifecycleInactive()) return false;
		const filters = operationalFilterValues();
		state.rosterFilterIntentGeneration += 1;
		state.rosterFilter = state.rosterFilterCommitted;
		if (byId("roster-search-slug")) {
			byId("roster-search-slug").value = state.rosterFilterCommitted;
		}
		const request = beginViewRequest("operationalRoster");
		try {
			const payload = await fetchOperationalRoster(filters, request.controller.signal);
			if (!viewRequestIsCurrent("operationalRoster", request)) return false;
			state.rosterFilters = filters;
			state.rosterOperations = payload;
			state.rosterFilter = "";
			state.rosterFilterCommitted = "";
			if (byId("roster-search-slug")) byId("roster-search-slug").value = "";
			renderPreservingInteraction(renderer.renderRoster);
			return true;
		} catch (error) {
			if (viewRequestIsCurrent("operationalRoster", request)) {
				if (error?.name !== "AbortError") showNotice(error.message, true);
				state.rosterFilter = state.rosterFilterCommitted;
				if (byId("roster-search-slug")) {
					byId("roster-search-slug").value = state.rosterFilterCommitted;
				}
				renderPreservingInteraction(renderer.renderRoster);
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
		if (lifecycleInactive()) return false;
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
				const active = state.rosterReview || {};
				if (
					!remediationProjectionIsStable(payload, current)
					|| !remediationProjectionIsStable(payload, active)
				) {
					throw new Error(
						"The remediation collection changed while this page was loading; the current page was preserved.",
					);
				}
				const itemField = kind === "pending" ? "remediation_attempts" : "remediation_history";
				const existing = Array.isArray(active[itemField]) ? active[itemField] : [];
				const incoming = Array.isArray(payload[itemField]) ? payload[itemField] : [];
				const seen = new Set(existing.map((item) => item?.event_id).filter(Boolean));
				const merged = [
					...existing,
					...incoming.filter((item) => !item?.event_id || !seen.has(item.event_id)),
				];
				const next = {
					...active,
					[itemField]: merged,
					[cursorField]: String(payload[cursorField] || ""),
					remediation_revision: payload.remediation_revision,
					remediation_unvalidated_resolution_count: Number.isInteger(
						payload.remediation_unvalidated_resolution_count,
					)
						? payload.remediation_unvalidated_resolution_count
						: active.remediation_unvalidated_resolution_count,
					remediation_stale_resolution_count: Number.isInteger(
						payload.remediation_stale_resolution_count,
					)
						? payload.remediation_stale_resolution_count
						: active.remediation_stale_resolution_count,
				};
				if (kind === "pending") {
					next.remediation_pending_has_more = payload.remediation_pending_has_more === true;
				} else {
					next.remediation_history_has_more = payload.remediation_history_has_more === true;
				}
				state.rosterReview = next;
				state.remediationExtent[kind] = true;
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
			if (typeof button.removeAttribute === "function") button.removeAttribute("aria-busy");
			else button.setAttribute?.("aria-busy", "false");
		}
		finishViewRequest("remediation", request);
		return loaded;
	}

	function rosterRequestPath() {
		return state.rosterFilter
			? `/api/agents/lookup?slug=${encodeURIComponent(state.rosterFilter)}`
			: "/api/roster?limit=100";
	}

	function validateExactRosterLookup(payload, requestedSlug) {
		const expected = normalizeRosterFilter(requestedSlug);
		const agents = payload?.agents;
		if (
			!expected
			|| payload?.filter_slug !== expected
			|| !Array.isArray(agents)
			|| agents.length > 1
			|| agents.some((agent) => agent?.agent_slug !== expected)
		) {
			throw new Error("Exact roster lookup response did not match the requested agent.");
		}
		return payload;
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
		if (lifecycleInactive()) return false;
		const intentGeneration = state.rosterFilterIntentGeneration + 1;
		state.rosterFilterIntentGeneration = intentGeneration;
		state.rosterFilter = slug;
		byId("roster-search-slug").value = slug;
		const refreshed = await refreshAll();
		if (
			intentGeneration !== state.rosterFilterIntentGeneration
			|| lifecycleInactive()
		) return false;
		if (refreshed) {
			state.rosterFilterCommitted = slug;
			return true;
		}
		if (!lifecycleInactive()) {
			state.rosterFilter = state.rosterFilterCommitted;
			byId("roster-search-slug").value = state.rosterFilterCommitted;
			renderer.renderRoster();
		}
		return false;
	}

	function searchRoster(event) {
		event.preventDefault();
		return applyRosterFilter(byId("roster-search-slug").value);
	}

	function clearRosterSearch() {
		return applyRosterFilter("");
	}

	async function fetchControlSnapshot(signal) {
		const snapshot = await api("/api/control", { signal });
		if (snapshot?.schema_version !== "agency.dashboard.control.v1") {
			if (signal?.aborted || lifecycleInactive()) {
				throw new runtime.DOMException("Aborted", "AbortError");
			}
			throw new Error("Dashboard control response has an unsupported schema.");
		}
		if (!snapshot.restart_required) {
			snapshot.roster = await completeRosterPage(
				snapshot.roster,
				signal,
				"/api/roster?limit=200",
				snapshot.config.revision,
			);
			snapshot.governance = await completeGovernanceSnapshot(
				snapshot.governance,
				signal,
			);
			if (state.rosterFilter) {
				const requestedSlug = state.rosterFilter;
				const requestedPath = rosterRequestPath();
				const filteredRoster = validateExactRosterLookup(
					await api(requestedPath, { signal }),
					requestedSlug,
				);
				snapshot.roster = await completeRosterPage(
					filteredRoster,
					signal,
					requestedPath,
					snapshot.config.revision,
				);
			}
			if (Object.keys(state.rosterFilters || {}).length) {
				snapshot.governance = {
					...(snapshot.governance || {}),
					operations: await fetchOperationalRoster(
						state.rosterFilters,
						signal,
						snapshot.config.revision,
					),
				};
			}
		}
		return snapshot;
	}

	function setControlFresh(snapshot) {
		state.control.revision = String(snapshot.control_revision || "unknown");
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
		if (!isRecord(snapshot)) {
			throw new Error("Dashboard control response is invalid.");
		}
		if (!isRecord(snapshot.config)) {
			throw new Error("Dashboard control response omitted configuration.");
		}
		const restartRequired = snapshot.restart_required === true
			|| snapshot.config.service_binding?.store_restart_required === true;
		if (
			!restartRequired
			&& (
				!Array.isArray(snapshot.hosts)
				|| !isRecord(snapshot.roster)
				|| !isRecord(snapshot.governance)
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
			|| state.full.inFlight
			|| Object.values(state.requests).some((request) => request.controller)
			|| lifecycleInactive()
			|| document.visibilityState === "hidden"
		) return;
		const controller = new AbortController();
		const commitGeneration = state.commit.generation;
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
				|| state.commit.generation !== commitGeneration
				|| state.lifecycle.suspended
			) return;
			applyControlSnapshot(snapshot, { render: false });
			if (workforce) commitWorkforceCollections(workforce, { render: false });
			renderPreservingInteraction(renderer.renderActiveControlView);
		} catch (error) {
			if (
				state.control.controller === controller
				&& !lifecycleInactive()
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
		cancelViewRequests();
		cancelFullRefresh();
		const commitGeneration = state.commit.generation;
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
				|| state.commit.generation !== commitGeneration
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
			if (lifecycleInactive()) return false;
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
			if (!payload || lifecycleInactive()) return false;
			applyLiveSnapshot(payload);
			state.live.failures = 0;
			setConnection(true, "Authenticated");
			setLiveStatus("Live · authenticated", "live");
			return true;
		} finally {
			scheduleLive(LIVE_INTERVAL_MS);
		}
	}

	function normalizeHiringEvidenceCaseId(value) {
		if (typeof value !== "string") {
			throw new Error("Hiring case ID must be a string.");
		}
		const caseId = value.trim();
		if (
			!caseId
			|| caseId !== value
			|| caseId.length > 512
			|| /[\u0000-\u001f\u007f]/.test(caseId)
		) {
			throw new Error("Hiring case ID is invalid.");
		}
		return caseId;
	}

	function validateHiringEvidenceResponse(payload, expectedCaseId) {
		if (!isRecord(payload)) {
			throw new Error("The exact hiring evidence response is invalid.");
		}
		const hiringCase = payload.hiring_case;
		if (!isRecord(hiringCase)) {
			throw new Error("The exact hiring evidence response omitted its case object.");
		}
		if (hiringCase.id !== expectedCaseId) {
			throw new Error("The exact hiring evidence response returned the wrong case.");
		}
		if (hiringCase.evidence_included !== true) {
			throw new Error("The exact hiring evidence response lacks its full-evidence marker.");
		}
		HIRING_EVIDENCE_DOCUMENTS.forEach(([field, label]) => {
			const documentValue = hiringCase[field];
			if (!isRecord(documentValue)) {
				throw new Error(`The exact hiring evidence response omitted ${label.toLowerCase()}.`);
			}
		});
		return hiringCase;
	}

	async function loadHiringEvidence(value) {
		let caseId;
		try {
			caseId = normalizeHiringEvidenceCaseId(value);
		} catch (error) {
			showNotice(error.message, true);
			return false;
		}
		if (lifecycleInactive()) return false;
		const request = beginViewRequest("hiringEvidence");
		state.hiringEvidenceLoadingCaseId = caseId;
		if (state.activeView === "workforce") {
			renderPreservingInteraction(renderer.renderWorkforce);
		}
		try {
			const payload = await api(
				`/api/hiring?case_id=${encodeURIComponent(caseId)}`,
				{ signal: request.controller.signal },
			);
			if (!viewRequestIsCurrent("hiringEvidence", request)) return false;
			state.hiringEvidence = validateHiringEvidenceResponse(payload, caseId);
			return true;
		} catch (error) {
			if (
				error?.name !== "AbortError"
				&& viewRequestIsCurrent("hiringEvidence", request)
			) showNotice(error.message, true);
			return false;
		} finally {
			if (viewRequestIsCurrent("hiringEvidence", request)) {
				state.hiringEvidenceLoadingCaseId = "";
				if (state.activeView === "workforce") {
					renderPreservingInteraction(renderer.renderWorkforce);
				}
			}
			finishViewRequest("hiringEvidence", request);
		}
	}

	async function refreshWorkforce({ signal } = {}) {
		if (signal) {
			const commitGeneration = state.commit.generation;
			const collections = await fetchWorkforceCollections(signal);
			if (
				signal.aborted
				|| state.commit.generation !== commitGeneration
				|| lifecycleInactive()
			) return false;
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
		if (lifecycleInactive()) return false;
		showNotice(successMessage);
		try {
			await refreshRuntimeEvidence();
		} catch (error) {
			if (lifecycleInactive()) return false;
			if (terminalLiveFailure(error)) handleLiveFailure(error);
			else showNotice(`${successMessage} The live view could not refresh: ${error.message}`, true);
		}
		return true;
	}

	async function reconcileAll(successMessage) {
		if (lifecycleInactive()) return false;
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
		cancelUpdateRequest,
		ensureUpdateSurface,
		applyUpdateStatus,
		renderUpdateStatus,
		scheduleUpdateRefresh,
		refreshUpdateStatus,
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
		validateExactRosterLookup,
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
		loadHiringEvidence,
		refreshWorkforce,
		reconcileRuntimeEvidence,
		reconcileAll,
	};
}
