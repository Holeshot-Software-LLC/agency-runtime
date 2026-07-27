export function createConfigController(core) {
	const codexReasoningEfforts = ["low", "medium", "high", "xhigh", "max", "ultra"];
	const {
		document,
		state,
		byId,
		el,
		showNotice,
		nestedValue,
		comparable,
		api,
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
			if (privacy) {
				privacy.textContent = enabled
					? "Redacted runtime content"
					: "Runtime metadata only";
			}
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
			syncWorkforceProviderOptions([]);
			return;
		}
		select.disabled = true;
		providers.forEach((provider, index) => {
			const option = el("option", "", provider?.name || `Provider ${index + 1}`);
			option.value = String(index);
			select.append(option);
		});
		select.value = [...select.options].some((option) => option.value === selected)
			? selected
			: "0";
		syncWorkforceProviderOptions(providers);
	}

	function configuredProviders() {
		try {
			const value = JSON.parse(byId("config-providers")?.value || "[]");
			return Array.isArray(value) ? value.filter((item) => item && typeof item === "object") : [];
		} catch {
			return [];
		}
	}

	function syncWorkforceProviderOptions(providers = configuredProviders()) {
		const options = byId("workforce-provider-options");
		if (!options) return;
		options.replaceChildren();
		providers.forEach((provider) => {
			const name = typeof provider.name === "string" ? provider.name.trim() : "";
			if (!name) return;
			const option = el("option", "", name);
			option.value = name;
			options.append(option);
		});
	}

	async function discoverModels(transport, refresh) {
		const suffix = refresh ? "&refresh=true" : "";
		const catalog = await api(
			`/api/providers/models?transport=${encodeURIComponent(transport)}${suffix}`,
		);
		const models = Array.isArray(catalog?.models)
			? catalog.models.filter((model) => model && typeof model.slug === "string" && model.slug)
			: [];
		return { catalog, models };
	}

	function appendModelOptions(select, models) {
		models.forEach((model) => {
			const option = el("option", "", model.display_name || model.slug);
			option.value = model.slug;
			option.title = model.description || model.slug;
			select.append(option);
		});
	}

	async function loadWorkforceModels({ refresh = false } = {}) {
		const providerName = byId("config-workforce-provider")?.value.trim() || "";
		const providers = configuredProviders();
		const provider = providers.find(
			(item) => String(item.name || "").toLowerCase() === providerName.toLowerCase(),
		) || (!providerName ? providers[0] : null);
		const options = byId("workforce-model-options");
		const status = byId("workforce-model-status");
		if (!options || !status) return false;
		options.replaceChildren();
		if (!provider) {
			status.textContent = "Choose a configured provider to discover models.";
			return false;
		}
		const type = String(provider.type || "").toLowerCase();
		const transport = String(provider.transport || "").toLowerCase();
		if (type !== "cli" || !["codex", "claude"].includes(transport)) {
			status.textContent = type === "litellm"
				? "Enter the LiteLLM router or model-group alias in any stage model field."
				: "This provider uses manually entered model names.";
			return false;
		}
		status.textContent = `Discovering ${transport} account models…`;
		try {
			const { catalog, models } = await discoverModels(transport, refresh);
			appendModelOptions(options, models);
			status.textContent = models.length
				? `${models.length} account model${models.length === 1 ? "" : "s"} available for every workforce stage.`
				: catalog?.error || `No visible ${transport} models were found.`;
			return models.length > 0;
		} catch (error) {
			status.textContent = error.message || "Model discovery failed.";
			return false;
		}
	}

	function providerBuilderDraft() {
		const name = byId("provider-builder-name")?.value.trim() || "";
		const type = byId("provider-builder-type")?.value.trim() || "";
		const selectedModel = byId("provider-builder-model-select")?.value || "__manual__";
		const model = selectedModel === "__manual__"
			? byId("provider-builder-model")?.value.trim() || ""
			: selectedModel;
		const transport = byId("provider-builder-transport")?.value.trim() || "";
		const requestedEffort = byId("provider-builder-reasoning-effort")?.value.trim() || "";
		const reasoningEffort = type === "cli" && transport === "codex" ? requestedEffort : "";
		const baseUrl = byId("provider-builder-url")?.value.trim() || "";
		const apiKeyEnv = byId("provider-builder-env")?.value.trim() || "";
		const timeout = Number(
			byId("provider-builder-timeout")?.value || (type === "cli" ? 60 : 15),
		);
		if (!name) throw new Error("Provider name is required.");
		if (!type) throw new Error("Provider type is required.");
		if (!Number.isFinite(timeout) || timeout < 0.05 || timeout > 60) {
			throw new Error("Provider timeout must be between 0.05 and 60 seconds.");
		}
		if (type === "cli" && !["codex", "claude"].includes(transport)) {
			throw new Error("CLI providers require a Codex or Claude transport.");
		}
		if (reasoningEffort && !codexReasoningEfforts.includes(reasoningEffort)) {
			throw new Error("Codex reasoning effort is not supported.");
		}
		if (type === "litellm" && !model) {
			throw new Error("LiteLLM providers require a model or router alias.");
		}
		return {
			name,
			type,
			transport: type === "cli" ? transport : "",
			model,
			base_url: type === "cli" ? "" : baseUrl,
			api_key_env: type === "cli" ? "" : apiKeyEnv,
			ollama_mode: type === "ollama",
			timeout,
			reasoning_effort: reasoningEffort,
		};
	}

	function syncProviderReasoningEffortOptions() {
		const input = byId("provider-builder-reasoning-effort");
		const help = byId("provider-builder-reasoning-effort-help");
		if (!input) return;
		const type = byId("provider-builder-type")?.value.trim() || "";
		const transport = byId("provider-builder-transport")?.value.trim() || "";
		const selectedModel = byId("provider-builder-model-select")?.value || "__manual__";
		const available = state.providerReasoningLevels?.[selectedModel];
		const levels = Array.isArray(available) && available.length
			? available.filter((value) => codexReasoningEfforts.includes(value))
			: codexReasoningEfforts;
		const previous = input.value || "";
		input.replaceChildren();
		const defaultOption = el("option", "", "Model default");
		defaultOption.value = "";
		input.append(defaultOption);
		levels.forEach((value) => {
			const option = el("option", "", value === "xhigh" ? "Extra high" : `${value[0].toUpperCase()}${value.slice(1)}`);
			option.value = value;
			input.append(option);
		});
		const enabled = type === "cli" && transport === "codex";
		input.disabled = !enabled;
		input.value = enabled && (previous === "" || levels.includes(previous)) ? previous : "";
		if (help) {
			help.textContent = enabled
				? "Codex subscription only. Low is usually enough for compact routing plans."
				: "Reasoning effort is available for Codex subscription providers.";
		}
	}

	function syncProviderTimeoutRecommendation() {
		const type = byId("provider-builder-type")?.value.trim() || "";
		const input = byId("provider-builder-timeout");
		if (!input) return;
		const current = String(input.value || "").trim();
		if (type === "cli" && (!current || current === "15")) input.value = "60";
		if (type !== "cli" && (!current || current === "60")) input.value = "15";
	}

	async function loadProviderModels({ refresh = false } = {}) {
		const type = byId("provider-builder-type")?.value || "";
		const transport = byId("provider-builder-transport")?.value || "";
		const select = byId("provider-builder-model-select");
		const status = byId("provider-builder-model-status");
		const manual = byId("provider-builder-model");
		if (!select || !status || !manual) return false;
		select.replaceChildren();
		const manualOption = el("option", "", "Enter a model or router alias");
		manualOption.value = "__manual__";
		select.append(manualOption);
		select.value = "__manual__";
		manual.hidden = false;
		if (type !== "cli" || !transport) {
			state.providerReasoningLevels = {};
			syncProviderReasoningEffortOptions();
			status.textContent = type === "litellm"
				? "Enter the LiteLLM router or model-group alias below."
				: "Choose a CLI subscription transport to discover account models.";
			return false;
		}
		status.textContent = `Discovering ${transport} account models…`;
		try {
			const { catalog, models } = await discoverModels(transport, refresh);
			state.providerReasoningLevels = Object.fromEntries(models.map((model) => [
				model.slug,
				Array.isArray(model.supported_reasoning_levels)
					? model.supported_reasoning_levels
					: [],
			]));
			appendModelOptions(select, models);
			if (models.length) {
				select.value = models[0].slug;
				manual.hidden = true;
				status.textContent = `${models.length} account model${models.length === 1 ? "" : "s"} from ${catalog.source || transport}.`;
				syncProviderReasoningEffortOptions();
				return true;
			}
			syncProviderReasoningEffortOptions();
			status.textContent = catalog?.error || `No visible ${transport} models were found.`;
			return false;
		} catch (error) {
			state.providerReasoningLevels = {};
			syncProviderReasoningEffortOptions();
			status.textContent = error.message || "Model discovery failed.";
			return false;
		}
	}

	function syncProviderModelInput() {
		const select = byId("provider-builder-model-select");
		const manual = byId("provider-builder-model");
		if (!select || !manual) return;
		manual.hidden = select.value !== "__manual__";
		syncProviderReasoningEffortOptions();
	}

	function upsertProviderDraft() {
		const draft = providerBuilderDraft();
		const control = byId("config-providers");
		const providers = JSON.parse(control.value || "[]");
		if (!Array.isArray(providers)) throw new Error("Provider array must be a JSON list.");
		const index = providers.findIndex(
			(provider) => String(provider?.name || "").toLowerCase() === draft.name.toLowerCase(),
		);
		if (index >= 0) {
			const existing = providers[index];
			const typeChanged = String(existing.type).toLowerCase() !== draft.type;
			if (!typeChanged && existing.ollama_mode === true) draft.ollama_mode = true;
		}
		if (index < 0) providers.push(draft);
		else providers[index] = { ...providers[index], ...draft };
		control.value = JSON.stringify(providers, null, 2);
		syncProviderSecretOptions();
		updateConfigDirtyState();
		return draft;
	}

	function removeSelectedProvider() {
		const select = byId("config-provider-secret-index");
		if (!select || select.value === "") throw new Error("Select a provider to remove.");
		const control = byId("config-providers");
		const providers = JSON.parse(control.value || "[]");
		if (!Array.isArray(providers)) throw new Error("Provider array must be a JSON list.");
		providers.splice(Number(select.value), 1);
		control.value = JSON.stringify(providers, null, 2);
		syncProviderSecretOptions();
		updateConfigDirtyState();
	}

	function updateConfigDirtyState() {
		syncProviderSecretOptions();
		if (state.surfaceReadOnly === true) {
			state.configDirty = false;
			byId("config-change-count").textContent = "Read-only monitoring";
			byId("config-save-button").disabled = true;
			return;
		}
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
		syncWorkforceProviderOptions,
		loadWorkforceModels,
		providerBuilderDraft,
		syncProviderTimeoutRecommendation,
		syncProviderReasoningEffortOptions,
		loadProviderModels,
		syncProviderModelInput,
		upsertProviderDraft,
		removeSelectedProvider,
		updateConfigDirtyState,
		serviceRestartRequired,
		applyServiceBinding,
		renderConfig,
		applyConfigSnapshot,
	};
}
