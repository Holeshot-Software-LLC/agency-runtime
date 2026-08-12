export function createActionController(core, config, renderer, live) {
	const {
		state,
		byId,
		api,
		showNotice,
		withRequestId,
		formatBytes,
		requestConfirmation,
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

	function validateWorkerDetailResponse(payload, requestedSlug) {
		const detail = payload?.detail;
		const worker = detail?.worker;
		const expected = String(requestedSlug || "").trim().toLowerCase();
		if (
			typeof detail !== "object"
			|| detail === null
			|| Array.isArray(detail)
			|| typeof worker !== "object"
			|| worker === null
			|| Array.isArray(worker)
			|| !expected
			|| worker.agent_slug !== expected
			|| typeof worker.worker_id !== "string"
			|| !worker.worker_id.trim()
			|| !Number.isSafeInteger(worker.revision)
			|| worker.revision < 0
		) {
			throw new Error("Worker detail response did not match the requested governed worker.");
		}
		if (!["events", "hiring_cases", "lineage", "outcomes"].every(
			(field) => Array.isArray(detail[field]),
		)) {
			throw new Error("Worker detail response has an invalid evidence collection.");
		}
		return detail;
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
				showNotice(withRequestId(
					result.message || "Agency Runtime is off; routing was bypassed.",
					result.request_id,
				), true);
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

	async function trimRuntime() {
		const confirm = byId("trim-confirm").value;
		if (confirm !== "TRIM RUNTIME DATA") {
			return showNotice("Enter the exact confirmation phrase.", true);
		}
		const days = Number(byId("trim-days").value);
		if (!Number.isInteger(days) || days < 1 || days > 3650) {
			return showNotice("Older than days must be an integer from 1 through 3650.", true);
		}
		markButtonPending("trim-button");
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
			if (!state.lifecycle.destroyed) clearButtonPending("trim-button");
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
		try {
			operations = config.collectConfigChanges();
		} catch (error) {
			return showNotice(error.message, true);
		}
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

		markButtonPending("config-save-button");
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
			if (!state.lifecycle.destroyed) {
				clearButtonPending("config-save-button");
				config.updateConfigDirtyState();
			}
			live.finishMutation(controller);
		}
	}

	async function rosterAction(action, snapshotId) {
		if (serviceControlBlocked()) return;
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

	async function toggleHost(host, enabled, expectedGeneration) {
		if (serviceControlBlocked()) return;
		if (!Number.isInteger(expectedGeneration) || expectedGeneration < 0) {
			return showNotice("Host control state is stale. Refresh and try again.", true);
		}
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
				body: JSON.stringify({
					host,
					enabled,
					confirm: expected,
					expected_generation: expectedGeneration,
				}),
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

	async function toggleAgent(slug, enabled, reason = "") {
		if (serviceControlBlocked()) return;
		const expected = `${enabled ? "ENABLE" : "DISABLE"} ${slug}`;
		const accepted = await requestConfirmation(
			expected,
			"This changes routing and new specialist loads without deleting the governed roster definition or its history.",
		);
		if (state.lifecycle.destroyed || state.lifecycle.suspended) return;
		if (!accepted) return showNotice("Agent action cancelled.", true);
		const controller = live.beginMutation();
		try {
			const result = await api("/api/agents/toggle", {
				method: "POST",
				body: JSON.stringify({
					slug,
					enabled,
					confirm: expected,
					...(reason ? { reason } : {}),
					expected_revision: state.controlConfigRevision
						|| state.config?.revision
						|| "missing",
				}),
				signal: controller.signal,
			});
			if (!live.mutationIsCurrent(controller)) return;
			const committedRevision = String(result?.config?.revision || "");
			if (committedRevision) state.controlConfigRevision = committedRevision;
			await live.reconcileAll(`${slug} ${enabled ? "enabled" : "disabled"}.`);
		} catch (error) {
			if (maySurface(error, controller)) showNotice(error.message, true);
		} finally {
			live.finishMutation(controller);
		}
	}

	async function toggleMaster(enabled) {
		if (!state.master || !Number.isInteger(state.master.generation)) {
			return showNotice("Agency master state is still loading. Refresh and try again.", true);
		}
		const expected = enabled ? "ENABLE AGENCY" : "DISABLE AGENCY";
		const accepted = await requestConfirmation(
			expected,
			enabled
				? "This resumes Agency staffing selection, request-scoped card injection, and evidence capture. Native hosts still own spawning and execution."
				: "This bypasses Agency staffing selection, card injection, hooks, and evidence capture. Native hosts still own spawning and execution; dashboard configuration remains available.",
		);
		if (state.lifecycle.destroyed || state.lifecycle.suspended) return;
		if (!accepted) return showNotice("Agency master action cancelled.", true);
		markButtonPending("master-toggle");
		const controller = live.beginMutation();
		try {
			const result = await api("/api/runtime/toggle", {
				method: "POST",
				body: JSON.stringify({
					enabled,
					confirm: expected,
					expected_generation: state.master.generation,
				}),
				signal: controller.signal,
			});
			if (!live.mutationIsCurrent(controller)) return;
			live.applyMasterState(result.master);
			await live.reconcileAll(
				`Agency Runtime ${enabled ? "enabled" : "disabled"} globally.`,
			);
		} catch (error) {
			if (maySurface(error, controller)) showNotice(error.message, true);
		} finally {
			if (!state.lifecycle.destroyed) {
				clearButtonPending("master-toggle");
				live.syncMasterControl();
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
			state.selectedWorkerDetail = validateWorkerDetailResponse(payload, slug);
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

	async function workforceAction(event) {
		event.preventDefault();
		if (serviceControlBlocked()) return;
		const action = byId("workforce-action-kind").value.trim().toLowerCase();
		const worker = byId("workforce-action-worker").value.trim();
		const target = byId("workforce-action-target").value.trim();
		const reason = byId("workforce-action-reason").value.trim();
		const revision = Number(byId("workforce-action-revision").value);
		if (!worker || !Number.isInteger(revision) || revision < 0) {
			return showNotice("Worker lifecycle evidence is stale. Select the worker again.", true);
		}
		if (!reason) return showNotice("Add an evidence-based reason for this lifecycle action.", true);
		if (action === "enable" || action === "disable") {
			return toggleAgent(worker, action === "enable", reason);
		}
		if (action === "merge" && !target) return showNotice("A merge target is required.", true);
		let confirm = "";
		if (["suspend", "retire", "merge"].includes(action)) {
			confirm = action === "merge"
				? `MERGE ${worker} INTO ${target}`
				: `${action.toUpperCase()} ${worker}`;
			const accepted = await requestConfirmation(
				confirm,
				"This lifecycle change is revision-bound and retained in the worker evidence ledger.",
			);
			if (state.lifecycle.destroyed || state.lifecycle.suspended) return;
			if (!accepted) return showNotice("Workforce action cancelled.", true);
		}
		markButtonPending("workforce-action-submit");
		const controller = live.beginMutation();
		try {
			await api("/api/workforce/action", {
				method: "POST",
				body: JSON.stringify({
					action,
					worker,
					into: action === "merge" ? target : "",
					expected_revision: revision,
					reason,
					confirm,
				}),
				signal: controller.signal,
			});
			if (!live.mutationIsCurrent(controller)) return;
			state.selectedWorkerDetail = null;
			byId("workforce-action-reason").value = "";
			byId("workforce-action-target").value = "";
			await live.reconcileAll(`${worker} lifecycle changed: ${action}.`);
		} catch (error) {
			if (maySurface(error, controller)) showNotice(error.message, true);
		} finally {
			if (!state.lifecycle.destroyed) clearButtonPending("workforce-action-submit");
			live.finishMutation(controller);
		}
	}

	async function hiringApprove(caseId) {
		if (serviceControlBlocked()) return;
		const approvedBy = String(byId("hiring-approver-identity")?.value || "").trim();
		if (!approvedBy) {
			return showNotice(
				"Enter the approver audit identity before approving this case.",
				true,
			);
		}
		if (
			approvedBy.length > 128
			|| new TextEncoder().encode(approvedBy).byteLength > 128
			|| /[\u0000-\u001f\u007f]/.test(approvedBy)
		) {
			return showNotice("Enter a valid approver audit identity.", true);
		}
		const confirm = `APPROVE ${caseId}`;
		const accepted = await requestConfirmation(
			confirm,
			`This records explicit owner approval by ${approvedBy} for a high-risk proposed hire.`,
		);
		if (state.lifecycle.destroyed || state.lifecycle.suspended) return;
		if (!accepted) return showNotice("Hiring approval cancelled.", true);
		const controller = live.beginMutation();
		try {
			await api("/api/hiring/approve", {
				method: "POST",
				body: JSON.stringify({
					case_id: caseId,
					approved_by: approvedBy,
					confirm,
				}),
				signal: controller.signal,
			});
			if (!live.mutationIsCurrent(controller)) return;
			await live.reconcileAll(`Hiring case ${caseId} approved.`);
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
		serviceControlBlocked,
		saveConfig,
		rosterAction,
		toggleAgent,
		toggleHost,
		toggleMaster,
		selectWorker,
		validateWorkerDetailResponse,
		workforceAction,
		hiringApprove,
	};
}
