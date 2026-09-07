// Optional real-browser QA; npm tooling is separate from the runtime package.
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync, readdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";

const [tools, output, executablePath, packageRoot] = process.argv.slice(2);
const requireTool = createRequire(path.join(tools, "package.json"));
const { chromium } = requireTool("playwright");
const axeSource = readFileSync(requireTool.resolve("axe-core/axe.min.js"), "utf8");
const browser = await chromium.launch({
  ...(executablePath ? {executablePath} : {}), headless: true, chromiumSandbox: true,
});
const assetRoot = path.join(packageRoot, "dashboard");
const report = {
  observed: new Date().toISOString(),
  browser: browser.version(),
  playwright: requireTool("playwright/package.json").version,
  axe: requireTool("axe-core/package.json").version,
  scope: "Installed wheel; private five-agent Store; host inspection stubbed; server outbound connections denied. Not a native-host canary or full WCAG certification.",
  assets: Object.fromEntries(readdirSync(assetRoot).filter(name => /\.(html|css|js|svg)$/.test(name))
    .sort().map(name => [name, createHash("sha256").update(readFileSync(path.join(assetRoot, name))).digest("hex")])),
  views: [], interactions: [], controlFailures: [], postRequests: 0, unexpectedErrors: [], failures: [],
};
const uuid = /\b[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b/i;
try {
  for (const viewport of [{width: 1280, height: 900}, {width: 1024, height: 768}, {width: 375, height: 812}]) {
    const context = await browser.newContext({viewport, reducedMotion: "reduce"});
    const page = await context.newPage();
    page.setDefaultTimeout(10000);
    const errors = [];
    const requestPaths = [];
    let controlRequests = 0;
    page.on("request", request => {
      requestPaths.push(new URL(request.url()).pathname);
      if (request.method() !== "GET") report.postRequests += 1;
      if (new URL(request.url()).pathname === "/api/control") controlRequests += 1;
    });
    page.on("pageerror", error => errors.push({kind: "pageerror", message: error.message}));
    page.on("console", message => {
      if (["error", "warning"].includes(message.type())) errors.push({kind: message.type(), message: message.text()});
    });
    page.on("response", response => {
      if (response.status() >= 400) errors.push({kind: "http", status: response.status(), path: new URL(response.url()).pathname});
    });
    await page.goto(`${process.env.QA_URL}/#token=${process.env.QA_TOKEN}`);
    await page.waitForFunction(async () => {
      const app = (await import("/app.js")).bootstrappedDashboard;
      return !location.hash && !app.state.full.inFlight && Boolean(app.state.control.revision);
    });
    await page.evaluate(axeSource);
    const views = await page.locator(".nav-item").evaluateAll(nodes => nodes.map(node => node.dataset.view));
    assert.equal(views.length, 7);
    for (const view of views) {
      await page.locator(`.nav-item[data-view="${view}"]`).click();
      await page.locator(`#view-${view}`).waitFor({state: "visible"});
      assert.equal(await page.evaluate(async () => (await import("/app.js")).bootstrappedDashboard.refreshAll()), true);
      // Match the UI's view-scoped follow-up after the full control refresh.
      // Calling refreshAll alone intentionally cancels outstanding view reads.
      if (view === "overview") {
        assert.equal(await page.evaluate(async () => (await import("/app.js")).bootstrappedDashboard.refreshMetricEvidence()), true);
      } else if (view === "evidence") {
        assert.equal(await page.evaluate(async () => (await import("/app.js")).bootstrappedDashboard.refreshVisionEvidence({force: true})), true);
      }
      const accessibility = await page.evaluate(async () => {
        const result = await axe.run(document, {runOnly: {type: "tag", values: ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"]}});
        const project = item => ({id: item.id, impact: item.impact, nodes: item.nodes.map(node => ({target: node.target, summary: node.failureSummary}))});
        return {violations: result.violations.map(project), incomplete: result.incomplete.map(project), passes: result.passes.length};
      });
      const layout = await page.evaluate(() => {
        const heading = document.querySelector(".topbar-heading").getBoundingClientRect();
        return {viewport: innerWidth, document: document.documentElement.scrollWidth, headingHeight: heading.height,
          clippedMetrics: [...document.querySelectorAll(".view.active .metric-evidence-summary .metric")].filter(node => {
            const box = node.getBoundingClientRect(), parent = node.closest(".panel").getBoundingClientRect();
            return box.left < parent.left || box.right > parent.right || box.bottom > parent.bottom;
          }).map(node => node.querySelector("strong")?.id)};
      });
      const failed = accessibility.violations.length > 0 || layout.document > viewport.width + 1
        || layout.clippedMetrics.length > 0 || (viewport.width === 375 && layout.headingHeight >= 100);
      if (failed) report.failures.push(`${viewport.width}:${view}`);
      report.views.push({viewport, view, accessibility, layout});
      console.log(JSON.stringify({width: viewport.width, view, violations: accessibility.violations.map(item => item.id), clippedMetrics: layout.clippedMetrics}));
      if (view === "overview") {
        await page.screenshot({path: path.join(output, `${viewport.width}-overview.png`), fullPage: true});
      }
    }

    // A real control poll must preserve unsaved text, selection and disclosures.
    await page.locator("#config-judge-model").fill("unsaved-browser-check");
    await page.evaluate(() => {
      document.querySelectorAll("#view-settings details").forEach(node => { node.open = true; });
      document.querySelector("#config-judge-model").setSelectionRange(2, 9);
    });
    const fieldState = () => page.evaluate(() => ({
      focus: document.activeElement.id,
      value: document.querySelector("#config-judge-model").value,
      start: document.querySelector("#config-judge-model").selectionStart,
      end: document.querySelector("#config-judge-model").selectionEnd,
      details: [...document.querySelectorAll("#view-settings details")].map(node => node.open),
    }));
    const before = await fieldState();
    const requestsBeforePoll = controlRequests;
    await page.evaluate(async () => (await import("/app.js")).bootstrappedDashboard.refreshControlPlane());
    assert.ok(controlRequests > requestsBeforePoll, "The preservation check must execute a real control poll");
    assert.deepEqual(await fieldState(), before);
    const configOutput = page.locator("#config-output");
    await configOutput.focus();
    await configOutput.press("ArrowDown");
    await page.waitForFunction(() => document.querySelector("#config-output").scrollTop > 0);
    report.interactions.push({width: viewport.width, preservesDirtyFieldFocusSelectionAndDetails: true, keyboardScrollsConfiguration: true});
    report.unexpectedErrors.push(...errors.map(error => ({width: viewport.width, ...error})));
    errors.length = 0;

    // Inject one bounded network failure only after recording clean-page errors.
    const revision = await page.evaluate(async () => (await import("/app.js")).bootstrappedDashboard.state.control.revision);
    await page.route("**/api/control", route => route.abort("failed"));
    await page.evaluate(async () => (await import("/app.js")).bootstrappedDashboard.refreshControlPlane());
    const stale = await page.evaluate(async () => {
      const app = (await import("/app.js")).bootstrappedDashboard;
      return {revision: app.state.control.revision, stale: app.state.control.stale,
        notice: document.querySelector("#notice").textContent};
    });
    assert.equal(stale.stale, true);
    assert.equal(stale.revision, revision);
    assert.match(stale.notice, uuid);
    const requestId = stale.notice.match(uuid)[0];
    assert.ok(errors.some(error => error.kind === "error" && error.message.includes(requestId)));
    await page.unroute("**/api/control");
    assert.equal(await page.evaluate(async () => (await import("/app.js")).bootstrappedDashboard.refreshAll()), true);
    assert.equal(await page.evaluate(async () => (await import("/app.js")).bootstrappedDashboard.state.control.stale), false);
    report.interactions.at(-1).failure = {retainsRevision: true, visibleStaleMarker: true, requestId, consoleCorrelated: true, recovered: true};
    for (const method of ["refreshControlPlane", "refreshAll"]) {
      for (const fault of ["missing-endpoint", "network", "missing-schema", "wrong-schema", "null-payload", "malformed-json"]) {
        const controlState = () => page.evaluate(async () => {
          const {state} = (await import("/app.js")).bootstrappedDashboard;
          return JSON.stringify({config: state.config, pendingConfig: state.pendingConfig,
            hosts: state.hosts, roster: state.roster, snapshots: state.snapshots,
            overview: state.overview, controlRevision: state.control.revision, liveRevision: state.live.revision});
        });
        const lastGood = await controlState();
        const firstRequest = requestPaths.length;
        let sentId;
        let responseId = null;
        await page.route("**/api/control", async route => {
          sentId = route.request().headers()["x-agency-request-id"];
          if (fault === "network") return route.abort("failed");
          const response = await route.fetch();
          const headers = {...response.headers()};
          responseId = headers["x-agency-request-id"];
          assert.equal(responseId, sentId, "The real server must echo the actual request ID");
          delete headers["content-length"];
          delete headers["content-encoding"];
          let payload = await response.json();
          assert.equal(payload.schema_version, "agency.dashboard.control.v1");
          if (fault === "missing-endpoint") payload = {error: "control endpoint unavailable"};
          if (fault === "missing-schema") delete payload.schema_version;
          if (fault === "wrong-schema") payload.schema_version = "agency.dashboard.control.v2";
          if (fault === "null-payload") payload = null;
          await route.fulfill({status: fault === "missing-endpoint" ? 404 : response.status(), headers,
            ...(fault === "malformed-json" ? {body: "{"} : {body: JSON.stringify(payload)})});
        });
        await page.evaluate(async name => (await import("/app.js")).bootstrappedDashboard[name](), method);
        assert.ok(sentId && uuid.test(sentId), "The fault must reach an actual correlated request");
        assert.equal(await controlState(), lastGood);
        const failure = await page.evaluate(async () => {
          const {state} = (await import("/app.js")).bootstrappedDashboard;
          return {stale: state.control.stale, requestId: state.control.errorRequestId,
            notice: document.querySelector("#notice").textContent};
        });
        assert.equal(failure.stale, true);
        assert.equal(failure.requestId, sentId);
        assert.ok(failure.notice.includes(sentId));
        const legacyRequests = requestPaths.slice(firstRequest).filter(name =>
          ["/api/config", "/api/hosts", "/api/roster", "/api/snapshots"].includes(name));
        assert.deepEqual(legacyRequests, []);
        if (method === "refreshAll" && fault === "wrong-schema") {
          await page.screenshot({path: path.join(output, `${viewport.width}-control-schema.png`), fullPage: true});
        }
        await page.unroute("**/api/control");
        assert.equal(await page.evaluate(async () => (await import("/app.js")).bootstrappedDashboard.refreshAll()), true);
        assert.equal(await page.evaluate(async () => (await import("/app.js")).bootstrappedDashboard.state.control.stale), false);
        report.controlFailures.push({width: viewport.width, method, fault, requestId: sentId,
          responseRequestId: responseId, retainedState: true, legacyRequests: 0, recovered: true});
      }
    }
    assert.equal(errors.filter(error => error.kind === "pageerror").length, 0);
    await context.close();
  }
} catch (error) {
  report.failures.push(String(error.stack || error).replaceAll(process.env.QA_TOKEN, "[fixture-token]"));
} finally {
  await browser.close();
  report.passed = report.views.length === 21 && report.controlFailures.length === 36
    && report.postRequests === 0 && report.failures.length === 0 && report.unexpectedErrors.length === 0;
  writeFileSync(path.join(output, "report.json"), JSON.stringify(report, null, 2) + "\n", {flag: "wx"});
}
console.log(JSON.stringify({passed: report.passed, views: report.views.length, interactions: report.interactions,
  controlFailures: report.controlFailures.length, postRequests: report.postRequests,
  failures: report.failures, unexpectedErrors: report.unexpectedErrors}));
process.exitCode = report.passed ? 0 : 1;
