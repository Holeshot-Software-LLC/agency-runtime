---
title: "AR-413 HTTP status propagation and bounded planner reliability repair"
status: active
category: worklog
created: 2026-09-08
updated: 2026-09-08
tags: [workforce, transport, receipts, live-evidence]
related:
  - docs/roadmap/issue-AR-413-preserve-http-status-in-staffing-receipts.md
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/handoffs/issue-AR-404.md
  - docs/decisions/0209-name-the-transport-cause-instead-of-one-code.md
supersedes: []
superseded_by: null
type: worklog
commit: ed26177f281fba0e4aea807d2092574ea0e47e3d
short: ed26177f
date: 2026-09-08
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/768
related_issues: [docs/roadmap/issue-AR-413-preserve-http-status-in-staffing-receipts.md, docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md]
---

# AR-413 status propagation and planner reliability

## Purpose

The owner approved planner/gateway configuration changes after two native turns
timed out upstream. Preserve actual HTTP status before further live diagnosis.

## Approach

Add the existing transport status to workforce/hiring attempt records and both
bounded receipt projections. Strict integer100..599 only; absent/zero omitted
for legacy fixed points. No response bodies, headers, endpoints or credentials.
Apply existing ADR-0209, without inference, retry or staffing-policy changes.

## Challenges and alternatives

The live gateway lists133deployments; the planner alias has subscription gpt-5.5
at order1 and existing glm-5-turbo at order2, both45secondtimeouts. Earlier native
activation succeeded through GLM; ordinary turns fail near45.8seconds. Plan one
reversible experiment promoting the existing GLM entry to order0, retaining the
subscription fallback and all other fields. No new provider/key or timeout
increase. Verify readback and ordinary staffing before retaining the change.

## Verification

80 focused tests pass across HTTP-status, staffing-failure, transport-cause and
preflight-diagnosis modules. The new tests cross actual failed workforce turns,
SQLite, routing/operator projection fixed points, hiring and malformed metadata.
Fast Python spine1151passed/3skipped in70.63seconds; dashboard224passed. Ruff
lint passes. Canonical artifact build at716fb04f failed before publication with
release Git output limit; diagnosis pending, no installed proof claimed.

At12:36:01UTC the authorized live gateway PATCH changed only existing GLM planner
deployment ed1b5bbc-bbb7-533a-b3d8-5873a004e4c1 order2 to0. Exact-ID/alias/model
preconditions pass; readback confirms0 and all other deployment parameters
unchanged. The original2 is retained for a scoped inverse PATCH. No service
restart, new key/provider, increased timeout or other alias change.

The next native check uses the existing trusted installed source4cbebf73 (not
the uninstalled status patch) and Codex's built-in approve-for-me reviewer for
the bounded MCP write. This is reviewed approval in workspace-write mode, not
hook-trust bypass or persistent approval reconfiguration. No empty IDs allowed.

## Follow-ups

Final owner delivery at13:02UTC: installed the independently verified d08c5008
wheel with no dependency changes. Its production files equal PR768/main; all614
installed package files compare byte-for-byte with that wheel. Codex install
completed native remove/add refresh, preserving a retained native backup, with
no optional dashboard restart. New bundle0fe533927f560ef672e1d97147802eced939e890dc5990aebb71f8a02b63700d,
projectionab77dcb13e8eb56928de9ec1fc87977dc78ef78b74355fa29d5aab9fb274b23f,
plugin0.1.0+codex.fa16f6ec90e5. Registered/enabled, no configuration drift;
fresh hook trust required and old activation stale by bundle/install ID. Stopped
at waiting_for_operator, without bypass or repeated native attempts. Other host
bundles remain on the prior projection and were not refreshed in this package.
The active capsule contains the exact terminal trust and activation steps.

The order experiment failed: native session01a08106-8cc4-7930-8a16-8544d1bd0db4,
trace01a08106-8d31-7d41-ace6-f019e6fc1295,73.764secondwall, planner HTTP failure
46910ms, no staffing/delegation/finalization. At12:40:26UTC restored order0 to2;
exact readback and unchanged other parameters pass. No speculative priority
change remains. The approval reviewer was enabled but no valid binding existed,
so this run cannot establish successful finalizer approval.

The release Git limit came from repository configuration-name inspection,
not source size. A clean local clone with the same exact d08c5008 source passes
canonical build, strict Twine and independent distribution verification without
raising limits or changing shared Git configuration. Wheel SHA256
fb385b5cbfa79301fb53b5c626815a7424dcbc50ab1e04552aa51bda922a819a.
An isolated target install executes four real loopback HTTP requests through
installed workforce code and SQLite:401/408/429/502 all read back exactly,
rejected turn status retained, private response body absent. Synthetic failure
fixture, not external-provider or native-host success. Owner hooks remain on
their trusted prior payload; this diagnostic installation did not refresh them.

Deterministic routing gates pass. Decision-conformance's first baseline fails on
private test-directory permissions under ambient umask; the077 rerun passes,
source_unchanged true. A minimal structured call to the exact GLM deployment
returns the correct object in2951ms; the alias returns it in2142ms. These prove
basic request reachability, not full staffing quality. A production planner
payload using the real293-worker snapshot (5337prompt characters,1967schema
characters,4096reply tokens) fails on both alias and directGLM with HTTP408 in
45704/45137ms. No native hook or worker execution is involved in this comparison.

The requested Codex install refresh reports already_current/no_op, enabled and
registered but activation required, hook trust unverified. Its published bundle
is f838a7676e42ac9b336da1335f3b26ca73e32cdc4c4126ace68c5d2c28f6aa7f,
plugin0.1.0+codex.7773634d503c. Bundle digest and projection digest are distinct
identities, not evidence of a changed installation. A separate current host
status inspection reports trusted hooks, runtime-verified maturity and the
matching11:24UTC activation attestation (digest7d808bc795bf). It still does not
attest ordinary staffing reliability after the observed planner failures.

The isolated Codex acceptance reviewer satisfied1/3/4 and marked2 absent for
missing explicit non-HTTP/legacy evidence. Added those three cases;83focused
tests now pass. The default Claude verifier returned no usable verdict. No
builder-authored verdict or acceptance override was used. PR768 owns delivery.

The second isolated Codex run records four satisfied verdicts against65a387ed;
AR-413 is complete on that exact diagnostic scope. A request-only low-effort
comparison still fails HTTP408 in45111ms. No persistent reasoning change was
made. The owner planner profile sends medium effort, but lowering it alone did
not repair this failure; no performance improvement or causal diagnosis claimed.

A final request-only comparison replaced strict JSON-schema response format with
JSON-object mode, retaining the production prompt and schema instruction. It
also fails HTTP408 in45284ms. No product/provider format setting was changed.
These bounded probes isolate a full-payload provider failure but do not identify
its upstream cause. No further full native retry is justified by these results.

AR-413 installed failure proof and isolated acceptance; AR-404 native ordinary
staffing/finalization with valid current binding and approved MCP-write mode.
Do not promote the old activation into current ordinary reliability evidence.

Source checkpoint `ed26177f281fba0e4aea807d2092574ea0e47e3d` preserves HTTP status through the full staffing failure path;80focused tests pass. Clean substantive/ledger pair precedes the authorized gateway experiment.

Pre-live checkpoint `0c240444ce167c0ca34054b38b65a31d7950913c` records the reversible order-only planner experiment and successful fast verification. Native runtime remains the trusted prior payload; artifact build is blocked on a bounded Git output diagnostic.

Installed checkpoint `6debb9f2ae7f0ae43ab1486b0cbd48f7c9e85897` proves all four HTTP statuses through the verified wheel and SQLite, and records the unsuccessful native planner experiment plus exact rollback. No gateway order change remains.

Evidence checkpoint `ecd1d26be53341d6f0e6f142c9879e34c33c23bb` binds the installed status demonstration, successful conformance rerun and direct deployment probe. Native ordinary staffing remains unverified.

Review checkpoint `b4899374bac82266e5d4000a43836d84cb9fbe18` adds explicit non-HTTP and legacy absence tests;83focused tests pass. Alias and direct deployment both fail the real planner payload with HTTP408.

Acceptance checkpoint `35cd65392adcaef9e78dc5f046f6dcb99e2c8270` records four isolated satisfied verdicts and closes only the HTTP-status scope; the full planner payload remains HTTP408 on every bounded comparison.

PR768 merged as `947dfaef34d07303ed23c4e9b909de2edea21ac2`; tracker765 is CLOSED. The verified d08c5008 wheel has identical production code to this merge and is installed in the owner runtime; Codex hook refresh follows.

Owner-install checkpoint `013ab75f66c5c3ce1e147e9fd8794c2ea32aa168` records614matching installed files, a completed Codex refresh and the fresh trust requirement. No live activation is claimed; the planner payload failure remains open.

PR769 merged as `2088ea069ba659edd5c95407e26cc9aa37e85842` with the installed delivery and operator trust checkpoint. AR-413 is closed; AR-404 remains open for planner reliability and fresh native activation.
