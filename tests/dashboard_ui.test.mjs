import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import test from "node:test";
import vm from "node:vm";

const require = createRequire(import.meta.url);
const AgencyCharts = require("../agency_runtime/dashboard/charts.js");
const APP_SOURCE = readFileSync(
  new URL("../agency_runtime/dashboard/app.js", import.meta.url),
  "utf8",
);

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
}

class FakeNode {
  constructor(id = "") {
    this.id = id;
    this.attributes = new Map();
    this.classList = new FakeClassList();
    this.dataset = {};
    this.disabled = false;
    this.hidden = false;
    this.listeners = new Map();
    this.textContent = "";
    this.value = "";
  }

  addEventListener(name, listener) {
    const listeners = this.listeners.get(name) || [];
    listeners.push(listener);
    this.listeners.set(name, listeners);
  }

  append() {}

  closest() {
    return null;
  }

  focus() {}

  getAttribute(name) {
    return this.attributes.get(name) ?? null;
  }

  querySelectorAll() {
    return [];
  }

  replaceChildren() {}

  setAttribute(name, value) {
    this.attributes.set(name, String(value));
  }
}

function createAppHarness(fetchImpl) {
  let nextTimerId = 1;
  const timerTasks = new Map();
  const nodes = new Map();
  const documentListeners = new Map();
  const windowListeners = new Map();
  const node = (id) => {
    if (!nodes.has(id)) nodes.set(id, new FakeNode(id));
    return nodes.get(id);
  };
  const addListener = (registry, name, listener) => {
    const listeners = registry.get(name) || [];
    listeners.push(listener);
    registry.set(name, listeners);
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
    createElement: (tag) => new FakeNode(tag),
    getElementById: node,
    querySelector: (selector) => (selector === ".rail-foot" ? node("rail-foot") : null),
    querySelectorAll: () => [],
  };
  class HTMLElement {}
  class HTMLInputElement extends HTMLElement {}
  const window = {
    location: { hash: "", pathname: "/" },
    addEventListener: (name, listener) => addListener(windowListeners, name, listener),
    clearTimeout: (id) => timers.clear(id),
    setTimeout: (callback, delay) => timers.set(callback, delay),
  };
  const context = vm.createContext({
    AbortController,
    AgencyCharts,
    DOMException,
    HTMLElement,
    HTMLInputElement,
    URLSearchParams,
    console,
    document,
    fetch: fetchImpl,
    history: { replaceState() {} },
    sessionStorage: { getItem: () => null, setItem() {} },
    window,
  });
  const expose = `
    globalThis.__test = {
      state,
      APIError,
      fetchLiveSnapshot,
      cancelLiveRequest,
      runLivePoll,
      scheduleLive,
      cancelControlRequest,
      scheduleControlRefresh,
      cancelFullRefresh,
      refreshAll,
      handleVisibilityChange,
      handlePageShow,
      liveCanRun,
    };
  `;
  new vm.Script(`${APP_SOURCE}\n${expose}`, { filename: "app.js" }).runInContext(context);
  return {
    api: context.__test,
    context,
    document,
    documentListeners,
    node,
    nodes,
    timers,
    windowListeners,
  };
}

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
  assert.equal(AgencyCharts.retryDelay(100, () => 0), 30_000);
  assert.equal(AgencyCharts.retryDelay(100, () => 1), 30_000);
  assert.ok(Number.isInteger(AgencyCharts.retryDelay(3, () => 0.314159)));
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
  assert.equal(requests.length, 6);
  const activeGeneration = harness.api.state.full.generation;

  harness.api.cancelFullRefresh();
  assert.ok(harness.api.state.full.generation > activeGeneration);
  assert.ok(requests.every((request) => request.signal.aborted));

  requests.forEach((request) => request.pending.resolve(jsonResponse(200, {})));
  assert.equal(await refresh, false);
  assert.equal(harness.api.state.overview, null);
  assert.equal(harness.api.state.full.inFlight, false);
  assert.equal(harness.api.state.full.controller, null);
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
