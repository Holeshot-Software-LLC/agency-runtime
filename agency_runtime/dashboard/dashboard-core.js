export const LIVE_INTERVAL_MS = 2500;
export const CONTROL_INTERVAL_MS = 15000;
export const HIRING_EVIDENCE_DOCUMENTS = Object.freeze([
	["gap_evidence", "Gap evidence"],
	["duplicate_evidence", "Duplicate analysis"],
	["contract_evidence", "Contract evidence"],
	["critic_evidence", "Independent critic"],
	["model_evidence", "Model receipts"],
]);

export function isRecord(value) {
	return value !== null && typeof value === "object" && !Array.isArray(value);
}

export class APIError extends Error {
	constructor(message, status, retryAfter = null, requestId = "") {
		super(message);
		this.name = "APIError";
		this.status = status;
		this.retryAfter = retryAfter;
		this.requestId = requestId;
	}
}

export function createState() {
	return {
		token: "",
		master: null,
		overview: null,
		activity: {},
		activityCollections: {},
		hosts: [],
		roster: [],
		rosterPage: null,
		rosterFilter: "",
		rosterFilterCommitted: "",
		rosterOperations: null,
		rosterFilters: {},
		rosterReview: null,
		workforce: [],
		workforceCounts: {},
		workforcePage: null,
		hiring: [],
		hiringPage: null,
		hiringEvidence: null,
		hiringEvidenceLoadingCaseId: "",
		selectedWorkerDetail: null,
		snapshots: [],
		config: null,
		serviceBinding: null,
		controlConfigRevision: "",
		configBaseline: new Map(),
		configDirty: false,
		pendingConfig: null,
		activeView: "overview",
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
			generation: 0,
			revision: "",
			sampledAt: null,
			stale: false,
			errorRequestId: "",
		},
		full: {
			controller: null,
			inFlight: false,
			generation: 0,
		},
		mutation: {
			active: 0,
			controllers: new Set(),
		},
		connection: {
			generation: 0,
		},
		commit: {
			generation: 0,
		},
		requests: {
			operationalRoster: { controller: null, generation: 0 },
			remediation: { controller: null, generation: 0 },
			workforce: { controller: null, generation: 0 },
			workerDetail: { controller: null, generation: 0 },
			hiringEvidence: { controller: null, generation: 0 },
		},
		remediationExtent: {
			pending: false,
			history: false,
		},
		rosterFilterIntentGeneration: 0,
		lifecycle: {
			bound: false,
			destroyed: false,
			suspended: false,
		},
	};
}

export function nestedValue(root, path) {
	return path.split(".").reduce((value, part) => (
		value != null && Object.hasOwn(value, part) ? value[part] : undefined
	), root);
}

export function stableValue(value) {
	if (Array.isArray(value)) return value.map(stableValue);
	if (value && typeof value === "object") {
		return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stableValue(value[key])]));
	}
	return value;
}

export function comparable(value) {
	return JSON.stringify(stableValue(value));
}

export function createCore(runtime = globalThis) {
	const {
		document,
		window,
		fetch,
		history,
		sessionStorage,
		crypto,
		HTMLElement,
		HTMLInputElement,
		AbortController,
	} = runtime;
	const state = createState();
	const listenerDisposers = [];

	function byId(id) { return document.getElementById(id); }

	function el(tag, className, text) {
		const node = document.createElement(tag);
		if (className) node.className = className;
		if (text != null) node.textContent = String(text);
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
		showNotice.timer = window.setTimeout(() => {
			showNotice.timer = null;
			notice.hidden = true;
		}, 6000);
	}
	showNotice.timer = null;

	function clearNotice() {
		window.clearTimeout(showNotice.timer);
		showNotice.timer = null;
		byId("notice").hidden = true;
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
		if (host.runtime_enabled === false) return "runtime-disabled";
		if (host.inspection_status && host.inspection_status !== "complete") {
			return `inspection-${host.inspection_status}`;
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
		const requestId = crypto?.randomUUID?.();
		if (
			typeof requestId !== "string"
			|| !/^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(requestId)
		) {
			throw new Error("Secure browser request IDs are unavailable.");
		}
		const headers = {
			Authorization: `Bearer ${state.token}`,
			"X-Agency-Request-ID": requestId,
			...(options.headers || {}),
		};
		if (options.body !== undefined) headers["Content-Type"] = "application/json";
		let response;
		try {
			response = await fetch(path, {
				...options,
				headers,
				cache: "no-store",
				credentials: "omit",
			});
		} catch (error) {
			if (error?.name === "AbortError") throw error;
			runtime.console?.error?.(`Agency dashboard request ${requestId} failed before response.`);
			throw new APIError(
				String(error?.message || "Network request failed."),
				0,
				null,
				requestId,
			);
		}
		let payload;
		try { payload = await response.json(); } catch { payload = { error: `HTTP ${response.status}` }; }
		const responseId = String(
			payload?.request_id
				|| response.headers.get("X-Agency-Request-ID")
				|| response.headers.get("X-Request-ID")
				|| requestId,
		);
		if (!response.ok) {
			runtime.console?.error?.(
				`Agency dashboard request ${responseId} failed with HTTP ${response.status}.`,
			);
			throw new APIError(
				payload.error || `HTTP ${response.status}`,
				response.status,
				response.headers.get("Retry-After"),
				responseId,
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
		if (!state.token) {
			throw new Error("This dashboard URL has no active access token. Run `agency dashboard service open` or restart `agency dashboard`.");
		}
	}

	function listen(target, name, listener, options) {
		target.addEventListener(name, listener, options);
		listenerDisposers.push(() => target.removeEventListener(name, listener, options));
		return listener;
	}

	function disposeListeners() {
		while (listenerDisposers.length) listenerDisposers.pop()();
	}

	function disposeCore() {
		clearNotice();
		if (state.confirmation) finishConfirmation(false);
	}

	function interactionDescriptor(node) {
		if (!node) return null;
		if (node.id) return { kind: "id", value: node.id };
		for (const field of ["preserveKey", "worker"]) {
			const value = String(node.dataset?.[field] || "");
			if (value) return { kind: field, value };
		}
		return null;
	}

	function findInteractionNode(descriptor) {
		if (!descriptor) return null;
		if (descriptor.kind === "id") return byId(descriptor.value);
		return [...document.querySelectorAll("[data-preserve-key], [data-worker]")]
			.find((node) => String(node.dataset?.[descriptor.kind] || "") === descriptor.value)
			|| null;
	}

	function captureInteractionState() {
		const active = document.activeElement;
		const focus = interactionDescriptor(active);
		const selection = active && Number.isInteger(active.selectionStart)
			? [active.selectionStart, active.selectionEnd]
			: null;
		const open = [...document.querySelectorAll("details[open]")]
			.map(interactionDescriptor)
			.filter(Boolean);
		return { focus, open, selection };
	}

	function restoreInteractionState(snapshot) {
		if (!snapshot) return;
		snapshot.open.forEach((descriptor) => {
			const node = findInteractionNode(descriptor);
			if (node) node.open = true;
		});
		const active = findInteractionNode(snapshot.focus);
		if (!active) return;
		active.focus?.({ preventScroll: true });
		if (snapshot.selection && typeof active.setSelectionRange === "function") {
			active.setSelectionRange(...snapshot.selection);
		}
	}

	function renderPreservingInteraction(render) {
		const snapshot = captureInteractionState();
		render();
		restoreInteractionState(snapshot);
	}

	return {
		runtime,
		document,
		window,
		HTMLElement,
		HTMLInputElement,
		AbortController,
		state,
		byId,
		el,
		formatBytes,
		formatTime,
		showNotice,
		clearNotice,
		requestConfirmation,
		finishConfirmation,
		modalFocusable,
		handleModalKeyboard,
		hostState,
		truthLabel,
		hostLocation,
		api,
		installToken,
		listen,
		disposeListeners,
		disposeCore,
		captureInteractionState,
		restoreInteractionState,
		renderPreservingInteraction,
		nestedValue,
		stableValue,
		comparable,
	};
}
