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

OpenClaw is the only active package. Hermes is the running break-glass host and
must not be installed, stopped, restarted, or otherwise mutated. OpenClaw
`2026.7.1-2` runs native primary `litellm/task-general`; Agency separately maps
its harness to `linux-task-agency-router` with exact requested LiteLLM alias
`task-agency-router`. Native model and alias catalogs contain no Agency-router
override.

Installation and channel startup pass, and exact bridge status returns exit 0.
Do not reuse the first local control as acceptance: session
`57f19f38-338d-4d93-9c46-eac7b6a4831a` / trace
`4959bd8c-a0bc-4e3d-bcb9-8cbcc1441547` ended `response_invalid` with missing
`actual_model_selected`. AR-271 repairs the dropped `model_call_ended` receipt
fields and is reinstalled, but a fresh post-fix session is still required.

After the mandatory clean checkpoint, run serially:

1. A new local OpenClaw session whose first message is exact `agency status`;
   preserve native transcript and require terminal Store success.
2. Operator Telegram `/new`, then exact `agency status`; preserve the first
   response before any other message and require a queued delivery receipt.
3. One harmless Agency skill load without a child, then the specified genuinely
   new restart-safety review without delegation.
4. Correlate runs, resident binding, routing decision, specialist, skill, model,
   provider-attempt, and finalization receipts. Requested alias evidence may be
   reported; actual model remains unavailable unless authoritative telemetry
   supplies it.

The direct CLI Telegram send suppression is an expected uncorrelated-outbound
gate receipt and does not prove channel failure or success. No host canary is
authorized for this package, and no Rule-4 or matrix claim follows.
