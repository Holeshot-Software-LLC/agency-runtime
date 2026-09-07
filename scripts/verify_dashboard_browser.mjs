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
  views: [], interactions: [], unexpectedErrors: [], failures: [],
};
const uuid = /\b[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b/i;
try {
  for (const viewport of [{width: 1280, height: 900}, {width: 1024, height: 768}, {width: 375, height: 812}]) {
    const context = await browser.newContext({viewport, reducedMotion: "reduce"});
    const page = await context.newPage();
    page.setDefaultTimeout(10000);
    const errors = [];
    let controlRequests = 0;
    page.on("request", request => {
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
    await context.close();
  }
} catch (error) {
  report.failures.push(String(error.stack || error).replaceAll(process.env.QA_TOKEN, "[fixture-token]"));
} finally {
  await browser.close();
  report.passed = report.views.length === 21 && report.failures.length === 0 && report.unexpectedErrors.length === 0;
  writeFileSync(path.join(output, "report.json"), JSON.stringify(report, null, 2) + "\n", {flag: "wx"});
}
console.log(JSON.stringify({passed: report.passed, views: report.views.length, interactions: report.interactions,
  failures: report.failures, unexpectedErrors: report.unexpectedErrors}));
process.exitCode = report.passed ? 0 : 1;
