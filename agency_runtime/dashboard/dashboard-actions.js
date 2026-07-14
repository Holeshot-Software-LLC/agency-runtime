"use strict";

export function createActionController(core, config, renderer, live) {
  const {
    state,
    byId,
    api,
    showNotice,
    formatBytes,
    requestConfirmation,
  } = core;

  function maySurface(error, controller) {
    return error?.name !== "AbortError"
      && live.mutationIsCurrent(controller);
  }

  async function runRoute() {
    const task = byId("route-task").value.trim();
    if (!task) return showNotice("Enter a task before running the routing lab.", true);
    byId("route-button").disabled = true;
    byId("route-status").textContent = "RUNNING";
    const controller = live.beginMutation();
    try {
      const result = await api("/api/route", {
        method: "POST",
        body: JSON.stringify({
          task,
          session_id: byId("route-session").value.trim(),
          limit: 12,
        }),
        signal: controller.signal,
      });
      if (!live.mutationIsCurrent(controller)) return;
      renderer.renderReceipt(result);
      await live.reconcileRuntimeEvidence("Routing receipt completed.");
    } catch (error) {
      if (maySurface(error, controller)) {
        showNotice(error.message, true);
        byId("route-status").textContent = "FAILED";
      }
    } finally {
      if (!state.lifecycle.destroyed) {
        byId("route-button").disabled = false;
        if (controller.signal.aborted) byId("route-status").textContent = "CANCELLED";
      }
      live.finishMutation(controller);
    }
  }

  async function trimRuntime() {
    const confirm = byId("trim-confirm").value;
    if (confirm !== "TRIM RUNTIME DATA") {
      return showNotice("Enter the exact confirmation phrase.", true);
    }
    const days = Number(byId("trim-days").value);
    if (!Number.isInteger(days) || days < 1 || days > 3650) {
      return showNotice("Older than days must be an integer from 1 through 3650.", true);
    }
    byId("trim-button").disabled = true;
    const controller = live.beginMutation();
    try {
      const result = await api("/api/maintenance/trim", {
        method: "POST",
        body: JSON.stringify({ confirm, older_than_days: days, vacuum: false }),
        signal: controller.signal,
      });
      if (!live.mutationIsCurrent(controller)) return;
      byId("trim-confirm").value = "";
      delete byId("trim-days").dataset.dirty;
      await live.reconcileAll(
        `Runtime evidence trimmed. Database is ${formatBytes(result.db_size_after_bytes)}.`,
      );
    } catch (error) {
      if (maySurface(error, controller)) showNotice(error.message, true);
    } finally {
      if (!state.lifecycle.destroyed) byId("trim-button").disabled = false;
      live.finishMutation(controller);
    }
  }

  function requiredConfigConfirmations(operations) {
    const confirmations = ["SAVE CONFIG"];
    if (operations.some((operation) => operation.op === "secret")) {
      confirmations.push("SAVE SENSITIVE CONFIG");
    }
    const profile = operations.find((operation) => operation.path === "profile");
    if (profile?.value === "local-only") confirmations.push("APPLY LOCAL-ONLY PROFILE");
    const capture = operations.find(
      (operation) => operation.path === "observability.capture_content",
    );
    if (capture?.value === true) confirmations.push("ENABLE CONTENT CAPTURE");
    return confirmations;
  }

  async function saveConfig(event) {
    event.preventDefault();
    let operations;
    try { operations = config.collectConfigChanges(); }
    catch (error) { return showNotice(error.message, true); }
    if (!operations.length) return;

    const confirmations = [];
    for (const phrase of requiredConfigConfirmations(operations)) {
      const accepted = await requestConfirmation(
        phrase,
        "Configuration changes are validated and written to your user configuration file.",
      );
      if (state.lifecycle.destroyed || state.lifecycle.suspended) return;
      if (!accepted) return showNotice("Configuration save cancelled.", true);
      confirmations.push(phrase);
    }

    byId("config-save-button").disabled = true;
    const controller = live.beginMutation();
    try {
      const result = await api("/api/config", {
        method: "POST",
        body: JSON.stringify({
          expected_revision: state.config?.revision || "missing",
          operations,
          confirmations,
        }),
        signal: controller.signal,
      });
      if (!live.mutationIsCurrent(controller)) return;
      config.renderConfig(result);
      const restarts = result.restart_required_paths || [];
      const savedMessage = restarts.length
        ? `Configuration saved. Restart required for: ${restarts.join(", ")}.`
        : "Configuration saved and active.";
      await live.reconcileRuntimeEvidence(savedMessage);
    } catch (error) {
      if (maySurface(error, controller)) {
        showNotice(error.message, true);
        config.updateConfigDirtyState();
      }
    } finally {
      if (controller.signal.aborted && !state.lifecycle.destroyed) {
        config.updateConfigDirtyState();
      }
      live.finishMutation(controller);
    }
  }

  async function rosterAction(action, snapshotId) {
    const expected = `${action.toUpperCase()} ${snapshotId}`;
    const accepted = await requestConfirmation(
      expected,
      `This will ${action} roster snapshot ${snapshotId}.`,
    );
    if (state.lifecycle.destroyed || state.lifecycle.suspended) return;
    if (!accepted) return showNotice("Roster action cancelled.", true);
    const controller = live.beginMutation();
    try {
      await api("/api/roster/action", {
        method: "POST",
        body: JSON.stringify({ action, snapshot_id: snapshotId, confirm: expected }),
        signal: controller.signal,
      });
      if (!live.mutationIsCurrent(controller)) return;
      await live.reconcileAll(`Snapshot ${snapshotId} ${action}d.`);
    } catch (error) {
      if (maySurface(error, controller)) showNotice(error.message, true);
    } finally {
      live.finishMutation(controller);
    }
  }

  async function toggleHost(host, enabled) {
    const expected = `${enabled ? "ENABLE" : "DISABLE"} ${host}`;
    const accepted = await requestConfirmation(
      expected,
      "This changes Agency Runtime immediately for this host. Native plugin registration is unchanged.",
    );
    if (state.lifecycle.destroyed || state.lifecycle.suspended) return;
    if (!accepted) return showNotice("Host action cancelled.", true);
    const controller = live.beginMutation();
    try {
      await api("/api/hosts/toggle", {
        method: "POST",
        body: JSON.stringify({ host, enabled, confirm: expected }),
        signal: controller.signal,
      });
      if (!live.mutationIsCurrent(controller)) return;
      await live.reconcileAll(`${host} runtime ${enabled ? "enabled" : "disabled"}.`);
    } catch (error) {
      if (maySurface(error, controller)) showNotice(error.message, true);
    } finally {
      live.finishMutation(controller);
    }
  }

  return {
    runRoute,
    trimRuntime,
    requiredConfigConfirmations,
    saveConfig,
    rosterAction,
    toggleHost,
  };
}
