import { HIRING_EVIDENCE_DOCUMENTS, isRecord, safeRequestId } from "./dashboard-core.js";

const EXECUTION_HOSTS = ["codex", "claude", "openclaw", "hermes", "zcode"];
const ROUTE_LAB_HOST_INVENTORY_LIMIT = EXECUTION_HOSTS.length * 2;
const ROUTE_LAB_CAPABILITY_LIMIT = 64;
const ROUTE_LAB_EVIDENCE_LIMIT = 8;
const ROUTE_LAB_TOKEN_PATTERN = /^[a-z0-9][a-z0-9._+-]{0,63}$/;
const ROUTE_LAB_NATIVE_CAPABILITIES = new Set([
	"code-execution",
	"native-delegation",
	"package-management",
	"repository-read",
	"repository-write",
	"runtime-evidence",
	"shell-execution",
	"source-control",
	"test-execution",
]);
const ROUTE_LAB_PLATFORMS = new Set(["windows", "linux"]);

const EVIDENCE_COLUMNS = {
	specialists: [["slug", "Specialist"], ["session_id", "Session"], ["trace_id", "Trace"], ["state", "Evidence state"], ["loaded_at", "Activated"], ["expired_at", "Expired"]],
	delegations: [["observed_child", "Observed child"], ["host", "Host"], ["status", "Event state"], ["backend", "Host tool"], ["work_unit_id", "Recorded correlation ID"], ["started_at", "Observed"]],
	routing: [["trace_id", "Trace"], ["id", "Decision"], ["status", "Outcome"], ["semantic_status", "Semantic result"], ["source", "Source"], ["selected_ids", "Selected"], ["fallback_applied", "Fallback applied"], ["fallback_companion_ids", "Fallback policy IDs"], ["created_at", "Created"]],
	receipts: [["requested_model", "Requested"], ["model_group", "LiteLLM router / model group"], ["resolved_provider", "Actual provider"], ["resolved_model", "Actual model"], ["host", "Host"], ["status", "Status"], ["source", "Source"], ["ended_at", "Ended"]],
	runs: [["trace_id", "Trace"], ["session_id", "Session"], ["host", "Host"], ["status", "Status"], ["started_at", "Started"], ["ended_at", "Ended"]],
	preflight_failures: [["trace_id", "Trace"], ["host", "Host"], ["stage", "Failed stage"], ["reason_code", "Reason"], ["invariant_code", "Invariant"], ["exception_category", "Category"], ["recorded_at", "Recorded"]],
	finalizations: [["trace_id", "Trace"], ["host", "Host"], ["action", "Action"], ["missing", "Missing"], ["created_at", "Created"]],
};

function observedChildIdentity(row) {
	if (!isRecord(row)) return "No correlated child identity";
	const kind = typeof row.executed_worker_kind === "string"
		? row.executed_worker_kind.trim()
		: "";
	const workerId = typeof row.executed_worker_id === "string"
		? row.executed_worker_id.trim()
		: "";
	const nativeRunId = typeof row.native_run_id === "string"
		? row.native_run_id.trim()
		: "";
	if (!kind || !workerId || !nativeRunId) return "Not observed";
	return `${kind} · ${workerId} · run ${nativeRunId}`;
}

function routeLabTokensAreValid(values, { allowed = null, limit = ROUTE_LAB_CAPABILITY_LIMIT } = {}) {
	if (!Array.isArray(values) || values.length > limit) return false;
	if (values.some((value) => (
		typeof value !== "string"
		|| !ROUTE_LAB_TOKEN_PATTERN.test(value)
		|| (allowed && !allowed.has(value))
	))) return false;
	return values.every((value, index) => index === 0 || values[index - 1] < value);
}

function routeLabEvidenceIsValid(values) {
	if (!Array.isArray(values) || values.length > ROUTE_LAB_EVIDENCE_LIMIT) return false;
	const seen = new Set();
	return values.every((value) => {
		if (typeof value !== "string" || !value || value.length > 256) return false;
		if (value.trim().replace(/\s+/g, " ") !== value || seen.has(value)) return false;
		seen.add(value);
		return true;
	});
}

function routeLabReceiptIsValid(receipt, host) {
	return isRecord(receipt)
		&& receipt.contract_version === "1"
		&& receipt.surface === host
		&& receipt.execution_host === host
		&& receipt.inference_surface === ""
		&& ROUTE_LAB_PLATFORMS.has(receipt.platform)
		&& receipt.status === "native-installation-verified"
		&& receipt.source === "native-installation-evidence"
		&& routeLabTokensAreValid(receipt.capabilities, { allowed: ROUTE_LAB_NATIVE_CAPABILITIES })
		&& routeLabTokensAreValid(receipt.unknown_tools)
		&& routeLabEvidenceIsValid(receipt.evidence)
		&& receipt.session_id === ""
		&& receipt.trace_id === ""
		&& receipt.observed_at === "";
}

function hiringEvidenceIsComplete(value, caseId) {
	return isRecord(value)
		&& value.id === caseId
		&& value.evidence_included === true
		&& HIRING_EVIDENCE_DOCUMENTS.every(([field]) => (
			isRecord(value[field])
		));
}

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
	const div = (...args) => el("div", ...args);
	const span = (...args) => el("span", ...args);
	const small = (...args) => el("small", ...args);
	const strong = (...args) => el("strong", ...args);
	const paragraph = (...args) => el("p", ...args);
	const animationListeners = new Map();
	const configuredTabs = new WeakSet();

	function runButtonAction(button, action) {
		button.disabled = true;
		button.setAttribute("aria-busy", "true");
		return Promise.resolve()
			.then(action)
			.finally(() => {
				button.disabled = false;
				button.removeAttribute("aria-busy");
			});
	}

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

	function collectionSourceState(name) {
		const source = state.workforceSources?.[name];
		const status = ["not_loaded", "current", "stale", "unavailable"].includes(source?.status)
			? source.status
			: "not_loaded";
		return {
			status,
			error: typeof source?.error === "string" ? source.error : "",
			lastGoodAt: source?.lastGoodAt || null,
		};
	}

	function collectionSourceLabel(source) {
		return source.status.replaceAll("_", " ").toUpperCase();
	}

	function collectionSourceSummary(source, label) {
		const sampled = source.lastGoodAt ? ` from ${formatTime(source.lastGoodAt)}` : "";
		if (source.status === "current") return `${label} source current${sampled}.`;
		if (source.status === "stale") {
			return `${label} source stale; retaining the last-good sample${sampled}.${source.error ? ` ${source.error}` : ""}`;
		}
		if (source.status === "unavailable") {
			return `${label} source unavailable; no validated sample.${source.error ? ` ${source.error}` : ""}`;
		}
		return `${label} source has not loaded.`;
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
		if (isRecord(row)) {
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

	function definitionList(className, rows) {
		const list = el("dl", className);
		rows.forEach(([label, value]) => {
			const row = el("div");
			row.append(el("dt", "", label), el("dd", "", value));
			list.append(row);
		});
		return list;
	}

	function tokenList(values, fallback, limit = Infinity) {
		const list = div( "token-list");
		const items = Array.isArray(values) ? values.filter(Boolean) : [];
		(items.length ? items : [fallback]).slice(0, limit).forEach((value) => {
			list.append(el("span", "token", value));
		});
		return list;
	}

	function appendTokenGroups(root, groups, className, labelTag, fallback, limit = Infinity) {
		groups.forEach(([label, values]) => {
			const group = div( className);
			group.append(el(labelTag, "", label), tokenList(values, fallback, limit));
			root.append(group);
		});
	}

	function formatLatency(value) {
		const milliseconds = Number(value);
		if (!Number.isFinite(milliseconds) || milliseconds < 0) return "—";
		if (milliseconds < 1000) return `${Math.round(milliseconds)} ms`;
		return `${(milliseconds / 1000).toFixed(milliseconds < 10_000 ? 2 : 1)} s`;
	}

	function metricSourceMetadata(name) {
		return state.metricEvidence?.sources?.[name]
			|| { stale: false, unavailable: false, error: "", sampledAt: null };
	}

	function metricEvidenceContext(name, base) {
		const metadata = metricSourceMetadata(name);
		if (metadata.stale) {
			return `${base} Last refresh retained prior evidence: ${metadata.error || "source unavailable"}`;
		}
		if (metadata.unavailable) {
			return `${base} No validated source sample is available: ${metadata.error || "source unavailable"}`;
		}
		return base;
	}

	function renderSelectionDistribution() {
		const data = state.selectionDistribution;
		const chart = byId("selection-chart");
		const tail = byId("selection-tail-body");
		chart?.replaceChildren();
		tail?.replaceChildren();
		if (!chart || !tail) return;
		const stateTag = byId("selection-evidence-state");
		const sourceMetadata = metricSourceMetadata("selections");
		if (!data) {
			setMetric("selection-metric-decisions", "—");
			setMetric("selection-metric-distinct", "—");
			setMetric("selection-metric-roster", "—");
			setMetric("selection-metric-occurrences", "—");
			setMetric("selection-metric-concentration", "—");
			if (stateTag) {
				stateTag.textContent = sourceMetadata.unavailable ? "UNAVAILABLE" : "LOADING";
				stateTag.dataset.state = sourceMetadata.unavailable ? "unavailable" : "unknown";
			}
			byId("selection-evidence-context").textContent = metricEvidenceContext("selections",
				"Selection evidence has not loaded.",
			);
			const empty = div("empty-compact", "No selection-bearing decisions recorded.");
			empty.setAttribute("role", "listitem");
			chart.append(empty);
			tail.append(emptyRow(4, "No bounded long-tail evidence."));
			return;
		}

		const decisions = data.decisions_with_selections;
		setMetric("selection-metric-decisions", decisions);
		setMetric("selection-metric-distinct", data.distinct_selected_specialists);
		setMetric("selection-metric-roster", data.active_roster_size);
		setMetric("selection-metric-occurrences", data.selection_occurrences);
		setMetric(
			"selection-metric-concentration",
			`${(data.top_10_share_of_selection_occurrences * 100).toFixed(1)}%`,
		);
		if (stateTag) {
			stateTag.textContent = sourceMetadata.stale
				? "STALE"
				: decisions > 0 ? "OBSERVED" : "NO DATA";
			stateTag.dataset.state = sourceMetadata.stale
				? "stale"
				: decisions > 0 ? "observed" : "unknown";
		}
		const scanState = data.selection_bearing_decision_scan_truncated
			? `Newest ${data.selection_bearing_decision_scan_limit} selection-bearing decisions; older retained evidence is outside this view.`
			: `All retained selection-bearing decisions were scanned, up to the ${data.selection_bearing_decision_scan_limit}-decision safety limit.`;
		byId("selection-evidence-context").textContent = metricEvidenceContext("selections",
			decisions > 0
				? `${decisions} decisions contain ${data.selection_occurrences} specialist selections. Current active roster: ${data.active_roster_size}. ${scanState} Per-specialist decision shares are independent and need not sum to 100%.`
				: `No selection-bearing decisions recorded. Current active roster: ${data.active_roster_size}. ${scanState}`,
		);
		if (!decisions) {
			const empty = div("empty-compact", "No selection-bearing decisions recorded.");
			empty.setAttribute("role", "listitem");
			chart.append(empty);
		} else {
			data.top_specialists.slice(0, 15).forEach((row) => {
				const share = row.share_of_decisions_with_selections * 100;
				const item = div("selection-bar-row");
				item.setAttribute("role", "listitem");
				const label = div("selection-bar-label");
				label.append(
					strong("", row.slug),
					small("", `${row.decisions_containing_specialist} decisions · ${share.toFixed(1)}%`),
				);
				const track = el("progress", "selection-bar-track");
				track.setAttribute("aria-hidden", "true");
				track.max = 100;
				track.value = Math.max(0, Math.min(100, share));
				track.setAttribute("max", "100");
				track.setAttribute("value", track.value.toFixed(2));
				item.append(label, track);
				chart.append(item);
			});
		}
		data.top_specialists.slice(10).forEach((row) => {
			const tr = el("tr");
			[
				row.slug,
				row.decisions_containing_specialist,
				`${(row.share_of_decisions_with_selections * 100).toFixed(1)}%`,
				row.selection_occurrences,
			].forEach((value) => tr.append(el("td", "", value)));
			tail.append(tr);
		});
		if (data.long_tail.specialist_count > 0) {
			const tr = el("tr", "aggregate-row");
			[
				`${data.long_tail.specialist_count} specialists beyond top 50`,
				data.long_tail.decisions_containing_specialist,
				`${(data.long_tail.share_of_decisions_with_selections * 100).toFixed(1)}%`,
				data.long_tail.selection_occurrences,
			].forEach((value) => tr.append(el("td", "", value)));
			tail.append(tr);
		}
		if (!tail.children.length) tail.append(emptyRow(4, "No specialists outside the top 10."));
	}

	function renderRoutingLatency() {
		const data = state.routingLatency;
		const sourceBody = byId("latency-source-body");
		const slowestBody = byId("latency-slowest-body");
		sourceBody?.replaceChildren();
		slowestBody?.replaceChildren();
		if (!sourceBody || !slowestBody) return;
		const budgetTag = byId("latency-budget-state");
		const sourceMetadata = metricSourceMetadata("latency");
		if (!data) {
			for (const id of ["latency-metric-p50", "latency-metric-p95", "latency-metric-provider", "latency-metric-agency", "latency-metric-calls"]) {
				setMetric(id, "—");
			}
			if (budgetTag) {
				budgetTag.textContent = sourceMetadata.unavailable ? "UNAVAILABLE" : "UNKNOWN";
				budgetTag.dataset.state = sourceMetadata.unavailable ? "unavailable" : "unknown";
			}
			byId("latency-evidence-context").textContent = metricEvidenceContext("latency",
				"Routing latency evidence has not loaded.",
			);
			sourceBody.append(emptyRow(4, "No eligible routing evidence."));
			slowestBody.append(emptyRow(5, "No eligible routing evidence."));
			return;
		}

		const hasEvidence = data.overall.count > 0;
		setMetric("latency-metric-p50", hasEvidence ? formatLatency(data.overall.p50_ms) : "—");
		setMetric("latency-metric-p95", hasEvidence ? formatLatency(data.overall.p95_ms) : "—");
		setMetric("latency-metric-provider", data.split.provider_ms.count
			? formatLatency(data.split.provider_ms.p50_ms) : "—");
		setMetric("latency-metric-agency", data.split.agency_ms.count
			? formatLatency(data.split.agency_ms.p50_ms) : "—");
		setMetric("latency-metric-calls", data.split.decisions
			? data.split.calls_per_decision.toFixed(2) : "—");
		const budgetState = !hasEvidence ? "UNKNOWN" : data.over_budget ? "OVER BUDGET" : "WITHIN BUDGET";
		if (budgetTag) {
			budgetTag.textContent = `${sourceMetadata.stale ? "STALE · " : ""}${budgetState}`;
			budgetTag.dataset.state = sourceMetadata.stale
				? "stale" : !hasEvidence ? "unknown" : data.over_budget ? "over" : "within";
		}
		const attribution = data.split.unattributed_decisions
			? `${data.split.unattributed_decisions} decision(s) have incomplete provider timing and are excluded from the provider/Agency split.`
			: `${data.split.decisions} decision(s) have complete provider timing.`;
		byId("latency-evidence-context").textContent = metricEvidenceContext("latency",
			hasEvidence
				? `Newest ${data.overall.count} positive-latency decisions within a ${data.window.limit}-decision window. p95 is compared with the ${formatLatency(data.budget_ms)} budget; equality passes. ${attribution}`
				: `No eligible routing evidence. Zero or absent durations are unknown, never fast. Budget: ${formatLatency(data.budget_ms)}.`,
		);
		Object.entries(data.by_source).forEach(([source, summary]) => {
			const tr = el("tr");
			[source, summary.count, formatLatency(summary.p50_ms), formatLatency(summary.p95_ms)]
				.forEach((value) => tr.append(el("td", "", value)));
			sourceBody.append(tr);
		});
		if (!sourceBody.children.length) sourceBody.append(emptyRow(4, "No eligible routing evidence."));
		data.slowest.forEach((row) => {
			const attributable = Number(row.provider_calls) > 0
				&& Number(row.provider_unknown_calls || 0) === 0
				&& Number(row.provider_timed_calls ?? row.provider_calls) === Number(row.provider_calls)
				&& Number(row.provider_ms) > 0;
			const tr = el("tr");
			[
				row.source || "unknown",
				formatLatency(row.latency_ms),
				attributable ? formatLatency(row.provider_ms) : "unknown",
				attributable ? formatLatency(Math.max(0, row.latency_ms - row.provider_ms)) : "unknown",
				formatTime(row.created_at),
			].forEach((value) => tr.append(el("td", "", value)));
			slowestBody.append(tr);
		});
		if (!slowestBody.children.length) slowestBody.append(emptyRow(5, "No eligible routing evidence."));
	}

	function renderMetricEvidence() {
		renderSelectionDistribution();
		renderRoutingLatency();
		const freshness = byId("metric-evidence-freshness");
		if (freshness) {
			const sourceLine = (name, label) => {
				const metadata = metricSourceMetadata(name);
				if (metadata.stale && metadata.sampledAt) {
					return `${label} last-good sample ${formatTime(metadata.sampledAt)}; refresh failed`;
				}
				if (metadata.unavailable) return `${label} unavailable; no validated sample`;
				if (metadata.sampledAt) return `${label} source sampled ${formatTime(metadata.sampledAt)}`;
				return `${label} source not loaded`;
			};
			const message = `${sourceLine("selections", "Selection")}; ${sourceLine("latency", "latency")}.`;
			if (freshness.textContent !== message) freshness.textContent = message;
		}
		const status = byId("metric-evidence-status");
		if (status) {
			const sourceState = (name) => {
				const metadata = metricSourceMetadata(name);
				if (metadata.stale) return "stale";
				if (metadata.unavailable) return "unavailable";
				if (metadata.sampledAt) return "current";
				return "not loaded";
			};
			const message = `Decision evidence: selection ${sourceState("selections")}; latency ${sourceState("latency")}.`;
			if (status.textContent !== message) status.textContent = message;
		}
	}

	function renderOverview() {
		const data = state.overview || {};
		setMetric(
			"metric-runtime",
			state.master?.enabled === false ? "Paused" : (data.status === "ok" ? "Online" : "Unknown"),
		);
		setMetric("metric-roster", data.roster_count ?? "—");
		setMetric("metric-routing", data.recent?.routing ?? "—");
		setMetric("metric-delegations", data.recent?.delegations ?? "—");
		setMetric("metric-store", formatBytes((data.db_size_bytes || 0) + (data.wal_size_bytes || 0)));
		byId("setting-capture").textContent = data.capture_content ? "Opt-in enabled" : "Disabled";
		byId("setting-retention").textContent = `${data.retention_days || 30} days`;
		byId("privacy-chip").textContent = data.capture_content
			? "Redacted runtime content"
			: "Runtime metadata only";
		const tbody = byId("overview-delegations");
		tbody.replaceChildren();
		const previousOverviewKeys = state.evidenceKeys.get("overview") || new Set();
		const nextOverviewKeys = new Set();
		(state.activity.delegations || []).slice(0, 12).forEach((row, index) => {
			const tr = el("tr");
			const key = evidenceRowKey(row, index);
			nextOverviewKeys.add(key);
			if (previousOverviewKeys.size && !previousOverviewKeys.has(key)) tr.classList.add("is-new");
			[observedChildIdentity(row), row.host || "unknown"].forEach((value) => {
				tr.append(el("td", "", value));
			});
			const status = span( `status ${row.status || ""}`, row.status || "unknown");
			const statusCell = el("td");
			statusCell.append(status);
			tr.append(statusCell);
			tr.append(el("td", "", row.backend || "—"), el("td", "", formatTime(row.started_at)));
			tbody.append(tr);
		});
		state.evidenceKeys.set("overview", nextOverviewKeys);
		if (!tbody.children.length) tbody.append(emptyRow(5, "No delegation-event rows observed yet."));

		const hostStack = byId("overview-hosts");
		hostStack.replaceChildren();
		state.hosts.forEach((host) => {
			const row = div( "host-row");
			const current = hostState(host);
			const copy = el("div");
			copy.append(strong( "", host.host), small( "", hostLocation(host)));
			row.append(copy, span( `host-state ${current}`, current));
			hostStack.append(row);
		});
		if (!hostStack.children.length) {
			hostStack.append(el(
				"div",
				"empty-compact",
				"No supported agent hosts were found. Install or register a host, then refresh.",
			));
		}

		const providerStack = byId("provider-health");
		providerStack.replaceChildren();
		const inference = isRecord(data.inference)
			? data.inference
			: null;
		const inferenceState = String(inference?.state || "unknown").toLowerCase();
		const inferenceTag = byId("inference-state");
		if (inferenceTag) {
			inferenceTag.textContent = inferenceState.toUpperCase().replaceAll("_", " ");
			inferenceTag.dataset.state = inferenceState;
		}
		(inference?.provider_chain || []).forEach((provider) => {
			const row = div( "provider-row provider-chain-row");
			const copy = el("div");
			const request = provider.requested_model || "model not declared";
			copy.append(
				strong( "", `${provider.order}. ${provider.name}`),
				small( "", `${provider.type || "unknown"} · requested ${request}`),
			);
			if (provider.router) copy.append(small( "provider-router", `Router / model group: ${provider.router}`));
			const observed = provider.observed_receipt;
			if (observed) {
				copy.append(el(
					"small",
					"provider-resolution",
					`Observed actual: ${observed.actual_provider || "unavailable"} / ${observed.actual_model || "unavailable"}`,
				));
			}
			const ready = provider.configuration_ready === true;
			row.append(copy, span( `status ${ready ? "configured" : "failed"}`, ready ? "config ready" : "config gap"));
			providerStack.append(row);
		});
		if (!providerStack.children.length) {
			(data.provider_health || []).forEach((provider) => {
				const row = div( "provider-row");
				const copy = el("div");
				copy.append(
					strong( "", provider.provider),
					small( "", `${provider.success_count} successful · ${provider.failure_count} failed · ${provider.unknown_count} unknown`),
				);
				const latest = String(provider.latest_status || "unknown").toLowerCase();
				row.append(copy, span( `status ${latest}`, latest));
				providerStack.append(row);
			});
		}
		renderMetricEvidence();
		if (!providerStack.children.length) {
			providerStack.append(div( "empty-compact", inference?.configured
				? "Configured inference has no provider-chain projection."
				: "Inference is not configured and no provider receipts were observed."));
		}
		const failures = Array.isArray(inference?.recent_failures)
			? inference.recent_failures
			: [];
		const failureCount = byId("provider-failure-count");
		if (failureCount) failureCount.textContent = String(inference?.failure_count || failures.length);
		const failureStack = byId("provider-failures");
		if (failureStack) {
			failureStack.replaceChildren();
			failures.forEach((failure) => {
				const row = div( "failure-row");
				const copy = el("div");
				const title = failure.kind === "model_receipt"
					? `${failure.requested_model || "unidentified model"} · ${failure.status || "failed"}`
					: failure.kind === "preflight_failure"
						? `${failure.stage || "preflight"} · ${failure.reason_code || "failed"}`
						: `${failure.provider || "routing inference"} · ${failure.status || "degraded"}`;
				copy.append(strong( "", title));
				if (failure.kind === "model_receipt") {
					copy.append(
						small( "", `Router: ${failure.router || "none"}`),
						small( "", `Actual: ${failure.actual_provider || "unavailable"} / ${failure.actual_model || "unavailable"}`),
					);
				} else if (failure.kind === "preflight_failure") {
					const invariant = failure.invariant_code
						? `Invariant: ${failure.invariant_code}`
						: "Invariant: none recorded";
					const staffingCodes = Array.isArray(failure.staffing_reason_codes)
						? failure.staffing_reason_codes.join(", ")
						: "";
					const hiringCodes = Array.isArray(failure.hiring_reason_codes)
						? failure.hiring_reason_codes.join(", ")
						: "";
					copy.append(
						small( "", `Host: ${failure.host || "unknown"} · ${failure.exception_category || "unavailable"}`),
						small( "", invariant),
						small( "", `Trace: ${failure.trace_id || "unavailable"} · ${(failure.provider_attempts || []).length} provider attempt(s)`),
					);
					if (staffingCodes) copy.append(small( "", `Staffing: ${staffingCodes}`));
					if (hiringCodes) copy.append(small( "", `Hiring: ${hiringCodes}`));
				} else copy.append(small( "", `Trace: ${failure.trace_id || "unavailable"}`));
				row.append(copy, el("time", "", formatTime(failure.recorded_at || failure.created_at)));
				failureStack.append(row);
			});
			if (!failureStack.children.length) {
				failureStack.append(div( "empty-compact", "No persisted inference failures in the bounded window."));
			}
		}
		renderCharts();
	}

	function renderHosts() {
		const grid = byId("host-grid");
		grid.replaceChildren();
		const serviceBlocked = config.serviceRestartRequired();
		state.hosts.forEach((host) => {
			const card = el("article", "host-card");
			const heading = div( "host-row");
			const current = hostState(host);
			heading.append(strong( "", host.host), span( `host-state ${current}`, current));
			card.append(heading, small( "", hostLocation(host)));
			const tags = div( "token-list");
			tags.append(span( "token", truthLabel(host.registered, "registered", "not registered", "registration unknown")));
			tags.append(span( "token", truthLabel(host.enabled, "native enabled", "native disabled", "native enablement unknown")));
			tags.append(span( "token", truthLabel(
				host.runtime_enabled,
				"runtime on",
				"runtime off",
				"runtime state unknown",
			)));
			tags.append(span( "token", truthLabel(host.effective_enabled, "effective", "inactive", "effective state unverified")));
			tags.append(span( "token", host.maturity || "unverified"));
			card.append(tags);
			if (host.hook_trust_action) {
				card.append(paragraph( "host-action", host.hook_trust_action));
			}
			if (String(host.host || "").toLowerCase() === "codex") {
				const proof = div( "activation-proof");
				const inspection = String(host.inspection_status || "unknown").toLowerCase();
				const status = String(host.canary_attestation_status || "absent").toLowerCase();
				const attestation = host.canary_attestation && typeof host.canary_attestation === "object"
					? host.canary_attestation
					: null;
				const appendFacts = () => {
					if (!attestation) return;
					proof.append(
						small( "", `Contract · ${attestation.proof_contract || "unavailable"}`),
						small( "", `Proof fingerprint · ${attestation.proof_digest || "unavailable"}`),
						small( "", `Profile · ${attestation.profile_scope || "unavailable"}`),
						small( "", `Passed · ${formatTime(attestation.passed_at)}`),
						small( "", `Trace · ${attestation.trace_id || "unavailable"}`),
					);
				};
				if (inspection !== "complete") {
					proof.append(
						strong( "", "Activation proof unavailable"),
						small( "", `Host inspection is ${inspection}; no current activation claim is shown.`),
					);
					if (attestation) {
						proof.append(small( "activation-proof-history", "Historical proof metadata (not current)"));
						appendFacts();
					}
				} else if (status === "verified") {
					proof.append(
						strong( "", "Last successful activation proof"),
						small( "", "Current for the recorded host and install identity; model and host-native lifecycle settings are not bound."),
					);
					appendFacts();
				} else if (status === "stale") {
					const reasons = Array.isArray(host.canary_stale_reasons)
						? host.canary_stale_reasons.filter((reason) => typeof reason === "string" && reason)
						: [];
					proof.append(
						strong( "", "Historical activation proof"),
						small( "", `Not current${reasons.length ? ` · ${reasons.join(", ")}` : ""}.`),
					);
					appendFacts();
				} else {
					proof.append(
						strong( "", "Activation proof"),
						small( "", "No current-profile Codex activation proof is attested."),
					);
				}
				card.append(proof);
			}
			if (host.executable_discovered === true) {
				const actions = div("card-actions");
				const inspectionCurrent = !host.inspection_status || host.inspection_status === "complete";
				const generationKnown = Number.isInteger(host.runtime_control_generation)
					&& host.runtime_control_generation >= 0;
				const directionKnown = !serviceBlocked
					&& inspectionCurrent
					&& typeof host.runtime_enabled === "boolean"
					&& generationKnown;
				const enabled = host.runtime_enabled === true;
				const label = directionKnown
					? (enabled ? "Disable" : "Enable")
					: serviceBlocked
						? "Restart required"
						: (!inspectionCurrent ? "Inspection stale" : "State unknown");
				const button = el("button", `button compact ${enabled ? "danger" : "solid"}`, label);
				button.type = "button";
				button.disabled = !directionKnown;
				button.setAttribute(
					"aria-label",
					directionKnown
						? `${label} ${host.host} runtime`
						: `${host.host} runtime action unavailable: ${label}`,
				);
				if (directionKnown) {
					button.addEventListener("click", () => runButtonAction(
						button,
						() => callbacks.toggleHost(
							host.host,
							!enabled,
							host.runtime_control_generation,
						),
					));
				} else {
					button.title = serviceBlocked
						? "Restart the dashboard service to use host controls."
						: "A current host inspection is required before this action is available.";
				}
				actions.append(button);
				card.append(actions);
			}
			grid.append(card);
		});
		if (!grid.children.length) {
			grid.append(el(
				"div",
				"empty-compact empty-grid",
				"No supported agent hosts were found. Install or register a host, then refresh.",
			));
		}
		const uninstall = el("article", "host-card empty-grid");
		uninstall.append(
			strong("", "Attended uninstall"),
			small(
				"",
				"Preview every host with Agency integration evidence in a terminal. The preview changes nothing and returns the exact digest required to apply it.",
			),
		);
		const command = el("code", "", "agency uninstall --all --dry-run");
		command.id = "uninstall-preview-command";
		const actions = div("card-actions");
		const copy = el("button", "button ghost", "Copy uninstall preview");
		copy.id = "uninstall-copy-button";
		copy.type = "button";
		copy.dataset.command = command.textContent;
		actions.append(copy);
		uninstall.append(command, actions);
		grid.append(uninstall);
	}

	function renderRouteHosts() {
		const select = byId("route-host");
		if (!select) return "";
		const previous = String(select.value || "");
		const byHost = new Map();
		const duplicates = new Set();
		const inventoryBounded = Array.isArray(state.hosts)
			&& state.hosts.length <= ROUTE_LAB_HOST_INVENTORY_LIMIT;
		if (inventoryBounded) {
			state.hosts.forEach((host) => {
				const name = typeof host?.host === "string" ? host.host.trim().toLowerCase() : "";
				if (!EXECUTION_HOSTS.includes(name)) return;
				if (byHost.has(name)) {
					duplicates.add(name);
					byHost.delete(name);
					return;
				}
				if (duplicates.has(name)) return;
				byHost.set(name, host);
			});
			for (const [name, host] of byHost) {
				const receipt = host?.execution_capabilities;
				if (
					host.effective_enabled !== true
					|| !routeLabReceiptIsValid(receipt, name)
				) byHost.delete(name);
			}
		}
		const available = EXECUTION_HOSTS.filter((host) => byHost.has(host));
		select.replaceChildren();
		if (!available.length) {
			const option = el("option", "", "No verified, enabled execution host");
			option.value = "";
			select.append(option);
			select.value = "";
		} else {
			available.forEach((host) => {
				const option = el("option");
				option.value = host;
				const capabilityCount = byHost.get(host).execution_capabilities.capabilities.length;
				option.textContent = `${host} · ${capabilityCount} verified capabilities`;
				select.append(option);
			});
			select.value = available.includes(previous) ? previous : available[0];
		}
		const serviceBlocked = config.serviceRestartRequired();
		const masterEnabled = state.master?.enabled === true;
		select.disabled = serviceBlocked || !masterEnabled || !available.length;
		const help = byId("route-host-help");
		if (help) {
			help.textContent = !inventoryBounded
				? "Host inventory exceeded the safe Route Lab bound. Refresh host discovery before retrying."
				: duplicates.size
					? "Ambiguous duplicate host evidence was excluded. Refresh host discovery before retrying."
					: !available.length
				? "No current native installation receipt can authorize Route Lab. Install and enable a supported host, then refresh."
				: available.length === 1
					? `Using the current ${available[0]} installation and capability receipt.`
					: "Choose the current native host whose verified capabilities should constrain this explanation.";
		}
		const routeButton = byId("route-button");
		if (routeButton && routeButton.getAttribute("aria-busy") !== "true") {
			routeButton.disabled = serviceBlocked || !masterEnabled || !select.value;
			routeButton.setAttribute("aria-disabled", String(routeButton.disabled));
			routeButton.title = serviceBlocked
				? "Restart the dashboard service to use Route Lab."
				: !masterEnabled
					? "Enable Agency Runtime to use Route Lab"
					: !select.value
						? "A verified and enabled execution host is required"
						: `Run a routing explanation for ${select.value}`;
		}
		return select.value;
	}

	function populateRosterFacet(id, values, emptyLabel) {
		const select = byId(id);
		if (!select) return;
		const previous = select.value;
		const empty = el("option", "", emptyLabel);
		empty.value = "";
		select.replaceChildren(empty);
		(Array.isArray(values) ? values : []).forEach((value) => {
			const option = el("option", "", value);
			option.value = value;
			select.append(option);
		});
		select.value = [...select.options].some((option) => option.value === previous) ? previous : "";
	}

	function appendOperationalAgentDetails(card, agent) {
		if (!agent.audit_status && !agent.source_revision && !agent.authority) return;
		const identity = div( "agent-contract-line");
		identity.append(
			span( `status ${agent.audit_status === "approved" ? "configured" : "failed"}`, agent.audit_status || "audit unknown"),
			span( "contract-authority", agent.authority || "authority unassigned"),
		);
		card.append(identity);
		const details = el("details", "agent-governance-detail");
		details.dataset.preserveKey = `agent:${agent.agent_slug}:governance`;
		details.append(el("summary", "", "Contract, compatibility & history"));
		details.append(definitionList("agent-metadata", [
			["Source revision", agent.source_revision || "unavailable"],
			["Source content hash", agent.source_content_hash || agent.content_hash || "unavailable"],
			["Audit revision", agent.audit_revision || "unavailable"],
			["Context mode", agent.context_mode || "unassigned"],
		]));
		appendTokenGroups(details, [
			["Hosts", agent.supported_hosts],
			["Platforms", agent.supported_platforms],
			["Required tools", agent.required_tools],
			["Conflicts", agent.conflicts_with],
			["Requires", agent.requires],
		], "contract-token-row", "strong", "none declared");
		const history = el("ol", "revision-history");
		(agent.revision_history || []).forEach((revision) => {
			const row = el("li");
			row.append(
				strong( "", revision.version || "version unavailable"),
				span( "", `${revision.audit_status || "audit unknown"} · ${formatTime(revision.created_at)}`),
			);
			history.append(row);
		});
		if (!history.children.length) history.append(el("li", "", "No immutable revision history is available."));
		details.append(el("h4", "", "Immutable revision history"), history);
		card.append(details);
	}

	function renderReviewQueue() {
		const review = state.rosterReview || {};
		const candidates = Array.isArray(review.candidates) ? review.candidates : [];
		const remediationAttempts = Array.isArray(review.remediation_attempts)
			? review.remediation_attempts
			: [];
		const rawRemediationHistory = Array.isArray(review.remediation_history)
			? review.remediation_history
			: [];
		const pendingQueueEventIds = new Set(
			remediationAttempts
				.map((entry) => entry?.event_id)
				.filter((eventId) => typeof eventId === "string" && eventId),
		);
		const remediationHistory = rawRemediationHistory.filter((entry) => (
			typeof entry?.queue_event_id !== "string"
			|| !entry.queue_event_id
			|| !pendingQueueEventIds.has(entry.queue_event_id)
		));
		const remediationOverlapCount = rawRemediationHistory.length - remediationHistory.length;
		const count = byId("review-count");
		if (count) {
			count.textContent = String(
				review.queue_count ?? candidates.length + remediationAttempts.length,
			);
		}
		const upstream = review.upstream || {};
		const upstreamStatus = byId("upstream-status");
		if (upstreamStatus) {
			upstreamStatus.textContent = upstream.packaged_source_revision
				? `Packaged source ${upstream.packaged_source_revision} · remote freshness ${upstream.remote_freshness || "unverified"} · ${upstream.state || "status unknown"}.`
				: "Packaged roster audit status is unavailable.";
		}
		const list = byId("review-list");
		if (!list) return;
		list.replaceChildren();
		candidates.forEach((entry) => {
			const candidate = entry.candidate || {};
			const audit = entry.latest_audit || {};
			const details = el("details", "review-card");
			details.dataset.preserveKey = `candidate:${candidate.id || candidate.slug || "unknown"}`;
			const summary = el("summary");
			const copy = el("span");
			copy.append(
				strong( "", candidate.name || candidate.slug || "Unknown candidate"),
				small( "", `${candidate.slug || "unknown"} · ${entry.change || "uncompared"}`),
			);
			summary.append(copy, span( `status ${audit.verdict === "passed" ? "configured" : "failed"}`, audit.verdict || "not audited"));
			details.append(summary);
			details.append(definitionList("agent-metadata", [
				["Candidate revision", candidate.source_revision || "unavailable"],
				["Candidate hash", candidate.content_hash || "unavailable"],
				["Active revision", entry.active?.source_revision || "none"],
				["Active hash", entry.active?.content_hash || "none"],
				["Inference audit", audit.inference_status || "unknown"],
			]));
			const changed = div( "contract-token-row");
			changed.append(
				strong( "", "Changed fields"),
				tokenList(entry.changed_fields, "none"),
			);
			details.append(changed);
			const findings = el("ul", "finding-list");
			(audit.findings || []).forEach((finding) => {
				findings.append(el("li", `finding-${finding.severity || "unknown"}`, `${finding.severity || "unknown"} · ${finding.code || "finding"}`));
			});
			if (!findings.children.length) findings.append(el("li", "", "No audit findings recorded."));
			details.append(el("h4", "", "Redacted audit findings"), findings);
			list.append(details);
		});
		remediationAttempts.forEach((entry) => {
			const receipt = entry.receipt || {};
			const slug = entry.slug || "unknown";
			const details = el("details", "review-card remediation-card");
			details.dataset.preserveKey = `remediation:${entry.event_id || slug}`;
			details.setAttribute("aria-label", `Remediation attempt for ${slug}`);
			const summary = el("summary");
			const copy = el("span");
			copy.append(
				strong( "", slug),
				small( "", "remediation attempt · non-executable"),
			);
			summary.append(
				copy,
				span( "status", receipt.status || "status unknown"),
			);
			details.append(summary);
			details.append(definitionList("agent-metadata", [
				["Original hash", receipt.original_hash || "unavailable"],
				["Proposal hash", receipt.proposal_hash || "none generated"],
				[
					"Attempted rules",
					Array.isArray(receipt.attempted_rule_ids) && receipt.attempted_rule_ids.length
						? receipt.attempted_rule_ids.join(", ")
						: "none",
				],
				["Matched rule", receipt.matched_rule_id || "none"],
				["Status", receipt.status || "unknown"],
				["Next action", receipt.next_action || "manual review required"],
				["Created at", entry.created_at || "unavailable"],
			]));
			const guard = el(
				"p",
				"remediation-guard",
				"Review evidence only · this attempt cannot activate an agent.",
			);
			guard.setAttribute("role", "note");
			details.append(guard);
			list.append(details);
		});
		remediationHistory.forEach((entry) => {
			const slug = entry.slug || "unknown";
			const details = el("details", "review-card remediation-card remediation-history-card");
			details.dataset.preserveKey = `remediation-history:${entry.event_id || slug}`;
			details.setAttribute("aria-label", `Resolved remediation for ${slug}`);
			const summary = el("summary");
			const copy = el("span");
			copy.append(
				strong( "", slug),
				small( "", "repair provenance · immutable history"),
			);
			summary.append(
				copy,
				span( "status configured", entry.resolution || "resolved"),
			);
			details.append(summary);
			details.append(definitionList("agent-metadata", [
				["Original hash", entry.original_hash || "unavailable"],
				["Candidate hash", entry.candidate_hash || "unavailable"],
				["Source hash", entry.source_hash || "unavailable"],
				["Candidate", entry.candidate_id || "unavailable"],
				[
					"Audit policy",
					entry.audit_policy_current === false ? "historical policy" : "current policy",
				],
				["Resolved at", entry.created_at || "unavailable"],
			]));
			list.append(details);
		});
		if (!list.children.length) {
			list.append(
				el(
					"div",
					"empty-state",
					"No candidates, remediation attempts, or repair history are available.",
				),
			);
		}
		const pendingCount = Number.isInteger(review.remediation_count)
			? review.remediation_count
			: remediationAttempts.length;
		const historyCount = Number.isInteger(review.remediation_history_count)
			? review.remediation_history_count
			: remediationHistory.length;
		const unvalidatedResolutionCount = Number.isInteger(
			review.remediation_unvalidated_resolution_count,
		)
			? review.remediation_unvalidated_resolution_count
			: 0;
		const staleResolutionCount = Number.isInteger(
			review.remediation_stale_resolution_count,
		)
			? review.remediation_stale_resolution_count
			: 0;
		const pageStatus = byId("review-page-status");
		if (pageStatus) {
			const overlapStatus = remediationOverlapCount > 0
				? ` ${remediationOverlapCount} conflicting history ${remediationOverlapCount === 1 ? "row was" : "rows were"} suppressed.`
				: "";
			const staleStatus = staleResolutionCount > 0
				? ` ${staleResolutionCount} stale signed resolution ${staleResolutionCount === 1 ? "was" : "were"} reopened for review.`
				: "";
			const invalidStatus = unvalidatedResolutionCount > 0
				? ` ${unvalidatedResolutionCount} unvalidated resolution ${unvalidatedResolutionCount === 1 ? "record remains" : "records remain"} quarantined.`
				: "";
			const anomalyStatus = `${overlapStatus}${staleStatus}${invalidStatus}`;
			pageStatus.textContent = `Showing ${remediationAttempts.length} of ${pendingCount} pending repairs and ${remediationHistory.length} of ${historyCount} resolved repairs.${anomalyStatus}`;
			pageStatus.classList.toggle(
				"failed",
				unvalidatedResolutionCount + staleResolutionCount + remediationOverlapCount > 0,
			);
			pageStatus.dataset.remediationOverlapCount = String(remediationOverlapCount);
			pageStatus.dataset.unvalidatedResolutionCount = String(unvalidatedResolutionCount);
			pageStatus.dataset.staleResolutionCount = String(staleResolutionCount);
		}
		[
			["pending", review.remediation_pending_has_more, review.next_remediation_pending_cursor],
			["history", review.remediation_history_has_more, review.next_remediation_history_cursor],
		].forEach(([kind, hasMore, cursor]) => {
			const button = byId(`review-${kind}-more`);
			if (!button) return;
			button.hidden = hasMore !== true;
			button.disabled = hasMore === true && !cursor;
		});
	}

	function renderRoster() {
		const grid = byId("roster-grid");
		grid.replaceChildren();
		const operations = !state.rosterFilter && state.rosterOperations?.agents
			? state.rosterOperations
			: null;
		const roster = operations ? operations.agents : state.roster;
		const page = operations || state.rosterPage;
		const pageCount = Number.isInteger(page?.page_count)
			? page.page_count
			: Number.isInteger(page?.count)
			? page.count
			: roster.length;
		const totalCount = Number.isInteger(page?.total_count)
			? page.total_count
			: pageCount;
		const filteredCount = Number.isInteger(page?.filtered_count)
			? page.filtered_count
			: Number.isInteger(page?.matched_count)
			? page.matched_count
			: totalCount;
		const truncated = page?.truncated === true;
		const filter = state.rosterFilter;
		const serviceBlocked = config.serviceRestartRequired();
		const enabledCount = Number.isInteger(page?.enabled_count)
			? page.enabled_count
			: totalCount;
		byId("roster-count").textContent = `${enabledCount} enabled · ${totalCount} total`;
		byId("roster-search-clear").hidden = !filter;
		const pageStatus = byId("roster-page-status");
		if (pageStatus) {
			pageStatus.hidden = !filter && !truncated;
			if (filter) {
				pageStatus.textContent = pageCount
					? `Showing the exact governed specialist match for ${filter}.`
					: `No governed specialist matches ${filter}.`;
			} else if (truncated) {
				const remaining = Math.max(0, totalCount - pageCount);
				pageStatus.textContent = `Showing ${pageCount} of ${totalCount} governed specialists; ${remaining} are not shown. Find any specialist by its exact agent slug.`;
			} else if (operations && Object.keys(state.rosterFilters || {}).length) {
				pageStatus.hidden = false;
				pageStatus.textContent = `Showing ${pageCount} of ${filteredCount} specialists matching the active operational filters · ${totalCount} global specialists.`;
			} else pageStatus.textContent = "";
		}
		const facets = operations?.facets || state.rosterOperations?.facets || {};
		populateRosterFacet("roster-filter-division", facets.divisions, "All divisions");
		populateRosterFacet("roster-filter-capability", facets.capabilities, "All capabilities");
		populateRosterFacet("roster-filter-authority", facets.authorities, "All authorities");
		populateRosterFacet("roster-filter-host", facets.hosts, "All hosts");
		populateRosterFacet("roster-filter-platform", facets.platforms, "All platforms");
		populateRosterFacet("roster-filter-tool", facets.tools, "All tools");
		roster.forEach((agent) => {
			const enabled = agent.enabled !== false;
			const protectedAgent = agent.protected === true;
			const card = el("article", `agent-card${enabled ? "" : " disabled"}`);
			card.append(
				strong( "", agent.name || agent.agent_slug),
				small( "", `${agent.agent_slug} · ${agent.division || "unassigned"}`),
			);
			const tags = div( "token-list");
			(agent.capabilities || []).slice(0, 4).forEach((value) => {
				tags.append(span( "token", value));
			});
			if (!tags.children.length) tags.append(span( "token", "no capability tags"));
			card.append(tags);
			appendOperationalAgentDetails(card, agent);
			const controls = div("card-actions");
			const status = protectedAgent ? "protected" : enabled ? "enabled" : "disabled";
			controls.append(span(`host-state ${enabled ? "verified" : "runtime-disabled"}`, status));
			const button = el(
				"button",
				`button compact ${enabled ? "ghost" : "solid"}`,
				protectedAgent ? "always enabled" : enabled ? "disable" : "enable",
			);
			button.type = "button";
			button.disabled = protectedAgent || serviceBlocked;
			const identity = agent.name && agent.name !== agent.agent_slug
				? `${agent.name} (${agent.agent_slug})`
				: agent.agent_slug;
			button.setAttribute(
				"aria-label",
				protectedAgent
					? `${identity} is protected and always enabled`
					: `${enabled ? "Disable" : "Enable"} ${identity} specialist`,
			);
			if (serviceBlocked) {
				button.title = "Restart the dashboard service to use roster controls.";
			} else if (protectedAgent) {
				button.title = "The default coordinators are always enabled.";
			} else {
				button.addEventListener("click", () => runButtonAction(
					button,
					() => callbacks.toggleAgent(agent.agent_slug, !enabled),
				));
			}
			controls.append(button);
			card.append(controls);
			grid.append(card);
		});
		const list = byId("snapshot-list");
		list.replaceChildren();
		state.snapshots.forEach((snapshot) => {
			const row = div( "stack-item");
			const copy = el("div");
			copy.append(
				strong( "", snapshot.snapshot_id),
				small( "", `${snapshot.agent_count || 0} agents · ${formatTime(snapshot.created_at)}`),
			);
			const status = snapshot.activated ? "activated" : snapshot.approved ? "approved" : "pending";
			const controls = div( "card-actions");
			controls.append(span( `host-state ${snapshot.activated ? "verified" : ""}`, status));
			if (!snapshot.activated) {
				const action = snapshot.approved ? "activate" : "approve";
				const button = el("button", "button compact ghost", action);
				button.type = "button";
				button.disabled = serviceBlocked;
				button.setAttribute(
					"aria-label",
					`${action[0].toUpperCase()}${action.slice(1)} roster snapshot ${snapshot.snapshot_id}`,
				);
				if (serviceBlocked) {
					button.title = "Restart the dashboard service to use roster controls.";
				} else {
					button.addEventListener("click", () => runButtonAction(
						button,
						() => callbacks.rosterAction(action, snapshot.snapshot_id),
					));
				}
				controls.append(button);
			}
			row.append(copy, controls);
			list.append(row);
		});
		if (!list.children.length) list.append(div( "empty-state", "No roster snapshots."));
		renderReviewQueue();
	}

	function renderVisionSourceState(name, data) {
		const metadata = state.visionEvidence?.sources?.[name] || {};
		const unavailable = metadata.unavailable || (metadata.stale && !data);
		const tagId = name === "rejections" ? "vision-rule8-state" : `vision-${name}-state`;
		const tag = byId(tagId);
		if (tag) {
			tag.textContent = unavailable ? "UNAVAILABLE"
				: metadata.stale ? "STALE" : data ? "OBSERVED" : "NOT LOADED";
			tag.dataset.state = unavailable
				? "unavailable" : metadata.stale ? "stale" : data ? "observed" : "unknown";
		}
		const freshnessId = name === "rejections"
			? "vision-rule8-freshness"
			: `vision-${name}-freshness`;
		const freshness = byId(freshnessId);
		if (freshness) {
			if (unavailable) {
				freshness.textContent = `No validated source sample is available. Refresh failed: ${metadata.error || "source unavailable"}`;
			} else if (metadata.stale && data) {
				freshness.textContent = `Last-good source sample ${formatTime(metadata.sampledAt)}. Refresh failed: ${metadata.error || "source unavailable"}`;
			} else if (metadata.sampledAt) {
				freshness.textContent = `Source sampled ${formatTime(metadata.sampledAt)}.`;
			} else {
				freshness.textContent = "This proof source has not been loaded; the live-sync timestamp does not apply.";
			}
		}
	}

	function renderChildDeliveryEvidence() {
		const data = state.visionEvidence?.children;
		renderVisionSourceState("children", data);
		const source = byId("vision-children-source");
		const bounds = byId("vision-children-bounds");
		const summary = byId("vision-children-summary");
		const list = byId("vision-children-list");
		if (!source || !bounds || !summary || !list) return;
		list.replaceChildren();
		source.textContent = data
			? "Source: hash-verified specialist cards in host-written Claude and Codex child artifacts. Agency Store staffing rows are not consulted."
			: "Source: host-written Claude and Codex child artifacts; Agency Store staffing rows are not a substitute.";
		if (!data) {
			bounds.textContent = "Bounded artifact scan details will appear after this source loads.";
			summary.textContent = "No validated child-delivery proof sample is available.";
			const empty = div("empty-compact", "Child-delivery proof has not loaded.");
			empty.setAttribute("role", "listitem");
			list.append(empty);
			return;
		}
		const totals = data.hosts.reduce((result, host) => ({
			candidates: result.candidates + host.artifact_candidates,
			scanned: result.scanned + host.artifacts_scanned,
			evidence: result.evidence + host.evidence_count,
			staffed: result.staffed + host.staffed_children,
			correlated: result.correlated + host.correlated_staffed_children,
			uncorrelated: result.uncorrelated + host.uncorrelated_staffed_children,
			legacy: result.legacy + host.legacy_deliveries,
			visits: result.visits + host.filesystem_entries_visited,
			incomplete: result.incomplete || !host.artifact_candidate_count_complete,
		}), { candidates: 0, scanned: 0, evidence: 0, staffed: 0, correlated: 0, uncorrelated: 0, legacy: 0, visits: 0, incomplete: false });
		bounds.textContent = `Bounds: at most ${data.bounds.filesystem_visit_limit_per_host} host-tree entries and ${data.bounds.artifact_scan_limit_per_host} artifact bodies per host; ${formatBytes(data.bounds.artifact_prefix_bytes)} prefix and ${data.bounds.artifact_record_limit} records per artifact; ${data.bounds.detail_limit} detail rows per host. Visited ${totals.visits} entries and scanned ${totals.scanned} of ${totals.candidates}${totals.incomplete ? "+" : ""} observed candidates in this sample${totals.incomplete ? "; candidate counts are lower bounds where traversal stopped" : ""}.`;
		summary.textContent = `${totals.staffed} children contain verified specialist cards (${totals.correlated} parent-correlated, ${totals.uncorrelated} uncorrelated); ${totals.legacy} legacy delivery markers contain no specialist card proof.`;
		data.hosts.forEach((host) => {
			const row = el("article", "vision-proof-row");
			row.setAttribute("role", "listitem");
			row.append(
				strong("", host.host),
				small("", `${host.artifacts_scanned} of ${host.artifact_candidates}${host.artifact_candidate_count_complete ? "" : "+"} observed candidates scanned · ${host.filesystem_entries_visited} host-tree entries visited${host.artifact_scan_truncated ? " · traversal or body bound reached" : ""}`),
				small("", `${host.staffed_children} verified staffed children · ${host.evidence_count} delivery findings${host.detail_truncated ? " · details truncated" : ""}`),
				small("vision-proof-path", `Artifact root (${host.root_present ? "present" : "not observed"}): ${host.root}`),
			);
			host.children.forEach((child) => {
				const detail = div("vision-proof-detail");
				const cardSummary = child.cards.length
					? child.cards.map((card) => `${card.slug}@${card.version}`).join(", ")
					: "legacy delivery marker; no verified specialist cards";
				detail.append(
					strong("", child.child_id),
					small("", `${child.correlated ? "parent-correlated" : "not parent-correlated"} · ${cardSummary}`),
					small("vision-proof-path", child.artifact),
				);
				row.append(detail);
			});
			list.append(row);
		});
		if (totals.staffed === 0) {
			const empty = div(
				"empty-compact vision-proof-caveat",
				"No verified specialist-card delivery evidence was found in the bounded artifact scan. This does not mean no children were started.",
			);
			empty.setAttribute("role", "listitem");
			list.append(empty);
		}
	}

	function rule8RunRow(row, label) {
		const item = el("article", "vision-proof-row");
		item.setAttribute("role", "listitem");
		item.append(
			strong("", `${label} · ${row.status}`),
			small("", `Host ${row.host || "unknown"} · ended ${formatTime(row.ended_at || row.started_at)}`),
			small("", `Trace ${row.trace_id || "unavailable"} · session ${row.session_id || "unavailable"}`),
		);
		return item;
	}

	function renderRule8Evidence() {
		const data = state.visionEvidence?.rejections;
		renderVisionSourceState("rejections", data);
		const source = byId("vision-rule8-source");
		const bounds = byId("vision-rule8-bounds");
		const summary = byId("vision-rule8-summary");
		const list = byId("vision-rule8-list");
		if (!source || !bounds || !summary || !list) return;
		list.replaceChildren();
		source.textContent = "Source: Agency Store runs.status. These rows distinguish Agency-withheld responses from Agency-blind failures; they are not host execution or publication proof.";
		if (!data) {
			bounds.textContent = "The bounded exceptional-run window will appear after this source loads.";
			summary.textContent = "No validated Rule-8 evidence sample is available.";
			const empty = div("empty-compact", "Rule-8 evidence has not loaded.");
			empty.setAttribute("role", "listitem");
			list.append(empty);
			return;
		}
		bounds.textContent = `Bounds: newest ${data.window.limit} matching exceptional runs${data.window.host ? ` for ${data.window.host}` : " across all hosts"}; ${data.window.returned} returned.`;
		summary.textContent = `${data.counts.withheld} withheld by Agency · ${data.counts.agency_blind} Agency-blind failures · ${data.counts.matching_exceptional_runs} total matching statuses.`;
		data.withheld.forEach((row) => list.append(rule8RunRow(row, "Withheld by Agency")));
		data.agency_blind.forEach((row) => list.append(
			rule8RunRow(row, "Agency blind; publication not inferred"),
		));
		if (data.counts.matching_exceptional_runs === 0) {
			const empty = div(
				"empty-compact vision-proof-caveat",
				"No matching exceptional statuses were found in the bounded window. This is not a health claim.",
			);
			empty.setAttribute("role", "listitem");
			list.append(empty);
		}
	}

	function wiringOutcome(host) {
		if (host.status === "wired") {
			return ["WIRED", "Trusted staged and wired projection hashes match."];
		}
		if (host.status === "drift") {
			return ["DRIFT", `Measured staged and wired projections differ (${host.reason_code}).`];
		}
		if (host.status === "not_measured") {
			return ["UNKNOWN", "This host's wiring location is not measured; its wiring state remains unknown."];
		}
		return ["UNKNOWN", `The bounded trusted-file measurement could not establish both projections (${host.reason_code}); wiring state remains unknown.`];
	}

	function projectionDigest(value) {
		return value ? `${value.slice(0, 12)}…` : "projection unknown";
	}

	function renderWiringEvidence() {
		const data = state.visionEvidence?.wiring;
		renderVisionSourceState("wiring", data);
		const source = byId("vision-wiring-source");
		const bounds = byId("vision-wiring-bounds");
		const summary = byId("vision-wiring-summary");
		const list = byId("vision-wiring-list");
		if (!source || !bounds || !summary || !list) return;
		list.replaceChildren();
		source.textContent = data
			? `Source: trusted staged and host-cache wiring files. Measured hosts: ${data.source.measured_hosts.join(", ") || "none"}. This is not a live canary.`
			: "Source: trusted staged and host-cache wiring files; this is not a live canary.";
		if (!data) {
			bounds.textContent = "Trusted-file read bounds will appear after this source loads.";
			summary.textContent = "No validated host-wiring proof sample is available.";
			const empty = div("empty-compact", "Host-wiring proof has not loaded.");
			empty.setAttribute("role", "listitem");
			list.append(empty);
			return;
		}
		const measured = data.hosts.filter((host) => host.measurement_status === "measured").length;
		const wired = data.hosts.filter((host) => host.status === "wired").length;
		const drift = data.hosts.filter((host) => host.status === "drift").length;
		bounds.textContent = `Bounds: current wiring files for ${data.window.hosts.length} hosts; at most ${formatBytes(data.bounds.file_prefix_bytes)} read per trusted file.`;
		summary.textContent = `${measured} measured · ${wired} wired · ${drift} drift · ${data.hosts.length - wired - drift} unknown or not measured.`;
		data.hosts.forEach((host) => {
			const [label, explanation] = wiringOutcome(host);
			const row = el("article", "vision-proof-row");
			row.setAttribute("role", "listitem");
			const heading = div("vision-proof-heading");
			heading.append(strong("", host.host), span(`status wiring-${host.status}`, label));
			row.append(
				heading,
				small("", explanation),
				small("vision-proof-path", `Staged: ${host.staged_state} · ${projectionDigest(host.staged_projection)} · ${host.staged_path || "path unavailable"}`),
				small("vision-proof-path", `Wired: ${host.wired_state} · ${projectionDigest(host.wired_projection)} · ${host.wired_path || "path unavailable"}`),
			);
			list.append(row);
		});
	}

	function renderVisionEvidence() {
		renderChildDeliveryEvidence();
		renderRule8Evidence();
		renderWiringEvidence();
		const status = byId("vision-evidence-status");
		if (status) {
			const sourceState = (name) => {
				const metadata = state.visionEvidence?.sources?.[name] || {};
				if (metadata.stale && state.visionEvidence?.[name]) return "stale";
				if (metadata.unavailable || (state.visionEvidence?.loaded && !state.visionEvidence?.[name])) {
					return "unavailable";
				}
				if (state.visionEvidence?.[name]) return "current";
				return "not loaded";
			};
			const message = `Vision evidence: child delivery ${sourceState("children")}; Rule 8 ${sourceState("rejections")}; host wiring ${sourceState("wiring")}.`;
			if (status.textContent !== message) status.textContent = message;
		}
	}

	function renderEvidence(kind = "specialists") {
		renderVisionEvidence();
		const columns = EVIDENCE_COLUMNS[kind];
		const label = kind.endsWith("s") ? kind.slice(0, -1) : kind;
		const head = byId("evidence-head");
		const body = byId("evidence-body");
		head.replaceChildren();
		body.replaceChildren();
		const caption = byId("evidence-caption");
		if (caption) {
			caption.textContent = kind === "specialists"
				? "Specialist activation evidence by current-turn and historical state"
				: kind === "delegations"
					? "Recorded delegation-event row evidence"
				: `${label[0].toUpperCase()}${label.slice(1)} runtime evidence`;
		}
		const context = byId("evidence-context");
		const rows = state.activity[kind] || [];
		const collection = state.activityCollections?.[kind] || {};
		const filteredCount = Number.isInteger(collection.filtered_count)
			? collection.filtered_count
			: rows.length;
		const totalCount = Number.isInteger(collection.total_count)
			? collection.total_count
			: filteredCount;
		const pageSummary = `Showing ${rows.length} of ${filteredCount} filtered · ${totalCount} total`;
		let contextMessage;
		if (kind === "specialists") {
			const current = rows.filter((row) => row.state === "current").length;
			const historical = rows.length - current;
			contextMessage = `${pageSummary}. ${current} current-turn activation${current === 1 ? "" : "s"} · ${historical} historical activation${historical === 1 ? "" : "s"}. Current-turn rows are unexpired and trace-correlated; historical rows remain as immutable audit evidence. Agency Store activation rows are not independent proof that a specialist card reached a child or that child execution completed.`;
		} else if (kind === "delegations") {
			contextMessage = `${pageSummary}. These are bounded delegation-event row projections. Observed-child identity comes only from recorded execution correlation; a staffing recommendation is never presented as the executor. Rows do not independently prove specialist-card delivery or child completion.`;
		} else {
			contextMessage = `${pageSummary}. Bounded metadata-only runtime evidence; payload content and worker output are not included.`;
		}
		if (context && context.textContent !== contextMessage) context.textContent = contextMessage;
		const trh = el("tr");
		columns.forEach(([, columnLabel]) => {
			const heading = el("th", "", columnLabel);
			heading.setAttribute("scope", "col");
			trh.append(heading);
		});
		head.append(trh);
		const previousKeys = state.evidenceKeys.get(kind) || new Set();
		const nextKeys = new Set();
		rows.forEach((row, index) => {
			const tr = el("tr");
			const key = evidenceRowKey(row, index);
			nextKeys.add(key);
			if (previousKeys.size && !previousKeys.has(key)) tr.classList.add("is-new");
			columns.forEach(([columnKey]) => {
				let value = columnKey === "observed_child"
					? observedChildIdentity(row)
					: row[columnKey];
				if (Array.isArray(value)) value = value.join(", ") || "—";
				if (columnKey.endsWith("_at") || columnKey === "created_at") value = formatTime(value);
				if (columnKey === "fallback_applied") value = value === true ? "Yes" : "No";
				const td = el("td");
				if (columnKey === "state") {
					const stateLabel = value === "current" ? "Current turn" : "Historical";
					td.append(span( `status activation-${value || "historical"}`, stateLabel));
				} else if (columnKey === "status" || columnKey === "action") {
					td.append(span( `status ${value || ""}`, value || "—"));
				} else td.textContent = value || "—";
				tr.append(td);
			});
			body.append(tr);
		});
		state.evidenceKeys.set(kind, nextKeys);
		if (!body.children.length) {
			const emptyLabel = kind === "specialists"
				? "specialist activation"
				: kind === "delegations"
					? "delegation-event row"
					: label;
			body.append(emptyRow(columns.length, `No ${emptyLabel} evidence yet.`));
		}
	}

	function renderReceipt(receipt) {
		const root = byId("route-result");
		root.className = "receipt";
		root.replaceChildren();
		const selected = (receipt.selected || [])
			.map((item) => item.slug || item.agent_slug || item.id)
			.filter(Boolean);
		const eligibility = receipt.eligibility || {};
		const hostCapability = receipt.host_capability_receipt || {};
		const routing = receipt.routing || {};
		const requestId = safeRequestId(receipt.request_id);
		const providerAttempts = Array.isArray(routing.provider_attempts)
			? routing.provider_attempts
				.slice(0, 8)
				.filter(isRecord)
			: [];
		const eligibilitySummary = Number.isInteger(eligibility.rejection_count)
			? `${eligibility.eligible_count || 0} eligible · ${eligibility.rejection_count} rejected${eligibility.truncated ? " · bounded view" : ""}`
			: "not reported";
		const blocks = [
			["Status", receipt.status || receipt.signals?.selection?.status || "unknown"],
			["Host context", eligibility.execution_host || hostCapability.execution_host || "unproven"],
			["Host capability evidence", hostCapability.status
				? `${hostCapability.status} · ${(hostCapability.capabilities || []).length} capabilities`
				: "unproven"],
			["Eligibility", eligibilitySummary],
			["Selected specialists", selected.length ? selected : ["abstained"]],
			["Policy actions", receipt.signals?.policy?.matched_actions || []],
			["Decision source", receipt.signals?.selection?.provider || receipt.provider || "deterministic"],
			["Inference mode", routing.inference_mode || "not reported"],
			["Provider calls", providerAttempts.length],
			...(requestId ? [["Request ID", requestId]] : []),
		];
		blocks.forEach(([label, value]) => {
			const block = div( "receipt-block");
			block.append(span( "", label));
			if (Array.isArray(value)) {
				const list = div( "token-list");
				(value.length ? value : ["none"]).forEach((item) => {
					list.append(span( "token", typeof item === "string" ? item : JSON.stringify(item)));
				});
				block.append(list);
			} else block.append(paragraph( "", value));
			root.append(block);
		});
		const modelBlock = div( "receipt-block model-receipts");
		modelBlock.append(span( "", "Inference and model receipts"));
		if (!providerAttempts.length) {
			modelBlock.append(paragraph( "", "No model call was recorded for this route."));
		} else {
			const modelList = div( "model-receipt-list");
			modelList.setAttribute("role", "list");
			modelList.setAttribute("aria-label", "Inference provider and model receipts");
			providerAttempts.forEach((attempt, index) => {
				const status = String(attempt.status || "unknown").toLowerCase();
				const card = el("article", "model-receipt-card");
				card.setAttribute("role", "listitem");
				const heading = div( "model-receipt-heading");
				heading.append(
					strong( "", String(attempt.stage || "provider") + " call " + (index + 1)),
					span( "model-receipt-status status-" + status, status.replaceAll("_", " ")),
				);
				card.append(heading);
				card.append(definitionList("model-receipt-facts", [
					[
						"Configured provider",
						[attempt.provider_name, attempt.provider_type].filter(Boolean).join(" · ")
							|| "unavailable",
					],
					["Requested model", attempt.requested_model || "not declared"],
					["Router / model group", attempt.model_group || "none"],
					["Actual model", attempt.actual_model || "unavailable"],
					["Receipt source", attempt.model_receipt_source || "unavailable"],
					[
						"Latency",
						Number.isFinite(Number(attempt.latency_ms))
							? (Number(attempt.latency_ms) / 1000).toFixed(2) + " s"
							: "unavailable",
					],
				]));
				if (attempt.reason_code || attempt.validation_detail) {
					const detail = [
						String(attempt.reason_code || "").replaceAll("_", " "),
						attempt.validation_detail,
					].filter(Boolean).join(" · ");
					card.append(paragraph( "model-receipt-detail", detail));
				}
				modelList.append(card);
			});
			modelBlock.append(modelList);
		}
		root.append(modelBlock);
		const rejectionRows = Array.isArray(eligibility.rejections)
			? eligibility.rejections
			: [];
		const rejectionBlock = div( "receipt-block");
		rejectionBlock.append(span( "", "Eligibility rejections"));
		rejectionBlock.append(tokenList(
			rejectionRows.map((item) => `${item.slug}: ${item.reason}`),
			"none: none",
		));
		root.append(rejectionBlock);
		byId("route-status").textContent = String(
			receipt.status || receipt.signals?.selection?.status || "complete",
		).toUpperCase();
	}

	function appendTokenGroup(root, label, values) {
		appendTokenGroups(root, [[label, values]], "workforce-token-group", "small", "none recorded", 12);
	}

	function workforceActions(worker) {
		const stateValue = String(worker.state || "").toLowerCase();
		const employment = String(worker.employment_class || "").toLowerCase();
		if (stateValue === "retired" || stateValue === "merged") return [];
		if (stateValue === "suspended") {
			return [
				["resume", "Resume worker"],
				["retire", "Retire worker"],
				["merge", "Merge into another worker"],
			];
		}
		if (stateValue === "disabled") {
			return [
				["enable", "Enable worker"],
				["suspend", "Suspend worker"],
				["retire", "Retire worker"],
				["merge", "Merge into another worker"],
			];
		}
		const actions = [];
		if (employment === "contractor") actions.push(["promote", "Promote contractor"]);
		actions.push(
			["disable", "Disable worker"],
			["suspend", "Suspend worker"],
			["retire", "Retire worker"],
			["merge", "Merge into another worker"],
		);
		return actions;
	}

	function appendWorkerHistory(root, detail) {
		const history = el("details", "workforce-history");
		history.dataset.preserveKey = `worker:${detail.worker?.agent_slug || "unknown"}:history`;
		history.append(el("summary", "", "Recent lifecycle and outcome evidence"));
		const list = div( "workforce-history-list");
		const rows = [
			...(Array.isArray(detail.events) ? detail.events : []).map((item) => {
				return {
					kind: item.event_type || "lifecycle",
					result: item.reason_present === true
						? "Reason recorded"
						: (String(item.from_standing || "—") + " → " + String(item.to_standing || "—")),
					at: item.created_at,
				};
			}),
			...(Array.isArray(detail.outcomes) ? detail.outcomes : []).map((item) => ({
				kind: item.event_type || "outcome",
				result: item.outcome || "recorded",
				at: item.created_at,
			})),
		].sort((left, right) => String(right.at || "").localeCompare(String(left.at || "")));
		if (!rows.length) {
			list.append(small( "", "No assignment or outcome evidence has been recorded yet."));
		} else {
			const visible = rows.slice(0, 12);
			visible.forEach((item) => {
				const row = div( "workforce-history-row");
				row.append(
					strong( "", item.kind),
					span( "", item.result),
					el("time", "", formatTime(item.at)),
				);
				list.append(row);
			});
			if (visible.length < rows.length) {
				list.append(el(
					"small",
					"workforce-history-bound",
					`Showing ${visible.length} of ${rows.length} loaded lifecycle and outcome records.`,
				));
			}
		}
		history.append(list);
		root.append(history);
	}

	function appendWorkerRecords(root, detail, key, className, summary, empty, cells) {
		const records = Array.isArray(detail[key]) ? detail[key] : [];
		const section = el("details", `workforce-history ${className}`);
		const preserveKey = key === "hiring_cases" ? "hiring" : key;
		section.dataset.preserveKey = `worker:${detail.worker?.agent_slug || "unknown"}:${preserveKey}`;
		section.append(el("summary", "", summary));
		const list = div( "workforce-history-list");
		if (!records.length) {
			list.append(small( "", empty));
		} else {
			records.forEach((item) => {
				const row = div( "workforce-history-row");
				row.append(...cells(item), el("time", "", formatTime(item.created_at)));
				list.append(row);
			});
		}
		section.append(list);
		root.append(section);
	}

	function appendWorkerLineage(root, detail) {
		appendWorkerRecords(
			root,
			detail,
			"lineage",
			"workforce-lineage",
			"Loaded version lineage evidence",
			"No version lineage evidence is loaded.",
			(item) => [
				strong( "", item.version || item.agent_version_id || "unknown version"),
				span( "", item.relation || "unknown relation"),
			],
		);
	}

	function appendWorkerHiringCases(root, detail) {
		appendWorkerRecords(
			root,
			detail,
			"hiring_cases",
			"workforce-hiring-cases",
			"Loaded hiring case metadata",
			"No hiring case metadata is loaded.",
			(item) => [
				strong( "", item.case_type || "hiring"),
				span( "", [
					item.status || "unknown status",
					item.proposed_slug || item.id || "unknown case",
				].join(" · ")),
			],
		);
	}

	function renderWorkerDetail() {
		const root = byId("workforce-detail");
		const form = byId("workforce-action-form");
		const detail = state.selectedWorkerDetail;
		if (!root) return;
		root.replaceChildren();
		if (!detail?.worker) {
			root.className = "empty-state";
			root.textContent = "Select a worker to inspect scope, lineage, hiring evidence, assignments, and outcomes.";
			if (form) form.hidden = true;
			byId("workforce-detail-state").textContent = "SELECT";
			return;
		}
		root.className = "workforce-detail";
		const worker = detail.worker;
		const contract = detail.recruitment_contract || {};
		byId("workforce-detail-state").textContent = String(worker.state || "unknown").toUpperCase();
		const heading = div( "workforce-detail-heading");
		heading.append(
			span( "worker-state", worker.state || "unknown"),
			el("h3", "", worker.display_label || worker.display_name || worker.agent_slug),
			paragraph( "", contract.scope || contract.narrow_scope || worker.agent_slug),
		);
		root.append(heading);
		root.append(definitionList("workforce-facts", [
			["Stable worker ID", worker.worker_id],
			["Agent slug", worker.agent_slug],
			["Version", worker.current_version],
			["Revision", worker.revision],
			["Archetype", contract.archetype],
			["Authority", contract.authority],
			["Origin", worker.origin],
		].map(([label, value]) => [label, value || "—"])));
		appendTokenGroup(root, "Domains", contract.domains);
		appendTokenGroup(root, "Stacks", contract.stacks);
		appendTokenGroup(root, "Outcomes owned", contract.outcomes || contract.outcomes_owned);
		appendTokenGroup(root, "Evidence required", contract.evidence_requirements);
		const readiness = detail.promotion_readiness || {};
		const readinessCard = el(
			"section",
			"promotion-readiness " + (readiness.eligible_for_automatic_promotion ? "ready" : ""),
		);
		readinessCard.append(
			small( "", "Promotion readiness"),
			el(
				"strong",
				"",
				readiness.automatic_policy_enabled
					? String(readiness.verified_successes || 0) + " / " + String(readiness.required_successes || 0) + " verified assignments"
					: "Human-controlled",
			),
			paragraph( "", (readiness.reasons || []).join(" ") || "No promotion evidence applies."),
			span( "", readiness.evidence_rule || ""),
		);
		root.append(readinessCard);
		const comparisons = el("section", "workforce-comparisons");
		comparisons.append(small( "", "Closest workers"));
		const comparisonRows = Array.isArray(detail.closest_workers) ? detail.closest_workers : [];
		if (!comparisonRows.length) {
			comparisons.append(paragraph( "", "No comparable worker evidence is available."));
		} else {
			comparisonRows.slice(0, 5).forEach((item) => {
				const row = el("article", "workforce-comparison " + String(item.recommendation || ""));
				row.append(
					strong( "", item.right || "unknown"),
					span( "", String(Math.round(Number(item.score || 0) * 100)) + "% overlap"),
					small( "", (item.reasons || []).join("; ")),
				);
				comparisons.append(row);
			});
		}
		root.append(comparisons);
		const prompt = detail.compiled_prompt;
		if (prompt?.preview) {
			const promptDetails = el("details", "compiled-prompt-preview");
			promptDetails.dataset.preserveKey = `worker:${worker.agent_slug}:prompt`;
			promptDetails.append(
				el("summary", "", "Compiled prompt preview"),
				small( "", "Version " + String(prompt.version || "unknown") + " · " + String(prompt.hash || "no hash")),
				small(
					"",
					"Owner-only governed specialist definition · separate from runtime observation capture",
				),
			);
			const pre = el("pre");
			pre.textContent = String(prompt.preview) + (prompt.truncated ? "\n… preview truncated" : "");
			promptDetails.append(pre);
			root.append(promptDetails);
		}
		const evidence = div( "workforce-evidence-summary");
		const evidenceLabel = (key, label) => {
			const rows = Array.isArray(detail[key]) ? detail[key] : [];
			const rawTotal = detail[`${key}_total_count`];
			const exactTotal = typeof rawTotal === "number"
				&& Number.isSafeInteger(rawTotal)
				&& rawTotal >= rows.length;
			const truncated = detail[`${key}_truncated`] === true;
			if (!exactTotal) {
				return truncated
					? `${rows.length} ${label} shown (bounded; total unavailable)`
					: `${rows.length} ${label}`;
			}
			const bounded = truncated || rawTotal > rows.length;
			const count = bounded ? `${rows.length} of ${rawTotal}` : String(rawTotal);
			return `${count} ${label}${bounded ? " (bounded)" : ""}`;
		};
		evidence.append(
			strong( "", evidenceLabel("lineage", "version records")),
			span( "", evidenceLabel("events", "lifecycle events")),
			span( "", evidenceLabel("outcomes", "recorded outcomes")),
			span( "", evidenceLabel("hiring_cases", "hiring records")),
		);
		root.append(evidence);
		appendWorkerLineage(root, detail);
		appendWorkerHiringCases(root, detail);
		appendWorkerHistory(root, detail);
		if (!form) return;
		byId("workforce-action-worker").value = worker.agent_slug || "";
		byId("workforce-action-revision").value = String(worker.revision ?? "");
		const actionSelect = byId("workforce-action-kind");
		const actions = workforceActions(worker);
		actionSelect.replaceChildren();
		actions.forEach(([value, label]) => {
			const option = el("option", "", label);
			option.value = value;
			actionSelect.append(option);
		});
		form.hidden = actions.length === 0;
	}

	function renderWorkforce() {
		const workers = Array.isArray(state.workforce) ? state.workforce : [];
		const workforceSource = collectionSourceState("workforce");
		const counts = state.workforceCounts || {};
		setMetric("workforce-employees", counts.employee || 0);
		setMetric("workforce-contractors", counts.contractor || 0);
		setMetric("workforce-disabled", counts.disabled || 0);
		setMetric("workforce-suspended", counts.suspended || 0);
		setMetric("workforce-retired", counts.retired || 0);
		setMetric("workforce-merged", counts.merged || 0);
		const workforcePage = state.workforcePage || {};
		const workforceFiltered = Number.isInteger(workforcePage.filtered_count)
			? workforcePage.filtered_count
			: workers.length;
		const workforceTotal = Number.isInteger(workforcePage.total_count)
			? workforcePage.total_count
			: workforceFiltered;
		setMetric(
			"workforce-count",
			`${workers.length} shown · ${workforceFiltered} filtered · ${workforceTotal} total · ${collectionSourceLabel(workforceSource)}`,
		);
		const grid = byId("workforce-grid");
		if (grid) {
			grid.replaceChildren();
			if (workforceSource.status === "stale") {
				grid.append(div("empty-compact", collectionSourceSummary(workforceSource, "Workforce")));
			}
			if (!workers.length) {
				const emptyMessage = workforceSource.status === "current"
					? "No governed workers are installed yet."
					: workforceSource.status === "stale"
						? "The retained last-good workforce sample contains no governed workers."
						: collectionSourceSummary(workforceSource, "Workforce");
				grid.append(div("empty-state", emptyMessage));
			}
			workers.forEach((worker) => {
				const card = el("button", `workforce-card state-${worker.state || "unknown"}`);
				card.type = "button";
				card.dataset.worker = worker.agent_slug || "";
				card.setAttribute("aria-label", `Inspect ${worker.display_label || worker.agent_slug}`);
				const head = span( "workforce-card-head");
				head.append(
					strong( "", worker.display_label || worker.display_name || worker.agent_slug),
					span( "worker-state", worker.state || "unknown"),
				);
				card.append(
					head,
					span( "workforce-card-slug", worker.agent_slug),
					small( "", `v${worker.current_version || "unknown"} · revision ${worker.revision ?? 0}`),
				);
				grid.append(card);
			});
		}
		const hiring = Array.isArray(state.hiring) ? state.hiring : [];
		const hiringSource = collectionSourceState("hiring");
		const hiringPage = state.hiringPage || {};
		const hiringFiltered = Number.isInteger(hiringPage.filtered_count)
			? hiringPage.filtered_count
			: hiring.length;
		const hiringTotal = Number.isInteger(hiringPage.total_count)
			? hiringPage.total_count
			: hiringFiltered;
		const hiringFilters = state.hiringFilters || {};
		const hiringActiveFilterCount = Object.keys(hiringFilters).length;
		const hiringFilterSummary = hiringActiveFilterCount
			? Object.entries(hiringFilters)
				.map(([key, value]) => `${key}=${value}`)
				.join(", ")
			: "";
		const hiringCollectionLabel = hiringFilterSummary
			? `${hiring.length} shown · ${hiringFiltered} filtered · ${hiringTotal} total · ${hiringFilterSummary}`
			: `${hiring.length} shown · ${hiringFiltered} filtered · ${hiringTotal} total`;
		setMetric(
			"hiring-count",
			`${hiringCollectionLabel} · ${collectionSourceLabel(hiringSource)}`,
		);
		const hiringPageStatus = byId("hiring-page-status");
		if (hiringPageStatus) {
			const sourceNeedsAttention = hiringSource.status !== "current";
			if (hiringActiveFilterCount || sourceNeedsAttention) {
				hiringPageStatus.hidden = false;
				hiringPageStatus.textContent = [
					sourceNeedsAttention ? collectionSourceSummary(hiringSource, "Hiring") : "",
					hiringActiveFilterCount ? `Filter active: ${hiringFilterSummary}.` : "",
				].filter(Boolean).join(" ");
			} else {
				hiringPageStatus.hidden = true;
				hiringPageStatus.textContent = "";
			}
		}
		const hiringList = byId("hiring-list");
		if (hiringList) {
			hiringList.replaceChildren();
			if (!hiring.length) {
				const emptyMessage = hiringSource.status === "current"
					? "No hiring cases match the committed source filters."
					: hiringSource.status === "stale"
						? "The retained last-good hiring sample contains no matching cases."
						: collectionSourceSummary(hiringSource, "Hiring");
				hiringList.append(div("empty-state", emptyMessage));
			}
			hiring.forEach((item) => {
				const caseId = typeof item?.id === "string" ? item.id : "";
				const exactEvidence = hiringEvidenceIsComplete(state.hiringEvidence, caseId)
					? state.hiringEvidence
					: null;
				const loading = Boolean(caseId)
					&& state.hiringEvidenceLoadingCaseId === caseId;
				const card = el("article", `hiring-card status-${item.status || "unknown"}`);
				card.dataset.preserveKey = `hiring:${caseId || item.proposed_slug || "unknown"}:card`;
				const head = div( "hiring-card-head");
				head.append(
					strong( "", item.proposed_slug || "Unnamed candidate"),
					span( "worker-state", `${item.case_type || "hire"} · ${item.status || "unknown"}`),
				);
				card.append(
					head,
					el(
						"small",
						"",
						`Case ${caseId || "unavailable"} · Risk: ${item.risk_tier || "standard"} · staffing need ${item.work_unit_id || "—"}`,
					),
					el(
						"small",
						"read-only-note",
						"Metadata summary only · full evidence is not loaded from this collection.",
					),
				);
				const actions = div( "card-actions");
				const load = el("button", "button ghost compact", "Load full evidence");
				load.type = "button";
				load.dataset.preserveKey = `hiring:${caseId || "unavailable"}:load`;
				if (caseId) load.dataset.hiringEvidenceCase = caseId;
				load.disabled = !caseId || loading;
				load.setAttribute("aria-busy", String(loading));
				load.setAttribute("aria-expanded", String(Boolean(exactEvidence)));
				load.setAttribute(
					"aria-label",
					caseId
						? `Load full evidence for hiring case ${caseId}`
						: "Full hiring evidence is unavailable because the case ID is missing",
				);
				actions.append(load);
				if (item.status === "proposed" && item.human_approval_required === true) {
					const approve = el(
						"button",
						"button ghost compact",
						item.case_type === "amend"
							? "Approve and apply amendment"
							: "Approve reviewed contractor",
					);
					approve.type = "button";
					approve.disabled = !caseId;
					if (caseId) approve.dataset.hiringApproveCase = caseId;
					approve.setAttribute(
						"aria-label",
						caseId
							? `Approve hiring case ${caseId}`
							: "Hiring approval unavailable because the case ID is missing",
					);
					actions.append(approve);
				}
				card.append(actions);
				if (exactEvidence) {
					card.append(el(
						"small",
						"read-only-note",
						"Full evidence loaded from the exact hiring-case response.",
					));
				}
				HIRING_EVIDENCE_DOCUMENTS.forEach(([field, label]) => {
					if (!exactEvidence) return;
					const details = el("details", "hiring-evidence");
					details.dataset.preserveKey = `hiring:${caseId}:evidence:${field}`;
					details.append(el("summary", "", label));
					const pre = el("pre");
					pre.textContent = JSON.stringify(exactEvidence[field], null, 2);
					details.append(pre);
					card.append(details);
				});
				hiringList.append(card);
			});
		}
		renderWorkerDetail();
	}

	function activeEvidenceKind() {
		return document.querySelector(".subnav-item.active")?.dataset.evidence || "specialists";
	}

	function renderActiveView() {
		renderRouteHosts();
		if (state.activeView === "overview" && state.overview) renderOverview();
		else if (state.activeView === "evidence") renderEvidence(activeEvidenceKind());
		else if (state.activeView === "hosts") renderHosts();
		else if (state.activeView === "roster") renderRoster();
		else if (state.activeView === "workforce") renderWorkforce();
	}

	function renderActiveControlView() {
		renderRouteHosts();
		if (state.activeView === "overview" && state.overview) renderOverview();
		else if (state.activeView === "hosts") renderHosts();
		else if (state.activeView === "roster") renderRoster();
		else if (state.activeView === "workforce") renderWorkforce();
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
			workforce: "Workforce operations",
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
		renderMetricEvidence,
		renderOverview,
		emptyRow,
		renderHosts,
		renderRouteHosts,
		renderRoster,
		renderWorkforce,
		renderWorkerDetail,
		renderVisionEvidence,
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
