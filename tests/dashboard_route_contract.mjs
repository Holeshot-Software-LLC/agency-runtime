// Minimal DOM/transport doubles for the Python UI-to-POST contract test.
// Host eligibility and outgoing request construction use production modules.
import { createRenderer } from "../agency_runtime/dashboard/dashboard-render.js";
import { createActionController } from "../agency_runtime/dashboard/dashboard-actions.js";

let input = "";
for await (const chunk of process.stdin) input += chunk;
const payload = JSON.parse(input);
const nodes = new Map();
function element() {
  return {
    value: "", textContent: "", disabled: false, children: [], attributes: new Map(),
    append(node) { this.children.push(node); },
    replaceChildren() { this.children = []; },
    setAttribute(name, value) { this.attributes.set(name, value); },
    getAttribute(name) { return this.attributes.get(name) ?? null; },
    removeAttribute(name) { this.attributes.delete(name); },
  };
}
function byId(id) {
  if (!nodes.has(id)) nodes.set(id, element());
  return nodes.get(id);
}
const requests = [];
const state = { hosts: payload.hosts, master: payload.master, lifecycle: { destroyed: false } };
const core = {
  state, byId, el: element,
  showNotice() {},
  withRequestId: (message) => message,
  api: async (path, options) => {
    requests.push({ path, method: options.method, body: JSON.parse(options.body) });
    // Only capture outgoing bodies here; Python sends them to the real server.
    return { bypassed: true, master: payload.master };
  },
};
const config = { serviceRestartRequired: () => false };
const renderer = createRenderer(core, config, {});
const live = {
  beginMutation: () => new AbortController(),
  mutationIsCurrent: () => true,
  applyMasterState() {},
  finishMutation() {},
};
const actions = createActionController(core, config, renderer, live);
renderer.renderRouteHosts();
const available = byId("route-host").children.map((node) => node.value).filter(Boolean);
const disabled = byId("route-button").disabled;
const reason = byId("route-host-help").textContent;
byId("route-task").value = "  Verify host eligibility  ";
byId("route-session").value = " dashboard-contract ";
for (const host of available.length ? available : [""]) {
  byId("route-host").value = host;
  await actions.runRoute();
}
process.stdout.write(JSON.stringify({ available, disabled, reason, requests }));
