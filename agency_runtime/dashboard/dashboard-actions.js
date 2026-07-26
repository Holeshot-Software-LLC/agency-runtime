export function createActionController(core, config, renderer, live) {
  const {
    state,
    byId,
    api,
    showNotice,
  } = core;

  function maySurface(error, controller) {
    return error?.name !== "AbortError"
      && live.mutationIsCurrent(controller);
  }

  function markButtonPending(id) {
    const button = byId(id);
    button.disabled = true;
    button.setAttribute("aria-busy", "true");
  }

  function clearButtonPending(id) {
    const button = byId(id);
    button.disabled = false;
    button.removeAttribute("aria-busy");
  }

  function serviceControlBlocked() {
    if (!config.serviceRestartRequired()) return false;
    showNotice(
      "Restart the dashboard service before using routing, roster, or host controls.",
      true,
    );
    return true;
  }

  async function runRoute() {
    if (serviceControlBlocked()) return;
    if (state.master?.enabled === false) {
      byId("route-status").textContent = "BYPASSED";
      return showNotice(
        "Agency Runtime is off. Enable the master switch to use Route Lab.",
        true,
      );
    }
    const task = byId("route-task").value.trim();
    if (!task) return showNotice("Enter a task before running the routing lab.", true);
    const host = byId("route-host").value.trim().toLowerCase();
    if (!host) {
      return showNotice(
        "Route Lab needs a verified, enabled execution host. Refresh host discovery after installing or enabling one.",
        true,
      );
    }
    markButtonPending("route-button");
    byId("route-status").textContent = "RUNNING";
    const controller = live.beginMutation();
    try {
      const result = await api("/api/route", {
        method: "POST",
        body: JSON.stringify({
          task,
          host,
          session_id: byId("route-session").value.trim(),
          limit: 12,
        }),
        signal: controller.signal,
      });
      if (!live.mutationIsCurrent(controller)) return;
      if (result.bypassed === true) {
        live.applyMasterState(result.master);
        byId("route-status").textContent = "BYPASSED";
        showNotice(result.message || "Agency Runtime is off; routing was bypassed.", true);
        return;
      }
      renderer.renderReceipt(result);
      await live.reconcileRuntimeEvidence("Routing receipt completed.");
    } catch (error) {
      if (maySurface(error, controller)) {
        showNotice(error.message, true);
        byId("route-status").textContent = "FAILED";
      }
    } finally {
      if (!state.lifecycle.destroyed) {
        clearButtonPending("route-button");
        renderer.renderRouteHosts();
        if (controller.signal.aborted) byId("route-status").textContent = "CANCELLED";
      }
      live.finishMutation(controller);
    }
  }

  async function selectWorker(slug) {
    if (!slug || state.lifecycle.destroyed || state.lifecycle.suspended) return;
    const request = live.beginViewRequest("workerDetail");
    try {
      const payload = await api(
        `/api/workforce?worker=${encodeURIComponent(slug)}&limit=100`,
        { signal: request.controller.signal },
      );
      if (!live.viewRequestIsCurrent("workerDetail", request)) return;
      state.selectedWorkerDetail = payload.detail || null;
      renderer.renderWorkerDetail();
    } catch (error) {
      if (
        error?.name !== "AbortError"
        && live.viewRequestIsCurrent("workerDetail", request)
      ) showNotice(error.message, true);
    } finally {
      live.finishViewRequest("workerDetail", request);
    }
  }

  return {
    runRoute,
    serviceControlBlocked,
    selectWorker,
  };
}
