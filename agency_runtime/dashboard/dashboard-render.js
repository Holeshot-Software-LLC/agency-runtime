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
      if (host.hook_trust_action) {
        card.append(el("p", "host-action", host.hook_trust_action));
      }
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
    const routing = receipt.routing || {};
    const providerAttempts = Array.isArray(routing.provider_attempts)
      ? routing.provider_attempts
        .slice(0, 8)
        .filter((attempt) => attempt && typeof attempt === "object")
      : [];
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
      ["Inference mode", routing.inference_mode || "not reported"],
      ["Provider calls", providerAttempts.length],
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
    const modelBlock = el("div", "receipt-block model-receipts");
    modelBlock.append(el("span", "", "Inference and model receipts"));
    if (!providerAttempts.length) {
      modelBlock.append(el("p", "", "No model call was recorded for this route."));
    } else {
      const modelList = el("div", "model-receipt-list");
      modelList.setAttribute("role", "list");
      modelList.setAttribute("aria-label", "Inference provider and model receipts");
      providerAttempts.forEach((attempt, index) => {
        const status = String(attempt.status || "unknown").toLowerCase();
        const card = el("article", "model-receipt-card");
        card.setAttribute("role", "listitem");
        const heading = el("div", "model-receipt-heading");
        heading.append(
          el("strong", "", String(attempt.stage || "provider") + " call " + (index + 1)),
          el("span", "model-receipt-status status-" + status, status.replaceAll("_", " ")),
        );
        card.append(heading);
        const facts = el("dl", "model-receipt-facts");
        [
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
        ].forEach(([label, value]) => {
          const fact = el("div");
          fact.append(el("dt", "", label), el("dd", "", value));
          facts.append(fact);
        });
        card.append(facts);
        if (attempt.reason_code || attempt.validation_detail) {
          const detail = [
            String(attempt.reason_code || "").replaceAll("_", " "),
            attempt.validation_detail,
          ].filter(Boolean).join(" · ");
          card.append(el("p", "model-receipt-detail", detail));
        }
        modelList.append(card);
      });
      modelBlock.append(modelList);
    }
    root.append(modelBlock);
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
    const delegationPlan = receipt.delegation_plan || {};
    const planUnits = Array.isArray(delegationPlan.units)
      ? delegationPlan.units
        .slice(0, 16)
        .filter((unit) => unit && typeof unit === "object")
      : [];
    const planBlock = el("div", "receipt-block delegation-plan");
    planBlock.append(el("span", "", "Unit → specialist delegation plan"));
    const planAuthority = el(
      "p",
      "delegation-plan-authority",
      delegationPlan.authority === "recommendation_only"
        ? "Recommendation only · this is not proof that delegation executed"
        : "No authoritative delegation recommendation is available",
    );
    planBlock.append(planAuthority);
    if (delegationPlan.mechanism) {
      const mechanism = el("p", "delegation-plan-mechanism");
      mechanism.append(
        el("strong", "", `Native ${delegationPlan.execution_host || "host"} mechanism`),
        el("small", "", delegationPlan.mechanism),
      );
      planBlock.append(mechanism);
    }
    if (delegationPlan.evidence_contract) {
      const contract = el("p", "delegation-plan-evidence");
      contract.append(
        el("strong", "", "Evidence contract"),
        el("small", "", delegationPlan.evidence_contract),
      );
      planBlock.append(contract);
    }
    if (!planUnits.length) {
      planBlock.append(el("p", "", "No unit-to-specialist assignments were produced."));
    } else {
      const planList = el("div", "delegation-plan-list");
      planList.setAttribute("role", "list");
      planList.setAttribute("aria-label", "Recommended unit-to-specialist assignments");
      planUnits.forEach((unit, index) => {
        const card = el("article", "delegation-plan-unit");
        card.setAttribute("role", "listitem");
        const heading = el("div", "delegation-plan-heading");
        heading.append(
          el("strong", "", unit.work_unit_id || `unit-${index + 1}`),
          el(
            "span",
            `delegation-strength strength-${unit.assignment_strength || "unknown"}`,
            String(unit.assignment_strength || "unknown").replaceAll("_", " "),
          ),
        );
        card.append(
          heading,
          el("h3", "", unit.recommended_agent || "No specialist assigned"),
          el("p", "delegation-plan-goal", unit.goal_preview || "Goal preview unavailable"),
        );
        const facts = el("dl", "delegation-plan-facts");
        [
          ["Confidence", Number.isFinite(Number(unit.confidence))
            ? Number(unit.confidence).toFixed(2)
            : "unavailable"],
          ["Deliverable", unit.expected_deliverable || unit.deliverable_kind || "unspecified"],
          ["Execution shape", `${unit.parallelization || "unspecified"} · ${unit.mutation_scope || "unspecified"}`],
          ["Dependencies", (Array.isArray(unit.dependencies)
            ? unit.dependencies.slice(0, 16)
            : []).join(", ") || "none"],
        ].forEach(([label, value]) => {
          const fact = el("div");
          fact.append(el("dt", "", label), el("dd", "", value));
          facts.append(fact);
        });
        card.append(facts);
        [
          ["Compatible specialists", unit.compatible_specialists],
          ["Required tools", unit.required_tools],
          ["Required evidence", unit.required_evidence],
          ["Rationale", unit.rationale_codes],
        ].forEach(([label, values]) => {
          const group = el("div", "delegation-plan-tokens");
          group.append(el("small", "", label));
          const tokens = el("div", "token-list");
          (Array.isArray(values) && values.length ? values.slice(0, 8) : ["none"]).forEach((value) => {
            tokens.append(el("span", "token", value));
          });
          group.append(tokens);
          card.append(group);
        });
        planList.append(card);
      });
      planBlock.append(planList);
    }
    root.append(planBlock);
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

  function appendTokenGroup(root, label, values) {
    const items = Array.isArray(values) ? values.filter(Boolean) : [];
    const group = el("div", "workforce-token-group");
    group.append(el("small", "", label));
    const tokens = el("div", "token-list");
    (items.length ? items : ["none recorded"]).slice(0, 12).forEach((value) => {
      tokens.append(el("span", "token", value));
    });
    group.append(tokens);
    root.append(group);
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
    history.append(el("summary", "", "Recent lifecycle and outcome evidence"));
    const list = el("div", "workforce-history-list");
    const rows = [
      ...(Array.isArray(detail.events) ? detail.events : []).map((item) => ({
        kind: item.event_type || "lifecycle",
        result: item.reason || (String(item.from_standing || "—") + " → " + String(item.to_standing || "—")),
        at: item.created_at,
      })),
      ...(Array.isArray(detail.outcomes) ? detail.outcomes : []).map((item) => ({
        kind: item.event_type || "outcome",
        result: item.outcome || "recorded",
        at: item.created_at,
      })),
    ].sort((left, right) => String(right.at || "").localeCompare(String(left.at || "")));
    if (!rows.length) {
      list.append(el("small", "", "No assignment or outcome evidence has been recorded yet."));
    } else {
      rows.slice(0, 12).forEach((item) => {
        const row = el("div", "workforce-history-row");
        row.append(
          el("strong", "", item.kind),
          el("span", "", item.result),
          el("time", "", formatTime(item.at)),
        );
        list.append(row);
      });
    }
    history.append(list);
    root.append(history);
  }

  function renderWorkerDetail() {
    const root = byId("workforce-detail");
    const form = byId("workforce-action-form");
    const detail = state.selectedWorkerDetail;
    if (!root || !form) return;
    root.replaceChildren();
    if (!detail?.worker) {
      root.className = "empty-state";
      root.textContent = "Select a worker to inspect scope, lineage, hiring evidence, assignments, and outcomes.";
      form.hidden = true;
      byId("workforce-detail-state").textContent = "SELECT";
      return;
    }
    root.className = "workforce-detail";
    const worker = detail.worker;
    const contract = detail.recruitment_contract || {};
    byId("workforce-detail-state").textContent = String(worker.state || "unknown").toUpperCase();
    const heading = el("div", "workforce-detail-heading");
    heading.append(
      el("span", "worker-state", worker.state || "unknown"),
      el("h3", "", worker.display_label || worker.display_name || worker.agent_slug),
      el("p", "", contract.scope || contract.narrow_scope || worker.agent_slug),
    );
    root.append(heading);
    const facts = el("dl", "workforce-facts");
    [
      ["Stable worker ID", worker.worker_id],
      ["Agent slug", worker.agent_slug],
      ["Version", worker.current_version],
      ["Revision", worker.revision],
      ["Archetype", contract.archetype],
      ["Authority", contract.authority],
      ["Origin", worker.origin],
    ].forEach(([label, value]) => {
      const fact = el("div");
      fact.append(el("dt", "", label), el("dd", "", value || "—"));
      facts.append(fact);
    });
    root.append(facts);
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
      el("small", "", "Promotion readiness"),
      el(
        "strong",
        "",
        readiness.automatic_policy_enabled
          ? String(readiness.verified_successes || 0) + " / " + String(readiness.required_successes || 0) + " verified assignments"
          : "Human-controlled",
      ),
      el("p", "", (readiness.reasons || []).join(" ") || "No promotion evidence applies."),
      el("span", "", readiness.evidence_rule || ""),
    );
    root.append(readinessCard);
    const comparisons = el("section", "workforce-comparisons");
    comparisons.append(el("small", "", "Closest workers"));
    const comparisonRows = Array.isArray(detail.closest_workers) ? detail.closest_workers : [];
    if (!comparisonRows.length) {
      comparisons.append(el("p", "", "No comparable worker evidence is available."));
    } else {
      comparisonRows.slice(0, 5).forEach((item) => {
        const row = el("article", "workforce-comparison " + String(item.recommendation || ""));
        row.append(
          el("strong", "", item.right || "unknown"),
          el("span", "", String(Math.round(Number(item.score || 0) * 100)) + "% overlap"),
          el("small", "", (item.reasons || []).join("; ")),
        );
        comparisons.append(row);
      });
    }
    root.append(comparisons);
    const prompt = detail.compiled_prompt;
    if (prompt?.preview) {
      const promptDetails = el("details", "compiled-prompt-preview");
      promptDetails.append(
        el("summary", "", "Compiled prompt preview"),
        el("small", "", "Version " + String(prompt.version || "unknown") + " · " + String(prompt.hash || "no hash")),
      );
      const pre = el("pre");
      pre.textContent = String(prompt.preview) + (prompt.truncated ? "\n… preview truncated" : "");
      promptDetails.append(pre);
      root.append(promptDetails);
    }
    const evidence = el("div", "workforce-evidence-summary");
    evidence.append(
      el("strong", "", `${detail.lineage?.length || 0} version records`),
      el("span", "", `${detail.events?.length || 0} lifecycle events`),
      el("span", "", `${detail.outcomes?.length || 0} recorded outcomes`),
      el("span", "", `${detail.hiring_cases?.length || 0} hiring records`),
    );
    root.append(evidence);
    appendWorkerHistory(root, detail);
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
    const counts = state.workforceCounts || {};
    setMetric("workforce-employees", counts.employee || 0);
    setMetric("workforce-contractors", counts.contractor || 0);
    setMetric("workforce-disabled", counts.disabled || 0);
    setMetric("workforce-suspended", counts.suspended || 0);
    setMetric("workforce-retired", counts.retired || 0);
    setMetric("workforce-merged", counts.merged || 0);
    setMetric("workforce-count", workers.length);
    const grid = byId("workforce-grid");
    if (grid) {
      grid.replaceChildren();
      if (!workers.length) grid.append(el("div", "empty-state", "No governed workers are installed yet."));
      workers.forEach((worker) => {
        const card = el("button", `workforce-card state-${worker.state || "unknown"}`);
        card.type = "button";
        card.dataset.worker = worker.agent_slug || "";
        card.setAttribute("aria-label", `Inspect ${worker.display_label || worker.agent_slug}`);
        const head = el("span", "workforce-card-head");
        head.append(
          el("strong", "", worker.display_label || worker.display_name || worker.agent_slug),
          el("span", "worker-state", worker.state || "unknown"),
        );
        card.append(
          head,
          el("span", "workforce-card-slug", worker.agent_slug),
          el("small", "", `v${worker.current_version || "unknown"} · revision ${worker.revision ?? 0}`),
        );
        listen(card, "click", () => callbacks.selectWorker(worker.agent_slug));
        grid.append(card);
      });
    }
    const hiring = Array.isArray(state.hiring) ? state.hiring : [];
    setMetric("hiring-count", hiring.length);
    const hiringList = byId("hiring-list");
    if (hiringList) {
      hiringList.replaceChildren();
      if (!hiring.length) hiringList.append(el("div", "empty-state", "No hiring cases have been recorded."));
      hiring.forEach((item) => {
        const card = el("article", `hiring-card status-${item.status || "unknown"}`);
        const head = el("div", "hiring-card-head");
        head.append(
          el("strong", "", item.proposed_slug || "Unnamed candidate"),
          el("span", "worker-state", `${item.case_type || "hire"} · ${item.status || "unknown"}`),
        );
        card.append(head, el("small", "", `Risk: ${item.risk_tier || "standard"} · work unit ${item.work_unit_id || "—"}`));
        [
          ["Gap evidence", item.gap_evidence],
          ["Duplicate analysis", item.duplicate_evidence],
          ["Independent critic", item.critic_evidence],
          ["Model receipts", item.model_evidence],
        ].forEach(([label, value]) => {
          const details = el("details", "hiring-evidence");
          details.append(el("summary", "", label));
          const pre = el("pre");
          pre.textContent = JSON.stringify(value || {}, null, 2);
          details.append(pre);
          card.append(details);
        });
        if (item.status === "proposed" && item.human_approval_required === true) {
          const approve = el(
            "button",
            "button ghost",
            item.case_type === "amend"
              ? "Approve and apply amendment"
              : "Approve reviewed contractor",
          );
          approve.type = "button";
          listen(approve, "click", () => callbacks.hiringApprove(item.id));
          card.append(approve);
        }
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
    renderOverview,
    emptyRow,
    renderHosts,
    renderRouteHosts,
    renderRoster,
    renderWorkforce,
    renderWorkerDetail,
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
