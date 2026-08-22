---
title: "Exact-main Linux handoff for OpenClaw and Hermes"
status: active
category: roadmap
created: 2026-08-16
updated: 2026-08-21
tags: [roadmap, verification, hosts, openclaw, hermes, linux, AR-119]
related:
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/roadmap/AR-119-founding-vision.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0158-collect-child-canary-proof-inside-disposable-host-profiles.md
  - docs/roadmap/issue-AR-272-expose-openclaw-native-finalizer-tool.md
  - docs/roadmap/issue-AR-273-model-agnostic-structured-inference-profiles.md
  - docs/decisions/0163-keep-litellm-inference-profiles-model-agnostic.md
supersedes: []
superseded_by: null
type: reference
issue_id: AR-119
---

# Exact-main Linux handoff for OpenClaw and Hermes

OpenClaw and Hermes are intentionally absent from the Windows evidence
workstation. This packet is the bounded transfer to the owner's Linux box. It
is a recipe, not installed or live evidence, and it moves no AR-119 matrix cell.

The implementation anchor is exact main f76050d7. The evidence-only branch
that refreshed this packet changes documentation, not runtime code. After its
[skip ci] pull request merges, use the resulting exact origin/main, record its
SHA, and prove that it contains the implementation anchor.

## 1. Freeze the Linux starting point

Run from the Linux checkout:

~~~bash
git fetch origin
git switch main
git pull --ff-only
git status --short
git rev-parse HEAD
git merge-base --is-ancestor f76050d7 HEAD
python -m agency_runtime.cli --version
python -m agency_runtime.cli doctor
python -m agency_runtime.cli status --json
~~~

The status output must be empty for git status --short, the ancestor check must
exit zero, and doctor must not report Store/runtime schema drift. Exact main
uses Store schema 47. Do not measure through an older PATH launcher or a
checkout whose imported agency_runtime.__file__ is ambiguous.

Before mutation, stop active host sessions and make a recoverable owner-Store
backup with SQLite integrity and SHA-256 recorded. Do not copy a live database
without its WAL state. Preserve the before-install host versions, Agency status,
Store contractor count, and current launcher manifests.

OpenClaw installation accepts only the audited stable 2026.7.x line, at least
2026.7.1. A prerelease, older release, newer release line, or live gateway is a
named stop condition. Stop the gateway through OpenClaw's native procedure; the
Agency installer must not restart it.

## 2. Install exact main, one host at a time

Use the checkout module, not a stale packaged executable:

~~~bash
python -m agency_runtime.cli install --agent openclaw --no-dashboard --json
python -m agency_runtime.cli status --json
python -m agency_runtime.cli install --agent hermes --no-dashboard --json
python -m agency_runtime.cli status --json
~~~

For each host retain the complete JSON result and record:

- checkout SHA and clean-tree state;
- native host version and profile identity;
- install status, registration, enablement, and restart requirement;
- ~/.agency-runtime/launchers/current-<host>.json;
- runtime digest, source root, bundle/manifest digest, and Store schema;
- every refusal or partial result exactly as emitted.

Both hosts must point at the runtime produced by the same checkout. Restart each
host and open a fresh session; a session opened before installation cannot
prove the installed projection. Do not reinstall merely to refresh a session.

## 3. First-response and skill evidence

In a completely new session for each host:

1. Send exact agency status as the first user message.
2. Preserve the first assistant response and host transcript before sending a
   second message.
3. Correlate the session and trace with runs, resident_manager_bindings,
   routing_decisions, and specialists_loaded.
4. Only if the response has a real Store-backed Agency header, load one harmless
   available skill through the host's installed Agency skill surface without
   spawning a child.
5. Preserve the updated five-line header and matching skills_loaded row.

No header plus no Store lifecycle row is activation unavailable, not
Agency/Agencies loaded: none. A Store row without the host-written response is
not response-delivery proof. If a host lacks the expected status or skill
surface, record the exact mismatch and stop that sub-proof.

## 4. Current exact-main child-proof boundary

Do not run either of these commands with --execute:

~~~bash
python -m agency_runtime.cli host-canary openclaw
python -m agency_runtime.cli host-canary hermes
~~~

The readiness reports are useful artifacts, but exact main intentionally limits
SAFE_CANARY_HOSTS to Codex and Claude. OpenClaw and Hermes reject live canary
execution because no proven bounded noninteractive native-child mode exists.
Do not bypass that gate or hand-construct a confirmation.

Exact main also has no supported child-artifact root/reader for either host.
Their bridges deliver child context in process, while ADR-0156 requires a
host-authored artifact containing the exact inference-selected card hashes
before first child speech. Therefore:

- installation, registration, parent header, skill, Store, or bridge stdout may
  support their own bounded claims but cannot prove Rule 4;
- an ordinary native child may diagnose the bridge payload, but it cannot move
  a Rule-4 cell without a supported host-authored artifact and matching
  native_child_delivery_verifications row;
- routing_decisions, specialists_loaded, copied plugin content, or model prose
  never substitute for that artifact.

If development continues on Linux, the first bounded diagnostic is to capture
the raw host-owned child-launch payload before Agency interprets it. Record
whether parent_session_id, parent_trace_id, worker_id, and native_run_id are all
present. Hermes may otherwise fall through as an ordinary user turn; OpenClaw
may take an early post-tool path before the shared child-start recorder.
Preserve a missing field or missing artifact as the product boundary rather
than patching evidence after the fact.

## 5. Live-work discipline

- Use genuinely new work units. Do not replay the consumed SAP, Erlang,
  COBOL/CICS/VSAM, Python-install-guide, or PostgreSQL-recovery units.
- Serialize hosts and provider calls. Keep every failed or timed-out attempt;
  never retry until green.
- Keep ordinary provider routing unchanged. The Windows Option A pins apply to
  Claude, Codex, and ZCode canaries only; they do not silently select a Linux
  host provider.
- Set a 420-second outer ceiling for any explicitly authorized live unit and
  terminate once at the ceiling. A killed or malformed upstream response is not
  a provider loss or successful staffing result.
- Never claim a contractor outcome, promotion, rule, or matrix movement from
  registration, a Store projection, or useful generic-child prose.
- Do not dispatch hosted Actions from this packet.

## 6. Evidence to return

Return one bundle per host containing:

~~~text
host:
checkout_sha:
clean_tree:
host_version:
profile:
runtime_digest:
store_schema:
install_result:
fresh_session_id:
agency_trace_id:
first_response_artifact:
header_exact:
resident_binding_id:
routing_decision_ids:
specialists_loaded_ids:
skill_name_and_row_id:
native_child_id:
raw_child_launch_payload_artifact:
child_artifact_path_and_sha256:
delivery_verification_id:
timeout_or_failure_receipt:
known_limit:
~~~

Also return the before/after contractor counts and Store integrity receipts.
Prompt and response bodies need not enter the durable roadmap; content-free IDs,
hashes, provider receipts, exact headers, and host artifact paths are enough.
Cells that this packet cannot reach remain unproven, which is the correct
result.


## 7. Current Linux OpenClaw checkpoint — 2026-08-21

OpenClaw was the only Agency-install target. Hermes remained the active
break-glass host and was not installed, stopped, restarted, or reconfigured.
Claude, ZCode, Codex, Codex OAuth, and the consumed Codex canary remained
outside the mutation boundary.

### Installation and invariants

The install checkout was clean at `a70131d63c511e418edcda2ccae1f8e45866a95a`.
OpenClaw remains the existing audited `2026.7.1-2 (0790d9f)` package with native
primary `litellm/task-general`, six fallbacks, 21 LiteLLM models, and 27 total
model entries. Only the existing gateway was stopped and restarted. Agency-only
install `479c1a47-7e89-4091-a0f4-548f6913db58` completed without restarting it
or changing contractors. The installer reported registered, enabled, and
runtime-verified Agency integration; dashboard installation was opted out.

The installed launcher resolves to this checkout. Bundle digest is
`475e56274dec5f7eb61b54a469489274247caa60a18910ff200ec7757bed59a4`, runtime
digest is `52724f5a8803d1662228a67c03c9a986a5eeebc2289ddb68cdad0306272de066`,
launcher SHA-256 is
`5539744ef47aa464921887ee067e3f3c54c9caeacac252259f5a5bb008d462cb`, and
install-manifest SHA-256 is
`8d25e7420dc7e8614e3981df0b20274d72add6617b7f899112c925287b82e8b6`.
The installed native plugin reports ten typed hooks, provider-safe tool
`agency_finalize`, conversation access enabled, zero diagnostics, and zero MCP
servers.

Latest pre-install online Store backup is
`~/.agency-runtime/backups/ar272-openclaw-nativehost-preinstall-Ah1yzQNU/agency.db`;
live and backup integrity are `ok`, and backup SHA-256 is
`64421c3fc50623940930d757f15f7cd5930537ea9f8d9dd682a5ca771c8ea66d`. Store
schema is 47 and contractor count is 15 before / 15 after. Redacted config
comparison proves native model, provider, credential, channel, and plugin-policy
semantics did not drift. Slack and Telegram report configured/running with an
empty current error.

Agency profile `linux-task-agency-router` uses provider type `litellm`, exact
requested alias/model-group `task-agency-router`, base
`http://127.0.0.1:4000/v1`, populated credential variable `LITELLM_API_KEY`, and
120000 ms. It is selected by the OpenClaw harness without changing the global,
Codex, or Claude routes. The OpenClaw gateway process has the credential
variable populated; no credential value is recorded.

### Exact-status control evidence

Fresh session `ba9ea05a-3694-4725-b2ea-0357bd16a112` began with exact first
message `agency status`. Native/Agency trace is
`c2574ce1-b81b-4e29-b66a-06293c6dde85`; Store run
`aedb79d3-79d9-428c-9eb3-90dbc8aac8c9` completed. The exact header was:

~~~text
Agency/Agencies loaded: agency-steward
Agency/Agencies delegated: none
Skills loaded: none
Actual Model selected: observed execution receipt: [general] task-general -> completed
Recruited via: deterministic
~~~

Accepted finalization `b0f9a0f4-8da2-4b54-b678-826b3a5b61bc` is labeled
`host=openclaw`. Response SHA-256
`bcba81da99187df1157a81e813538251e6108a853b2fb3265a21c9585a3794ca` exactly
matches the 680-byte assistant text in native transcript
`~/.openclaw/agents/nexus/sessions/ba9ea05a-3694-4725-b2ea-0357bd16a112.jsonl`,
whose SHA-256 is
`182788c62ac9dd84cd2c73390f10bbb0e4868826cdb0d9df67bbd7c7b1b980da`.
Routing decision `ea8821a5-b220-474b-9713-0fbb1e8d0498` abstained
deterministically. Request-scoped binding
`rmb-aa818901a43ad2bacee6d93edd010488` correctly has no durable resident row.
There are no specialist or skill rows. Native parent receipts used
`task-general` with zero fallback. This is status-control, finalization, and
delivery proof only.

### Agency inference failure and AR-273 repair checkpoint

The only harmless skill attempt used genuinely new text and was not retried.
Trace `9384d3a3-0a28-4150-a8fa-ab493efda7bf`, run
`a5504721-0aa9-4fa3-98df-f5667c933b5b`, and failure receipt
`3193483a-712b-4c1d-8f13-ccb6799433a1` record `preflight_failed` /
`workforce_inference_failed`. Both planner attempts automatically selected
harness `openclaw`, profile/provider name `linux-task-agency-router`, provider
type `litellm`, and exact requested model/model-group `task-agency-router`. Both
were rejected as `provider_response_contract_invalid`; no fallback to Codex,
Claude, or any other provider occurred. No Store-backed header, finalization,
skill row, routing decision, specialist, or model receipt was written. The bare
native word `Loaded.` is therefore not successful Agency skill evidence.

AR-273 traced the strict rejection to Agency's generic HTTP payload. The
LiteLLM/OpenAI-compatible path requested JSON-object mode but never supplied
the already bounded Agency schema to the model. It also recorded a configured
LiteLLM thinking level without forwarding it. The alias mapping was not the
defect and remains operator-owned and unchanged.

The retained pre-fix regression has six failures: two absent schema
instructions and four absent LiteLLM reasoning levels. The smallest repair
adds one deterministic schema instruction shared by compatible HTTP paths and
forwards `thinking_level` as LiteLLM's standardized `reasoning_effort`.
Strict local validation, bounded retries, fallback behavior, requested-alias
evidence, and actual-model reconciliation are unchanged. Exact regressions
pass 7/7; the affected warning-strict inference slice passes 134/134. No
shared-proxy, alias, host, credential, or host-native model configuration
changed. Live proof waits for the repository-required clean checkpoint.

No post-proof Telegram-scoped Store run has arrived. Operator `/new` plus exact
`agency status` is still required for Telegram delivery proof. No OpenClaw or
Hermes host canary ran, Rule 4 remains outside this package, and no AR-119 matrix
cell moved.

### Post-AR-273 install and retained live result — 2026-08-22

Agency-only install `4dd7ee41-121f-4cde-a391-9cecd0665d72` projected the
AR-273 repair into the existing OpenClaw host. Bundle digest is
`51320b45f63cc68db52b267928c1939ab908052f623900a51786228c5b978419`;
runtime digest is
`c71fbb41ca8780b5e5a5424ef240dbf92bdf56a36dbc9d2caac70dcfa22d3497`;
launcher SHA-256 is
`755ec953638d85b175f1b4aa705e9cc388cde3d5011520a6bfc7f2986528a78c`.
OpenClaw itself was not reinstalled. Its pre/current config comparison changes
only `meta.lastTouchedAt`; primary remains `litellm/task-general`.

Fresh exact first-message control session
`b610efe7-4e71-43c7-8011-fb13f2736f2b`, trace
`de166bdc-d649-462d-996b-b2b030a34a8e`, and run
`c5e8d0bd-99b5-431c-9bb3-6bead5d2eeef` completed. Routing decision
`bf93dd03-9d01-4043-a779-49ddee0adff8` abstained deterministically;
finalization `cbc9107f-a34a-4fad-b919-17f3e1ae1d44` accepted. The exact header
remains the five lines above with request-scoped binding
`rmb-5ccde2d9de6ac9c0ca8f254cb45e9a85`, which is correctly non-durable.
Transcript SHA-256 is
`2eeec604f55265e6c245944c2b7fa840c530efc50abb4ea37ac3cdab889049a3`.

The required distinct substantive session
`31f52706-f329-4640-a012-c9540e283770` reached the OpenClaw 180-second
provider-phase ceiling and is retained as a timeout, not a pass. Its transcript
SHA-256 is
`07257c4875c2526cbb7447be73ff74f2ea7333efd74b67925356dad812a70289`.
Agency trace `517c2c78-95e6-4dea-bfd7-b43f6d48671a`, run
`c080b393-72fd-4133-9485-d3e786e6c90a`, and failure receipt
`de5f98bc-ca21-4b9b-b881-d862bf5b4da8` record one
`provider_no_valid_response` attempt. It automatically selected harness
`openclaw`, profile/provider `linux-task-agency-router`, type `litellm`,
and exact requested alias/model-group `task-agency-router`, with zero
fallback. The OpenClaw process has `LITELLM_API_KEY`; LiteLLM returned HTTP
200 at the attempt boundary. No routing, finalization, skill, specialist, or
model row was created, and no actual answering model is available.

The proxy has no Agency callback. Exact response-envelope classification now
waits on explicit permission for one local diagnostic that uses the existing
credential only in memory and emits only field types, lengths, and parse
booleans. The rejected permission attempt sent no request and exposed no value.
The consumed substantive input will not be retried unchanged.

### Approved envelope classification and exact-schema repair

Lucas approved one content-free local diagnostic against the existing
`task-agency-router` alias. It read the populated `LITELLM_API_KEY` only
from OpenClaw process memory and never printed, wrote, or retained the value.
Only types, lengths, and parse booleans were emitted. The response was HTTP 200
and 477 bytes with a normal OpenAI choices/message envelope, no error, no tool
calls, and no separate reasoning content. Its 157-character content was braced
JSON and parsed as an object, but its four keys did not match the exact
two-property closed schema. The model field was present but its value was not
retained and is not actual-model evidence.

This proves endpoint reachability, authentication, alias acceptance, and
response-envelope compatibility. It also proves the remaining failure is not
an OpenClaw channel or LiteLLM transport defect: prompt-only schema delivery
does not enforce `additionalProperties: false` for the current routed model.

The installed LiteLLM 1.94.0 implementation maps the OpenAI-standard
`json_schema` response format to the routed provider's native schema format.
The focused repair therefore changes only LiteLLM Agency payloads to send the
exact bounded schema with `strict: true`; schema prompt delivery and strict
local validation remain. No target inspection, alias remap, retry, fallback,
proxy callback, host model, or credential configuration is added. Direct
OpenAI-compatible and other adapters remain unchanged.

The focused test failed before repair only on `json_object` versus exact
`json_schema` and is retained at
`/tmp/ar273-litellm-native-schema-red.xml`. The repair plus unchanged
OpenAI-compatible and reasoning behavior passes 6/6 at
`/tmp/ar273-litellm-native-schema-green.xml`. This is local code evidence;
the repair is not yet installed or live-proven.

### Deferred Hermes bundle

Hermes effective home remains `/home/holeshot/.hermes-nexus`; its gateway and
dashboard stayed active. Redacted config SHA-256 remained
`a984d9343cbd56b7ac3bb70586ce4db90a739d6a063a530b9183c5baca1e170d`, and no
Agency launcher was created or changed for Hermes in this package. Install,
fresh session, Store, skill, provider, and child fields are deliberately
`not run — owner-directed break-glass preservation`, not failed or successful
evidence.
