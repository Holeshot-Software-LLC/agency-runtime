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

### Agency inference failure and external prerequisite

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

Authenticated proxy metadata maps shared alias `task-agency-router` to
`ollama/qwen3.5:2b`. Its model metadata advertises function calling as false and
no structured-response support. The proxy has no Agency callback and cannot
import this checkout. Its response alias echo must not be promoted to the actual
answering model; actual model remains unavailable. Lucas must authorize an
approved structured-output-capable target for the shared alias, or approve a
contract-compatible strategy for the current target, before another inference
proof. Strict Agency validation must not be weakened.

No post-proof Telegram-scoped Store run has arrived. Operator `/new` plus exact
`agency status` is still required for Telegram delivery proof. No OpenClaw or
Hermes host canary ran, Rule 4 remains outside this package, and no AR-119 matrix
cell moved.

### Deferred Hermes bundle

Hermes effective home remains `/home/holeshot/.hermes-nexus`; its gateway and
dashboard stayed active. Redacted config SHA-256 remained
`a984d9343cbd56b7ac3bb70586ce4db90a739d6a063a530b9183c5baca1e170d`, and no
Agency launcher was created or changed for Hermes in this package. Install,
fresh session, Store, skill, provider, and child fields are deliberately
`not run — owner-directed break-glass preservation`, not failed or successful
evidence.
