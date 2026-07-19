"use strict";

const EXECUTION_HOSTS = ["codex", "claude", "openclaw", "hermes"];

const EVIDENCE_COLUMNS = {
  specialists: [["slug", "Specialist"], ["session_id", "Session"], ["trace_id", "Trace"], ["state", "Evidence state"], ["loaded_at", "Activated"], ["expired_at", "Expired"]],
  delegations: [["recommended_agent", "Agent"], ["host", "Host"], ["status", "Status"], ["backend", "Backend"], ["work_unit_id", "Work unit"], ["started_at", "Started"]],
  routing: [["trace_id", "Trace"], ["id", "Decision"], ["status", "Outcome"], ["semantic_status", "Semantic result"], ["source", "Source"], ["selected_ids", "Selected"], ["fallback_applied", "Fallback applied"], ["fallback_companion_ids", "Fallback policy IDs"], ["created_at", "Created"]],
  receipts: [["requested_model", "Requested"], ["model_group", "LiteLLM router / model group"], ["resolved_provider", "Actual provider"], ["resolved_model", "Actual model"], ["host", "Host"], ["status", "Status"], ["source", "Source"], ["ended_at", "Ended"]],
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
    if (!hostStack.children.length) {
      hostStack.append(el(
        "div",
        "empty-compact",
        "No supported agent hosts were found. Install or register a host, then refresh.",
      ));
    }

    const providerStack = byId("provider-health");
    providerStack.replaceChildren();
    const inference = data.inference && typeof data.inference === "object"
      ? data.inference
      : null;
    const inferenceState = String(inference?.state || "unknown").toLowerCase();
    const inferenceTag = byId("inference-state");
    if (inferenceTag) {
      inferenceTag.textContent = inferenceState.toUpperCase().replaceAll("_", " ");
      inferenceTag.dataset.state = inferenceState;
    }
    (inference?.provider_chain || []).forEach((provider) => {
      const row = el("div", "provider-row provider-chain-row");
      const copy = el("div");
      const request = provider.requested_model || "model not declared";
      copy.append(
        el("strong", "", `${provider.order}. ${provider.name}`),
        el("small", "", `${provider.type || "unknown"} · requested ${request}`),
      );
      if (provider.router) copy.append(el("small", "provider-router", `Router / model group: ${provider.router}`));
      const observed = provider.observed_receipt;
      if (observed) {
        copy.append(el(
          "small",
          "provider-resolution",
          `Observed actual: ${observed.actual_provider || "unavailable"} / ${observed.actual_model || "unavailable"}`,
        ));
      }
      const ready = provider.configuration_ready === true;
      row.append(copy, el("span", `status ${ready ? "configured" : "failed"}`, ready ? "config ready" : "config gap"));
      providerStack.append(row);
    });
    if (!providerStack.children.length) {
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
    }
    if (!providerStack.children.length) {
      providerStack.append(el("div", "empty-compact", inference?.configured
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
        const row = el("div", "failure-row");
        const copy = el("div");
        const title = failure.kind === "model_receipt"
          ? `${failure.requested_model || "unidentified model"} · ${failure.status || "failed"}`
          : `${failure.provider || "routing inference"} · ${failure.status || "degraded"}`;
        copy.append(el("strong", "", title));
        if (failure.kind === "model_receipt") {
          copy.append(
            el("small", "", `Router: ${failure.router || "none"}`),
            el("small", "", `Actual: ${failure.actual_provider || "unavailable"} / ${failure.actual_model || "unavailable"}`),
          );
        } else copy.append(el("small", "", `Trace: ${failure.trace_id || "unavailable"}`));
        row.append(copy, el("time", "", formatTime(failure.recorded_at || failure.created_at)));
        failureStack.append(row);
      });
      if (!failureStack.children.length) {
        failureStack.append(el("div", "empty-compact", "No persisted inference failures in the bounded window."));
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
      const heading = el("div", "host-row");
      const current = hostState(host);
      heading.append(el("strong", "", host.host), el("span", `host-state ${current}`, current));
      card.append(heading, el("small", "", hostLocation(host)));
      const tags = el("div", "token-list");
      tags.append(el("span", "token", truthLabel(host.registered, "registered", "not registered", "registration unknown")));
      tags.append(el("span", "token", truthLabel(host.enabled, "native enabled", "native disabled", "native enablement unknown")));
      tags.append(el("span", "token", truthLabel(
        host.runtime_enabled,
        "runtime on",
        "runtime off",
        "runtime state unknown",
      )));
      tags.append(el("span", "token", truthLabel(host.effective_enabled, "effective", "inactive", "effective state unverified")));
      tags.append(el("span", "token", host.maturity || "unverified"));
      card.append(tags);
      if (host.executable_discovered === true) {
        const actions = el("div", "card-actions");
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
        button.setAttribute("aria-label", directionKnown
          ? `${label} ${host.host} runtime`
          : `${host.host} runtime action unavailable: ${label}`);
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
  }

  function renderRouteHosts() {
    const select = byId("route-host");
    if (!select) return "";
    const previous = String(select.value || "");
    const byHost = new Map();
    state.hosts.forEach((host) => {
      const name = typeof host?.host === "string" ? host.host.trim().toLowerCase() : "";
      const receipt = host?.execution_capabilities;
      if (
        EXECUTION_HOSTS.includes(name)
        && !byHost.has(name)
        && host.effective_enabled === true
        && receipt?.status === "native-installation-verified"
        && receipt.execution_host === name
        && Array.isArray(receipt.capabilities)
      ) byHost.set(name, host);
    });
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
      help.textContent = !available.length
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
    const identity = el("div", "agent-contract-line");
    identity.append(
      el("span", `status ${agent.audit_status === "approved" ? "configured" : "failed"}`, agent.audit_status || "audit unknown"),
      el("span", "contract-authority", agent.authority || "authority unassigned"),
    );
    card.append(identity);
    const details = el("details", "agent-governance-detail");
    details.append(el("summary", "", "Contract, compatibility & history"));
    const metadata = el("dl", "agent-metadata");
    [
      ["Source revision", agent.source_revision || "unavailable"],
      ["Source content hash", agent.source_content_hash || agent.content_hash || "unavailable"],
      ["Audit revision", agent.audit_revision || "unavailable"],
      ["Context mode", agent.context_mode || "unassigned"],
    ].forEach(([label, value]) => {
      const row = el("div");
      row.append(el("dt", "", label), el("dd", "", value));
      metadata.append(row);
    });
    details.append(metadata);
    [
      ["Hosts", agent.supported_hosts],
      ["Platforms", agent.supported_platforms],
      ["Required tools", agent.required_tools],
      ["Conflicts", agent.conflicts_with],
      ["Requires", agent.requires],
    ].forEach(([label, values]) => {
      const section = el("div", "contract-token-row");
      section.append(el("strong", "", label));
      const tokens = el("div", "token-list");
      (Array.isArray(values) && values.length ? values : ["none declared"])
        .forEach((value) => tokens.append(el("span", "token", value)));
      section.append(tokens);
      details.append(section);
    });
    const history = el("ol", "revision-history");
    (agent.revision_history || []).forEach((revision) => {
      const row = el("li");
      row.append(
        el("strong", "", revision.version || "version unavailable"),
        el("span", "", `${revision.audit_status || "audit unknown"} · ${formatTime(revision.created_at)}`),
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
    const remediationHistory = Array.isArray(review.remediation_history)
      ? review.remediation_history
      : [];
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
      const summary = el("summary");
      const copy = el("span");
      copy.append(
        el("strong", "", candidate.name || candidate.slug || "Unknown candidate"),
        el("small", "", `${candidate.slug || "unknown"} · ${entry.change || "uncompared"}`),
      );
      summary.append(copy, el("span", `status ${audit.verdict === "passed" ? "configured" : "failed"}`, audit.verdict || "not audited"));
      details.append(summary);
      const comparison = el("dl", "agent-metadata");
      [
        ["Candidate revision", candidate.source_revision || "unavailable"],
        ["Candidate hash", candidate.content_hash || "unavailable"],
        ["Active revision", entry.active?.source_revision || "none"],
        ["Active hash", entry.active?.content_hash || "none"],
        ["Inference audit", audit.inference_status || "unknown"],
      ].forEach(([label, value]) => {
        const row = el("div");
        row.append(el("dt", "", label), el("dd", "", value));
        comparison.append(row);
      });
      details.append(comparison);
      const changed = el("div", "contract-token-row");
      changed.append(el("strong", "", "Changed fields"));
      const changedTokens = el("div", "token-list");
      (entry.changed_fields?.length ? entry.changed_fields : ["none"])
        .forEach((value) => changedTokens.append(el("span", "token", value)));
      changed.append(changedTokens);
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
      details.setAttribute("aria-label", `Remediation attempt for ${slug}`);
      const summary = el("summary");
      const copy = el("span");
      copy.append(
        el("strong", "", slug),
        el("small", "", "remediation attempt · non-executable"),
      );
      summary.append(
        copy,
        el("span", "status", receipt.status || "status unknown"),
      );
      details.append(summary);
      const metadata = el("dl", "agent-metadata");
      [
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
      ].forEach(([label, value]) => {
        const row = el("div");
        row.append(el("dt", "", label), el("dd", "", value));
        metadata.append(row);
      });
      details.append(metadata);
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
      details.setAttribute("aria-label", `Resolved remediation for ${slug}`);
      const summary = el("summary");
      const copy = el("span");
      copy.append(
        el("strong", "", slug),
        el("small", "", "repair provenance · immutable history"),
      );
      summary.append(
        copy,
        el("span", "status configured", entry.resolution || "resolved"),
      );
      details.append(summary);
      const metadata = el("dl", "agent-metadata");
      [
        ["Original hash", entry.original_hash || "unavailable"],
        ["Candidate hash", entry.candidate_hash || "unavailable"],
        ["Source hash", entry.source_hash || "unavailable"],
        ["Candidate", entry.candidate_id || "unavailable"],
        [
          "Audit policy",
          entry.audit_policy_current === false ? "historical policy" : "current policy",
        ],
        ["Resolved at", entry.created_at || "unavailable"],
      ].forEach(([label, value]) => {
        const row = el("div");
        row.append(el("dt", "", label), el("dd", "", value));
        metadata.append(row);
      });
      details.append(metadata);
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
    const pageStatus = byId("review-page-status");
    if (pageStatus) {
      const anomalyStatus = unvalidatedResolutionCount > 0
        ? ` ${unvalidatedResolutionCount} unvalidated resolution ${unvalidatedResolutionCount === 1 ? "record remains" : "records remain"} quarantined.`
        : "";
      pageStatus.textContent = `Showing ${remediationAttempts.length} of ${pendingCount} pending repairs and ${remediationHistory.length} of ${historyCount} resolved repairs.${anomalyStatus}`;
      pageStatus.classList.toggle("failed", unvalidatedResolutionCount > 0);
      pageStatus.dataset.unvalidatedResolutionCount = String(unvalidatedResolutionCount);
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
    const pageCount = Number.isInteger(page?.count)
      ? page.count
      : roster.length;
    const totalCount = Number.isInteger(page?.total_count)
      ? page.total_count
      : pageCount;
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
        pageStatus.textContent = `Showing ${operations.matched_count ?? pageCount} specialists matching the active operational filters.`;
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
        el("strong", "", agent.name || agent.agent_slug),
        el("small", "", `${agent.agent_slug} · ${agent.division || "unassigned"}`),
      );
      const tags = el("div", "token-list");
      (agent.capabilities || []).slice(0, 4).forEach((value) => {
        tags.append(el("span", "token", value));
      });
      if (!tags.children.length) tags.append(el("span", "token", "no capability tags"));
      card.append(tags);
      appendOperationalAgentDetails(card, agent);
      const controls = el("div", "card-actions");
      const status = protectedAgent ? "protected" : enabled ? "enabled" : "disabled";
      controls.append(el("span", `host-state ${enabled ? "verified" : "runtime-disabled"}`, status));
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
    if (!list.children.length) list.append(el("div", "empty-state", "No roster snapshots."));
    renderReviewQueue();
  }

  function renderEvidence(kind = "specialists") {
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
        : `${label[0].toUpperCase()}${label.slice(1)} runtime evidence`;
    }
    const context = byId("evidence-context");
    const rows = state.activity[kind] || [];
    let contextMessage;
    if (kind === "specialists") {
      const current = rows.filter((row) => row.state === "current").length;
      const historical = rows.length - current;
      contextMessage = `${current} current-turn activation${current === 1 ? "" : "s"} · ${historical} historical activation${historical === 1 ? "" : "s"}. Current-turn rows are unexpired and trace-correlated; historical rows remain as immutable audit evidence.`;
    } else {
      contextMessage = "Bounded metadata-only runtime evidence. Payload content and worker output are not included.";
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
        let value = row[columnKey];
        if (Array.isArray(value)) value = value.join(", ") || "—";
        if (columnKey.endsWith("_at") || columnKey === "created_at") value = formatTime(value);
        if (columnKey === "fallback_applied") value = value === true ? "Yes" : "No";
        const td = el("td");
        if (columnKey === "state") {
          const stateLabel = value === "current" ? "Current turn" : "Historical";
          td.append(el("span", `status activation-${value || "historical"}`, stateLabel));
        } else if (columnKey === "status" || columnKey === "action") {
          td.append(el("span", `status ${value || ""}`, value || "—"));
        } else td.textContent = value || "—";
        tr.append(td);
      });
      body.append(tr);
    });
    state.evidenceKeys.set(kind, nextKeys);
    if (!body.children.length) {
      const emptyLabel = kind === "specialists" ? "specialist activation" : label;
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
    const eligibilitySummary = Number.isInteger(eligibility.rejection_count)
      ? `${eligibility.eligible_count || 0} eligible · ${eligibility.rejection_count} rejected${eligibility.truncated ? " · bounded view" : ""}`
      : "not reported";
    const workUnits = receipt.signals?.delegation?.work_units?.units
      || receipt.signals?.work_units?.units
      || receipt.work_units?.units
      || [];
    const blocks = [
      ["Status", receipt.status || receipt.signals?.selection?.status || "unknown"],
      ["Execution host", eligibility.execution_host || hostCapability.execution_host || "unproven"],
      ["Host capability evidence", hostCapability.status
        ? `${hostCapability.status} · ${(hostCapability.capabilities || []).length} capabilities`
        : "unproven"],
      ["Eligibility", eligibilitySummary],
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
    const rejectionRows = Array.isArray(eligibility.rejections)
      ? eligibility.rejections
      : [];
    const rejectionBlock = el("div", "receipt-block");
    rejectionBlock.append(el("span", "", "Eligibility rejections"));
    const rejectionList = el("div", "token-list");
    (rejectionRows.length ? rejectionRows : [{ slug: "none", reason: "none" }])
      .forEach((item) => {
        rejectionList.append(el("span", "token", `${item.slug}: ${item.reason}`));
      });
    rejectionBlock.append(rejectionList);
    root.append(rejectionBlock);
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
    return document.querySelector(".subnav-item.active")?.dataset.evidence || "specialists";
  }

  function renderActiveView() {
    renderRouteHosts();
    if (state.activeView === "overview" && state.overview) renderOverview();
    else if (state.activeView === "evidence") renderEvidence(activeEvidenceKind());
    else if (state.activeView === "hosts") renderHosts();
    else if (state.activeView === "roster") renderRoster();
  }

  function renderActiveControlView() {
    renderRouteHosts();
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
    renderRouteHosts,
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
