import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";
import vm from "node:vm";

const CHARTS_PATH = fileURLToPath(new URL("../agency_runtime/dashboard/charts.js", import.meta.url));
const CHARTS_SOURCE = readFileSync(CHARTS_PATH, "utf8");
await import(pathToFileURL(CHARTS_PATH).href);
const AgencyCharts = globalThis.AgencyCharts;
const APP_PATH = fileURLToPath(new URL("../agency_runtime/dashboard/app.js", import.meta.url));
const APP_URL = pathToFileURL(APP_PATH).href;
const APP_CSS_PATH = fileURLToPath(new URL("../agency_runtime/dashboard/app.css", import.meta.url));
const APP_CSS_SOURCE = readFileSync(APP_CSS_PATH, "utf8");
const INDEX_PATH = fileURLToPath(new URL("../agency_runtime/dashboard/index.html", import.meta.url));
const INDEX_SOURCE = readFileSync(INDEX_PATH, "utf8");
const originalDocument = Object.getOwnPropertyDescriptor(globalThis, "document");
const originalWindow = Object.getOwnPropertyDescriptor(globalThis, "window");
const bootstrapNode = { hidden: false };
globalThis.document = {
  addEventListener() {},
  removeEventListener() {},
  getElementById() { return bootstrapNode; },
};
globalThis.window = {
  clearTimeout() {},
  setTimeout() { return 0; },
};
const { bootstrappedDashboard, createDashboard } = await import(APP_URL);
bootstrappedDashboard.destroy();
if (originalDocument) Object.defineProperty(globalThis, "document", originalDocument);
else delete globalThis.document;
if (originalWindow) Object.defineProperty(globalThis, "window", originalWindow);
else delete globalThis.window;

const NOW = Date.parse("2026-07-11T12:00:30.500Z");
const isoBefore = (milliseconds) => new Date(NOW - milliseconds).toISOString();

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

function jsonResponse(status, payload) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: () => null },
    json: async () => payload,
  };
}

function verifiedHost(host = "codex", capabilities = ["repository-read", "test-execution"]) {
  return {
    effective_enabled: true,
    enabled: true,
    executable_discovered: true,
    host,
    inspection_status: "complete",
    registered: true,
    runtime_enabled: true,
    execution_capabilities: {
      capabilities,
      contract_version: "1",
      evidence: [`native-inventory-verified:${host}`],
      execution_host: host,
      inference_surface: "",
      platform: "windows",
      source: "native-installation-evidence",
      status: "native-installation-verified",
      surface: host,
      unknown_tools: [],
    },
  };
}

class FakeClassList {
  constructor() {
    this.values = new Set();
  }

  toggle(name, force) {
    const enabled = force === undefined ? !this.values.has(name) : Boolean(force);
    if (enabled) this.values.add(name);
    else this.values.delete(name);
    return enabled;
  }

  contains(name) {
    return this.values.has(name);
  }

  add(name) {
    this.values.add(name);
  }

  remove(name) {
    this.values.delete(name);
  }
}

class FakeNode {
  constructor(id = "") {
    this.id = id;
    this.attributes = new Map();
    this.classList = new FakeClassList();
    this.children = [];
    this.checked = false;
    this.className = "";
    this.closestNode = null;
    this.dataset = {};
    this.disabled = false;
    this.focusCount = 0;
    this.hidden = false;
    this.isConnected = true;
    this.listeners = new Map();
    this.labels = [];
    this.offsetWidth = 1;
    this.parentElement = null;
    this.queryNodes = [];
    this.tabIndex = 0;
    this.textContent = "";
    this.type = "";
    this.value = "";
    this.validationMessage = "";
  }

  addEventListener(name, listener) {
    const listeners = this.listeners.get(name) || [];
    listeners.push(listener);
    this.listeners.set(name, listeners);
  }

  removeEventListener(name, listener) {
    const listeners = this.listeners.get(name) || [];
    this.listeners.set(name, listeners.filter((candidate) => candidate !== listener));
  }

  append(...children) {
    this.children.push(...children);
  }

  get options() {
    return this.children;
  }

  closest() {
    return this.closestNode;
  }

  focus() { this.focusCount += 1; }

  getAttribute(name) {
    return this.attributes.get(name) ?? null;
  }

  querySelectorAll() {
    return this.queryNodes;
  }

  removeAttribute(name) {
    this.attributes.delete(name);
  }

  replaceChildren(...children) {
    this.children = [...children];
  }

  setAttribute(name, value) {
    this.attributes.set(name, String(value));
  }

  setCustomValidity(message) {
    this.validationMessage = String(message);
  }
}

class FakeSvgNode {
  constructor(tag) {
    this.tag = tag;
    this.attributes = new Map();
    this.children = [];
    this.dataset = {};
    this.textContent = "";
  }

  append(...children) { this.children.push(...children); }
  setAttribute(name, value) { this.attributes.set(name, String(value)); }
  replaceChildren(...children) { this.children = [...children]; }
}

function svgHarness() {
  const documentRef = { createElementNS: (_namespace, tag) => new FakeSvgNode(tag) };
  const root = new FakeSvgNode("root");
  root.ownerDocument = documentRef;
  return root;
}

function descendants(root) {
  const nodes = [];
  const visit = (node) => {
    nodes.push(node);
    node.children?.forEach(visit);
  };
  visit(root);
  return nodes;
}

function createAppHarness(fetchImpl) {
  let nextTimerId = 1;
  const timerTasks = new Map();
  const nodes = new Map();
  const documentListeners = new Map();
  const historyCalls = [];
  const missingIds = new Set();
  const sessionValues = new Map();
  const windowListeners = new Map();
  const selectorNodes = new Map();
  const node = (id) => {
    if (!nodes.has(id)) nodes.set(id, new FakeNode(id));
    return nodes.get(id);
  };
  const addListener = (registry, name, listener) => {
    const listeners = registry.get(name) || [];
    listeners.push(listener);
    registry.set(name, listeners);
  };
  const removeListener = (registry, name, listener) => {
    const listeners = registry.get(name) || [];
    registry.set(name, listeners.filter((candidate) => candidate !== listener));
  };
  const timers = {
    tasks: timerTasks,
    set(callback, delay = 0) {
      const id = nextTimerId;
      nextTimerId += 1;
      timerTasks.set(id, { callback, delay: Number(delay) });
      return id;
    },
    clear(id) {
      timerTasks.delete(id);
    },
  };
  const document = {
    activeElement: null,
    visibilityState: "visible",
    addEventListener: (name, listener) => addListener(documentListeners, name, listener),
    removeEventListener: (name, listener) => removeListener(documentListeners, name, listener),
    createElement: (tag) => new FakeNode(tag),
    getElementById: (id) => (missingIds.has(id) ? null : node(id)),
    querySelector: (selector) => {
      if (selector === ".rail-foot") return node("rail-foot");
      if (selector === ".shell") return node("shell");
      if (selectorNodes.has(selector)) return selectorNodes.get(selector)[0] || null;
      return null;
    },
    querySelectorAll: (selector) => selectorNodes.get(selector) || [],
  };
  const HTMLElement = FakeNode;
  class HTMLInputElement extends FakeNode {}
  const window = {
    location: { hash: "", pathname: "/" },
    addEventListener: (name, listener) => addListener(windowListeners, name, listener),
    removeEventListener: (name, listener) => removeListener(windowListeners, name, listener),
    clearTimeout: (id) => timers.clear(id),
    setTimeout: (callback, delay) => timers.set(callback, delay),
  };
  const context = {
    AbortController,
    AgencyCharts,
    DOMException,
    HTMLElement,
    HTMLInputElement,
    URLSearchParams,
    console,
    document,
    fetch: fetchImpl,
    history: { replaceState: (...args) => historyCalls.push(args) },
    sessionStorage: {
      getItem: (key) => sessionValues.get(key) ?? null,
      setItem: (key, value) => sessionValues.set(key, String(value)),
    },
    window,
  };
  const api = createDashboard(context);
  return {
    api,
    context,
    document,
    documentListeners,
    historyCalls,
    HTMLInputElement,
    node,
    nodes,
    missing(id) { missingIds.add(id); },
    sessionValues,
    select(selector, values) { selectorNodes.set(selector, values); },
    timers,
    windowListeners,
  };
}

test("app.js accepts a token fragment that arrives after initial page load", () => {
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });

  harness.context.window.location.hash = "#token=late-token";
  harness.api.installToken();

  assert.equal(harness.api.state.token, "late-token");
  assert.equal(harness.sessionValues.get("agency-dashboard-token"), "late-token");
  assert.equal(harness.historyCalls.length, 1);
});

test("app.js API requests keep credentials in-memory and fail closed on malformed errors", async () => {
  const calls = [];
  const harness = createAppHarness(async (path, options) => {
    calls.push({ path, options });
    if (path === "/malformed") {
      return {
        ok: false,
        status: 503,
        headers: { get: (name) => (name === "Retry-After" ? "7" : null) },
        json: async () => { throw new Error("not JSON"); },
      };
    }
    return jsonResponse(200, { ok: true });
  });
  harness.api.state.token = "fragment-only-secret";

  assert.equal((await harness.api.api("/ok", {
    body: "{}",
    headers: { "X-Request-ID": "test-request" },
    method: "POST",
  })).ok, true);
  assert.equal(calls[0].options.headers.Authorization, "Bearer fragment-only-secret");
  assert.equal(calls[0].options.headers["Content-Type"], "application/json");
  assert.equal(calls[0].options.headers["X-Request-ID"], "test-request");
  assert.equal(calls[0].options.cache, "no-store");
  assert.equal(calls[0].options.credentials, "omit");

  await assert.rejects(
    harness.api.api("/malformed"),
    (error) => error.name === "APIError"
      && error.status === 503
      && error.retryAfter === "7"
      && error.message === "HTTP 503",
  );
});

test("app.js typed confirmations trap focus and reject incorrect phrases", async () => {
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  const returnFocus = new FakeNode("return-focus");
  const first = new FakeNode("first");
  const last = new FakeNode("last");
  harness.document.activeElement = returnFocus;
  harness.node("confirmation-modal").queryNodes = [first, last];

  const rejected = harness.api.requestConfirmation("SAVE CONFIG", "Review this change.");
  assert.equal(harness.node("shell").inert, true);
  harness.node("confirmation-input").value = "save config";
  harness.api.finishConfirmation(true);
  assert.notEqual(harness.api.state.confirmation, null);
  assert.equal(harness.node("confirmation-error").hidden, false);

  harness.document.activeElement = first;
  let trapped = false;
  harness.api.handleModalKeyboard({
    key: "Tab",
    preventDefault() { trapped = true; },
    shiftKey: true,
  });
  assert.equal(trapped, true);
  assert.equal(last.focusCount, 1);

  let escaped = false;
  harness.api.handleModalKeyboard({
    key: "Escape",
    preventDefault() { escaped = true; },
  });
  assert.equal(escaped, true);
  assert.equal(await rejected, false);
  assert.equal(harness.node("shell").inert, false);

  harness.document.activeElement = returnFocus;
  const accepted = harness.api.requestConfirmation("ENABLE HOST", "Enable it.");
  harness.node("confirmation-input").value = "ENABLE HOST";
  harness.api.finishConfirmation(true);
  assert.equal(await accepted, true);
  assert.equal(returnFocus.focusCount, 2);
});

test("app.js renders provider configuration without reflecting stored API keys", () => {
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  const providers = new FakeNode("config-providers");
  providers.dataset.configPath = "providers";
  providers.dataset.valueType = "json";
  providers.labels = [{ textContent: "Providers" }];
  harness.nodes.set("config-providers", providers);
  harness.select("[data-config-path]", [providers]);

  harness.api.renderConfig({
    effective: {
      providers: [{ api_key: "must-not-reach-the-dom", name: "primary", weight: 2 }],
    },
    environment_overrides: { "judge.model": "AGENCY_JUDGE_MODEL" },
    path: "C:/safe/config.yaml",
    revision: "1234567890abcdef",
  });

  assert.equal(providers.value.includes("must-not-reach-the-dom"), false);
  assert.deepEqual(JSON.parse(providers.value), [{ name: "primary", weight: 2 }]);
  assert.equal(harness.node("config-provider-secret-index").disabled, false);
  assert.equal(harness.node("config-provider-secret-index").value, "0");
  assert.equal(harness.node("config-override-count").textContent, "1 ENV OVERRIDE");
  assert.equal(harness.node("config-revision").textContent, "1234567890");

  harness.node("config-provider-secret").value = "replacement-secret";
  const operations = harness.api.collectConfigChanges();
  assert.equal(operations.length, 1);
  assert.equal(operations[0].op, "secret");
  assert.equal(operations[0].path, "providers.0.api_key");
  assert.equal(operations[0].action, "replace");
  assert.equal(operations[0].value, "replacement-secret");

  assert.deepEqual(
    [...harness.api.requiredConfigConfirmations([
      operations[0],
      { op: "set", path: "profile", value: "local-only" },
      { op: "set", path: "observability.capture_content", value: true },
    ])],
    [
      "SAVE CONFIG",
      "SAVE SENSITIVE CONFIG",
      "APPLY LOCAL-ONLY PROFILE",
      "ENABLE CONTENT CAPTURE",
    ],
  );
  assert.throws(
    () => harness.api.appendSecretOperation([], "judge.api_key", "new", true),
    /either a new value or clear/i,
  );
});

test("provider builder exposes and stages a LiteLLM router alias", () => {
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  const providers = new FakeNode("config-providers");
  providers.dataset.configPath = "providers";
  providers.dataset.valueType = "json";
  providers.labels = [{ textContent: "Providers" }];
  providers.value = "[]";
  harness.nodes.set("config-providers", providers);
  harness.select("[data-config-path]", [providers]);
  harness.api.state.configBaseline = new Map([["providers", JSON.stringify([])]]);

  harness.node("provider-builder-name").value = "agency-router";
  harness.node("provider-builder-type").value = "litellm";
  harness.node("provider-builder-model").value = "task-agency-router";
  harness.node("provider-builder-transport").value = "";
  harness.node("provider-builder-url").value = "http://127.0.0.1:4000/v1";
  harness.node("provider-builder-env").value = "LITELLM_API_KEY";
  harness.node("provider-builder-timeout").value = "15";

  const provider = harness.api.upsertProviderDraft();

  assert.equal(provider.model, "task-agency-router");
  assert.deepEqual(JSON.parse(providers.value), [{
    name: "agency-router",
    type: "litellm",
    transport: "",
    model: "task-agency-router",
    base_url: "http://127.0.0.1:4000/v1",
    api_key_env: "LITELLM_API_KEY",
    ollama_mode: false,
    timeout: 15,
  }]);
  assert.equal(harness.node("config-provider-secret-index").value, "0");
  assert.equal(harness.node("config-save-button").disabled, false);
});

test("provider builder discovers signed-in Codex models and keeps manual fallback", async () => {
  const calls = [];
  const harness = createAppHarness(async (path) => {
    calls.push(path);
    return jsonResponse(200, {
      transport: "codex",
      source: "codex-cli",
      models: [
        { slug: "gpt-cheap", display_name: "Cheap", description: "Low cost" },
        { slug: "gpt-frontier", display_name: "Frontier", description: "Deep work" },
      ],
    });
  });
  harness.node("provider-builder-type").value = "cli";
  harness.node("provider-builder-transport").value = "codex";
  assert.equal(await harness.api.loadProviderModels({ refresh: true }), true);
  assert.equal(calls[0], "/api/providers/models?transport=codex&refresh=true");
  assert.equal(harness.node("provider-builder-model-select").value, "gpt-cheap");
  assert.equal(harness.node("provider-builder-model").hidden, true);
  assert.match(harness.node("provider-builder-model-status").textContent, /2 account models/);
  harness.node("provider-builder-model-select").value = "__manual__";
  harness.api.syncProviderModelInput();
  assert.equal(harness.node("provider-builder-model").hidden, false);
});

test("provider builder validates, updates, removes, and reports discovery fallbacks", async () => {
  const harness = createAppHarness(async () => jsonResponse(200, {
    transport: "codex",
    models: [null, { slug: 7 }, { slug: "" }],
    error: "No account models",
  }));
  const providers = new FakeNode("config-providers");
  providers.dataset.configPath = "providers";
  providers.dataset.valueType = "json";
  providers.labels = [{ textContent: "Providers" }];
  providers.value = JSON.stringify([{ name: "existing", timeout: 1 }]);
  harness.nodes.set("config-providers", providers);
  harness.select("[data-config-path]", [providers]);
  harness.api.state.configBaseline = new Map([["providers", providers.value]]);

  const builder = (values) => {
    harness.node("provider-builder-name").value = values.name ?? "provider";
    harness.node("provider-builder-type").value = values.type ?? "http";
    harness.node("provider-builder-model").value = values.model ?? "model";
    harness.node("provider-builder-model-select").value = "__manual__";
    harness.node("provider-builder-transport").value = values.transport ?? "";
    harness.node("provider-builder-timeout").value = values.timeout ?? "15";
  };
  builder({ timeout: "0" });
  assert.throws(() => harness.api.providerBuilderDraft(), /between 0.05 and 60/i);
  builder({ type: "cli", transport: "other" });
  assert.throws(() => harness.api.providerBuilderDraft(), /Codex or Claude/i);
  builder({ type: "cli", transport: "codex" });
  harness.node("provider-builder-url").value = "https://stale.example.test";
  harness.node("provider-builder-env").value = "STALE_API_KEY";
  const cliDraft = harness.api.providerBuilderDraft();
  assert.equal(cliDraft.base_url, "");
  assert.equal(cliDraft.api_key_env, "");
  builder({ type: "litellm", model: "" });
  assert.throws(() => harness.api.providerBuilderDraft(), /model or router alias/i);

  harness.node("provider-builder-type").value = "litellm";
  assert.equal(await harness.api.loadProviderModels(), false);
  assert.match(harness.node("provider-builder-model-status").textContent, /LiteLLM router/i);
  harness.node("provider-builder-type").value = "http";
  assert.equal(await harness.api.loadProviderModels(), false);
  assert.match(harness.node("provider-builder-model-status").textContent, /CLI subscription/i);
  harness.node("provider-builder-type").value = "cli";
  harness.node("provider-builder-transport").value = "codex";
  assert.equal(await harness.api.loadProviderModels(), false);
  assert.equal(harness.node("provider-builder-model-status").textContent, "No account models");

  builder({ name: "existing", type: "http", timeout: "12" });
  harness.api.upsertProviderDraft();
  assert.equal(JSON.parse(providers.value)[0].timeout, 12);
  harness.api.syncProviderSecretOptions();
  harness.node("config-provider-secret-index").value = "0";
  harness.api.removeSelectedProvider();
  assert.deepEqual(JSON.parse(providers.value), []);
  harness.node("config-provider-secret-index").value = "";
  assert.throws(() => harness.api.removeSelectedProvider(), /select a provider/i);

  const failed = createAppHarness(async () => jsonResponse(500, { error: "catalog offline" }));
  failed.node("provider-builder-type").value = "cli";
  failed.node("provider-builder-transport").value = "codex";
  assert.equal(await failed.api.loadProviderModels(), false);
  assert.match(failed.node("provider-builder-model-status").textContent, /catalog offline/i);
});

test("bound provider staging controls report successful and rejected edits", async () => {
  const harness = createAppHarness(() => { throw new Error("no fetch expected"); });
  const providers = new FakeNode("config-providers");
  providers.dataset.configPath = "providers";
  providers.dataset.valueType = "json";
  providers.labels = [{ textContent: "Providers" }];
  providers.value = "[]";
  harness.nodes.set("config-providers", providers);
  harness.select("[data-config-path]", [providers]);
  harness.api.state.configBaseline = new Map([["providers", "[]"]]);
  harness.node("provider-builder-name").value = "primary";
  harness.node("provider-builder-type").value = "http";
  harness.node("provider-builder-timeout").value = "15";
  harness.api.bindEvents();

  harness.node("provider-builder-save").listeners.get("click")[0]();
  assert.match(harness.node("notice").textContent, /Provider primary staged/i);
  harness.node("provider-builder-name").value = "";
  harness.node("provider-builder-save").listeners.get("click")[0]();
  assert.match(harness.node("notice").textContent, /name is required/i);

  harness.api.syncProviderSecretOptions();
  harness.node("config-provider-secret-index").value = "0";
  harness.node("provider-builder-remove").listeners.get("click")[0]();
  assert.match(harness.node("notice").textContent, /removal staged/i);
  harness.node("config-provider-secret-index").value = "";
  harness.node("provider-builder-remove").listeners.get("click")[0]();
  assert.match(harness.node("notice").textContent, /select a provider/i);
  harness.node("provider-builder-type").listeners.get("change")[0]();
  harness.node("provider-builder-transport").listeners.get("change")[0]();
  harness.node("provider-builder-model-select").listeners.get("change")[0]();
  harness.node("provider-builder-model-refresh").listeners.get("click")[0]();
  await Promise.resolve();
});

test("provider configuration defensive branches stay bounded", async () => {
  const missingName = createAppHarness(() => { throw new Error("no fetch"); });
  missingName.missing("provider-builder-name");
  assert.throws(() => missingName.api.providerBuilderDraft(), /name is required/i);
  const missingType = createAppHarness(() => { throw new Error("no fetch"); });
  missingType.node("provider-builder-name").value = "provider";
  missingType.missing("provider-builder-type");
  assert.throws(() => missingType.api.providerBuilderDraft(), /type is required/i);

  const sparse = createAppHarness(() => { throw new Error("no fetch"); });
  sparse.node("provider-builder-name").value = "sparse";
  sparse.node("provider-builder-type").value = "ollama";
  for (const id of [
    "provider-builder-model-select",
    "provider-builder-model",
    "provider-builder-transport",
    "provider-builder-url",
    "provider-builder-env",
    "provider-builder-timeout",
  ]) sparse.missing(id);
  const sparseDraft = sparse.api.providerBuilderDraft();
  assert.equal(sparseDraft.model, "");
  assert.equal(sparseDraft.timeout, 15);
  assert.equal(sparseDraft.ollama_mode, true);

  const selected = createAppHarness(() => { throw new Error("no fetch"); });
  selected.node("provider-builder-name").value = "selected";
  selected.node("provider-builder-type").value = "cli";
  selected.node("provider-builder-transport").value = "claude";
  selected.node("provider-builder-model-select").value = "account-model";
  selected.node("provider-builder-timeout").value = "61";
  assert.throws(() => selected.api.providerBuilderDraft(), /between 0.05 and 60/i);
  selected.node("provider-builder-timeout").value = "not-a-number";
  assert.throws(() => selected.api.providerBuilderDraft(), /between 0.05 and 60/i);
  selected.node("provider-builder-timeout").value = "10";
  assert.equal(selected.api.providerBuilderDraft().model, "account-model");

  for (const id of [
    "provider-builder-model-select",
    "provider-builder-model-status",
    "provider-builder-model",
  ]) {
    const absent = createAppHarness(() => { throw new Error("no fetch"); });
    absent.missing(id);
    assert.equal(await absent.api.loadProviderModels(), false);
  }
  const noTransport = createAppHarness(() => { throw new Error("no fetch"); });
  noTransport.node("provider-builder-type").value = "cli";
  noTransport.missing("provider-builder-transport");
  assert.equal(await noTransport.api.loadProviderModels(), false);

  const emptyCatalog = createAppHarness(async () => jsonResponse(200, null));
  emptyCatalog.node("provider-builder-type").value = "cli";
  emptyCatalog.node("provider-builder-transport").value = "codex";
  assert.equal(await emptyCatalog.api.loadProviderModels(), false);
  assert.match(emptyCatalog.node("provider-builder-model-status").textContent, /No visible/i);

  const singular = createAppHarness(async () => jsonResponse(200, {
    models: [{ slug: "solo" }],
  }));
  singular.node("provider-builder-type").value = "cli";
  singular.node("provider-builder-transport").value = "codex";
  assert.equal(await singular.api.loadProviderModels(), true);
  assert.match(singular.node("provider-builder-model-status").textContent, /1 account model from codex/i);
  assert.equal(singular.node("provider-builder-model-select").options[1].title, "solo");

  const broken = createAppHarness(async () => { throw new Error(""); });
  broken.node("provider-builder-type").value = "cli";
  broken.node("provider-builder-transport").value = "codex";
  assert.equal(await broken.api.loadProviderModels(), false);
  assert.equal(broken.node("provider-builder-model-status").textContent, "Model discovery failed.");

  const invalidProviders = createAppHarness(() => { throw new Error("no fetch"); });
  invalidProviders.node("provider-builder-name").value = "provider";
  invalidProviders.node("provider-builder-type").value = "http";
  invalidProviders.node("config-providers").value = "{}";
  assert.throws(() => invalidProviders.api.upsertProviderDraft(), /JSON list/i);
  invalidProviders.node("config-provider-secret-index").value = "0";
  assert.throws(() => invalidProviders.api.removeSelectedProvider(), /JSON list/i);

  const emptyProviders = createAppHarness(() => { throw new Error("no fetch"); });
  emptyProviders.node("provider-builder-name").value = "provider";
  emptyProviders.node("provider-builder-type").value = "http";
  emptyProviders.node("config-providers").value = "";
  assert.equal(emptyProviders.api.upsertProviderDraft().name, "provider");
  emptyProviders.node("config-providers").value = JSON.stringify([{}]);
  emptyProviders.node("provider-builder-name").value = "different";
  emptyProviders.api.upsertProviderDraft();
  assert.equal(JSON.parse(emptyProviders.node("config-providers").value).length, 2);

  const missingSelect = createAppHarness(() => { throw new Error("no fetch"); });
  missingSelect.missing("config-provider-secret-index");
  assert.throws(() => missingSelect.api.removeSelectedProvider(), /select a provider/i);
  const emptyRemove = createAppHarness(() => { throw new Error("no fetch"); });
  emptyRemove.node("config-provider-secret-index").value = "0";
  emptyRemove.node("config-providers").value = "";
  emptyRemove.api.removeSelectedProvider();
  assert.equal(emptyRemove.node("config-providers").value, "[]");
  const missingModelSelect = createAppHarness(() => { throw new Error("no fetch"); });
  missingModelSelect.missing("provider-builder-model-select");
  missingModelSelect.api.syncProviderModelInput();
  const missingManual = createAppHarness(() => { throw new Error("no fetch"); });
  missingManual.missing("provider-builder-model");
  missingManual.api.syncProviderModelInput();
});

test("app.js config controls normalize typed values and preserve dirty edits on refresh", () => {
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  const booleanControl = new FakeNode("boolean");
  booleanControl.checked = true;
  booleanControl.dataset.valueType = "boolean";
  const integerControl = new FakeNode("integer");
  integerControl.dataset.valueType = "integer";
  integerControl.labels = [{ textContent: "Worker count" }];
  integerControl.value = "12";
  const numberControl = new FakeNode("number");
  numberControl.dataset.valueType = "number";
  numberControl.value = "0.75";
  const nullableControl = new FakeNode("nullable");
  nullableControl.dataset.nullable = "true";
  nullableControl.value = "  ";

  assert.equal(harness.api.readConfigControl(booleanControl), true);
  assert.equal(harness.api.readConfigControl(integerControl), 12);
  assert.equal(harness.api.readConfigControl(numberControl), 0.75);
  assert.equal(harness.api.readConfigControl(nullableControl), null);
  integerControl.value = "1.5";
  assert.throws(() => harness.api.readConfigControl(integerControl), /must be an integer/i);
  numberControl.value = "Infinity";
  assert.throws(() => harness.api.readConfigControl(numberControl), /finite number/i);

  harness.api.state.activeView = "overview";
  assert.equal(harness.api.applyConfigSnapshot({ revision: "pending", effective: {} }), false);
  assert.equal(harness.api.state.config.revision, "pending");
  assert.equal(harness.api.state.pendingConfig.revision, "pending");

  harness.api.state.activeView = "settings";
  harness.api.state.config = { revision: "old" };
  harness.api.state.configDirty = true;
  assert.equal(harness.api.applyConfigSnapshot({ revision: "new", effective: {} }), false);
  assert.equal(harness.api.state.pendingConfig.revision, "new");
  assert.match(harness.node("notice").textContent, /changed outside this dashboard/i);

  harness.api.state.configDirty = false;
  assert.equal(
    harness.api.applyConfigSnapshot({ revision: "forced", effective: {} }, { force: true }),
    true,
  );
  assert.equal(harness.api.state.config.revision, "forced");
});

test("config snapshots keep effective privacy and retention summaries current", () => {
  const harness = createAppHarness(() => {
    throw new Error("summary projection does not fetch");
  });
  harness.api.state.activeView = "overview";

  assert.equal(harness.api.applyConfigSnapshot({
    effective: { observability: { capture_content: true, retention_days: 45 } },
    revision: "summary-current",
  }), false);
  assert.equal(harness.api.state.overview.capture_content, true);
  assert.equal(harness.api.state.overview.retention_days, 45);
  assert.equal(harness.node("setting-capture").textContent, "Opt-in enabled");
  assert.equal(harness.node("setting-retention").textContent, "45 days");
  assert.equal(harness.node("privacy-chip").textContent, "Redacted content");

  harness.api.state.activeView = "settings";
  harness.api.state.config = { revision: "editor-old" };
  harness.api.state.configDirty = true;
  assert.equal(harness.api.applyConfigSnapshot({
    effective: { observability: { capture_content: false, retention_days: 60 } },
    revision: "external-new",
  }), false);
  assert.equal(harness.api.state.config.revision, "editor-old");
  assert.equal(harness.api.state.pendingConfig.revision, "external-new");
  assert.equal(harness.api.state.overview.capture_content, false);
  assert.equal(harness.api.state.overview.retention_days, 60);
  assert.equal(harness.node("setting-capture").textContent, "Disabled");
  assert.equal(harness.node("setting-retention").textContent, "60 days");
  assert.equal(harness.node("privacy-chip").textContent, "Metadata only");
});

test("app.js host and formatting helpers distinguish unknown, stale, and installed states", () => {
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  assert.equal(harness.api.formatBytes(512), "512 B");
  assert.equal(harness.api.formatBytes(1536), "1.5 KB");
  assert.equal(harness.api.formatBytes(2 * (1024 ** 2)), "2.0 MB");
  assert.equal(harness.api.formatTime(null), "—");
  assert.equal(harness.api.formatTime("invalid-time"), "invalid-time");
  assert.equal(harness.api.hostState({ runtime_enabled: false }), "runtime-disabled");
  assert.equal(harness.api.hostState({ inspection_status: "stale" }), "inspection-stale");
  assert.equal(harness.api.hostState({ discovered: true }), "host-discovered");
  assert.equal(harness.api.hostState({}), "absent");
  assert.equal(harness.api.hostLocation({ executable: "/usr/bin/codex" }), "/usr/bin/codex");
  assert.equal(
    harness.api.hostLocation({ native_root: "/safe/plugin", native_root_exists: true }),
    "/safe/plugin",
  );
  assert.equal(
    harness.api.hostLocation({ current_native_root: true }),
    "Current native payload detected",
  );
  assert.equal(harness.api.hostLocation({}), "Not discovered");
  assert.equal(harness.api.truthLabel(true, "yes", "no", "unknown"), "yes");
  assert.equal(harness.api.truthLabel(false, "yes", "no", "unknown"), "no");
  assert.equal(harness.api.truthLabel(null, "yes", "no", "unknown"), "unknown");
});

test("host views disclose empty inventories and unknown runtime controls truthfully", () => {
  const harness = createAppHarness(() => {
    throw new Error("render-only test does not fetch");
  });
  harness.api.state.overview = { status: "ok", recent: {} };
  harness.api.state.activity = {};
  harness.api.state.hosts = [];

  harness.api.renderOverview();
  assert.match(
    harness.node("overview-hosts").children[0].textContent,
    /no supported agent hosts were found/i,
  );
  harness.api.renderHosts();
  assert.match(
    harness.node("host-grid").children[0].textContent,
    /install or register a host, then refresh/i,
  );

  harness.api.state.hosts = [{
    hook_trust_action: "Run /hooks, then verify activation.",
    host: "codex",
    maturity: "activation-required",
  }];
  harness.api.renderHosts();
  const labels = descendants(harness.node("host-grid")).map((node) => node.textContent);
  assert.ok(labels.includes("runtime state unknown"));
  assert.equal(labels.includes("runtime on"), false);
  assert.ok(labels.includes("Run /hooks, then verify activation."));
});

test("Route Lab offers only verified enabled execution hosts and preserves explicit choice", () => {
  const missing = createAppHarness(() => {
    throw new Error("missing optional Route Lab controls do not fetch");
  });
  missing.missing("route-host");
  assert.equal(missing.api.renderRouteHosts(), "");

  const harness = createAppHarness(() => {
    throw new Error("host rendering does not fetch");
  });
  harness.api.state.master = { enabled: true, generation: 1 };

  assert.equal(harness.api.renderRouteHosts(), "");
  assert.equal(harness.node("route-host").disabled, true);
  assert.equal(harness.node("route-button").disabled, true);
  assert.match(harness.node("route-host-help").textContent, /no current native installation/i);

  harness.api.state.hosts = [
    null,
    {
      effective_enabled: true,
      host: "codex",
      execution_capabilities: {
        capabilities: ["repository-read"],
        execution_host: "codex",
        status: "native-evidence-unproven",
      },
    },
    verifiedHost("claude", ["repository-read"]),
    verifiedHost("claude", ["duplicate-must-not-replace"]),
    verifiedHost("openclaw", ["repository-read", "native-delegation"]),
    verifiedHost("unknown"),
    {
      effective_enabled: true,
      host: "hermes",
      execution_capabilities: {
        capabilities: "not-a-list",
        execution_host: "hermes",
        status: "native-installation-verified",
      },
    },
  ];
  assert.equal(harness.api.renderRouteHosts(), "claude");
  assert.deepEqual(
    harness.node("route-host").children.map((option) => option.value),
    ["claude", "openclaw"],
  );
  assert.equal(harness.node("route-host").disabled, false);
  assert.equal(harness.node("route-button").disabled, false);
  assert.match(harness.node("route-host-help").textContent, /choose the current native host/i);

  harness.node("route-host").value = "openclaw";
  assert.equal(harness.api.renderRouteHosts(), "openclaw");
  assert.match(harness.node("route-button").title, /openclaw/i);

  harness.node("route-button").setAttribute("aria-busy", "true");
  harness.node("route-button").disabled = true;
  assert.equal(harness.api.renderRouteHosts(), "openclaw");
  assert.equal(harness.node("route-button").disabled, true);

  const optional = createAppHarness(() => {
    throw new Error("missing optional Route Lab labels do not fetch");
  });
  optional.missing("route-host-help");
  optional.missing("route-button");
  optional.api.state.master = { enabled: true, generation: 1 };
  optional.api.state.hosts = [verifiedHost("codex")];
  assert.equal(optional.api.renderRouteHosts(), "codex");
});

test("Route Lab renders authoritative host evidence and bounded eligibility rejections", () => {
  const harness = createAppHarness(() => {
    throw new Error("receipt rendering does not fetch");
  });
  harness.api.renderReceipt({
    delegation_graph: { edges: [], nodes: [] },
    eligibility: {
      capability_status: "native-installation-verified",
      eligible_count: 17,
      execution_host: "codex",
      rejection_count: 2,
      rejections: [
        { slug: "browser-specialist", reason: "missing_capabilities:browser-automation" },
        { slug: "linux-specialist", reason: "unsupported_tool_platform:windows" },
      ],
      truncated: true,
    },
    host_capability_receipt: {
      capabilities: ["repository-read", "test-execution"],
      execution_host: "codex",
      status: "native-installation-verified",
    },
    selected: [],
    signals: { selection: { status: "abstained" } },
  });

  const text = descendants(harness.node("route-result")).map((node) => node.textContent);
  assert.ok(text.includes("codex"));
  assert.ok(text.some((value) => /17 eligible · 2 rejected · bounded view/i.test(value)));
  assert.ok(text.some((value) => /browser-specialist: missing_capabilities/i.test(value)));
  assert.equal(harness.node("route-status").textContent, "ABSTAINED");

  harness.api.renderReceipt({
    delegation_graph: { edges: [], nodes: [] },
    eligibility: {
      eligible_count: 0,
      execution_host: "codex",
      rejection_count: 0,
      rejections: [],
      truncated: false,
    },
    host_capability_receipt: {
      execution_host: "codex",
      status: "native-installation-verified",
    },
    selected: [],
    signals: { selection: { status: "abstained" } },
  });
  const emptyText = descendants(harness.node("route-result")).map((node) => node.textContent);
  assert.ok(emptyText.includes("0 eligible · 0 rejected"));
  assert.ok(emptyText.includes("native-installation-verified · 0 capabilities"));
  assert.ok(emptyText.includes("none: none"));
});

test("bucketActivity returns a bounded empty series for absent or malformed data", () => {
  for (const activity of [undefined, null, {}, { routing: "bad", delegations: 42 }]) {
    const buckets = AgencyCharts.bucketActivity(activity, { now: NOW });
    assert.equal(buckets.length, 24);
    assert.ok(buckets.every((bucket) => bucket.routes === 0));
    assert.ok(buckets.every((bucket) => bucket.delegations === 0));
    assert.ok(buckets.every((bucket) => Number.isFinite(bucket.startMs)));
    assert.ok(buckets.every((bucket) => bucket.endMs > bucket.startMs));
  }

  assert.equal(
    AgencyCharts.bucketActivity({}, { now: NOW, bucketCount: 500 }).length,
    48,
  );
  const minimumWidth = AgencyCharts.bucketActivity(
    {},
    { now: NOW, bucketCount: 2, bucketMs: 1 },
  );
  assert.equal(minimumWidth[0].endMs - minimumWidth[0].startMs, 10_000);
});

test("charts.js preserves its legacy global fallback without weakening CommonJS exports", () => {
  const sandbox = { exports: {}, globalThis: undefined, module: { exports: {} } };
  vm.createContext(sandbox);
  new vm.Script(CHARTS_SOURCE, { filename: CHARTS_PATH }).runInContext(sandbox);

  assert.equal(typeof sandbox.module.exports.bucketActivity, "function");
  assert.equal(sandbox.AgencyCharts, sandbox.module.exports);
});

test("bucketActivity falls back safely for missing clocks and non-finite numeric timestamps", () => {
  const implicitNow = AgencyCharts.bucketActivity();
  assert.equal(implicitNow.length, 24);
  assert.ok(implicitNow.every((bucket) => Number.isFinite(bucket.startMs)));

  const invalidNow = AgencyCharts.bucketActivity({
    routing: [{ created_at: "" }, { created_at: Number.POSITIVE_INFINITY }],
  }, {
    now: Number.POSITIVE_INFINITY,
    bucketCount: 1,
    bucketMs: 10_000,
  });
  assert.equal(invalidNow.length, 1);
  assert.equal(invalidNow[0].routes, 0);
  assert.ok(Number.isFinite(invalidNow[0].startMs));
});

test("bucketActivity counts only valid in-window routing and delegation timestamps", () => {
  const activity = {
    routing: [
      { created_at: isoBefore(30_000) },
      { created_at: isoBefore(90_000) },
      { created_at: isoBefore(300_000) },
      { created_at: new Date(NOW + 1).toISOString() },
      { created_at: "not-a-date" },
      null,
    ],
    delegations: [
      { completed_at: isoBefore(15_000), started_at: "ignored" },
      { started_at: isoBefore(70_000) },
      { completed_at: "not-a-date", started_at: isoBefore(20_000) },
      { started_at: new Date(NOW + 60_000).toISOString() },
      {},
    ],
  };

  const buckets = AgencyCharts.bucketActivity(activity, {
    now: new Date(NOW),
    bucketCount: 4,
    bucketMs: 60_000,
  });

  assert.equal(buckets.length, 4);
  assert.equal(buckets.reduce((total, item) => total + item.routes, 0), 2);
  assert.equal(buckets.reduce((total, item) => total + item.delegations, 0), 2);
  assert.equal(buckets.at(-1).routes, 1);
  assert.equal(buckets.at(-1).delegations, 1);
});

test("bucketActivity remains deterministic for dense data and parseable now values", () => {
  const activity = {
    routing: Array.from({ length: 120 }, (_, index) => ({
      created_at: isoBefore((index % 12) * 10_000 + 1),
    })),
    delegations: Array.from({ length: 80 }, (_, index) => ({
      started_at: isoBefore((index % 8) * 15_000 + 1),
    })),
  };
  const options = {
    now: "2026-07-11T12:00:30.500Z",
    bucketCount: 12,
    bucketMs: 10_000,
  };

  const first = AgencyCharts.bucketActivity(activity, options);
  const second = AgencyCharts.bucketActivity(activity, options);

  assert.deepEqual(second, first);
  assert.equal(first.reduce((total, item) => total + item.routes, 0), 120);
  assert.equal(first.reduce((total, item) => total + item.delegations, 0), 80);
  assert.ok(first.every((bucket, index) => (
    index === 0 || bucket.startMs === first[index - 1].endMs
  )));
});

test("outcomeCounts classifies known outcomes and treats malformed statuses as unknown", () => {
  assert.deepEqual(AgencyCharts.outcomeCounts(), {
    success: 0,
    failed: 0,
    skipped: 0,
    unknown: 0,
    total: 0,
  });
  assert.deepEqual(AgencyCharts.outcomeCounts({ delegations: "bad" }), {
    success: 0,
    failed: 0,
    skipped: 0,
    unknown: 0,
    total: 0,
  });

  const counts = AgencyCharts.outcomeCounts({
    delegations: [
      { status: "success" },
      { status: "completed" },
      { status: "ok" },
      { status: "failed" },
      { status: "failure" },
      { status: "error" },
      { status: "cancelled" },
      { status: "timed_out" },
      { status: "timeout" },
      { status: "skipped" },
      { status: "blocked" },
      { status: "pending" },
      {},
      null,
    ],
  });
  assert.deepEqual(counts, { success: 3, failed: 6, skipped: 2, unknown: 3, total: 14 });
});

test("renderOutcomeChart exposes each non-empty segment to keyboard and assistive technology", () => {
  const root = svgHarness();
  const summary = { id: "outcome-summary", textContent: "" };
  AgencyCharts.renderOutcomeChart(root, summary, {
    delegations: [
      { status: "completed" },
      { status: "failed" },
      { status: "blocked" },
      { status: "something-new" },
    ],
  });

  const nodes = descendants(root);
  const segments = nodes.filter((node) => node.attributes?.get("role") === "img");
  assert.equal(segments.length, 4);
  assert.deepEqual(
    segments.map((node) => node.attributes.get("aria-label")),
    [
      "Completed: 1 (25.0%)",
      "Failed: 1 (25.0%)",
      "Skipped: 1 (25.0%)",
      "Unknown: 1 (25.0%)",
    ],
  );
  assert.ok(segments.every((node) => node.attributes.get("tabindex") === "0"));
});

test("renderActivityChart draws bounded series with readable axes and focusable observations", () => {
  const root = svgHarness();
  const summary = { id: "activity-summary", textContent: "" };
  const buckets = AgencyCharts.renderActivityChart(root, summary, {
    routing: [{ created_at: isoBefore(30_000) }, { created_at: isoBefore(90_000) }],
    delegations: [{ started_at: isoBefore(15_000), status: "completed" }],
  }, { now: NOW, bucketCount: 4, bucketMs: 60_000 });

  assert.equal(buckets.length, 4);
  assert.equal(root.dataset.routes, "2");
  assert.equal(root.dataset.delegations, "1");
  assert.match(summary.textContent, /2 observed routes · 1 delegations/i);
  const nodes = descendants(root);
  const axisLabels = nodes.filter((node) => node.attributes?.get("class")?.includes("axis-label"));
  assert.ok(axisLabels.some((node) => node.textContent === "0"));
  assert.ok(axisLabels.some((node) => node.textContent === "1"));
  const points = nodes.filter((node) => node.attributes?.get("data-chart-point") === "true");
  assert.equal(points.length, 3);
  assert.ok(points.every((node) => node.attributes.get("tabindex") === "0"));
  assert.ok(points.every((node) => node.attributes.get("aria-label")));
});

test("chart renderers support ambient documents, one-point windows, and empty outcomes", () => {
  const documentDescriptor = Object.getOwnPropertyDescriptor(globalThis, "document");
  const documentRef = { createElementNS: (_namespace, tag) => new FakeSvgNode(tag) };
  Object.defineProperty(globalThis, "document", {
    configurable: true,
    value: documentRef,
  });
  try {
    const activityRoot = new FakeSvgNode("activity-root");
    const buckets = AgencyCharts.renderActivityChart(activityRoot, null, {
      routing: [{ created_at: new Date(NOW).toISOString() }],
    }, { now: NOW, bucketCount: 1, bucketMs: 60_000 });
    assert.equal(buckets.length, 1);
    assert.equal(activityRoot.dataset.routes, "1");
    const activitySvg = activityRoot.children[0];
    assert.equal(activitySvg.attributes.get("role"), "group");
    assert.match(
      activitySvg.attributes.get("aria-describedby"),
      /^agency-chart-description-\d+$/,
    );

    const outcomeRoot = new FakeSvgNode("outcome-root");
    const counts = AgencyCharts.renderOutcomeChart(outcomeRoot, null, { delegations: [] });
    assert.deepEqual(counts, { success: 0, failed: 0, skipped: 0, unknown: 0, total: 0 });
    assert.equal(outcomeRoot.dataset.total, "0");
    assert.equal(
      descendants(outcomeRoot).filter((node) => node.attributes?.get("role") === "img").length,
      0,
    );
    assert.match(
      outcomeRoot.children[0].attributes.get("aria-describedby"),
      /^agency-chart-description-\d+$/,
    );
  } finally {
    if (documentDescriptor) {
      Object.defineProperty(globalThis, "document", documentDescriptor);
    } else {
      Reflect.deleteProperty(globalThis, "document");
    }
  }
});

test("pure chart helpers preserve hostile labels as inert input data", () => {
  const hostile = '<img src=x onerror="globalThis.compromised=true">';
  const activity = {
    routing: [{ created_at: isoBefore(1_000), selected_ids: [hostile] }],
    delegations: [
      { started_at: isoBefore(1_000), recommended_agent: hostile },
      { started_at: isoBefore(1_000), status: hostile, recommended_agent: hostile },
    ],
  };
  const before = structuredClone(activity);

  const buckets = AgencyCharts.bucketActivity(activity, {
    now: NOW,
    bucketCount: 1,
    bucketMs: 60_000,
  });
  const outcomes = AgencyCharts.outcomeCounts(activity);

  assert.deepEqual(activity, before);
  assert.equal(buckets[0].routes, 1);
  assert.equal(buckets[0].delegations, 2);
  assert.deepEqual(outcomes, { success: 0, failed: 0, skipped: 0, unknown: 2, total: 2 });
  assert.equal(globalThis.compromised, undefined);
});

test("retryDelay is deterministic, bounded, integer, and capped", () => {
  assert.equal(AgencyCharts.retryDelay(1, () => 0), 2_000);
  assert.equal(AgencyCharts.retryDelay(2, () => 0), 4_000);
  assert.equal(AgencyCharts.retryDelay(1, () => 1), 2_400);
  assert.equal(AgencyCharts.retryDelay(2, () => 1), 4_500);
  assert.equal(AgencyCharts.retryDelay(0, () => 0), 2_000);
  assert.equal(AgencyCharts.retryDelay(Number.NaN, () => 0), 2_000);
  assert.equal(AgencyCharts.retryDelay(1, () => -10), 2_000);
  assert.equal(AgencyCharts.retryDelay(1, () => 10), 2_400);
  assert.equal(AgencyCharts.retryDelay(1, 0.5), 2_200);
  assert.equal(AgencyCharts.retryDelay(1, Number.NaN), 2_000);
  assert.equal(AgencyCharts.retryDelay(1, () => { throw new Error("entropy unavailable"); }), 2_000);
  assert.equal(AgencyCharts.retryDelay(100, () => 0), 30_000);
  assert.equal(AgencyCharts.retryDelay(100, () => 1), 30_000);
  assert.ok(Number.isInteger(AgencyCharts.retryDelay(3, () => 0.314159)));
});

test("app.js renders hostile runtime labels as inert text across dashboard surfaces", () => {
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  const hostile = '<img src=x onerror="globalThis.compromised=true">';
  harness.api.state.overview = {
    capture_content: false,
    db_size_bytes: 1024,
    provider_health: [{
      failure_count: 1,
      latest_status: hostile,
      provider: hostile,
      success_count: 2,
      unknown_count: 0,
    }],
    recent: { delegations: 1, routing: 1 },
    retention_days: 30,
    roster_count: 1,
    status: "ok",
    wal_size_bytes: 512,
  };
  harness.api.state.hosts = [{
    current_native_root: true,
    discovered: true,
    effective_enabled: undefined,
    enabled: false,
    executable_discovered: true,
    host: hostile,
    inspection_status: "stale",
    maturity: "host-discovered",
    registered: true,
    runtime_enabled: true,
  }];
  harness.api.state.activity = {
    delegations: [{
      backend: hostile,
      host: hostile,
      id: "delegation-1",
      recommended_agent: hostile,
      started_at: "not-a-time",
      status: hostile,
    }],
    routing: [{
      created_at: "not-a-time",
      id: "routing-1",
      selected_ids: [hostile],
      source: hostile,
      status: hostile,
      trace_id: hostile,
    }],
  };

  harness.api.renderOverview();
  harness.api.renderHosts();
  harness.api.renderEvidence("routing");
  harness.api.renderReceipt({
    delegation_graph: {
      edges: [{ from: "one", reason: hostile, to: "two" }],
      nodes: [{ description: hostile, id: "one" }, { description: "safe", id: "two" }],
    },
    selected: [{ slug: hostile }],
    signals: { policy: { matched_actions: [hostile] } },
    status: hostile,
  });

  for (const root of [
    harness.node("overview-delegations"),
    harness.node("overview-hosts"),
    harness.node("provider-health"),
    harness.node("host-grid"),
    harness.node("evidence-body"),
    harness.node("route-result"),
  ]) {
    assert.ok(descendants(root).some((node) => node.textContent.includes(hostile)));
    assert.ok(descendants(root).every((node) => node.innerHTML === undefined));
  }
  assert.equal(harness.context.compromised, undefined);
});

test("app.js roster and empty evidence renderers expose actionable, scoped controls", async () => {
  const harness = createAppHarness(() => {
    throw new Error("render-only test does not fetch");
  });
  harness.api.state.roster = [
    {
      agent_slug: "security-reviewer",
      capabilities: ["security"],
      division: "review",
      enabled: true,
      name: "Security Reviewer",
    },
    { agent_slug: "generalist", capabilities: [], enabled: false },
    { agent_slug: "chief-of-staff", capabilities: [], enabled: true, protected: true },
  ];
  harness.api.state.rosterPage = {
    count: 3, total_count: 3, enabled_count: 2, disabled_count: 1, truncated: false,
  };
  harness.api.state.snapshots = [
    { activated: false, agent_count: 2, approved: false, created_at: null, snapshot_id: "pending" },
    { activated: false, agent_count: 2, approved: true, created_at: isoBefore(1_000), snapshot_id: "approved" },
    { activated: true, agent_count: 2, approved: true, created_at: isoBefore(2_000), snapshot_id: "active" },
  ];

  harness.api.renderRoster();
  assert.equal(harness.node("roster-count").textContent, "2 enabled · 3 total");
  const rosterNodes = descendants(harness.node("roster-grid"));
  assert.ok(rosterNodes.some((node) => node.textContent === "no capability tags"));
  assert.ok(rosterNodes.some((node) => node.className === "agent-card disabled"));
  const agentButtons = rosterNodes.filter((node) => node.type === "button");
  assert.equal(agentButtons.length, 3);
  assert.ok(agentButtons.some((node) => node.textContent === "enable"));
  assert.equal(agentButtons.filter((node) => node.disabled).length, 1);
  assert.deepEqual(agentButtons.map((node) => node.getAttribute("aria-label")), [
    "Disable Security Reviewer (security-reviewer) specialist",
    "Enable generalist specialist",
    "chief-of-staff is protected and always enabled",
  ]);
  assert.equal(agentButtons[2].textContent, "always enabled");
  assert.equal(agentButtons[2].getAttribute("aria-busy"), null);
  const disableButton = agentButtons.find((node) => node.textContent === "disable" && !node.disabled);
  const disabling = disableButton.listeners.get("click")[0]();
  assert.equal(disableButton.disabled, true);
  assert.equal(disableButton.getAttribute("aria-busy"), "true");
  await answerConfirmation(
    harness,
    disabling,
    "DISABLE security-reviewer",
    false,
  );
  assert.equal(disableButton.disabled, false);
  assert.equal(disableButton.getAttribute("aria-busy"), null);
  assert.match(harness.node("notice").textContent, /agent action cancelled/i);
  const snapshotNodes = descendants(harness.node("snapshot-list"));
  const snapshotButtons = snapshotNodes.filter((node) => node.type === "button");
  assert.deepEqual(snapshotButtons.map((node) => node.getAttribute("aria-label")), [
    "Approve roster snapshot pending",
    "Activate roster snapshot approved",
  ]);

  harness.api.state.activity = {};
  harness.api.renderEvidence("delegations");
  assert.equal(harness.node("evidence-head").children[0].children[0].getAttribute("scope"), "col");
  assert.match(
    harness.node("evidence-body").children[0].children[0].textContent,
    /no delegation evidence/i,
  );
});

test("app.js model receipts show requested alias, LiteLLM router, and actual model separately", () => {
  const harness = createAppHarness(() => {
    throw new Error("render-only test does not fetch");
  });
  harness.api.state.activity = {
    receipts: [{
      ended_at: isoBefore(1_000),
      host: "litellm",
      model_group: "production-router",
      requested_model: "task-general",
      resolved_model: "gpt-5.6",
      resolved_provider: "openai",
      source: "litellm",
      status: "success",
    }],
  };

  harness.api.renderEvidence("receipts");

  assert.deepEqual(
    harness.node("evidence-head").children[0].children.map((node) => node.textContent),
    [
      "Requested",
      "LiteLLM router / model group",
      "Actual provider",
      "Actual model",
      "Host",
      "Status",
      "Source",
      "Ended",
    ],
  );
  const values = harness.node("evidence-body").children[0].children
    .map((node) => node.textContent || node.children[0]?.textContent);
  assert.deepEqual(values.slice(0, 4), [
    "task-general",
    "production-router",
    "openai",
    "gpt-5.6",
  ]);
});

test("app.js specialist evidence separates current turns from immutable history", () => {
  const harness = createAppHarness(() => {
    throw new Error("render-only test does not fetch");
  });
  harness.api.state.activity = {
    specialists: [
      {
        expired_at: null,
        id: "activation-current",
        loaded_at: isoBefore(1_000),
        session_id: "session-current",
        slug: "security-reviewer",
        state: "current",
        trace_id: "trace-current",
      },
      {
        expired_at: isoBefore(2_000),
        id: "activation-history",
        loaded_at: isoBefore(3_000),
        session_id: "session-history",
        slug: "code-reviewer",
        state: "historical",
        trace_id: "trace-history",
      },
    ],
    routing: [{
      created_at: isoBefore(500),
      fallback_applied: true,
      fallback_companion_ids: ["agents-orchestrator", "chief-of-staff"],
      id: "decision-fallback",
      selected_ids: ["agents-orchestrator", "chief-of-staff"],
      semantic_status: "abstained",
      source: "policy_fallback",
      status: "policy_fallback",
      trace_id: "trace-current",
    }, {
      created_at: isoBefore(250),
      fallback_applied: false,
      fallback_companion_ids: [],
      id: "decision-semantic",
      selected_ids: ["security-reviewer"],
      semantic_status: "selected",
      source: "computed",
      status: "selected",
      trace_id: "trace-semantic",
    }],
  };

  harness.api.renderEvidence();

  assert.match(harness.node("evidence-caption").textContent, /current-turn and historical/i);
  assert.match(harness.node("evidence-context").textContent, /1 current-turn activation · 1 historical activation/i);
  assert.deepEqual(
    harness.node("evidence-head").children[0].children.map((node) => node.textContent),
    ["Specialist", "Session", "Trace", "Evidence state", "Activated", "Expired"],
  );
  const activationRows = harness.node("evidence-body").children;
  assert.equal(activationRows[0].children[3].children[0].textContent, "Current turn");
  assert.match(activationRows[0].children[3].children[0].className, /activation-current/);
  assert.equal(activationRows[1].children[3].children[0].textContent, "Historical");
  assert.match(activationRows[1].children[3].children[0].className, /activation-historical/);

  harness.api.state.activity.specialists = [{
    id: "activation-malformed-state",
    loaded_at: isoBefore(4_000),
    session_id: "session-legacy",
    slug: "legacy-reviewer",
    state: "",
    trace_id: "",
  }];
  harness.api.renderEvidence();
  assert.equal(harness.node("evidence-body").children[0].children[3].children[0].textContent, "Historical");
  assert.match(harness.node("evidence-context").textContent, /0 current-turn activations · 1 historical activation/i);

  harness.api.state.activity.specialists = [];
  harness.api.renderEvidence();
  assert.match(harness.node("evidence-context").textContent, /0 current-turn activations · 0 historical activations/i);
  assert.match(
    harness.node("evidence-body").children[0].children[0].textContent,
    /no specialist activation evidence/i,
  );

  harness.api.renderEvidence("routing");
  const routingValues = descendants(harness.node("evidence-body")).map((node) => node.textContent);
  assert.ok(routingValues.includes("abstained"));
  assert.ok(routingValues.includes("policy_fallback"));
  assert.ok(routingValues.includes("Yes"));
  assert.ok(routingValues.includes("No"));
  assert.ok(routingValues.includes("agents-orchestrator, chief-of-staff"));
  assert.match(harness.node("evidence-context").textContent, /metadata-only runtime evidence/i);
});

test("evidence context is static prose and deduplicates live-render writes", () => {
  const contextTag = INDEX_SOURCE.match(/<p id="evidence-context"[^>]*>/)?.[0] || "";
  assert.doesNotMatch(contextTag, /role="status"|aria-live=/);

  const harness = createAppHarness(() => {
    throw new Error("render-only test does not fetch");
  });
  const context = harness.node("evidence-context");
  let rendered = "";
  let writes = 0;
  Object.defineProperty(context, "textContent", {
    configurable: true,
    get() { return rendered; },
    set(value) { rendered = String(value); writes += 1; },
  });

  harness.api.state.activity = { specialists: [] };
  harness.api.renderEvidence("specialists");
  harness.api.renderEvidence("specialists");
  assert.equal(writes, 1);

  harness.api.state.activity.specialists.push({ state: "current" });
  harness.api.renderEvidence("specialists");
  assert.equal(writes, 2);
});

test("app.js evidence tabs implement roving keyboard focus and labelled panels", () => {
  const harness = createAppHarness(() => {
    throw new Error("keyboard-only test does not fetch");
  });
  const tabList = new FakeNode("tab-list");
  const delegationTab = new FakeNode();
  delegationTab.classList.add("active");
  delegationTab.dataset.evidence = "delegations";
  delegationTab.parentElement = tabList;
  const routingTab = new FakeNode();
  routingTab.dataset.evidence = "routing";
  routingTab.parentElement = tabList;
  const panel = new FakeNode("evidence-panel");
  harness.node("evidence-body").closestNode = panel;
  harness.select(".subnav-item", [delegationTab, routingTab]);
  harness.api.state.activity = { delegations: [], routing: [] };

  harness.api.configureEvidenceTabs();
  assert.equal(tabList.getAttribute("role"), "tablist");
  assert.equal(panel.getAttribute("role"), "tabpanel");
  assert.equal(delegationTab.tabIndex, 0);
  assert.equal(routingTab.tabIndex, -1);

  let prevented = false;
  delegationTab.listeners.get("keydown")[0]({
    key: "ArrowRight",
    preventDefault() { prevented = true; },
  });
  assert.equal(prevented, true);
  assert.equal(delegationTab.getAttribute("aria-selected"), "false");
  assert.equal(routingTab.getAttribute("aria-selected"), "true");
  assert.equal(routingTab.focusCount, 1);
  assert.equal(panel.getAttribute("aria-labelledby"), routingTab.id);
  assert.match(harness.node("evidence-caption").textContent, /routing runtime evidence/i);
});

test("app UI honors reduced motion, canonical CSS, and live toggle semantics", () => {
  assert.equal((APP_CSS_SOURCE.match(/^:root\s*{/gm) || []).length, 1);
  assert.equal((APP_CSS_SOURCE.match(/@media \(max-width: 980px\)/g) || []).length, 1);
  assert.equal((APP_CSS_SOURCE.match(/@media \(max-width: 620px\)/g) || []).length, 1);
  assert.match(APP_CSS_SOURCE, /\.button:disabled\s*{[^}]*cursor: not-allowed;/);
  assert.match(
    APP_CSS_SOURCE,
    /\.button:disabled\[aria-busy="true"\], \.button\.is-pending\s*{[^}]*cursor: wait;/,
  );
  const mutedDim = APP_CSS_SOURCE.match(/--muted-dim:\s*(#[0-9a-f]{6})/i)?.[1];
  assert.ok(mutedDim);
  const luminance = (color) => {
    const channels = [1, 3, 5].map((index) => Number.parseInt(color.slice(index, index + 2), 16) / 255);
    const linear = channels.map((value) => (
      value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
    ));
    return (0.2126 * linear[0]) + (0.7152 * linear[1]) + (0.0722 * linear[2]);
  };
  const contrast = (luminance(mutedDim) + 0.05) / (luminance("#0d1117") + 0.05);
  assert.ok(contrast >= 4.5, `muted small-text contrast was ${contrast.toFixed(2)}:1`);
  assert.doesNotMatch(APP_CSS_SOURCE, /main:focus\s*{[^}]*outline:\s*none/);
  assert.match(APP_CSS_SOURCE, /main:focus-visible\s*{[^}]*outline-offset:\s*-2px/);
  assert.match(APP_CSS_SOURCE, /scrollbar-width:\s*thin/);
  assert.match(APP_CSS_SOURCE, /\.rail::-webkit-scrollbar\s*{[^}]*height:\s*4px/);
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  const toggle = new harness.HTMLInputElement("live-toggle");
  toggle.type = "checkbox";
  harness.nodes.set("live-toggle", toggle);
  const metric = harness.node("metric-runtime");

  harness.context.window.matchMedia = () => ({ matches: true });
  harness.api.setMetric("metric-runtime", "Online");
  harness.api.setMetric("metric-runtime", "Offline");
  assert.equal(metric.classList.contains("is-updated"), false);

  harness.context.window.matchMedia = () => ({ matches: false });
  harness.api.setMetric("metric-runtime", "Online");
  assert.equal(metric.classList.contains("is-updated"), true);
  metric.listeners.get("animationend")[0]();
  assert.equal(metric.classList.contains("is-updated"), false);

  harness.api.state.live.enabled = false;
  harness.api.syncLiveToggle();
  assert.equal(toggle.getAttribute("aria-pressed"), "false");
  assert.equal(toggle.checked, false);
  harness.api.setLiveEnabled(true);
  assert.equal(toggle.getAttribute("aria-pressed"), "true");
  assert.equal(toggle.checked, true);
  assert.equal(harness.timers.tasks.get(harness.api.state.live.timer).delay, 0);
});

test("app.js live snapshots are single-flight", async () => {
  const pending = deferred();
  const calls = [];
  const harness = createAppHarness((path, options) => {
    calls.push({ path, options });
    return pending.promise;
  });

  const first = harness.api.fetchLiveSnapshot();
  const second = harness.api.fetchLiveSnapshot();

  assert.equal(await second, null);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].path, "/api/live?limit=100");
  assert.equal(harness.api.state.live.inFlight, true);
  assert.equal(calls[0].options.signal.aborted, false);

  pending.resolve(jsonResponse(200, { schema_version: 1, revision: "single-flight" }));
  const result = await first;

  assert.equal(result.revision, "single-flight");
  assert.equal(harness.api.state.live.inFlight, false);
  assert.equal(harness.api.state.live.controller, null);
});

test("app.js validates live schemas, deduplicates revisions, and retries transient failures", async () => {
  const successHarness = createAppHarness(async () => jsonResponse(200, {
    activity: { delegations: [], routing: [] },
    overview: { status: "ok" },
    revision: "poll-success",
    sampled_at: "2026-07-11T12:00:30.500Z",
    schema_version: 1,
  }));
  assert.throws(
    () => successHarness.api.applyLiveSnapshot({ schema_version: 2 }),
    /unsupported live dashboard response/i,
  );
  await successHarness.api.runLivePoll();
  assert.equal(successHarness.api.state.live.revision, "poll-success");
  assert.equal(successHarness.node("connection-label").textContent, "Authenticated");
  assert.equal(successHarness.node("live-status").dataset.state, "live");
  assert.equal(
    successHarness.timers.tasks.get(successHarness.api.state.live.timer).delay,
    2500,
  );

  successHarness.api.state.live.chartWindow = -1;
  assert.equal(successHarness.api.applyLiveSnapshot({
    revision: "poll-success",
    sampled_at: "2026-07-11T12:01:30.500Z",
    schema_version: 1,
  }), false);
  assert.equal(successHarness.api.state.live.revision, "poll-success");

  const retryHarness = createAppHarness(async () => jsonResponse(500, {
    error: "temporary local service failure",
  }));
  await retryHarness.api.runLivePoll();
  assert.equal(retryHarness.api.state.live.failures, 1);
  assert.equal(retryHarness.node("connection-label").textContent, "Reconnecting");
  assert.equal(retryHarness.node("live-status").dataset.state, "retrying");
  assert.match(retryHarness.node("notice").textContent, /reconnects/i);
  assert.ok(retryHarness.timers.tasks.get(retryHarness.api.state.live.timer).delay >= 2000);
});

test("app.js rejects stale live generations and treats abort rejection as cancellation", async () => {
  const stalePending = deferred();
  let staleSignal;
  const staleHarness = createAppHarness((_path, options) => {
    staleSignal = options.signal;
    return stalePending.promise;
  });

  const staleRequest = staleHarness.api.fetchLiveSnapshot();
  const activeGeneration = staleHarness.api.state.live.generation;
  staleHarness.api.cancelLiveRequest();

  assert.equal(staleSignal.aborted, true);
  assert.ok(staleHarness.api.state.live.generation > activeGeneration);
  stalePending.resolve(jsonResponse(200, { schema_version: 1, revision: "stale" }));
  assert.equal(await staleRequest, null);
  assert.equal(staleHarness.api.state.live.inFlight, false);
  assert.equal(staleHarness.api.state.live.revision, "");

  let abortCalls = 0;
  let abortSignal;
  const abortHarness = createAppHarness((_path, options) => {
    abortCalls += 1;
    abortSignal = options.signal;
    return new Promise((_resolve, reject) => {
      options.signal.addEventListener("abort", () => {
        const error = new Error("request aborted");
        error.name = "AbortError";
        reject(error);
      }, { once: true });
    });
  });

  const poll = abortHarness.api.runLivePoll();
  abortHarness.api.cancelLiveRequest();
  await poll;

  assert.equal(abortCalls, 1);
  assert.equal(abortSignal.aborted, true);
  assert.equal(abortHarness.api.state.live.failures, 0);
  assert.equal(abortHarness.api.state.live.terminal, false);
  assert.equal(abortHarness.api.state.live.timer, null);
  assert.equal(abortHarness.api.state.live.inFlight, false);
});

test("app.js cancels stale full refresh generations before they can render", async () => {
  const requests = [];
  const harness = createAppHarness((path, options) => {
    const pending = deferred();
    requests.push({ path, signal: options.signal, pending });
    return pending.promise;
  });

  const refresh = harness.api.refreshAll();
  assert.equal(requests.length, 1);
  assert.deepEqual(
    requests.map((request) => request.path),
    ["/api/config"],
  );
  const activeGeneration = harness.api.state.full.generation;

  harness.api.cancelFullRefresh();
  assert.ok(harness.api.state.full.generation > activeGeneration);
  assert.ok(requests.every((request) => request.signal.aborted));
  assert.equal(harness.node("refresh-button").disabled, false);

  requests.forEach((request) => request.pending.resolve(jsonResponse(200, {})));
  assert.equal(await refresh, false);
  assert.equal(harness.api.state.overview, null);
  assert.equal(harness.api.state.full.inFlight, false);
  assert.equal(harness.api.state.full.controller, null);
});

test("app.js initial refresh reuses the live fast path and preserves control-plane fields", async () => {
  const payloads = new Map([
    ["/api/live?limit=100", {
      schema_version: 1,
      revision: "initial-live",
      sampled_at: "2026-07-11T12:00:30.500Z",
      overview: {
        status: "ok",
        db_size_bytes: 2048,
        wal_size_bytes: 1024,
        recent: { routing: 3, delegations: 2 },
        provider_health: [],
      },
      activity: { delegations: [], routing: [] },
    }],
    ["/api/hosts", { hosts: [] }],
    ["/api/roster?limit=100", { agents: [{ agent_slug: "security-reviewer" }] }],
    ["/api/snapshots", { snapshots: [] }],
    ["/api/config", {
      revision: "config-revision",
      effective: { observability: { retention_days: 45, capture_content: true } },
      environment_overrides: {},
    }],
  ]);
  const calls = [];
  const harness = createAppHarness(async (path) => {
    calls.push(path);
    return jsonResponse(200, payloads.get(path));
  });

  assert.equal(await harness.api.refreshAll(), true);
  assert.deepEqual(calls, [
    "/api/config",
    "/api/live?limit=100",
    "/api/hosts",
    "/api/roster?limit=100",
    "/api/snapshots",
  ]);
  assert.equal(harness.api.state.live.revision, "initial-live");
  assert.equal(harness.api.state.overview.roster_count, 1);
  assert.equal(harness.api.state.overview.retention_days, 45);
  assert.equal(harness.api.state.overview.capture_content, true);
  assert.equal(harness.api.state.config.revision, "config-revision");
  assert.equal(harness.api.state.pendingConfig.revision, "config-revision");
  assert.equal(harness.node("metric-runtime").textContent, "Online");
  assert.equal(harness.node("metric-roster").textContent, "1");
  assert.equal(harness.node("privacy-chip").textContent, "Redacted content");
  assert.match(harness.node("window-label").textContent, /24 min window/i);

  harness.api.switchView("settings");
  assert.equal(harness.api.state.config.revision, "config-revision");
  assert.equal(harness.api.state.pendingConfig, null);
});

test("app.js control-plane refresh is single-flight and updates only current responses", async () => {
  const payloads = new Map([
    ["/api/hosts", { hosts: [{ host: "codex", discovered: true }] }],
    ["/api/roster?limit=100", { agents: [{ agent_slug: "reviewer" }, { agent_slug: "tester" }] }],
    ["/api/snapshots", { snapshots: [{ snapshot_id: "snapshot-1" }] }],
    ["/api/config", { effective: {}, revision: "control-config" }],
  ]);
  const calls = [];
  const harness = createAppHarness(async (path) => {
    calls.push(path);
    return jsonResponse(200, payloads.get(path));
  });
  harness.api.state.activeView = "hosts";

  await harness.api.refreshControlPlane();
  assert.deepEqual(calls, [
    "/api/config",
    "/api/hosts",
    "/api/roster?limit=100",
    "/api/snapshots",
  ]);
  assert.equal(harness.api.state.hosts[0].host, "codex");
  assert.equal(harness.api.state.roster.length, 2);
  assert.equal(harness.api.state.overview.roster_count, 2);
  assert.equal(harness.api.state.control.inFlight, false);
  assert.equal(
    harness.timers.tasks.get(harness.api.state.control.timer).delay,
    15000,
  );
  assert.equal(harness.node("host-grid").children.length, 1);

  harness.api.state.control.inFlight = true;
  await harness.api.refreshControlPlane();
  assert.equal(calls.length, 4);
});

test("store identity drift stays visible and disables routing, roster, and host controls", async () => {
  const calls = [];
  const harness = createAppHarness(async (path) => {
    calls.push(path);
    if (path === "/api/config") {
      return jsonResponse(200, {
        effective: {},
        revision: "restart-config",
        service_binding: {
          store_path: "C:\\runtime\\active.db",
          desired_store_path: "C:\\runtime\\next.db",
          store_restart_required: true,
        },
      });
    }
    if (path === "/api/live?limit=100") {
      return jsonResponse(200, {
        activity: {},
        master: { enabled: true, generation: 4 },
        overview: { status: "ok" },
        revision: "restart-live",
        schema_version: 1,
      });
    }
    throw new Error(`restart-blocked refresh must not call ${path}`);
  });

  assert.equal(await harness.api.refreshAll(), true);
  assert.deepEqual(calls, ["/api/config", "/api/live?limit=100"]);
  assert.equal(harness.api.serviceRestartRequired(), true);
  assert.equal(harness.node("store-restart-banner").hidden, false);
  assert.match(harness.node("store-restart-paths").textContent, /active\.db/i);
  assert.match(harness.node("store-restart-paths").textContent, /next\.db/i);
  assert.equal(harness.node("route-button").disabled, true);
  assert.equal(harness.node("roster-search-slug").disabled, true);
  assert.equal(harness.node("roster-search-submit").disabled, true);
  assert.ok(harness.node("shell").classList.contains("store-restart-required"));

  const callsBeforeBlockedSearch = calls.length;
  assert.equal(await harness.api.applyRosterFilter("reviewer"), false);
  assert.equal(calls.length, callsBeforeBlockedSearch);
  await harness.api.refreshControlPlane();
  assert.deepEqual(calls, [
    "/api/config",
    "/api/live?limit=100",
    "/api/config",
  ]);

  harness.api.state.hosts = [{
    ...verifiedHost("codex"),
    runtime_control_generation: 1,
  }];
  harness.api.renderRouteHosts();
  harness.api.renderHosts();
  const hostButton = descendants(harness.node("host-grid"))
    .find((node) => node.textContent === "Restart required");
  assert.equal(hostButton.disabled, true);

  harness.api.state.roster = [{
    agent_slug: "reviewer",
    capabilities: [],
    enabled: true,
    protected: false,
  }];
  harness.api.state.snapshots = [{
    activated: false,
    agent_count: 1,
    approved: false,
    snapshot_id: "snapshot-restart",
  }];
  harness.api.renderRoster();
  const rosterButtons = descendants(harness.node("roster-grid"))
    .filter((node) => node.type === "button");
  const snapshotButtons = descendants(harness.node("snapshot-list"))
    .filter((node) => node.type === "button");
  assert.ok(rosterButtons.length > 0 && rosterButtons.every((node) => node.disabled));
  assert.ok(snapshotButtons.length > 0 && snapshotButtons.every((node) => node.disabled));

  const callsBeforeBlockedActions = calls.length;
  await harness.api.runRoute();
  await harness.api.toggleHost("codex", false, 1);
  await harness.api.toggleAgent("reviewer", false);
  await harness.api.rosterAction("approve", "snapshot-restart");
  assert.match(harness.node("notice").textContent, /restart the dashboard service/i);
  assert.equal(calls.length, callsBeforeBlockedActions);

  harness.api.state.master = { enabled: true, generation: 4 };
  harness.api.applyServiceBinding({
    service_binding: {
      store_path: "C:\\runtime\\next.db",
      desired_store_path: "C:\\runtime\\next.db",
      store_restart_required: false,
    },
  });
  assert.equal(harness.node("store-restart-banner").hidden, true);
  assert.equal(harness.node("route-button").disabled, false);
  assert.equal(harness.node("roster-search-slug").disabled, false);
  assert.equal(harness.node("shell").classList.contains("store-restart-required"), false);
});

test("store binding renders bounded fallbacks when paths or controls are unavailable", () => {
  const harness = createAppHarness(() => {
    throw new Error("binding projection does not fetch");
  });
  harness.missing("roster-search-slug");
  harness.api.state.master = { enabled: true, generation: 1 };

  assert.equal(harness.api.applyServiceBinding({
    service_binding: {
      store_path: null,
      desired_store_path: 42,
      store_restart_required: true,
    },
  }), true);

  assert.equal(
    harness.node("store-restart-paths").textContent,
    "Active: unknown · Configured: unknown",
  );
  assert.equal(harness.node("roster-search-submit").disabled, true);
  assert.equal(harness.node("roster-search-clear").disabled, true);
  assert.equal(harness.node("route-button").disabled, true);
});

test("late control and full-refresh responses cannot cross restart generations", async () => {
  let staleControl;
  staleControl = createAppHarness(async (path) => {
    if (path === "/api/config") return jsonResponse(200, { effective: {} });
    if (path === "/api/snapshots") staleControl.api.state.lifecycle.suspended = true;
    const payloads = new Map([
      ["/api/hosts", { hosts: [] }],
      ["/api/roster?limit=100", { agents: [] }],
      ["/api/snapshots", { snapshots: [] }],
    ]);
    return jsonResponse(200, payloads.get(path));
  });
  await staleControl.api.refreshControlPlane();
  assert.equal(staleControl.api.state.hosts.length, 0);
  assert.equal(staleControl.api.state.control.inFlight, false);

  let staleRestart;
  staleRestart = createAppHarness(async (path) => {
    if (path === "/api/config") {
      return jsonResponse(200, {
        effective: {},
        service_binding: {
          store_path: "active.db",
          desired_store_path: "next.db",
          store_restart_required: true,
        },
      });
    }
    if (path === "/api/live?limit=100") {
      staleRestart.api.state.full.generation += 1;
      return jsonResponse(200, { revision: "obsolete-restart", schema_version: 1 });
    }
    throw new Error(`unexpected restart path ${path}`);
  });
  assert.equal(await staleRestart.api.refreshAll(), false);
  assert.equal(staleRestart.api.state.live.revision, "");

  let staleFull;
  staleFull = createAppHarness(async (path) => {
    if (path === "/api/snapshots") staleFull.api.state.full.generation += 1;
    const payloads = new Map([
      ["/api/config", { effective: {} }],
      ["/api/live?limit=100", { revision: "obsolete-full", schema_version: 1 }],
      ["/api/hosts", { hosts: [] }],
      ["/api/roster?limit=100", { agents: [] }],
      ["/api/snapshots", { snapshots: [] }],
    ]);
    return jsonResponse(200, payloads.get(path));
  });
  assert.equal(await staleFull.api.refreshAll(), false);
  assert.equal(staleFull.api.state.live.revision, "");
});

test("app.js routing lab posts bounded tasks and reconciles live evidence", async () => {
  const calls = [];
  const harness = createAppHarness(async (path, options) => {
    calls.push({ path, options });
    if (path === "/api/route") {
      return jsonResponse(200, {
        selected: [{ slug: "security-reviewer" }],
        signals: { policy: { matched_actions: ["review"] } },
        status: "selected",
      });
    }
    if (path === "/api/live?limit=100") {
      return jsonResponse(200, {
        activity: { delegations: [], routing: [] },
        overview: { status: "ok" },
        revision: "after-route",
        schema_version: 1,
      });
    }
    throw new Error(`unexpected path ${path}`);
  });

  await harness.api.runRoute();
  assert.match(harness.node("notice").textContent, /enter a task/i);
  assert.equal(calls.length, 0);

  harness.node("route-task").value = "Review this service";
  await harness.api.runRoute();
  assert.match(harness.node("notice").textContent, /verified, enabled execution host/i);
  assert.equal(calls.length, 0);

  harness.api.state.master = { enabled: true, generation: 1 };
  harness.api.state.hosts = [verifiedHost("codex")];
  harness.api.renderRouteHosts();
  harness.node("route-task").value = "  Review this service  ";
  harness.node("route-session").value = " dashboard-lab ";
  await harness.api.runRoute();
  assert.equal(calls.length, 2);
  const body = JSON.parse(calls[0].options.body);
  assert.deepEqual(body, {
    host: "codex",
    limit: 12,
    session_id: "dashboard-lab",
    task: "Review this service",
  });
  assert.equal(harness.node("route-status").textContent, "SELECTED");
  assert.ok(
    descendants(harness.node("route-result"))
      .some((node) => node.textContent === "security-reviewer"),
  );
  assert.equal(harness.api.state.live.revision, "after-route");
  assert.equal(harness.node("route-button").disabled, false);
  assert.equal(harness.node("route-button").getAttribute("aria-busy"), null);
});

test("app.js saves validated config only after the exact typed confirmation", async () => {
  const calls = [];
  const harness = createAppHarness(async (path, options) => {
    calls.push({ path, options });
    if (path === "/api/config") {
      return jsonResponse(200, {
        effective: { observability: { capture_content: false, retention_days: 31 } },
        restart_required_paths: [],
        revision: "saved-config",
      });
    }
    if (path === "/api/live?limit=100") {
      return jsonResponse(200, {
        activity: { delegations: [], routing: [] },
        overview: { status: "ok" },
        revision: "after-config",
        schema_version: 1,
      });
    }
    throw new Error(`unexpected path ${path}`);
  });
  const retention = new FakeNode("config-retention");
  retention.dataset.configPath = "observability.retention_days";
  retention.dataset.valueType = "integer";
  retention.labels = [{ textContent: "Retention days" }];
  retention.value = "31";
  harness.nodes.set("config-retention", retention);
  harness.select("[data-config-path]", [retention]);
  harness.api.state.config = { revision: "original-config" };
  harness.api.state.configBaseline.set("observability.retention_days", "30");

  let prevented = false;
  const saving = harness.api.saveConfig({ preventDefault() { prevented = true; } });
  await Promise.resolve();
  assert.equal(prevented, true);
  assert.equal(harness.api.state.confirmation.phrase, "SAVE CONFIG");
  harness.node("confirmation-input").value = "SAVE CONFIG";
  harness.api.finishConfirmation(true);
  await saving;

  assert.equal(calls.length, 2);
  const payload = JSON.parse(calls[0].options.body);
  assert.equal(payload.expected_revision, "original-config");
  assert.deepEqual(payload.confirmations, ["SAVE CONFIG"]);
  assert.deepEqual(payload.operations, [{
    op: "set",
    path: "observability.retention_days",
    value: 31,
  }]);
  assert.equal(harness.api.state.config.revision, "saved-config");
  assert.equal(harness.api.state.overview.retention_days, 31);
  assert.equal(harness.node("setting-retention").textContent, "31 days");
  assert.equal(harness.node("setting-capture").textContent, "Disabled");
  assert.equal(harness.node("privacy-chip").textContent, "Metadata only");
  assert.equal(harness.node("config-save-button").getAttribute("aria-busy"), null);
  assert.match(harness.node("notice").textContent, /saved and active/i);
});

test("app.js binds lifecycle controls for live pause, page cleanup, and late fragments", () => {
  const harness = createAppHarness(() => {
    throw new Error("registered listeners are not allowed to fetch in this test");
  });
  const overviewNav = new FakeNode("nav-overview");
  overviewNav.classList.add("active");
  overviewNav.dataset.view = "overview";
  const overviewPanel = new FakeNode("view-overview");
  overviewPanel.dataset.viewPanel = "overview";
  harness.select(".nav-item", [overviewNav]);
  harness.select(".view", [overviewPanel]);

  harness.api.bindEvents();
  assert.equal(harness.documentListeners.get("visibilitychange").length, 1);
  assert.equal(harness.windowListeners.get("hashchange").length, 1);
  assert.equal(harness.windowListeners.get("pagehide").length, 1);
  assert.equal(harness.windowListeners.get("pageshow").length, 1);

  harness.node("trim-days").listeners.get("input")[0]();
  assert.equal(harness.node("trim-days").dataset.dirty, "true");
  harness.node("live-toggle").listeners.get("click")[0]();
  assert.equal(harness.api.state.live.enabled, false);
  assert.equal(harness.node("live-status").dataset.state, "paused");

  harness.api.state.clockTimer = harness.timers.set(() => {}, 1000);
  harness.windowListeners.get("pagehide")[0]();
  assert.equal(harness.api.state.clockTimer, null);
  assert.equal(harness.api.state.live.timer, null);
  assert.equal(harness.api.state.control.timer, null);
  assert.equal(harness.api.state.full.inFlight, false);
});

test("app.js keeps inactive views out of the live render path and hides panels semantically", () => {
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  const overviewNav = new FakeNode("nav-overview");
  overviewNav.dataset.view = "overview";
  overviewNav.classList.add("active");
  const hostsNav = new FakeNode("nav-hosts");
  hostsNav.dataset.view = "hosts";
  const overviewPanel = new FakeNode("view-overview");
  overviewPanel.dataset.viewPanel = "overview";
  const hostsPanel = new FakeNode("view-hosts");
  hostsPanel.dataset.viewPanel = "hosts";
  harness.select(".nav-item", [overviewNav, hostsNav]);
  harness.select(".view", [overviewPanel, hostsPanel]);

  harness.api.switchView("hosts");
  assert.equal(harness.api.state.activeView, "hosts");
  assert.equal(overviewPanel.hidden, true);
  assert.equal(overviewPanel.getAttribute("aria-hidden"), "true");
  assert.equal(hostsPanel.hidden, false);
  assert.equal(hostsPanel.getAttribute("aria-hidden"), "false");
  assert.equal(hostsNav.getAttribute("aria-current"), "page");

  harness.node("metric-runtime").textContent = "not-rendered";
  harness.api.state.activeView = "routing";
  assert.equal(harness.api.applyLiveSnapshot({
    schema_version: 1,
    revision: "background-live",
    sampled_at: "2026-07-11T12:01:30.500Z",
    overview: { status: "ok" },
    activity: { delegations: [], routing: [] },
  }), true);
  assert.equal(harness.node("metric-runtime").textContent, "not-rendered");

  harness.api.state.activeView = "overview";
  harness.api.renderActiveView();
  assert.equal(harness.node("metric-runtime").textContent, "Online");
});

test("app.js marks malformed configuration JSON invalid and clears the error after correction", () => {
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  const providers = new FakeNode("config-providers");
  providers.dataset.configPath = "providers";
  providers.dataset.valueType = "json";
  providers.labels = [{ textContent: "Provider array" }];
  providers.value = "{";
  harness.nodes.set("config-providers", providers);
  harness.select("[data-config-path]", [providers]);
  harness.api.state.configBaseline.set("providers", "[]");

  harness.api.updateConfigDirtyState();
  assert.equal(providers.getAttribute("aria-invalid"), "true");
  assert.match(providers.validationMessage, /valid JSON/i);
  assert.equal(harness.node("config-save-button").disabled, true);
  assert.match(harness.node("config-change-count").textContent, /valid JSON/i);

  providers.value = "[]";
  harness.api.updateConfigDirtyState();
  assert.equal(providers.getAttribute("aria-invalid"), null);
  assert.equal(providers.validationMessage, "");
  assert.equal(harness.api.state.configDirty, false);
});

test("app.js pauses while hidden, resumes visibly, and gates BFCache restoration", () => {
  const harness = createAppHarness(() => {
    throw new Error("timers must not perform a fetch in this deterministic test");
  });
  harness.api.scheduleLive(500);
  harness.api.scheduleControlRefresh(750);
  assert.notEqual(harness.api.state.live.timer, null);
  assert.notEqual(harness.api.state.control.timer, null);

  harness.document.visibilityState = "hidden";
  harness.api.handleVisibilityChange();
  assert.equal(harness.api.state.live.timer, null);
  assert.equal(harness.api.state.control.timer, null);
  assert.equal(harness.node("live-status").dataset.state, "paused");
  assert.match(harness.node("live-status").textContent, /hidden/i);

  harness.document.visibilityState = "visible";
  harness.api.handleVisibilityChange();
  assert.equal(
    harness.timers.tasks.get(harness.api.state.live.timer).delay,
    0,
  );
  assert.equal(
    harness.timers.tasks.get(harness.api.state.control.timer).delay,
    0,
  );
  assert.notEqual(harness.api.state.clockTimer, null);
  assert.equal(harness.node("live-status").dataset.state, "connecting");

  harness.api.cancelLiveRequest();
  harness.api.cancelControlRequest();
  harness.node("refresh-button").disabled = true;
  harness.api.handlePageShow({ persisted: false });
  assert.equal(harness.node("refresh-button").disabled, true);
  assert.equal(harness.api.state.live.timer, null);
  assert.equal(harness.api.state.control.timer, null);

  harness.api.state.live.enabled = false;
  harness.api.handlePageShow({ persisted: true });
  assert.equal(harness.node("refresh-button").disabled, false);
  assert.equal(harness.api.state.live.timer, null);
  assert.equal(harness.api.state.control.timer, null);

  harness.api.state.live.enabled = true;
  harness.api.state.live.terminal = true;
  harness.api.handlePageShow({ persisted: true });
  assert.equal(harness.api.state.live.timer, null);
  assert.equal(harness.api.state.control.timer, null);

  harness.api.state.live.terminal = false;
  harness.node("refresh-button").disabled = true;
  harness.api.handlePageShow({ persisted: true });
  assert.equal(harness.node("refresh-button").disabled, false);
  assert.equal(
    harness.timers.tasks.get(harness.api.state.live.timer).delay,
    0,
  );
  assert.equal(
    harness.timers.tasks.get(harness.api.state.control.timer).delay,
    0,
  );
});

test("app.js treats 401 and 403 live responses as terminal", async (testContext) => {
  for (const status of [401, 403]) {
    await testContext.test(`HTTP ${status}`, async () => {
      let calls = 0;
      const harness = createAppHarness(async () => {
        calls += 1;
        return jsonResponse(status, { error: "authentication required" });
      });

      await harness.api.runLivePoll();

      assert.equal(calls, 1);
      assert.equal(harness.api.state.live.terminal, true);
      assert.equal(harness.api.state.live.inFlight, false);
      assert.equal(harness.api.state.live.controller, null);
      assert.equal(harness.api.state.live.timer, null);
      assert.equal(harness.node("connection-label").textContent, "Token expired");
      assert.equal(harness.node("live-status").dataset.state, "expired");
      assert.match(harness.node("live-status").textContent, /access expired/i);
      assert.match(harness.node("live-announcer").textContent, /access expired/i);
      assert.equal(harness.node("notice").hidden, false);
      assert.match(harness.node("notice").textContent, /token expired/i);

      harness.api.scheduleLive(0);
      await harness.api.runLivePoll();
      assert.equal(harness.api.state.live.timer, null);
      assert.equal(calls, 1);
    });
  }
});

test("app.js covers fallback helpers and forward modal focus trapping", async () => {
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  const plain = new FakeNode("plain");
  plain.value = "unchanged";
  assert.equal(harness.api.readConfigControl(plain), "unchanged");
  assert.equal(harness.api.evidenceRowKey("opaque", 7), "row:7");
  assert.equal(harness.api.activeEvidenceKind(), "specialists");

  const activeTab = new FakeNode("receipts-tab");
  activeTab.dataset.evidence = "receipts";
  harness.select(".subnav-item.active", [activeTab]);
  assert.equal(harness.api.activeEvidenceKind(), "receipts");

  const first = new FakeNode("first");
  const last = new FakeNode("last");
  harness.node("confirmation-modal").queryNodes = [first, last];
  const cancelled = harness.api.requestConfirmation("CONFIRM", "Confirm it.");
  harness.document.activeElement = last;
  let prevented = false;
  harness.api.handleModalKeyboard({
    key: "Tab",
    preventDefault() { prevented = true; },
    shiftKey: false,
  });
  assert.equal(prevented, true);
  assert.equal(first.focusCount, 1);
  harness.api.finishConfirmation(false);
  assert.equal(await cancelled, false);

  harness.node("config-provider-secret-index").value = "";
  harness.node("config-provider-secret").value = "new-secret";
  assert.throws(
    () => harness.api.collectConfigChanges(),
    /select a provider before changing its direct key/i,
  );
});

test("app.js reconnects from stored credentials and surfaces missing tokens", async () => {
  const payloads = new Map([
    ["/api/live?limit=100", {
      activity: {},
      overview: { status: "ok" },
      revision: "connected",
      schema_version: 1,
    }],
    ["/api/hosts", { hosts: [] }],
    ["/api/roster?limit=100", { agents: [] }],
    ["/api/snapshots", { snapshots: [] }],
    ["/api/config", { effective: {}, revision: "config" }],
  ]);
  const connected = createAppHarness(async (path) => jsonResponse(200, payloads.get(path)));
  connected.sessionValues.set("agency-dashboard-token", "stored-token");
  connected.api.showNotice("Connecting");
  await connected.api.connectFromLocation();
  assert.equal(connected.api.state.token, "stored-token");
  assert.equal(connected.node("notice").hidden, true);
  assert.equal(connected.node("connection-label").textContent, "Authenticated");

  let calls = 0;
  const missing = createAppHarness(async () => {
    calls += 1;
    return jsonResponse(500, {});
  });
  await missing.api.connectFromLocation();
  assert.equal(calls, 0);
  assert.equal(missing.node("connection-label").textContent, "Token required");
  assert.match(missing.node("notice").textContent, /no active access token/i);
});

test("app.js renders independent graphs and roster control refreshes", () => {
  const harness = createAppHarness(() => {
    throw new Error("render-only test does not fetch");
  });
  harness.api.renderReceipt({
    delegation_graph: {
      edges: [],
      nodes: [{ description: "Review auth", id: "unit-1" }],
    },
    selected: [],
  });
  assert.ok(
    descendants(harness.node("route-result"))
      .some((node) => /run independently/i.test(node.textContent)),
  );

  harness.api.state.activeView = "roster";
  harness.api.state.roster = [{ agent_slug: "reviewer", capabilities: [] }];
  harness.api.renderActiveControlView();
  assert.equal(harness.node("roster-count").textContent, "1 enabled · 1 total");
});

test("app.js renders a bounded recommendation-only unit delegation plan safely", () => {
  const harness = createAppHarness(() => {
    throw new Error("render-only test does not fetch");
  });
  const maliciousEvidence = "<img src=x onerror=alert(1)>";
  const units = Array.from({ length: 20 }, (_, index) => ({
    assignment_strength: index ? "preferred" : "strongly_preferred",
    compatible_specialists: ["security-reviewer", "evidence-reviewer"],
    confidence: 0.91,
    dependencies: index ? ["unit-0"] : [],
    expected_deliverable: "Prioritized findings with reproducible evidence.",
    goal_preview: `Review boundary ${index}`,
    mutation_scope: "read_only",
    parallelization: "parallel",
    rationale_codes: ["detected:clauses", "policy:prefer"],
    recommended_agent: "security-reviewer",
    required_evidence: [
      maliciousEvidence,
      ...Array.from({ length: 10 }, (_, tokenIndex) => `receipt-${tokenIndex}`),
    ],
    required_tools: ["repository-read"],
    work_unit_id: `unit-${index}`,
  }));
  units[0].work_unit_id = "";
  units[1].assignment_strength = "";
  units[2].recommended_agent = "";
  units[3].goal_preview = "";
  units[4].confidence = "invalid";
  units[5].expected_deliverable = "";
  units[5].deliverable_kind = "review";
  units[6].expected_deliverable = "";
  units[6].deliverable_kind = "";
  units[7].parallelization = "";
  units[7].mutation_scope = "";
  units[8].dependencies = "invalid";
  units[9].compatible_specialists = [];
  units[10].required_tools = "invalid";
  units[14] = null;
  units[15] = "invalid";

  harness.api.renderReceipt({
    delegation_graph: { edges: [], nodes: [] },
    delegation_plan: {
      authority: "recommendation_only",
      evidence_contract: "A plan is not execution. Correlated evidence is required.",
      execution_host: "codex",
      mechanism: "Dispatch with Codex spawn_agent.",
      units,
    },
  });

  const rendered = descendants(harness.node("route-result"));
  assert.ok(rendered.some((node) => /recommendation only.*not proof/i.test(node.textContent)));
  assert.ok(rendered.some((node) => node.textContent === "Dispatch with Codex spawn_agent."));
  assert.ok(rendered.some((node) => /correlated evidence is required/i.test(node.textContent)));
  assert.ok(rendered.some((node) => node.textContent === maliciousEvidence));
  assert.equal(rendered.some((node) => node.id === "img"), false);
  const planList = rendered.find((node) => node.className === "delegation-plan-list");
  assert.equal(planList.getAttribute("role"), "list");
  assert.equal(
    rendered.filter((node) => node.className === "delegation-plan-unit").length,
    14,
  );
  const firstEvidenceGroup = rendered.find(
    (node) => node.className === "delegation-plan-tokens"
      && node.children[0]?.textContent === "Required evidence",
  );
  assert.equal(firstEvidenceGroup.children[1].children.length, 8);

  harness.api.renderReceipt({
    delegation_graph: {},
    delegation_plan: {
      authority: "recommendation_only",
      evidence_contract: "No execution evidence.",
      mechanism: "Use the available native delegation mechanism.",
      units: [],
    },
  });
  assert.ok(
    descendants(harness.node("route-result"))
      .some((node) => /no unit-to-specialist assignments/i.test(node.textContent)),
  );
  assert.ok(
    descendants(harness.node("route-result"))
      .some((node) => node.textContent === "Native host mechanism"),
  );
});

test("app.js handles control-plane and full-refresh error classes", async () => {
  const terminal = createAppHarness(async () => jsonResponse(401, { error: "expired" }));
  await terminal.api.refreshControlPlane();
  assert.equal(terminal.api.state.live.terminal, true);
  assert.equal(terminal.node("connection-label").textContent, "Token expired");

  const aborted = createAppHarness(async () => {
    const error = new Error("cancelled");
    error.name = "AbortError";
    throw error;
  });
  assert.equal(await aborted.api.refreshAll(), false);
  assert.equal(aborted.node("connection-label").textContent, "");

  const unavailable = createAppHarness(async () => {
    throw new Error("network unavailable");
  });
  assert.equal(await unavailable.api.refreshAll(), undefined);
  assert.equal(unavailable.node("connection-label").textContent, "Unavailable");
  assert.match(unavailable.node("notice").textContent, /network unavailable/i);
  await assert.rejects(
    unavailable.api.refreshAll({ surfaceErrors: false }),
    /network unavailable/i,
  );

  const fullTerminal = createAppHarness(async () => jsonResponse(403, { error: "forbidden" }));
  assert.equal(await fullTerminal.api.refreshAll(), undefined);
  assert.equal(fullTerminal.api.state.live.terminal, true);
});

test("app.js reports post-mutation reconciliation failures without hiding success", async () => {
  const transient = createAppHarness(async () => jsonResponse(503, { error: "live unavailable" }));
  await transient.api.reconcileRuntimeEvidence("Mutation completed.");
  assert.match(transient.node("notice").textContent, /mutation completed.*could not refresh/i);

  const terminal = createAppHarness(async () => jsonResponse(401, { error: "expired" }));
  await terminal.api.reconcileRuntimeEvidence("Mutation completed.");
  assert.equal(terminal.api.state.live.terminal, true);
  assert.match(terminal.node("notice").textContent, /token expired/i);

  const allTransient = createAppHarness(async () => jsonResponse(503, { error: "control unavailable" }));
  await allTransient.api.reconcileAll("Roster updated.");
  assert.match(allTransient.node("notice").textContent, /roster updated.*could not refresh/i);

  const allTerminal = createAppHarness(async () => jsonResponse(403, { error: "expired" }));
  await allTerminal.api.reconcileAll("Host updated.");
  assert.equal(allTerminal.api.state.live.terminal, true);
  assert.match(allTerminal.node("notice").textContent, /token expired/i);
});

test("app.js validates and completes runtime trimming", async () => {
  const calls = [];
  const payloads = new Map([
    ["/api/live?limit=100", {
      activity: {}, overview: { status: "ok" }, revision: "trimmed", schema_version: 1,
    }],
    ["/api/hosts", { hosts: [] }],
    ["/api/roster?limit=100", { agents: [] }],
    ["/api/snapshots", { snapshots: [] }],
    ["/api/config", { effective: {}, revision: "config" }],
  ]);
  const harness = createAppHarness(async (path, options) => {
    calls.push({ path, options });
    if (path === "/api/maintenance/trim") {
      return jsonResponse(200, { db_size_after_bytes: 1536 });
    }
    return jsonResponse(200, payloads.get(path));
  });

  await harness.api.trimRuntime();
  assert.match(harness.node("notice").textContent, /exact confirmation phrase/i);
  harness.node("trim-confirm").value = "TRIM RUNTIME DATA";
  harness.node("trim-days").value = "0";
  await harness.api.trimRuntime();
  assert.match(harness.node("notice").textContent, /integer from 1 through 3650/i);

  harness.node("trim-days").value = "45";
  harness.node("trim-days").dataset.dirty = "true";
  await harness.api.trimRuntime();
  assert.deepEqual(JSON.parse(calls[0].options.body), {
    confirm: "TRIM RUNTIME DATA",
    older_than_days: 45,
    vacuum: false,
  });
  assert.equal(harness.node("trim-confirm").value, "");
  assert.equal(harness.node("trim-days").dataset.dirty, undefined);
  assert.equal(harness.node("trim-button").disabled, false);
  assert.equal(harness.node("trim-button").getAttribute("aria-busy"), null);
  assert.match(harness.node("notice").textContent, /database is 1.5 KB/i);

  const failed = createAppHarness(async () => jsonResponse(500, { error: "trim failed" }));
  failed.node("trim-confirm").value = "TRIM RUNTIME DATA";
  failed.node("trim-days").value = "30";
  await failed.api.trimRuntime();
  assert.match(failed.node("notice").textContent, /trim failed/i);
  assert.equal(failed.node("trim-button").disabled, false);
});

async function answerConfirmation(harness, pending, phrase, accepted = true) {
  await Promise.resolve();
  if (accepted) harness.node("confirmation-input").value = phrase;
  harness.api.finishConfirmation(accepted);
  await pending;
}

test("app.js confirms, cancels, and completes roster, host, and agent actions", async () => {
  const calls = [];
  const payloads = new Map([
    ["/api/live?limit=100", {
      activity: {}, overview: { status: "ok" }, revision: "mutated", schema_version: 1,
    }],
    ["/api/hosts", { hosts: [] }],
    ["/api/roster?limit=100", { agents: [] }],
    ["/api/snapshots", { snapshots: [] }],
    ["/api/config", { effective: {}, revision: "config" }],
  ]);
  const harness = createAppHarness(async (path, options) => {
    calls.push({ path, options });
    if (
      path === "/api/roster/action"
      || path === "/api/hosts/toggle"
      || path === "/api/agents/toggle"
    ) {
      return jsonResponse(200, { ok: true });
    }
    return jsonResponse(200, payloads.get(path));
  });

  await answerConfirmation(
    harness,
    harness.api.rosterAction("approve", "snapshot-1"),
    "APPROVE snapshot-1",
    false,
  );
  assert.match(harness.node("notice").textContent, /roster action cancelled/i);
  assert.equal(calls.length, 0);

  await answerConfirmation(
    harness,
    harness.api.rosterAction("approve", "snapshot-1"),
    "APPROVE snapshot-1",
  );
  assert.equal(calls[0].path, "/api/roster/action");
  assert.deepEqual(JSON.parse(calls[0].options.body), {
    action: "approve",
    confirm: "APPROVE snapshot-1",
    snapshot_id: "snapshot-1",
  });
  assert.match(harness.node("notice").textContent, /snapshot snapshot-1 approved/i);

  calls.length = 0;
  await harness.api.toggleHost("codex", false);
  assert.match(harness.node("notice").textContent, /host control state is stale/i);
  assert.equal(calls.length, 0);

  await answerConfirmation(
    harness,
    harness.api.toggleHost("codex", false, 0),
    "DISABLE codex",
    false,
  );
  assert.match(harness.node("notice").textContent, /host action cancelled/i);
  assert.equal(calls.length, 0);

  await answerConfirmation(
    harness,
    harness.api.toggleHost("codex", false, 0),
    "DISABLE codex",
  );
  assert.equal(calls[0].path, "/api/hosts/toggle");
  assert.deepEqual(JSON.parse(calls[0].options.body), {
    confirm: "DISABLE codex",
    enabled: false,
    expected_generation: 0,
    host: "codex",
  });
  assert.match(harness.node("notice").textContent, /codex runtime disabled/i);

  calls.length = 0;
  harness.api.state.config = { revision: "activation-revision" };
  harness.api.state.controlConfigRevision = "activation-revision";
  await answerConfirmation(
    harness,
    harness.api.toggleAgent("security-reviewer", false),
    "DISABLE security-reviewer",
    false,
  );
  assert.match(harness.node("notice").textContent, /agent action cancelled/i);
  assert.equal(calls.length, 0);

  await answerConfirmation(
    harness,
    harness.api.toggleAgent("security-reviewer", false),
    "DISABLE security-reviewer",
  );
  assert.equal(calls[0].path, "/api/agents/toggle");
  assert.deepEqual(JSON.parse(calls[0].options.body), {
    confirm: "DISABLE security-reviewer",
    enabled: false,
    expected_revision: "activation-revision",
    slug: "security-reviewer",
  });
  assert.match(harness.node("notice").textContent, /security-reviewer disabled/i);

  calls.length = 0;
  await answerConfirmation(
    harness,
    harness.api.toggleAgent("security-reviewer", true),
    "ENABLE security-reviewer",
  );
  assert.equal(calls[0].path, "/api/agents/toggle");
  assert.match(harness.node("notice").textContent, /security-reviewer enabled/i);

  calls.length = 0;
  const suspendedAction = harness.api.toggleAgent("security-reviewer", false);
  harness.api.state.lifecycle.suspended = true;
  await answerConfirmation(
    harness,
    suspendedAction,
    "DISABLE security-reviewer",
  );
  harness.api.state.lifecycle.suspended = false;
  assert.equal(calls.length, 0);

  const failed = createAppHarness(async () => jsonResponse(500, { error: "mutation failed" }));
  await answerConfirmation(
    failed,
    failed.api.rosterAction("activate", "snapshot-2"),
    "ACTIVATE snapshot-2",
  );
  assert.match(failed.node("notice").textContent, /mutation failed/i);
  await answerConfirmation(
    failed,
    failed.api.toggleHost("claude", true, 0),
    "ENABLE claude",
  );
  assert.match(failed.node("notice").textContent, /mutation failed/i);
  await answerConfirmation(
    failed,
    failed.api.toggleAgent("code-reviewer", true),
    "ENABLE code-reviewer",
  );
  assert.match(failed.node("notice").textContent, /mutation failed/i);
});

test("app.js ignores an agent mutation response after its request is cancelled", async () => {
  const response = deferred();
  const harness = createAppHarness(async (path) => {
    assert.equal(path, "/api/agents/toggle");
    return response.promise;
  });
  harness.api.state.config = { revision: "activation-revision" };

  const action = harness.api.toggleAgent("code-reviewer", true);
  await Promise.resolve();
  harness.node("confirmation-input").value = "ENABLE code-reviewer";
  harness.api.finishConfirmation(true);
  await Promise.resolve();
  harness.api.cancelMutationRequests();
  response.resolve(jsonResponse(200, { ok: true }));
  await action;

  assert.doesNotMatch(harness.node("notice").textContent, /code-reviewer enabled/i);
});

test("dirty settings preserve editor inputs while successive agent toggles advance CAS", async () => {
  const toggleRevisions = [];
  let revision = "revision-0";
  const harness = createAppHarness(async (path, options = {}) => {
    if (path === "/api/agents/toggle") {
      const body = JSON.parse(options.body);
      toggleRevisions.push(body.expected_revision);
      assert.equal(body.expected_revision, revision);
      revision = `revision-${toggleRevisions.length}`;
      return jsonResponse(200, { config: { revision } });
    }
    if (path === "/api/live?limit=100") {
      return jsonResponse(200, {
        activity: {}, overview: { status: "ok" }, revision, schema_version: 1,
      });
    }
    if (path === "/api/hosts") return jsonResponse(200, { hosts: [] });
    if (path === "/api/roster?limit=100") return jsonResponse(200, { agents: [] });
    if (path === "/api/snapshots") return jsonResponse(200, { snapshots: [] });
    if (path === "/api/config") return jsonResponse(200, { effective: {}, revision });
    throw new Error(`unexpected request: ${path}`);
  });
  const retention = new FakeNode("config-retention");
  retention.dataset.configPath = "observability.retention_days";
  retention.dataset.valueType = "integer";
  retention.value = "31";
  harness.nodes.set("config-retention", retention);
  harness.select("[data-config-path]", [retention]);
  harness.api.state.activeView = "settings";
  harness.api.state.config = { revision: "revision-0" };
  harness.api.state.controlConfigRevision = "revision-0";
  harness.api.state.configBaseline.set("observability.retention_days", "30");
  harness.api.state.configDirty = true;

  await answerConfirmation(
    harness,
    harness.api.toggleAgent("code-reviewer", false),
    "DISABLE code-reviewer",
  );
  assert.equal(harness.api.state.config.revision, "revision-0");
  assert.equal(harness.api.state.controlConfigRevision, "revision-1");
  assert.equal(harness.api.state.pendingConfig.revision, "revision-1");
  assert.equal(retention.value, "31");

  await answerConfirmation(
    harness,
    harness.api.toggleAgent("security-reviewer", false),
    "DISABLE security-reviewer",
  );
  assert.deepEqual(toggleRevisions, ["revision-0", "revision-1"]);
  assert.equal(harness.api.state.controlConfigRevision, "revision-2");
  assert.equal(harness.api.state.pendingConfig.revision, "revision-2");
  assert.equal(harness.api.state.configDirty, true);
  assert.equal(retention.value, "31");
});

test("app.js preserves config edits after save failures", async () => {
  const harness = createAppHarness(async () => jsonResponse(409, { error: "revision conflict" }));
  const retention = new FakeNode("config-retention");
  retention.dataset.configPath = "observability.retention_days";
  retention.dataset.valueType = "integer";
  retention.value = "31";
  harness.nodes.set("config-retention", retention);
  harness.select("[data-config-path]", [retention]);
  harness.api.state.config = { revision: "original" };
  harness.api.state.configBaseline.set("observability.retention_days", "30");

  const saving = harness.api.saveConfig({ preventDefault() {} });
  await Promise.resolve();
  harness.node("confirmation-input").value = "SAVE CONFIG";
  harness.api.finishConfirmation(true);
  await saving;
  assert.match(harness.node("notice").textContent, /revision conflict/i);
  assert.equal(harness.api.state.configDirty, true);
  assert.equal(harness.node("config-save-button").disabled, false);
});

test("app.js supports every evidence-tab keyboard command", () => {
  const harness = createAppHarness(() => {
    throw new Error("keyboard-only test does not fetch");
  });
  const tabList = new FakeNode("tab-list");
  const tabs = ["delegations", "routing", "receipts"].map((kind, index) => {
    const tab = new FakeNode();
    tab.dataset.evidence = kind;
    tab.parentElement = tabList;
    if (index === 1) tab.classList.add("active");
    return tab;
  });
  harness.select(".subnav-item", tabs);
  harness.api.state.activity = { delegations: [], receipts: [], routing: [] };
  harness.api.configureEvidenceTabs();

  const invoke = (tab, key) => {
    let prevented = false;
    tab.listeners.get("keydown")[0]({ key, preventDefault() { prevented = true; } });
    return prevented;
  };
  assert.equal(invoke(tabs[1], "ArrowLeft"), true);
  assert.equal(tabs[0].focusCount, 1);
  assert.equal(invoke(tabs[1], "ArrowUp"), true);
  assert.equal(invoke(tabs[1], "ArrowDown"), true);
  assert.equal(invoke(tabs[1], "Home"), true);
  assert.equal(invoke(tabs[1], "End"), true);
  assert.equal(tabs[2].focusCount, 2);
  assert.equal(invoke(tabs[1], "Enter"), true);
  assert.equal(invoke(tabs[1], " "), true);
  assert.equal(invoke(tabs[1], "Escape"), false);
});

test("app.js wires reset, confirmation keyboard, and DOM startup handlers", async () => {
  const payloads = new Map([
    ["/api/live?limit=100", {
      activity: {}, overview: { status: "ok" }, revision: "startup", schema_version: 1,
    }],
    ["/api/hosts", { hosts: [] }],
    ["/api/roster?limit=100", { agents: [] }],
    ["/api/snapshots", { snapshots: [] }],
    ["/api/config", { effective: {}, revision: "startup-config" }],
  ]);
  const harness = createAppHarness(async (path) => jsonResponse(200, payloads.get(path)));
  harness.sessionValues.set("agency-dashboard-token", "startup-token");
  harness.api.bindEvents();

  harness.api.state.pendingConfig = { effective: {}, revision: "pending-reset" };
  harness.node("config-reset-button").listeners.get("click")[0]();
  assert.equal(harness.api.state.config.revision, "pending-reset");

  let enterPrevented = false;
  const accepted = harness.api.requestConfirmation("ENTER", "Press Enter.");
  harness.node("confirmation-input").value = "ENTER";
  harness.node("confirmation-input").listeners.get("keydown")[0]({
    key: "Enter",
    preventDefault() { enterPrevented = true; },
  });
  assert.equal(enterPrevented, true);
  assert.equal(await accepted, true);

  let escapePrevented = false;
  const cancelled = harness.api.requestConfirmation("ESCAPE", "Press Escape.");
  harness.node("confirmation-input").listeners.get("keydown")[0]({
    key: "Escape",
    preventDefault() { escapePrevented = true; },
  });
  assert.equal(escapePrevented, true);
  assert.equal(await cancelled, false);

  await harness.documentListeners.get("DOMContentLoaded")[0]();
  assert.equal(harness.api.state.live.revision, "startup");
  assert.equal(harness.node("connection-label").textContent, "Authenticated");
  assert.notEqual(harness.api.state.clockTimer, null);
});

test("app.js executes every bound click, timer, and fragment callback", async () => {
  const payloads = new Map([
    ["/api/live?limit=100", {
      activity: {}, overview: { status: "ok" }, revision: "callback", schema_version: 1,
    }],
    ["/api/hosts", { hosts: [] }],
    ["/api/roster?limit=100", { agents: [] }],
    ["/api/snapshots", { snapshots: [] }],
    ["/api/config", { effective: {}, revision: "callback-config" }],
  ]);
  const harness = createAppHarness(async (path) => jsonResponse(200, payloads.get(path)));

  harness.api.showNotice("Temporary");
  const noticeTimer = harness.api.showNotice.timer;
  harness.timers.tasks.get(noticeTimer).callback();
  assert.equal(harness.node("notice").hidden, true);

  harness.api.state.hosts = [{
    executable_discovered: true,
    host: "codex",
    inspection_status: "complete",
    runtime_control_generation: 0,
    runtime_enabled: true,
  }];
  harness.api.renderHosts();
  const hostButton = descendants(harness.node("host-grid"))
    .find((node) => node.type === "button");
  hostButton.listeners.get("click")[0]();
  await Promise.resolve();
  harness.api.finishConfirmation(false);

  harness.api.state.snapshots = [{ approved: false, snapshot_id: "pending" }];
  harness.api.renderRoster();
  const rosterButton = descendants(harness.node("snapshot-list"))
    .find((node) => node.type === "button");
  rosterButton.listeners.get("click")[0]();
  await Promise.resolve();
  harness.api.finishConfirmation(false);

  const tab = new FakeNode();
  tab.classList.add("active");
  tab.dataset.evidence = "delegations";
  harness.select(".subnav-item", [tab]);
  harness.api.state.activity = { delegations: [] };
  harness.api.configureEvidenceTabs();
  tab.listeners.get("click")[0]();

  const nav = new FakeNode("nav-roster");
  nav.classList.add("active");
  nav.dataset.view = "roster";
  const panel = new FakeNode("panel-roster");
  panel.dataset.viewPanel = "roster";
  harness.select(".nav-item", [nav]);
  harness.select(".nav-item.active", [nav]);
  harness.select(".view", [panel]);
  harness.api.bindEvents();
  nav.listeners.get("click")[0]();
  assert.equal(harness.api.state.activeView, "roster");

  const cancelled = harness.api.requestConfirmation("CANCEL", "Cancel it.");
  harness.node("confirmation-cancel").listeners.get("click")[0]();
  assert.equal(await cancelled, false);
  const accepted = harness.api.requestConfirmation("ACCEPT", "Accept it.");
  harness.node("confirmation-input").value = "ACCEPT";
  harness.node("confirmation-accept").listeners.get("click")[0]();
  assert.equal(await accepted, true);

  harness.sessionValues.set("agency-dashboard-token", "fragment-token");
  harness.windowListeners.get("hashchange")[0]();
  await Promise.resolve();
  await Promise.resolve();
  assert.equal(harness.api.state.token, "fragment-token");
});

test("app.js exercises defensive configuration and optional-DOM branches", () => {
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  harness.api.finishConfirmation(false);
  harness.node("confirmation-modal").hidden = true;
  assert.equal(harness.api.modalFocusable().length, 0);
  harness.api.handleModalKeyboard({ key: "Tab", preventDefault() {} });
  harness.api.state.confirmation = { phrase: "x", resolve() {}, returnFocus: null };
  harness.api.handleModalKeyboard({ key: "A", preventDefault() {} });
  harness.node("confirmation-modal").hidden = false;
  harness.node("confirmation-modal").queryNodes = [];
  harness.api.handleModalKeyboard({ key: "Tab", preventDefault() {} });
  harness.api.finishConfirmation(false);

  const integer = new FakeNode("worker-count");
  integer.dataset.valueType = "integer";
  integer.value = "bad";
  assert.throws(() => harness.api.readConfigControl(integer), /worker-count/i);
  const number = new FakeNode("ratio");
  number.dataset.valueType = "number";
  number.value = "NaN";
  assert.throws(() => harness.api.readConfigControl(number), /ratio/i);
  const json = new FakeNode("metadata");
  json.dataset.valueType = "json";
  json.value = "{";
  assert.throws(() => harness.api.readConfigControl(json), /metadata/i);

  const boolean = new FakeNode("boolean");
  boolean.dataset.valueType = "boolean";
  harness.api.writeConfigControl(boolean, true);
  assert.equal(boolean.checked, true);
  const genericJson = new FakeNode("generic-json");
  genericJson.dataset.valueType = "json";
  harness.api.writeConfigControl(genericJson, null);
  assert.equal(genericJson.value, "[]");
  const nullableString = new FakeNode("nullable-string");
  harness.api.writeConfigControl(nullableString, null);
  assert.equal(nullableString.value, "");

  const clearOperations = [];
  harness.api.appendSecretOperation(clearOperations, "judge.api_key", "", true);
  assert.deepEqual(JSON.parse(JSON.stringify(clearOperations)), [{
    action: "clear", op: "secret", path: "judge.api_key",
  }]);

  const providers = new FakeNode("config-providers");
  providers.dataset.configPath = "providers";
  providers.dataset.valueType = "json";
  providers.value = "[{}]";
  harness.nodes.set("config-providers", providers);
  harness.api.syncProviderSecretOptions();
  assert.equal(harness.node("config-provider-secret-index").options[0].textContent, "Provider 1");

  assert.equal(harness.api.applyConfigSnapshot(null), false);
  harness.api.state.activeView = "settings";
  harness.api.state.configDirty = true;
  harness.api.state.config = {};
  harness.api.state.pendingConfig = { revision: "same" };
  assert.equal(harness.api.applyConfigSnapshot({ revision: "same", effective: {} }), false);

  const first = new FakeNode("first-control");
  first.dataset.configPath = "first";
  first.value = "changed";
  const second = new FakeNode("second-control");
  second.dataset.configPath = "second";
  second.value = "changed";
  harness.select("[data-config-path]", [first, second]);
  harness.api.state.configBaseline = new Map([["first", '"old"'], ["second", '"old"']]);
  harness.api.updateConfigDirtyState();
  assert.match(harness.node("config-change-count").textContent, /2 unsaved changes/i);

  harness.select("[data-config-path]", []);
  harness.api.renderConfig({ config: {}, environment_overrides: [], revision: null });
  assert.equal(harness.node("config-revision").textContent, "NEW FILE");
  assert.equal(harness.node("config-override-count").textContent, "NO OVERRIDES");
  assert.match(harness.node("config-path").textContent, /bundled defaults/i);

  harness.api.switchView("unrecognized");
  assert.equal(harness.node("view-title").textContent, "Agency Runtime");
  harness.missing("missing-metric");
  harness.api.setMetric("missing-metric", "ignored");
  harness.context.AgencyCharts = undefined;
  harness.api.renderCharts();
  harness.missing("live-toggle");
  harness.api.syncLiveToggle();
});

test("app.js renders sparse and changing runtime evidence defensively", () => {
  const harness = createAppHarness(() => {
    throw new Error("render-only test does not fetch");
  });
  harness.api.state.activeView = "evidence";
  const tab = new FakeNode("routing-tab");
  tab.dataset.evidence = "routing";
  harness.select(".subnav-item.active", [tab]);
  harness.api.state.activity = { routing: [] };
  harness.api.renderActiveView();
  harness.api.state.activeView = "roster";
  harness.api.renderActiveView();
  harness.api.state.activeView = "overview";
  harness.api.state.overview = null;
  harness.api.renderActiveControlView();
  harness.api.state.overview = {};
  harness.api.renderActiveControlView();

  assert.match(harness.api.evidenceRowKey({}, 3), /^trace:3$/);
  harness.api.state.overview = {
    provider_health: [{ failure_count: 0, provider: "local", success_count: 0, unknown_count: 1 }],
  };
  harness.api.state.hosts = [{ host: "codex", runtime_enabled: false }];
  harness.api.state.activity = {
    delegations: [{ started_at: null }],
  };
  harness.api.state.evidenceKeys.set("overview", new Set(["old"]));
  harness.api.renderOverview();
  assert.equal(harness.node("metric-runtime").textContent, "Unknown");
  assert.ok(harness.node("overview-delegations").children[0].classList.contains("is-new"));
  assert.ok(
    descendants(harness.node("overview-delegations"))
      .some((node) => node.textContent === "unassigned"),
  );

  harness.api.state.hosts = [
    { executable_discovered: false, host: "absent", runtime_enabled: false },
    { executable_discovered: true, host: "unknown", inspection_status: "complete" },
    { executable_discovered: true, host: "enabled", inspection_status: "complete", runtime_control_generation: 0, runtime_enabled: true },
    { executable_discovered: true, host: "disabled", inspection_status: "complete", runtime_control_generation: 0, runtime_enabled: false },
  ];
  harness.api.renderHosts();
  const buttons = descendants(harness.node("host-grid")).filter((node) => node.type === "button");
  assert.deepEqual(buttons.map((button) => button.textContent), ["State unknown", "Disable", "Enable"]);
  assert.equal(buttons[0].disabled, true);
  assert.equal(buttons[1].className.includes("danger"), true);
  assert.equal(buttons[2].className.includes("solid"), true);

  harness.api.state.activity = {
    finalizations: [{ action: "", missing: [], trace_id: "new" }],
  };
  harness.api.state.evidenceKeys.set("finalizations", new Set(["old"]));
  harness.api.renderEvidence("finalizations");
  const evidenceRow = harness.node("evidence-body").children[0];
  assert.equal(evidenceRow.classList.contains("is-new"), true);
  assert.ok(descendants(evidenceRow).some((node) => node.textContent === "—"));

  harness.api.renderReceipt({
    provider: "fallback-provider",
    selected: [{ agent_slug: "agent-two" }, { id: "agent-three" }, {}],
    signals: {
      selection: { provider: "judge", status: "ranked" },
      work_units: { units: [{ id: "unit" }] },
    },
  });
  assert.equal(harness.node("route-status").textContent, "RANKED");

  harness.api.updateLastSync("invalid");
  assert.equal(harness.node("last-sync").textContent, "Sync time unavailable");
  harness.api.updateLastSync();
  assert.match(harness.node("last-sync").textContent, /last sync/i);
});

test("app.js covers nested confirmations and final parsing fallbacks", async () => {
  const harness = createAppHarness(async () => jsonResponse(418, {}));

  const first = harness.api.requestConfirmation("FIRST", "First operation.");
  const second = harness.api.requestConfirmation("SECOND", "Second operation.");
  assert.equal(await first, false);
  harness.api.finishConfirmation(false);
  assert.equal(await second, false);

  harness.api.state.confirmation = { phrase: "x", resolve() {}, returnFocus: null };
  harness.node("confirmation-modal").hidden = false;
  harness.api.handleModalKeyboard({ key: "A", preventDefault() {} });
  harness.api.finishConfirmation(false);

  await assert.rejects(harness.api.api("/teapot"), /HTTP 418/);
  const number = new FakeNode("ratio");
  number.dataset.valueType = "number";
  number.labels = [{ textContent: "" }];
  number.value = "NaN";
  assert.throws(() => harness.api.readConfigControl(number), /ratio/i);
});

test("app.js covers sparse configuration and chart payload fallbacks", () => {
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  harness.select("[data-config-path]", []);
  harness.api.renderConfig({});
  assert.equal(harness.node("config-revision").textContent, "NEW FILE");
  harness.api.renderConfig({ effective: {}, environment_overrides: ["one", "two"] });
  assert.equal(harness.node("config-override-count").textContent, "2 ENV OVERRIDES");

  harness.api.state.activeView = "settings";
  harness.api.state.configDirty = true;
  harness.api.state.config = {};
  harness.api.state.pendingConfig = {};
  assert.equal(harness.api.applyConfigSnapshot({ revision: "new", effective: {} }), false);

  harness.context.AgencyCharts = {
    renderActivityChart: () => [],
    renderOutcomeChart: () => ({ failed: 0, skipped: 0, success: 0, unknown: 0 }),
  };
  harness.api.state.live.sampledAt = "invalid";
  harness.api.renderCharts();
  assert.match(harness.node("window-label").textContent, /^0 min window/);

  harness.api.state.overview = null;
  harness.api.renderOverview();
  assert.equal(harness.node("metric-runtime").textContent, "Unknown");
  harness.api.state.roster = [{ agent_slug: "no-capabilities-field" }];
  harness.api.state.snapshots = [];
  harness.api.renderRoster();
  assert.ok(
    descendants(harness.node("roster-grid"))
      .some((node) => node.textContent === "no capability tags"),
  );
});

test("app.js covers sparse receipts and live snapshots", () => {
  const harness = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  harness.api.renderReceipt({ delegation_graph: {} });
  assert.match(
    descendants(harness.node("route-result"))
      .find((node) => /no delegation work units/i.test(node.textContent)).textContent,
    /no delegation work units/i,
  );
  harness.api.renderReceipt({
    signals: { delegation: {}, work_units: {} },
    work_units: {},
  });
  assert.equal(harness.node("route-status").textContent, "COMPLETE");
  harness.api.renderReceipt({
    signals: { delegation: { work_units: { units: [{ id: "first-path" }] } } },
  });
  assert.ok(
    descendants(harness.node("route-result"))
      .some((node) => node.textContent.includes("first-path")),
  );

  harness.api.state.activeView = "routing";
  assert.equal(harness.api.applyLiveSnapshot({ schema_version: 1 }), true);
  assert.equal(harness.api.state.live.revision, "");
  assert.deepEqual(JSON.parse(JSON.stringify(harness.api.state.activity)), {});
  assert.deepEqual(JSON.parse(JSON.stringify(harness.api.state.overview)), {});

  harness.api.state.activeView = "overview";
  harness.api.state.live.chartWindow = 1;
  assert.equal(harness.api.applyLiveSnapshot({
    revision: "",
    sampled_at: "invalid",
    schema_version: 1,
  }), false);
});

test("app.js covers cancellation, stale control responses, and fallback retry", async () => {
  const retry = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  retry.context.AgencyCharts = undefined;
  retry.api.handleLiveFailure(new Error("offline"));
  assert.equal(retry.timers.tasks.get(retry.api.state.live.timer).delay, 2000);

  const livePending = deferred();
  const staleLive = createAppHarness(() => livePending.promise);
  const poll = staleLive.api.runLivePoll();
  staleLive.api.state.live.generation += 1;
  livePending.resolve(jsonResponse(200, { revision: "stale", schema_version: 1 }));
  await poll;
  assert.equal(staleLive.api.state.live.revision, "");
  assert.equal(staleLive.api.state.live.timer, null);

  const activeControl = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  const controller = new AbortController();
  activeControl.api.state.control.controller = controller;
  activeControl.api.cancelControlRequest();
  assert.equal(controller.signal.aborted, true);

  const requests = [];
  const staleControl = createAppHarness(() => {
    const pending = deferred();
    requests.push(pending);
    return pending.promise;
  });
  const refresh = staleControl.api.refreshControlPlane();
  staleControl.api.cancelControlRequest();
  requests.forEach((pending) => pending.resolve(jsonResponse(200, {})));
  await refresh;
  assert.equal(staleControl.api.state.control.timer, null);

  const sparseControl = createAppHarness(async () => jsonResponse(200, {}));
  await sparseControl.api.refreshControlPlane();
  assert.equal(sparseControl.api.state.hosts.length, 0);
  assert.equal(sparseControl.api.state.roster.length, 0);
  assert.equal(sparseControl.api.state.snapshots.length, 0);

  const hiddenClock = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  hiddenClock.document.visibilityState = "hidden";
  hiddenClock.api.updateLocalClock();
  assert.equal(hiddenClock.api.state.clockTimer, null);
});

test("app.js refreshes sparse payloads while live updates are paused", async () => {
  const payloads = new Map([
    ["/api/live?limit=100", { schema_version: 1 }],
    ["/api/hosts", {}],
    ["/api/roster?limit=100", {}],
    ["/api/snapshots", {}],
    ["/api/config", { config: {} }],
  ]);
  const harness = createAppHarness(async (path) => jsonResponse(200, payloads.get(path)));
  harness.api.state.live.enabled = false;
  assert.equal(await harness.api.refreshAll(), true);
  assert.equal(harness.api.state.hosts.length, 0);
  assert.equal(harness.api.state.roster.length, 0);
  assert.equal(harness.api.state.snapshots.length, 0);
  assert.equal(harness.node("live-status").textContent, "Live updates paused");
  assert.equal(harness.node("live-status").dataset.state, "paused");

  const emptyConfigPayloads = new Map(payloads);
  emptyConfigPayloads.set("/api/config", {});
  const emptyConfig = createAppHarness(async (path) => (
    jsonResponse(200, emptyConfigPayloads.get(path))
  ));
  assert.equal(await emptyConfig.api.refreshAll(), true);
  assert.equal(emptyConfig.api.state.overview.capture_content, false);
  assert.equal(emptyConfig.api.state.overview.retention_days, undefined);
  assert.equal(emptyConfig.api.state.overview.roster_count, 0);
});

test("app.js covers route and save validation, cancellation, and restart messages", async () => {
  const routeFailure = createAppHarness(async () => jsonResponse(500, { error: "route failed" }));
  routeFailure.node("route-task").value = "Review this";
  routeFailure.node("route-host").value = "codex";
  await routeFailure.api.runRoute();
  assert.equal(routeFailure.node("route-status").textContent, "FAILED");
  assert.match(routeFailure.node("notice").textContent, /route failed/i);

  const invalid = createAppHarness(() => {
    throw new Error("validation must stop the request");
  });
  const invalidControl = new FakeNode("count");
  invalidControl.dataset.configPath = "count";
  invalidControl.dataset.valueType = "integer";
  invalidControl.value = "bad";
  invalid.select("[data-config-path]", [invalidControl]);
  await invalid.api.saveConfig({ preventDefault() {} });
  assert.match(invalid.node("notice").textContent, /integer/i);

  const unchanged = createAppHarness(() => {
    throw new Error("unchanged config must not fetch");
  });
  unchanged.select("[data-config-path]", []);
  await unchanged.api.saveConfig({ preventDefault() {} });
  assert.equal(unchanged.api.state.confirmation, null);

  const cancelled = createAppHarness(() => {
    throw new Error("cancelled config must not fetch");
  });
  const changed = new FakeNode("profile");
  changed.dataset.configPath = "profile";
  changed.value = "balanced";
  cancelled.select("[data-config-path]", [changed]);
  cancelled.api.state.configBaseline.set("profile", '"old"');
  const cancelledSave = cancelled.api.saveConfig({ preventDefault() {} });
  await Promise.resolve();
  cancelled.api.finishConfirmation(false);
  await cancelledSave;
  assert.match(cancelled.node("notice").textContent, /save cancelled/i);

  const payloads = new Map([
    ["/api/live?limit=100", {
      activity: {}, overview: { status: "ok" }, revision: "saved", schema_version: 1,
    }],
  ]);
  const restarted = createAppHarness(async (path) => {
    if (path === "/api/config") {
      return jsonResponse(200, {
        effective: { profile: "balanced" },
        restart_required_paths: ["judge.model"],
        revision: "new",
      });
    }
    return jsonResponse(200, payloads.get(path));
  });
  const profile = new FakeNode("profile");
  profile.dataset.configPath = "profile";
  profile.value = "balanced";
  restarted.nodes.set("profile", profile);
  restarted.select("[data-config-path]", [profile]);
  restarted.api.state.configBaseline.set("profile", '"old"');
  const saving = restarted.api.saveConfig({ preventDefault() {} });
  await Promise.resolve();
  restarted.node("confirmation-input").value = "SAVE CONFIG";
  restarted.api.finishConfirmation(true);
  await saving;
  assert.match(restarted.node("notice").textContent, /restart required for: judge.model/i);

  const noRestart = createAppHarness(async (path) => {
    if (path === "/api/config") {
      return jsonResponse(200, { effective: { profile: "fast" }, revision: "newer" });
    }
    return jsonResponse(200, payloads.get(path));
  });
  const fastProfile = new FakeNode("profile");
  fastProfile.dataset.configPath = "profile";
  fastProfile.value = "fast";
  noRestart.nodes.set("profile", fastProfile);
  noRestart.select("[data-config-path]", [fastProfile]);
  noRestart.api.state.configBaseline.set("profile", '"old"');
  const saveWithoutRestart = noRestart.api.saveConfig({ preventDefault() {} });
  await Promise.resolve();
  noRestart.node("confirmation-input").value = "SAVE CONFIG";
  noRestart.api.finishConfirmation(true);
  await saveWithoutRestart;
  assert.match(noRestart.node("notice").textContent, /saved and active/i);
});

test("app.js covers enabled-host success and tab/reset fallbacks", async () => {
  const payloads = new Map([
    ["/api/live?limit=100", {
      activity: {}, overview: { status: "ok" }, revision: "enabled", schema_version: 1,
    }],
    ["/api/hosts", { hosts: [] }],
    ["/api/roster?limit=100", { agents: [] }],
    ["/api/snapshots", { snapshots: [] }],
    ["/api/config", { effective: {}, revision: "config" }],
  ]);
  const host = createAppHarness(async (path) => {
    if (path === "/api/hosts/toggle") return jsonResponse(200, {});
    return jsonResponse(200, payloads.get(path));
  });
  await answerConfirmation(host, host.api.toggleHost("claude", true, 0), "ENABLE claude");
  assert.match(host.node("notice").textContent, /claude runtime enabled/i);

  const tabs = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  const tabList = new FakeNode("tab-list");
  const tab = new FakeNode();
  tab.dataset.evidence = "";
  tab.parentElement = tabList;
  tabs.node("evidence-body").closestNode = new FakeNode("panel");
  tabs.select(".subnav-item", [tab]);
  tabs.api.configureEvidenceTabs();
  assert.equal(tab.id, "evidence-tab-0");
  assert.equal(tab.getAttribute("aria-selected"), "false");
  assert.equal(tabs.node("evidence-body").closestNode.getAttribute("aria-labelledby"), tab.id);

  const reset = createAppHarness(() => {
    throw new Error("this test does not fetch");
  });
  reset.api.bindEvents();
  reset.api.state.pendingConfig = null;
  reset.api.state.config = { effective: {}, revision: "current" };
  reset.node("config-reset-button").listeners.get("click")[0]();
  assert.equal(reset.api.state.config.revision, "current");
});

test("ES-module bootstrap and lifecycle teardown are deterministic", async () => {
  const harness = createAppHarness(() => {
    throw new Error("teardown must abort before fetching");
  });
  const nav = new FakeNode("nav-overview");
  nav.classList.add("active");
  nav.dataset.view = "overview";
  const panel = new FakeNode("view-overview");
  panel.dataset.viewPanel = "overview";
  const tab = new FakeNode("evidence-tab");
  tab.classList.add("active");
  tab.dataset.evidence = "delegations";
  harness.select(".nav-item", [nav]);
  harness.select(".nav-item.active", [nav]);
  harness.select(".view", [panel]);
  harness.select(".subnav-item", [tab]);

  assert.equal(harness.api.bindEvents(), true);
  assert.equal(harness.api.bindEvents(), false);
  harness.api.configureEvidenceTabs();
  assert.equal(nav.listeners.get("click").length, 1);
  assert.equal(tab.listeners.get("click").length, 1);

  harness.api.showNotice("clean me up");
  const metric = harness.node("metric-runtime");
  harness.api.markUpdated(metric);
  harness.api.markUpdated(metric);
  assert.equal(metric.listeners.get("animationend").length, 1);
  const confirmation = harness.api.requestConfirmation("CLOSE", "Close safely.");
  const mutation = harness.api.beginMutation();

  assert.equal(harness.api.destroy(), true);
  assert.equal(await confirmation, false);
  assert.equal(mutation.signal.aborted, true);
  assert.equal(harness.api.showNotice.timer, null);
  assert.equal(metric.listeners.get("animationend").length, 0);
  assert.equal(harness.documentListeners.get("visibilitychange").length, 0);
  assert.equal(harness.windowListeners.get("hashchange").length, 0);
  assert.equal(harness.api.finishMutation(mutation), false);
  assert.equal(harness.api.destroy(), false);
  assert.equal(await harness.api.start(), false);

  assert.equal(bootstrappedDashboard.state.lifecycle.destroyed, true);
});

test("connection and reconciliation generations reject stale async completions", async () => {
  const pendingRequests = [];
  const connected = createAppHarness((path) => {
    const pending = deferred();
    pendingRequests.push({ path, pending });
    return pending.promise;
  });
  connected.sessionValues.set("agency-dashboard-token", "stored-token");
  const connecting = connected.api.connectFromLocation();
  await Promise.resolve();
  connected.api.state.lifecycle.suspended = true;
  const payloads = new Map([
    ["/api/live?limit=100", { activity: {}, overview: {}, revision: "stale", schema_version: 1 }],
    ["/api/hosts", { hosts: [] }],
    ["/api/roster?limit=100", { agents: [] }],
    ["/api/snapshots", { snapshots: [] }],
    ["/api/config", { effective: {}, revision: "stale-config" }],
  ]);
  pendingRequests.forEach(({ path, pending }) => pending.resolve(jsonResponse(200, payloads.get(path))));
  assert.equal(await connecting, false);
  assert.equal(connected.node("connection-label").textContent, "");

  const rejected = deferred();
  const failed = createAppHarness(() => rejected.promise);
  failed.sessionValues.set("agency-dashboard-token", "stored-token");
  const staleFailure = failed.api.connectFromLocation();
  await Promise.resolve();
  failed.api.state.lifecycle.destroyed = true;
  rejected.reject(new Error("obsolete connection"));
  assert.equal(await staleFailure, false);
  assert.equal(failed.node("notice").textContent, "");

  const destroyedConnection = createAppHarness(() => {
    throw new Error("a missing token must fail before fetching");
  });
  destroyedConnection.api.state.lifecycle.destroyed = true;
  assert.equal(await destroyedConnection.api.connectFromLocation(), false);
  assert.equal(destroyedConnection.node("notice").textContent, "");

  const livePending = deferred();
  const live = createAppHarness(() => livePending.promise);
  const refreshing = live.api.refreshRuntimeEvidence();
  live.api.cancelLiveRequest();
  livePending.resolve(jsonResponse(200, { revision: "obsolete", schema_version: 1 }));
  assert.equal(await refreshing, false);
  assert.equal(live.api.state.live.revision, "");
  assert.equal(live.node("connection-label").textContent, "");

  live.api.state.lifecycle.destroyed = true;
  assert.equal(await live.api.reconcileRuntimeEvidence("ignored"), false);
  live.api.state.lifecycle.destroyed = false;
  live.api.state.lifecycle.suspended = true;
  assert.equal(await live.api.reconcileAll("ignored"), false);

  const reconcilePending = deferred();
  const staleReconcile = createAppHarness(() => reconcilePending.promise);
  const reconciling = staleReconcile.api.reconcileRuntimeEvidence("completed");
  staleReconcile.api.state.lifecycle.suspended = true;
  reconcilePending.reject(new Error("late failure"));
  assert.equal(await reconciling, false);
  assert.equal(staleReconcile.node("notice").textContent, "completed");
});

test("aborted mutations cannot render stale route, trim, config, roster, or host results", async () => {
  const requests = [];
  const harness = createAppHarness((path) => {
    const pending = deferred();
    requests.push({ path, pending });
    return pending.promise;
  });
  const takeRequest = (path) => {
    const index = requests.findIndex((request) => request.path === path);
    assert.notEqual(index, -1, `missing request for ${path}`);
    return requests.splice(index, 1)[0].pending;
  };

  harness.node("route-task").value = "inspect a stale route";
  harness.node("route-host").value = "codex";
  const routing = harness.api.runRoute();
  await Promise.resolve();
  const routeRequest = takeRequest("/api/route");
  assert.equal(harness.node("route-button").disabled, true);
  assert.equal(harness.node("route-button").getAttribute("aria-busy"), "true");
  harness.api.cancelMutationRequests();
  assert.equal(harness.node("refresh-button").disabled, false);
  routeRequest.resolve(jsonResponse(200, { status: "complete", selected: [{ slug: "late" }] }));
  await routing;
  assert.equal(harness.node("route-result").className, "");
  assert.equal(harness.node("route-status").textContent, "CANCELLED");
  assert.equal(harness.node("route-button").getAttribute("aria-busy"), null);

  harness.node("trim-confirm").value = "TRIM RUNTIME DATA";
  harness.node("trim-days").value = "30";
  const trimming = harness.api.trimRuntime();
  await Promise.resolve();
  const trimRequest = takeRequest("/api/maintenance/trim");
  assert.equal(harness.node("trim-button").disabled, true);
  assert.equal(harness.node("trim-button").getAttribute("aria-busy"), "true");
  harness.api.cancelMutationRequests();
  trimRequest.resolve(jsonResponse(200, { db_size_after_bytes: 1 }));
  await trimming;
  assert.equal(harness.node("trim-confirm").value, "TRIM RUNTIME DATA");
  assert.equal(harness.node("trim-button").getAttribute("aria-busy"), null);

  const profile = new FakeNode("config-profile");
  profile.dataset.configPath = "profile";
  profile.value = "power";
  harness.select("[data-config-path]", [profile]);
  harness.api.state.configBaseline.set("profile", '"standard"');
  harness.api.state.config = { revision: "before" };

  const suspendedSave = harness.api.saveConfig({ preventDefault() {} });
  await Promise.resolve();
  harness.api.state.lifecycle.suspended = true;
  harness.node("confirmation-input").value = "SAVE CONFIG";
  harness.api.finishConfirmation(true);
  await suspendedSave;
  assert.equal(requests.length, 0);
  harness.api.state.lifecycle.suspended = false;

  const saving = harness.api.saveConfig({ preventDefault() {} });
  await Promise.resolve();
  harness.node("confirmation-input").value = "SAVE CONFIG";
  harness.api.finishConfirmation(true);
  await Promise.resolve();
  const configRequest = takeRequest("/api/config");
  assert.equal(harness.node("config-save-button").disabled, true);
  assert.equal(harness.node("config-save-button").getAttribute("aria-busy"), "true");
  harness.api.cancelMutationRequests();
  configRequest.resolve(jsonResponse(200, { effective: { profile: "late" }, revision: "late" }));
  await saving;
  assert.equal(harness.api.state.config.revision, "before");
  assert.equal(harness.node("config-save-button").disabled, false);
  assert.equal(harness.node("config-save-button").getAttribute("aria-busy"), null);

  const suspendedRoster = harness.api.rosterAction("approve", "suspended");
  await Promise.resolve();
  harness.api.state.lifecycle.suspended = true;
  harness.node("confirmation-input").value = "APPROVE suspended";
  harness.api.finishConfirmation(true);
  await suspendedRoster;
  harness.api.state.lifecycle.suspended = false;

  const roster = harness.api.rosterAction("approve", "late-roster");
  await Promise.resolve();
  harness.node("confirmation-input").value = "APPROVE late-roster";
  harness.api.finishConfirmation(true);
  await Promise.resolve();
  const rosterRequest = takeRequest("/api/roster/action");
  harness.api.cancelMutationRequests();
  rosterRequest.resolve(jsonResponse(200, {}));
  await roster;

  const suspendedHost = harness.api.toggleHost("codex", false, 0);
  await Promise.resolve();
  harness.api.state.lifecycle.suspended = true;
  harness.node("confirmation-input").value = "DISABLE codex";
  harness.api.finishConfirmation(true);
  await suspendedHost;
  harness.api.state.lifecycle.suspended = false;

  const host = harness.api.toggleHost("codex", false, 0);
  await Promise.resolve();
  harness.node("confirmation-input").value = "DISABLE codex";
  harness.api.finishConfirmation(true);
  await Promise.resolve();
  const hostRequest = takeRequest("/api/hosts/toggle");
  harness.api.cancelMutationRequests();
  hostRequest.resolve(jsonResponse(200, {}));
  await host;

  assert.equal(requests.length, 0);
  assert.equal(harness.api.state.mutation.active, 0);
  assert.equal(harness.api.state.mutation.controllers.size, 0);
  assert.equal(harness.node("notice").textContent, "");
});

test("paged roster metadata drives global counts and accessible truncation disclosure", async () => {
  const hostileCursor = 'page/<img src=x onerror="compromised=true">';
  const payloads = new Map([
    ["/api/live?limit=100", {
      activity: {},
      overview: { status: "ok" },
      revision: "paged-roster",
      schema_version: 1,
    }],
    ["/api/hosts", { hosts: [] }],
    ["/api/roster?limit=100", {
      agents: [
        { agent_slug: "first", capabilities: [] },
        { agent_slug: "second", capabilities: [] },
      ],
      count: 2,
      total_count: 6,
      enabled_count: 4,
      disabled_count: 2,
      limit: 2,
      truncated: true,
      next_cursor: hostileCursor,
    }],
    ["/api/snapshots", { snapshots: [] }],
    ["/api/config", { effective: {}, revision: "paged-config" }],
  ]);
  const harness = createAppHarness(async (path) => jsonResponse(200, payloads.get(path)));

  assert.equal(await harness.api.refreshAll(), true);
  assert.deepEqual(harness.api.state.rosterPage, {
    agents: harness.api.state.roster,
    count: 2,
    total_count: 6,
    enabled_count: 4,
    disabled_count: 2,
    limit: 2,
    truncated: true,
    next_cursor: hostileCursor,
  });
  assert.equal(harness.api.state.overview.roster_count, 4);
  assert.equal(harness.node("metric-roster").textContent, "4");

  harness.api.state.activeView = "roster";
  harness.api.renderRoster();
  const pageStatus = harness.node("roster-page-status");
  assert.equal(harness.node("roster-count").textContent, "4 enabled · 6 total");
  assert.equal(pageStatus.hidden, false);
  assert.match(pageStatus.textContent, /showing 2 of 6 governed specialists/i);
  assert.match(pageStatus.textContent, /4 are not shown/i);
  assert.match(pageStatus.textContent, /find any specialist by its exact agent slug/i);
  assert.equal(pageStatus.textContent.includes("<img"), false);
  assert.equal(harness.node("roster-search-clear").hidden, true);
  assert.equal(harness.context.compromised, undefined);

  harness.api.applyRosterPage({
    agents: [{ agent_slug: "only", capabilities: [] }],
    count: 1,
    total_count: 1,
    limit: 50,
    truncated: false,
    next_cursor: null,
  });
  harness.api.renderRoster();
  assert.equal(harness.node("roster-count").textContent, "1 enabled · 1 total");
  assert.equal(pageStatus.hidden, true);
  assert.equal(pageStatus.textContent, "");

  harness.api.applyRosterPage({
    agents: [{ agent_slug: "first", capabilities: [] }],
    count: 1,
    total_count: 3,
    limit: 1,
    truncated: true,
  });
  harness.api.renderRoster();
  assert.match(pageStatus.textContent, /exact agent slug/i);

  harness.api.applyRosterPage({
    agents: [],
    count: 0,
    total_count: 2,
    limit: 0,
    truncated: true,
    next_cursor: "empty-page",
  });
  harness.api.renderRoster();
  assert.match(pageStatus.textContent, /showing 0 of 2/i);

  harness.api.state.rosterFilter = "missing-agent";
  harness.api.renderRoster();
  assert.match(pageStatus.textContent, /no governed specialist matches missing-agent/i);
  assert.equal(harness.node("roster-search-clear").hidden, false);
  harness.api.state.rosterFilter = "";

  assert.deepEqual(harness.api.applyRosterPage({
    agents: "invalid",
    count: -1,
    total_count: -2,
    limit: 0,
    truncated: "true",
    next_cursor: 7,
  }), {
    agents: [],
    count: 0,
    total_count: 0,
    enabled_count: 0,
    disabled_count: 0,
    limit: 0,
    truncated: false,
    next_cursor: null,
  });
  assert.deepEqual(harness.api.applyRosterPage(), {
    agents: [],
    count: 0,
    total_count: 0,
    enabled_count: 0,
    disabled_count: 0,
    limit: 0,
    truncated: false,
    next_cursor: null,
  });

  const optionalStatus = createAppHarness(() => {
    throw new Error("rendering roster metadata does not fetch");
  });
  optionalStatus.missing("roster-page-status");
  optionalStatus.api.state.roster = [];
  optionalStatus.api.renderRoster();
  assert.equal(optionalStatus.node("roster-count").textContent, "0 enabled · 0 total");
});

test("exact roster search reaches and toggles an agent beyond the first thousand", async () => {
  const calls = [];
  let targetEnabled = true;
  const initialRoster = {
    agents: [{ agent_slug: "agent-0000", capabilities: [] }],
    count: 1000,
    total_count: 1002,
    enabled_count: 1002,
    disabled_count: 0,
    limit: 1000,
    truncated: true,
    next_cursor: "agent-0999",
  };
  const harness = createAppHarness(async (path, options = {}) => {
    calls.push({ path, options });
    if (path === "/api/live?limit=100") {
      return jsonResponse(200, {
        activity: {}, overview: { status: "ok" }, revision: "roster-search", schema_version: 1,
      });
    }
    if (path === "/api/hosts") return jsonResponse(200, { hosts: [] });
    if (path === "/api/snapshots") return jsonResponse(200, { snapshots: [] });
    if (path === "/api/config") {
      return jsonResponse(200, { effective: {}, revision: "activation-revision" });
    }
    if (path === "/api/roster?limit=100") return jsonResponse(200, initialRoster);
    if (path === "/api/agents/lookup?slug=agent-1000") {
      return jsonResponse(200, {
        agents: [{
          agent_slug: "agent-1000",
          capabilities: ["deep-review"],
          enabled: targetEnabled,
        }],
        count: 1,
        total_count: 1002,
        enabled_count: targetEnabled ? 1002 : 1001,
        disabled_count: targetEnabled ? 0 : 1,
        limit: 1,
        truncated: false,
        next_cursor: null,
      });
    }
    if (path === "/api/agents/toggle") {
      targetEnabled = JSON.parse(options.body).enabled;
      return jsonResponse(200, { ok: true });
    }
    throw new Error(`unexpected request: ${path}`);
  });

  harness.api.state.activeView = "roster";
  harness.node("roster-search-slug").value = " Agent-1000 ";
  let prevented = false;
  assert.equal(await harness.api.searchRoster({ preventDefault() { prevented = true; } }), true);
  assert.equal(prevented, true);
  assert.equal(harness.api.state.rosterFilter, "agent-1000");
  assert.equal(harness.node("roster-search-slug").value, "agent-1000");
  assert.equal(harness.node("roster-search-clear").hidden, false);
  assert.match(harness.node("roster-page-status").textContent, /exact governed specialist match/i);
  assert.ok(calls.some(({ path }) => path === "/api/agents/lookup?slug=agent-1000"));

  const disable = descendants(harness.node("roster-grid"))
    .find((node) => node.type === "button" && node.textContent === "disable");
  const toggling = disable.listeners.get("click")[0]();
  await Promise.resolve();
  harness.node("confirmation-input").value = "DISABLE agent-1000";
  harness.api.finishConfirmation(true);
  await toggling;
  const toggleCall = calls.find(({ path }) => path === "/api/agents/toggle");
  assert.deepEqual(JSON.parse(toggleCall.options.body), {
    confirm: "DISABLE agent-1000",
    enabled: false,
    expected_revision: "activation-revision",
    slug: "agent-1000",
  });
  assert.equal(harness.api.state.roster[0].enabled, false);
  assert.match(harness.node("notice").textContent, /agent-1000 disabled/i);

  assert.equal(await harness.api.clearRosterSearch(), true);
  assert.equal(harness.api.state.rosterFilter, "");
  assert.equal(harness.node("roster-search-clear").hidden, true);

  const requestsBeforeInvalid = calls.length;
  harness.node("roster-search-slug").value = '<img src=x onerror="compromised=true">';
  assert.equal(await harness.api.searchRoster({ preventDefault() {} }), false);
  assert.equal(calls.length, requestsBeforeInvalid);
  assert.match(harness.node("notice").textContent, /agent slug must use/i);
  assert.equal(harness.context.compromised, undefined);
});

test("roster search markup permits the normalization performed before lookup", () => {
  const searchInput = INDEX_SOURCE.match(/<input id="roster-search-slug"[^>]*>/)?.[0] || "";
  assert.doesNotMatch(searchInput, /\s(?:pattern|minlength)=/);
  assert.match(searchInput, /maxlength="256"/);
  assert.match(searchInput, /aria-describedby="roster-search-help"/);

  const harness = createAppHarness(() => {
    throw new Error("normalization-only test does not fetch");
  });
  assert.equal(harness.api.normalizeRosterFilter("  Security-Reviewer  "), "security-reviewer");
});

test("roster search rolls back failed lookups and refuses inactive lifecycles", async () => {
  let calls = 0;
  const harness = createAppHarness(async () => {
    calls += 1;
    return jsonResponse(503, { error: "lookup unavailable" });
  });
  harness.api.state.activeView = "roster";
  harness.api.state.rosterFilter = "current-agent";
  harness.node("roster-search-slug").value = "current-agent";

  assert.equal(await harness.api.applyRosterFilter("target-agent"), false);
  assert.equal(harness.api.state.rosterFilter, "current-agent");
  assert.equal(harness.node("roster-search-slug").value, "current-agent");
  assert.match(harness.node("notice").textContent, /lookup unavailable/i);
  assert.ok(calls > 0);

  const callsAfterFailure = calls;
  harness.api.state.lifecycle.destroyed = true;
  assert.equal(await harness.api.applyRosterFilter("target-agent"), false);
  harness.api.state.lifecycle.destroyed = false;
  harness.api.state.lifecycle.suspended = true;
  assert.equal(await harness.api.applyRosterFilter("target-agent"), false);
  assert.equal(calls, callsAfterFailure);
});

test("Agency master control is accessible, confirmed, CAS-bound, and live-reconciled", async () => {
  const calls = [];
  const enabledMaster = {
    schema_version: 1,
    enabled: true,
    generation: 9,
    updated_at: "2026-07-16T12:00:00Z",
    source: "dashboard",
  };
  const disabledMaster = {
    ...enabledMaster,
    enabled: false,
    generation: 8,
    updated_at: "2026-07-16T11:59:00Z",
  };
  const harness = createAppHarness(async (path, options = {}) => {
    calls.push({ path, options });
    if (path === "/api/runtime/toggle") {
      return jsonResponse(200, { ok: true, changed: true, master: disabledMaster });
    }
    if (path === "/api/live?limit=100") {
      return jsonResponse(200, {
        schema_version: 1,
        revision: "master-disabled",
        sampled_at: "2026-07-16T11:59:00Z",
        overview: { status: "ok" },
        activity: {},
        master: disabledMaster,
      });
    }
    if (path === "/api/hosts") {
      return jsonResponse(200, { hosts: [verifiedHost("codex")], master: disabledMaster });
    }
    if (path === "/api/roster?limit=100") return jsonResponse(200, { agents: [] });
    if (path === "/api/snapshots") return jsonResponse(200, { snapshots: [] });
    if (path === "/api/config") return jsonResponse(200, { effective: {}, revision: "master" });
    throw new Error(`unexpected request: ${path}`);
  });

  harness.node("route-host").value = "codex";
  harness.api.applyMasterState({ ...enabledMaster, generation: 7 });
  assert.equal(harness.node("master-toggle").getAttribute("aria-pressed"), "true");
  assert.equal(harness.node("master-toggle").getAttribute("aria-label"), "Disable Agency Runtime globally");
  assert.equal(harness.node("master-label").textContent, "Agency on");
  assert.equal(harness.node("master-generation").textContent, "GEN 7");
  assert.equal(harness.node("runtime-paused-banner").hidden, true);
  assert.equal(harness.node("route-button").disabled, false);

  await answerConfirmation(
    harness,
    harness.api.toggleMaster(false),
    "DISABLE AGENCY",
  );

  const toggleCall = calls.find(({ path }) => path === "/api/runtime/toggle");
  assert.deepEqual(JSON.parse(toggleCall.options.body), {
    enabled: false,
    confirm: "DISABLE AGENCY",
    expected_generation: 7,
  });
  assert.equal(harness.api.state.master.enabled, false);
  assert.equal(harness.api.state.master.generation, 8);
  assert.equal(harness.node("master-toggle").getAttribute("aria-pressed"), "false");
  assert.equal(harness.node("master-toggle").getAttribute("aria-label"), "Enable Agency Runtime globally");
  assert.equal(harness.node("master-label").textContent, "Agency off");
  assert.equal(harness.node("runtime-paused-banner").hidden, false);
  assert.equal(harness.node("route-button").disabled, true);
  assert.equal(harness.node("route-button").getAttribute("aria-disabled"), "true");
  assert.equal(harness.node("route-status").textContent, "BYPASSED");
  assert.equal(harness.node("shell").classList.contains("agency-paused"), true);
  assert.match(harness.node("master-summary").textContent, /configuration remain available/i);

  harness.api.applyLiveSnapshot({
    schema_version: 1,
    revision: "master-enabled",
    sampled_at: "2026-07-16T12:00:00Z",
    overview: { status: "ok" },
    activity: {},
    master: enabledMaster,
  });
  assert.equal(harness.api.state.master.enabled, true);
  assert.equal(harness.node("runtime-paused-banner").hidden, true);
  assert.equal(harness.node("route-button").disabled, false);
  assert.equal(harness.node("route-status").textContent, "IDLE");
  assert.equal(harness.node("shell").classList.contains("agency-paused"), false);

  assert.equal(harness.api.applyMasterState(disabledMaster), false);
  assert.equal(harness.api.state.master.enabled, true);
});

test("Agency master control stays neutral until valid state arrives", async () => {
  const harness = createAppHarness(() => {
    throw new Error("loading-state controls must not fetch");
  });

  harness.api.syncMasterControl();
  assert.equal(harness.node("master-toggle").getAttribute("aria-pressed"), null);
  assert.equal(
    harness.node("master-toggle").getAttribute("aria-label"),
    "Agency master state loading",
  );
  assert.equal(harness.node("master-toggle").dataset.state, "loading");
  assert.equal(harness.node("master-label").textContent, "Agency status");
  assert.equal(harness.node("master-generation").textContent, "LOADING");
  assert.equal(harness.node("runtime-paused-banner").hidden, true);
  assert.equal(harness.node("route-button").disabled, true);
  assert.equal(harness.node("route-button").getAttribute("aria-disabled"), "true");
  assert.equal(harness.node("shell").dataset.agencyState, "loading");

  harness.api.bindEvents();
  await harness.node("master-toggle").listeners.get("click")[0]();
  assert.match(harness.node("notice").textContent, /master state is still loading/i);

  for (const invalid of [
    "invalid",
    { enabled: "yes", generation: 0 },
    { enabled: true, generation: 0.5 },
    { enabled: true, generation: -1 },
  ]) {
    assert.throws(
      () => harness.api.applyMasterState(invalid),
      /unsupported agency master-state response/i,
    );
  }

  harness.api.applyMasterState({
    schema_version: 1,
    enabled: false,
    generation: 1,
    updated_at: "2026-07-16T12:00:00Z",
    source: "dashboard",
  });
  const cancelled = harness.node("master-toggle").listeners.get("click")[0]();
  await Promise.resolve();
  harness.api.finishConfirmation(false);
  await cancelled;
  assert.match(harness.node("notice").textContent, /master action cancelled/i);
});

test("same-revision live snapshots render only when master state changes visibly", () => {
  const harness = createAppHarness(() => {
    throw new Error("same-revision rendering does not fetch");
  });
  harness.api.state.live.revision = "same-revision";
  harness.api.state.overview = { status: "ok", recent: {} };
  harness.api.applyMasterState({ enabled: true, generation: 1 });

  assert.equal(harness.api.applyLiveSnapshot({
    schema_version: 1,
    revision: "same-revision",
    sampled_at: "2026-07-16T12:00:00Z",
    overview: {},
    activity: {},
    master: { enabled: false, generation: 2 },
  }), true);
  assert.equal(harness.node("master-label").textContent, "Agency off");

  assert.equal(harness.api.applyLiveSnapshot({
    schema_version: 1,
    revision: "same-revision",
    sampled_at: "2026-07-16T12:00:01Z",
    overview: {},
    activity: {},
    master: { enabled: true, generation: 3 },
  }, { render: false }), true);
  assert.equal(harness.api.state.master.enabled, true);
});

test("Route Lab reconciles a server-side master bypass without rendering a receipt", async () => {
  for (const message of ["Agency was disabled concurrently.", ""]) {
    const disabledMaster = {
      schema_version: 1,
      enabled: false,
      generation: 2,
      updated_at: "2026-07-16T12:00:00Z",
      source: "dashboard",
    };
    const harness = createAppHarness(async (path) => {
      assert.equal(path, "/api/route");
      return jsonResponse(200, {
        bypassed: true,
        master: disabledMaster,
        message,
        status: "disabled",
      });
    });
    harness.api.applyMasterState({ ...disabledMaster, enabled: true, generation: 1 });
    harness.node("route-task").value = "Review this change";
    harness.node("route-host").value = "codex";

    await harness.api.runRoute();

    assert.equal(harness.api.state.master.enabled, false);
    assert.equal(harness.node("route-status").textContent, "BYPASSED");
    assert.match(
      harness.node("notice").textContent,
      message ? /disabled concurrently/i : /routing was bypassed/i,
    );
  }
});

test("Agency master mutation failures preserve the known state and surface the conflict", async () => {
  const harness = createAppHarness(async () => jsonResponse(409, { error: "generation conflict" }));
  harness.api.applyMasterState({
    schema_version: 1,
    enabled: false,
    generation: 4,
    updated_at: "2026-07-16T12:00:00Z",
    source: "dashboard",
  });

  await answerConfirmation(harness, harness.api.toggleMaster(true), "ENABLE AGENCY");

  assert.equal(harness.api.state.master.enabled, false);
  assert.match(harness.node("notice").textContent, /generation conflict/i);
  assert.equal(harness.node("master-toggle").getAttribute("aria-busy"), null);
});

test("Agency master enable success, lifecycle cancellation, and stale responses are bounded", async () => {
  const enabledMaster = {
    schema_version: 1,
    enabled: true,
    generation: 2,
    updated_at: "2026-07-16T12:00:00Z",
    source: "dashboard",
  };
  const success = createAppHarness(async (path) => {
    if (path === "/api/runtime/toggle") {
      return jsonResponse(200, { ok: true, changed: true, master: enabledMaster });
    }
    if (path === "/api/live?limit=100") {
      return jsonResponse(200, {
        schema_version: 1,
        revision: "enabled-master",
        overview: { status: "ok" },
        activity: {},
        master: enabledMaster,
      });
    }
    if (path === "/api/hosts") return jsonResponse(200, { hosts: [], master: enabledMaster });
    if (path === "/api/roster?limit=100") return jsonResponse(200, { agents: [] });
    if (path === "/api/snapshots") return jsonResponse(200, { snapshots: [] });
    if (path === "/api/config") return jsonResponse(200, { effective: {}, revision: "enabled" });
    throw new Error(`unexpected request: ${path}`);
  });
  success.api.applyMasterState({ ...enabledMaster, enabled: false, generation: 1 });
  await answerConfirmation(success, success.api.toggleMaster(true), "ENABLE AGENCY");
  assert.equal(success.api.state.master.enabled, true);
  assert.match(success.node("notice").textContent, /enabled globally/i);

  const suspended = createAppHarness(() => {
    throw new Error("suspended master mutation must not fetch");
  });
  suspended.api.applyMasterState({ ...enabledMaster, enabled: false, generation: 1 });
  const suspendedAction = suspended.api.toggleMaster(true);
  await Promise.resolve();
  suspended.api.state.lifecycle.suspended = true;
  suspended.node("confirmation-input").value = "ENABLE AGENCY";
  suspended.api.finishConfirmation(true);
  await suspendedAction;

  const response = deferred();
  const stale = createAppHarness(() => response.promise);
  stale.api.applyMasterState({ ...enabledMaster, enabled: false, generation: 1 });
  const staleAction = stale.api.toggleMaster(true);
  await Promise.resolve();
  stale.node("confirmation-input").value = "ENABLE AGENCY";
  stale.api.finishConfirmation(true);
  await Promise.resolve();
  stale.api.cancelMutationRequests();
  response.resolve(jsonResponse(200, { ok: true, master: enabledMaster }));
  await staleAction;
  assert.equal(stale.api.state.master.enabled, false);
});

test("Route Lab performs no request while Agency is globally bypassed", async () => {
  let calls = 0;
  const harness = createAppHarness(async () => {
    calls += 1;
    throw new Error("routing must not be requested");
  });
  harness.api.applyMasterState({
    schema_version: 1,
    enabled: false,
    generation: 3,
    updated_at: "2026-07-16T12:00:00Z",
    source: "dashboard",
  });
  harness.node("route-task").value = "Review this change";

  await harness.api.runRoute();

  assert.equal(calls, 0);
  assert.equal(harness.node("route-status").textContent, "BYPASSED");
  assert.match(harness.node("notice").textContent, /enable the master switch/i);
});

test("master control markup and motion treatment preserve accessibility", () => {
  const master = INDEX_SOURCE.match(/<button id="master-toggle"[^>]*>/)?.[0] || "";
  assert.match(master, /type="button"/);
  assert.match(master, /aria-label="Agency master state loading"/);
  assert.match(master, /data-state="loading"/);
  assert.match(master, /\sdisabled/);
  assert.doesNotMatch(master, /aria-pressed=/);
  assert.match(master, /aria-describedby="master-summary"/);
  const route = INDEX_SOURCE.match(/<button id="route-button"[^>]*>/)?.[0] || "";
  assert.match(route, /aria-disabled="true"/);
  assert.match(route, /\sdisabled/);
  assert.match(INDEX_SOURCE, /id="runtime-paused-banner"[^>]*role="status"[^>]*aria-live="polite"/);
  assert.match(APP_CSS_SOURCE, /\.master-control\[aria-pressed="false"\]/);
  assert.match(APP_CSS_SOURCE, /\.master-control\[data-state="loading"\]/);
  assert.match(APP_CSS_SOURCE, /\.agency-paused \.route-form/);
  assert.match(APP_CSS_SOURCE, /@media \(prefers-reduced-motion: reduce\)/);
});

test("operational dashboard renders governed roster, quarantine, and inference evidence", () => {
  const harness = createAppHarness(() => {
    throw new Error("render-only operational test does not fetch");
  });
  harness.node("roster-filter-division").value = "engineering";
  harness.node("roster-filter-authority").value = "obsolete";
  harness.missing("roster-filter-tool");
  harness.api.state.overview = {
    capture_content: false,
    db_size_bytes: 1,
    inference: {
      configured: true,
      failure_count: 2,
      provider_chain: [
        {
          order: 1,
          name: "production-router",
          type: "litellm",
          requested_model: "balanced",
          router: "balanced-group",
          configuration_ready: true,
          observed_receipt: {
            actual_provider: "anthropic",
            actual_model: "claude-production",
          },
        },
        {
          order: 2,
          name: "direct-fallback",
          configuration_ready: false,
          observed_receipt: {},
        },
      ],
      recent_failures: [
        {
          kind: "model_receipt",
          requested_model: "balanced",
          router: "balanced-group",
          actual_provider: "anthropic",
          actual_model: "claude-production",
          status: "failed",
          recorded_at: isoBefore(1_000),
        },
        {
          kind: "routing",
          provider: "production-router",
          status: "degraded",
          trace_id: "trace-safe",
          created_at: isoBefore(2_000),
        },
        { kind: "model_receipt" },
        { kind: "routing" },
      ],
      state: "degraded",
    },
    provider_health: [],
    recent: {},
    retention_days: 30,
    roster_count: 2,
    status: "ok",
    wal_size_bytes: 0,
  };
  harness.api.renderOverview();
  assert.equal(harness.node("inference-state").textContent, "DEGRADED");
  assert.equal(harness.node("provider-failure-count").textContent, "2");
  const providerText = descendants(harness.node("provider-health"))
    .map((node) => node.textContent).join(" ");
  assert.match(providerText, /Router \/ model group: balanced-group/);
  assert.match(providerText, /Observed actual: anthropic \/ claude-production/);
  assert.match(providerText, /config gap/);
  const failureText = descendants(harness.node("provider-failures"))
    .map((node) => node.textContent).join(" ");
  assert.match(failureText, /Actual: anthropic \/ claude-production/);
  assert.match(failureText, /Trace: trace-safe/);
  assert.match(failureText, /unidentified model · failed/);
  assert.match(failureText, /routing inference · degraded/);

  harness.api.state.overview.inference = {
    configured: true,
    provider_chain: [],
    recent_failures: [],
    state: "unknown",
  };
  harness.api.renderOverview();
  assert.match(
    harness.node("provider-health").children[0].textContent,
    /configured inference has no provider-chain projection/i,
  );

  harness.api.state.rosterFilters = { host: "codex" };
  harness.api.state.rosterOperations = {
    agents: [
      {
        agent_slug: "security-reviewer",
        name: "Security Reviewer",
        division: "engineering",
        capabilities: ["security"],
        enabled: true,
        authority: "review",
        audit_status: "approved",
        source_revision: "source-2",
        source_content_hash: "source-hash",
        audit_revision: "audit-2",
        context_mode: "isolated_only",
        supported_hosts: ["codex"],
        supported_platforms: ["windows", "linux"],
        required_tools: ["git"],
        conflicts_with: ["unsafe-agent"],
        requires: ["chief-of-staff"],
        revision_history: [{
          version: "2.0.0",
          audit_status: "approved",
          created_at: isoBefore(3_000),
        }],
      },
      {
        agent_slug: "plain-agent",
        capabilities: [],
        enabled: false,
      },
      {
        agent_slug: "sparse-audited-agent",
        capabilities: [],
        enabled: true,
        audit_status: "failed",
        content_hash: "fallback-content-hash",
      },
      {
        agent_slug: "sparse-history-agent",
        capabilities: [],
        enabled: true,
        authority: "advise",
        revision_history: [{}],
      },
    ],
    count: 4,
    matched_count: 4,
    total_count: 4,
    enabled_count: 3,
    truncated: false,
    facets: {
      divisions: ["engineering"],
      capabilities: ["security"],
      authorities: ["review"],
      hosts: ["codex"],
      platforms: ["linux", "windows"],
      tools: ["git"],
    },
  };
  harness.api.state.rosterReview = {
    queue_count: 3,
    upstream: {
      packaged_source_revision: "upstream-42",
      remote_freshness: "unverified",
      state: "review_pending",
    },
    candidates: [
      {
        candidate: {
          name: "Security Reviewer",
          slug: "security-reviewer",
          source_revision: "source-3",
          content_hash: "candidate-hash",
        },
        active: { source_revision: "source-2", content_hash: "active-hash" },
        change: "changed",
        changed_fields: ["capabilities"],
        latest_audit: {
          verdict: "passed",
          inference_status: "passed",
          findings: [{ severity: "warning", code: "review-change" }, {}],
        },
      },
      { candidate: {}, latest_audit: {}, changed_fields: [] },
      {},
    ],
    remediation_attempts: [
      {
        slug: "quarantined-specialist",
        created_at: "2026-07-11T11:58:00Z",
        receipt: {
          original_hash: "original-safe-hash",
          proposal_hash: "proposal-safe-hash",
          attempted_rule_ids: ["encoding-v1", "semantic-v1"],
          matched_rule_id: "encoding-v1",
          status: "proposal_pending_review",
          next_action: "review_deterministic_proposal_and_semantic_projection",
        },
      },
    ],
    remediation_history: [
      {
        slug: "repaired-specialist",
        original_hash: "raw-hash",
        candidate_hash: "candidate-hash",
        source_hash: "raw-hash",
        candidate_id: "candidate-42",
        resolution: "remediated_candidate",
        audit_policy_current: false,
        created_at: "2026-07-11T11:59:00Z",
      },
    ],
    remediation_count: 2,
    remediation_history_count: 3,
    remediation_unvalidated_resolution_count: 2,
    remediation_pending_has_more: true,
    remediation_history_has_more: true,
    next_remediation_pending_cursor: "pending-cursor",
    next_remediation_history_cursor: "history-cursor",
  };
  harness.api.renderRoster();
  assert.match(harness.node("roster-page-status").textContent, /active operational filters/i);
  assert.equal(harness.node("roster-filter-division").value, "engineering");
  assert.equal(harness.node("roster-filter-authority").value, "");
  const rosterText = descendants(harness.node("roster-grid"))
    .map((node) => node.textContent).join(" ");
  assert.match(rosterText, /Contract, compatibility & history/);
  assert.match(rosterText, /unsafe-agent/);
  assert.match(rosterText, /2\.0\.0/);
  const reviewText = descendants(harness.node("review-list"))
    .map((node) => node.textContent).join(" ");
  assert.match(reviewText, /Candidate revision/);
  assert.match(reviewText, /warning · review-change/);
  assert.match(reviewText, /unknown · finding/);
  assert.match(reviewText, /No audit findings recorded/);
  assert.match(reviewText, /quarantined-specialist/);
  assert.match(reviewText, /remediation attempt · non-executable/);
  assert.match(reviewText, /original-safe-hash/);
  assert.match(reviewText, /proposal-safe-hash/);
  assert.match(reviewText, /encoding-v1, semantic-v1/);
  assert.match(reviewText, /review_deterministic_proposal_and_semantic_projection/);
  assert.match(reviewText, /2026-07-11T11:58:00Z/);
  assert.match(reviewText, /cannot activate an agent/);
  assert.match(reviewText, /repaired-specialist/);
  assert.match(reviewText, /repair provenance · immutable history/);
  assert.match(reviewText, /historical policy/);
  assert.equal(harness.node("review-count").textContent, "3");
  assert.match(harness.node("review-page-status").textContent, /1 of 2 pending repairs/);
  assert.match(harness.node("review-page-status").textContent, /1 of 3 resolved repairs/);
  assert.match(
    harness.node("review-page-status").textContent,
    /2 unvalidated resolution records remain quarantined/,
  );
  assert.equal(
    harness.node("review-page-status").dataset.unvalidatedResolutionCount,
    "2",
  );
  assert.equal(harness.node("review-page-status").classList.contains("failed"), true);
  assert.equal(harness.node("review-pending-more").hidden, false);
  assert.equal(harness.node("review-history-more").hidden, false);
  const [remediationCard] = descendants(harness.node("review-list"))
    .filter((node) => node.className.includes("remediation-card"));
  assert.equal(
    remediationCard.getAttribute("aria-label"),
    "Remediation attempt for quarantined-specialist",
  );
  const [remediationGuard] = descendants(remediationCard)
    .filter((node) => node.className === "remediation-guard");
  assert.equal(remediationGuard.getAttribute("role"), "note");
  assert.match(harness.node("upstream-status").textContent, /upstream-42/);

  harness.api.state.rosterFilters = null;
  harness.api.renderRoster();
  harness.api.state.rosterFilters = { host: "codex" };
  delete harness.api.state.rosterOperations.matched_count;
  harness.api.state.rosterReview.upstream = { packaged_source_revision: "upstream-minimal" };
  harness.api.renderRoster();
  assert.match(harness.node("roster-page-status").textContent, /showing 4 specialists/i);
  assert.match(harness.node("upstream-status").textContent, /remote freshness unverified/i);
  assert.match(harness.node("upstream-status").textContent, /status unknown/i);

  harness.api.state.rosterReview = {
    candidates: [],
    remediation_attempts: [{
      slug: "unknown-remediation",
      receipt: { attempted_rule_ids: [] },
    }, {}],
  };
  harness.api.renderRoster();
  assert.equal(harness.node("review-count").textContent, "2");
  const remediationOnlyText = descendants(harness.node("review-list"))
    .map((node) => node.textContent).join(" ");
  assert.match(remediationOnlyText, /unknown-remediation/);
  assert.match(remediationOnlyText, /none generated/);
  assert.match(remediationOnlyText, /manual review required/);
  assert.doesNotMatch(remediationOnlyText, /No candidates .* await review/);

  harness.api.state.rosterReview = { candidates: [], remediation_attempts: [] };
  harness.api.renderRoster();
  assert.equal(harness.node("review-count").textContent, "0");
  assert.equal(
    harness.node("review-list").children[0].textContent,
    "No candidates, remediation attempts, or repair history are available.",
  );

  harness.api.state.rosterFilter = "exact-agent";
  harness.api.state.roster = [{ agent_slug: "exact-agent", capabilities: [] }];
  harness.api.state.rosterPage = {
    count: 1, total_count: 1, enabled_count: 1, truncated: false,
  };
  harness.api.renderRoster();
  assert.equal(harness.node("roster-filter-division").children.length, 2);

  const optional = createAppHarness(() => {
    throw new Error("optional review nodes do not fetch");
  });
  optional.missing("review-list");
  optional.missing("upstream-status");
  optional.missing("inference-state");
  optional.missing("provider-failure-count");
  optional.missing("provider-failures");
  optional.api.state.overview = {
    inference: { provider_chain: [], recent_failures: [] },
    provider_health: [], recent: {}, status: "ok",
  };
  optional.api.renderOverview();
  optional.api.renderRoster();
});

test("remediation queue controls page pending and history independently", async () => {
  const calls = [];
  const harness = createAppHarness(async (path) => {
    calls.push(path);
    if (path.includes("history_cursor")) {
      return jsonResponse(200, {
        remediation_attempts: [],
        remediation_history: [{ event_id: "history-2", slug: "second-resolution" }],
        remediation_unvalidated_resolution_count: 0,
        remediation_pending_has_more: false,
        remediation_history_has_more: false,
        next_remediation_pending_cursor: "",
        next_remediation_history_cursor: "",
      });
    }
    return jsonResponse(200, {
      remediation_attempts: [{
        event_id: "pending-2",
        slug: "second-repair",
        receipt: { attempted_rule_ids: [] },
      }],
      remediation_history: [],
      remediation_unvalidated_resolution_count: 1,
      remediation_pending_has_more: false,
      remediation_history_has_more: true,
      next_remediation_pending_cursor: "",
      next_remediation_history_cursor: "history-1",
    });
  });
  harness.api.state.rosterReview = {
    candidates: [],
    remediation_attempts: [{
      event_id: "pending-1",
      slug: "first-repair",
      receipt: { attempted_rule_ids: [] },
    }],
    remediation_history: [{ event_id: "history-1", slug: "resolved-repair" }],
    remediation_count: 2,
    remediation_history_count: 2,
    remediation_unvalidated_resolution_count: 0,
    remediation_pending_has_more: true,
    remediation_history_has_more: true,
    next_remediation_pending_cursor: "pending-1",
    next_remediation_history_cursor: "history-1",
    limit: 1,
  };

  harness.api.bindEvents();
  assert.equal(
    await harness.node("review-pending-more").listeners.get("click")[0](),
    true,
  );
  assert.equal(
    calls[0],
    "/api/roster/reviews?limit=1&pending_cursor=pending-1",
  );
  assert.deepEqual(
    harness.api.state.rosterReview.remediation_attempts.map((item) => item.event_id),
    ["pending-1", "pending-2"],
  );
  assert.equal(harness.api.state.rosterReview.remediation_history.length, 1);
  assert.equal(
    harness.api.state.rosterReview.remediation_unvalidated_resolution_count,
    1,
  );
  assert.equal(harness.node("review-pending-more").hidden, true);
  assert.equal(harness.node("review-history-more").hidden, false);
  assert.equal(
    await harness.node("review-history-more").listeners.get("click")[0](),
    true,
  );
  assert.equal(
    calls[1],
    "/api/roster/reviews?limit=1&history_cursor=history-1",
  );
  assert.deepEqual(
    harness.api.state.rosterReview.remediation_history.map((item) => item.event_id),
    ["history-1", "history-2"],
  );
  assert.equal(harness.api.state.rosterReview.remediation_history_has_more, false);
  await assert.rejects(
    harness.api.loadMoreRemediation("unknown"),
    /must be pending or history/,
  );

  const failed = createAppHarness(async () => jsonResponse(503, { error: "review unavailable" }));
  failed.api.state.rosterReview = {
    remediation_attempts: [],
    next_remediation_pending_cursor: "pending-error",
    limit: 1,
  };
  assert.equal(await failed.api.loadMoreRemediation("pending"), false);
  assert.match(failed.node("notice").textContent, /review unavailable/);

  const empty = createAppHarness(() => {
    throw new Error("empty remediation pages do not fetch");
  });
  empty.api.state.rosterReview = null;
  assert.equal(await empty.api.loadMoreRemediation("pending"), false);
  empty.api.state.lifecycle.suspended = true;
  assert.equal(await empty.api.loadMoreRemediation("pending"), false);

  const lateResponse = deferred();
  const late = createAppHarness(async () => lateResponse.promise);
  late.api.state.rosterReview = {
    remediation_attempts: [],
    next_remediation_pending_cursor: "pending-late",
  };
  const latePage = late.api.loadMoreRemediation("pending");
  await Promise.resolve();
  late.api.state.lifecycle.suspended = true;
  lateResponse.resolve(jsonResponse(200, { remediation_attempts: [] }));
  assert.equal(await latePage, false);

  const malformed = createAppHarness(async () => jsonResponse(200, {
    remediation_attempts: "invalid",
    remediation_unvalidated_resolution_count: "invalid",
    next_remediation_pending_cursor: null,
  }));
  malformed.api.state.rosterReview = {
    remediation_attempts: "invalid",
    remediation_unvalidated_resolution_count: 4,
    next_remediation_pending_cursor: "pending-malformed",
  };
  assert.equal(await malformed.api.loadMoreRemediation("pending"), true);
  assert.deepEqual(malformed.api.state.rosterReview.remediation_attempts, []);
  assert.equal(
    malformed.api.state.rosterReview.remediation_unvalidated_resolution_count,
    4,
  );

  const optional = createAppHarness(() => {
    throw new Error("optional remediation controls do not fetch");
  });
  optional.missing("review-history-more");
  optional.api.state.rosterReview = {
    candidates: [],
    remediation_attempts: [],
    remediation_history: [{}],
    remediation_pending_has_more: false,
    remediation_history_has_more: true,
    next_remediation_history_cursor: "history-optional",
  };
  optional.api.renderRoster();
  assert.match(
    descendants(optional.node("review-list")).map((node) => node.textContent).join(" "),
    /unknown/,
  );
});

test("operational roster filters are bounded, reversible, and lifecycle safe", async () => {
  const calls = [];
  const response = {
    agents: [], count: 0, matched_count: 0, total_count: 0, enabled_count: 0,
    truncated: false, facets: {},
  };
  const harness = createAppHarness(async (path) => {
    calls.push(path);
    return jsonResponse(200, response);
  });
  harness.node("roster-filter-query").value = "  secure review  ";
  harness.node("roster-filter-host").value = "codex";
  harness.missing("roster-filter-tool");
  let prevented = false;
  assert.equal(await harness.api.applyOperationalFilters({
    preventDefault() { prevented = true; },
  }), true);
  assert.equal(prevented, true);
  assert.equal(calls[0], "/api/roster/operations?limit=100&query=secure+review&host=codex");
  assert.deepEqual(harness.api.state.rosterFilters, { query: "secure review", host: "codex" });
  assert.equal(harness.api.operationalRosterPath({ platform: "linux" }), "/api/roster/operations?limit=100&platform=linux");

  assert.equal(await harness.api.clearOperationalFilters(), true);
  assert.equal(harness.node("roster-filter-query").value, "");
  assert.equal(harness.node("roster-filter-host").value, "");
  assert.equal(calls.at(-1), "/api/roster/operations?limit=100");
  assert.deepEqual(harness.api.applyGovernanceSnapshot({
    snapshots: [{ snapshot_id: "safe" }], operations: response, reviews: { candidates: [] },
  }), {
    snapshots: [{ snapshot_id: "safe" }], operations: response, reviews: { candidates: [] },
  });
  assert.deepEqual(harness.api.applyGovernanceSnapshot({ snapshots: "invalid" }).snapshots, []);

  harness.api.state.serviceBinding = { store_restart_required: true };
  assert.equal(await harness.api.applyOperationalFilters(), false);
  assert.match(harness.node("notice").textContent, /restart the dashboard service/i);
  harness.api.state.serviceBinding = { store_restart_required: false };
  harness.api.state.lifecycle.destroyed = true;
  assert.equal(await harness.api.applyOperationalFilters(), false);
  harness.api.state.lifecycle.destroyed = false;
  harness.api.state.lifecycle.suspended = true;
  assert.equal(await harness.api.applyOperationalFilters(), false);

  const pending = deferred();
  const late = createAppHarness(() => pending.promise);
  const applying = late.api.applyOperationalFilters();
  late.api.state.lifecycle.suspended = true;
  pending.resolve(jsonResponse(200, response));
  assert.equal(await applying, false);

  const failed = createAppHarness(async () => jsonResponse(503, { error: "filter unavailable" }));
  assert.equal(await failed.api.applyOperationalFilters(), false);
  assert.match(failed.node("notice").textContent, /filter unavailable/i);
});

test("operational dashboard markup and accessibility policies stay discoverable", () => {
  for (const id of [
    "inference-state", "provider-failures", "roster-operations-form",
    "roster-filter-division", "roster-filter-capability", "roster-filter-authority",
    "roster-filter-host", "roster-filter-platform", "roster-filter-tool",
    "review-list", "upstream-status",
  ]) assert.match(INDEX_SOURCE, new RegExp(`id="${id}"`));
  assert.match(APP_CSS_SOURCE, /\.roster-filter-grid/);
  assert.match(APP_CSS_SOURCE, /\.review-card/);
  assert.match(APP_CSS_SOURCE, /\.remediation-card/);
  assert.match(APP_CSS_SOURCE, /\.remediation-guard/);
  assert.match(APP_CSS_SOURCE, /\.provider-chain-row/);
  assert.match(APP_CSS_SOURCE, /@media \(forced-colors: active\)/);
  assert.match(APP_CSS_SOURCE, /@media \(prefers-reduced-motion: reduce\)/);
});
