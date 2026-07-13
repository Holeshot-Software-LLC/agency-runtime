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
    const effective = snapshot.effective || snapshot.config || {};
    state.config = snapshot;
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
    const currentRevision = String(state.config?.revision || "missing");
    const nextRevision = String(snapshot.revision || "missing");
    if (!force && state.activeView !== "settings" && !state.configDirty) {
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
    renderConfig,
    applyConfigSnapshot,
  };
}
