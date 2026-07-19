"use strict";

export function createConfigController(core) {
  const {
    document,
    state,
    byId,
    el,
    showNotice,
    nestedValue,
    comparable,
  } = core;

  function readConfigControl(node) {
    const kind = node.dataset.valueType || "string";
    if (kind === "boolean") return node.checked;
    if (kind === "integer") {
      const value = Number(node.value);
      if (!Number.isInteger(value)) {
        throw new Error(`${node.labels?.[0]?.textContent || node.id} must be an integer.`);
      }
      return value;
    }
    if (kind === "number") {
      const value = Number(node.value);
      if (!Number.isFinite(value)) {
        throw new Error(`${node.labels?.[0]?.textContent || node.id} must be a finite number.`);
      }
      return value;
    }
    if (kind === "json") {
      try { return JSON.parse(node.value); }
      catch { throw new Error(`${node.labels?.[0]?.textContent || node.id} must contain valid JSON.`); }
    }
    if (node.dataset.nullable === "true" && !node.value.trim()) return null;
    return node.value;
  }

  function writeConfigControl(node, value) {
    const kind = node.dataset.valueType || "string";
    if (kind === "boolean") node.checked = value === true;
    else if (kind === "json") {
      const safeValue = node.dataset.configPath === "providers" && Array.isArray(value)
        ? value.map(({ api_key: _secret, ...provider }) => provider)
        : value;
      node.value = JSON.stringify(safeValue ?? [], null, 2);
    } else node.value = value ?? "";
  }

  function configControls() {
    return [...document.querySelectorAll("[data-config-path]")];
  }

  function serviceRestartRequired() {
    return state.serviceBinding?.store_restart_required === true;
  }

  function applyServiceBinding(snapshot = {}) {
    const value = snapshot.service_binding;
    const binding = value && typeof value === "object" ? {
      store_path: typeof value.store_path === "string" ? value.store_path : "",
      desired_store_path: typeof value.desired_store_path === "string"
        ? value.desired_store_path
        : "",
      store_restart_required: value.store_restart_required === true,
    } : {
      store_path: "",
      desired_store_path: "",
      store_restart_required: false,
    };
    state.serviceBinding = binding;
    const blocked = binding.store_restart_required;
    const banner = byId("store-restart-banner");
    if (banner) banner.hidden = !blocked;
    const paths = byId("store-restart-paths");
    if (paths) {
      paths.textContent = blocked
        ? `Active: ${binding.store_path || "unknown"} · Configured: ${binding.desired_store_path || "unknown"}`
        : "";
    }
    document.querySelector(".shell")?.classList.toggle("store-restart-required", blocked);
    [
      "roster-search-slug",
      "roster-search-submit",
      "roster-search-clear",
      "roster-filter-query",
      "roster-filter-division",
      "roster-filter-capability",
      "roster-filter-authority",
      "roster-filter-host",
      "roster-filter-platform",
      "roster-filter-tool",
      "roster-filter-apply",
      "roster-filter-clear",
    ].forEach((id) => {
      const control = byId(id);
      if (!control) return;
      control.disabled = blocked;
      control.title = blocked
        ? "Restart the dashboard service to use roster controls."
        : "";
    });
    const routeHost = byId("route-host");
    const routeHostAvailable = Boolean(routeHost?.value);
    if (routeHost) {
      routeHost.disabled = blocked || state.master?.enabled !== true || !routeHostAvailable;
    }
    const route = byId("route-button");
    if (route && route.getAttribute("aria-busy") !== "true") {
      route.disabled = blocked || state.master?.enabled !== true || !routeHostAvailable;
      route.setAttribute("aria-disabled", String(route.disabled));
      if (blocked) {
        route.title = "Restart the dashboard service to use Route Lab.";
      } else if (!routeHostAvailable) {
        route.title = "A verified and enabled execution host is required";
      }
    }
    return blocked;
  }

  function projectConfigSummary(snapshot) {
    const effective = snapshot?.effective || snapshot?.config || {};
    const retentionDays = nestedValue(effective, "observability.retention_days");
    const captureContent = nestedValue(effective, "observability.capture_content");
    if (retentionDays === undefined && captureContent === undefined) return;
    state.overview = state.overview || {};
    if (retentionDays !== undefined) {
      state.overview.retention_days = retentionDays;
      const retention = byId("setting-retention");
      if (retention) retention.textContent = `${retentionDays} days`;
    }
    if (captureContent !== undefined) {
      const enabled = captureContent === true;
      state.overview.capture_content = enabled;
      const capture = byId("setting-capture");
      if (capture) capture.textContent = enabled ? "Opt-in enabled" : "Disabled";
      const privacy = byId("privacy-chip");
      if (privacy) privacy.textContent = enabled ? "Redacted content" : "Metadata only";
    }
  }

  function appendSecretOperation(operations, path, value, clear) {
    if (value && clear) {
      throw new Error(`Choose either a new value or clear for ${path}, not both.`);
    }
    if (value) operations.push({ op: "secret", path, action: "replace", value });
    if (clear) operations.push({ op: "secret", path, action: "clear" });
  }

  function collectConfigChanges() {
    const operations = [];
    configControls().forEach((node) => {
      const path = node.dataset.configPath;
      let value;
      try {
        value = readConfigControl(node);
      } catch (error) {
        error.control = node;
        throw error;
      }
      if (comparable(value) !== state.configBaseline.get(path)) {
        operations.push({ op: "set", path, value });
      }
    });
    appendSecretOperation(
      operations,
      "judge.api_key",
      byId("config-judge-secret").value,
      byId("config-judge-secret-clear").checked,
    );
    appendSecretOperation(
      operations,
      "adapters.litellm.api_key",
      byId("config-litellm-secret").value,
      byId("config-litellm-secret-clear").checked,
    );
    const providerIndex = byId("config-provider-secret-index").value;
    const providerSecret = byId("config-provider-secret").value;
    const clearProviderSecret = byId("config-provider-secret-clear").checked;
    if ((providerSecret || clearProviderSecret) && providerIndex === "") {
      throw new Error("Select a provider before changing its direct key.");
    }
    if (providerIndex !== "") {
      appendSecretOperation(
        operations,
        `providers.${providerIndex}.api_key`,
        providerSecret,
        clearProviderSecret,
      );
    }
    return operations;
  }

  function syncProviderSecretOptions() {
    const select = byId("config-provider-secret-index");
    const selected = select.value;
    let providers = [];
    try { providers = JSON.parse(byId("config-providers").value); }
    catch { providers = []; }
    select.replaceChildren();
    if (!Array.isArray(providers) || !providers.length) {
      const option = el("option", "", "No configured providers");
      option.value = "";
      select.append(option);
      select.disabled = true;
      return;
    }
    select.disabled = false;
    providers.forEach((provider, index) => {
      const option = el("option", "", provider?.name || `Provider ${index + 1}`);
      option.value = String(index);
      select.append(option);
    });
    select.value = [...select.options].some((option) => option.value === selected)
      ? selected
      : "0";
  }

  function updateConfigDirtyState() {
    syncProviderSecretOptions();
    configControls().forEach((node) => {
      node.removeAttribute("aria-invalid");
      if (typeof node.setCustomValidity === "function") node.setCustomValidity("");
    });
    let operations = [];
    try { operations = collectConfigChanges(); }
    catch (error) {
      state.configDirty = true;
      if (error.control) {
        error.control.setAttribute("aria-invalid", "true");
        if (typeof error.control.setCustomValidity === "function") {
          error.control.setCustomValidity(error.message);
        }
      }
      byId("config-change-count").textContent = error.message;
      byId("config-save-button").disabled = true;
      return;
    }
    const count = operations.length;
    state.configDirty = count > 0;
    const pending = state.pendingConfig ? " · newer configuration available; reset to load it" : "";
    byId("config-change-count").textContent = count
      ? `${count} unsaved change${count === 1 ? "" : "s"}${pending}`
      : `No unsaved changes${pending}`;
    byId("config-save-button").disabled = count === 0;
  }

  function renderConfig(snapshot) {
    applyServiceBinding(snapshot);
    const effective = snapshot.effective || snapshot.config || {};
    projectConfigSummary(snapshot);
    state.config = snapshot;
    state.controlConfigRevision = String(snapshot.revision || "missing");
    state.pendingConfig = null;
    configControls().forEach((node) => {
      writeConfigControl(node, nestedValue(effective, node.dataset.configPath));
    });
    byId("config-judge-secret").value = "";
    byId("config-judge-secret-clear").checked = false;
    byId("config-litellm-secret").value = "";
    byId("config-litellm-secret-clear").checked = false;
    byId("config-provider-secret").value = "";
    byId("config-provider-secret-clear").checked = false;
    syncProviderSecretOptions();
    state.configBaseline = new Map(configControls().map((node) => [
      node.dataset.configPath,
      comparable(readConfigControl(node)),
    ]));
    byId("config-output").textContent = JSON.stringify(effective, null, 2);
    byId("config-path").textContent = snapshot.path
      || "Bundled defaults; the next save creates the user config.";
    const revision = String(snapshot.revision || "missing");
    byId("config-revision").textContent = revision === "missing" ? "NEW FILE" : revision.slice(0, 10);
    const rawOverrides = snapshot.environment_overrides || {};
    const overrides = Array.isArray(rawOverrides) ? rawOverrides : Object.keys(rawOverrides);
    byId("config-override-count").textContent = overrides.length
      ? `${overrides.length} ENV OVERRIDE${overrides.length === 1 ? "" : "S"}`
      : "NO OVERRIDES";
    updateConfigDirtyState();
  }

  function applyConfigSnapshot(snapshot, { force = false } = {}) {
    if (!snapshot) return false;
    applyServiceBinding(snapshot);
    // The summary describes the effective runtime, not the editor baseline. It
    // must advance even while dirty fields retain their older CAS revision.
    projectConfigSummary(snapshot);
    const currentRevision = String(state.config?.revision || "missing");
    const nextRevision = String(snapshot.revision || "missing");
    // Quick card controls may safely advance their own CAS token while the
    // settings editor keeps its older baseline and revision for conflict-safe
    // saves. Never rewrite dirty inputs merely to unblock an unrelated toggle.
    state.controlConfigRevision = nextRevision;
    if (!force && state.activeView !== "settings" && !state.configDirty) {
      // Quick controls need the latest CAS token even while settings inputs are
      // off-screen. Keep the pending snapshot for deferred field rendering.
      state.config = snapshot;
      state.pendingConfig = snapshot;
      return false;
    }
    if (!force && state.configDirty) {
      if (currentRevision !== nextRevision) {
        const pendingRevision = String(state.pendingConfig?.revision || "");
        state.pendingConfig = snapshot;
        updateConfigDirtyState();
        if (pendingRevision !== nextRevision) {
          showNotice(
            "Configuration changed outside this dashboard. Your unsaved edits were preserved.",
            true,
          );
        }
      }
      return false;
    }
    renderConfig(snapshot);
    return true;
  }

  return {
    readConfigControl,
    writeConfigControl,
    configControls,
    collectConfigChanges,
    appendSecretOperation,
    syncProviderSecretOptions,
    updateConfigDirtyState,
    serviceRestartRequired,
    applyServiceBinding,
    renderConfig,
    applyConfigSnapshot,
  };
}
