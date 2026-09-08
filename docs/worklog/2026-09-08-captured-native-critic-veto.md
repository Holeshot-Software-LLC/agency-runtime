---
title: "Capture the native handoff veto and retain its qualified cause"
status: active
category: worklog
created: 2026-09-08
updated: 2026-09-08
tags: [critic, staffing, native, diagnostics]
related:
  - docs/roadmap/issue-AR-414-reliable-staffing-failure-headers.md
  - docs/roadmap/issue-AR-416-retain-qualified-critic-veto-causes.md
  - docs/decisions/0240-project-qualified-critic-veto-causes-with-an-omission-marker.md
supersedes: []
superseded_by: null
type: worklog
commit: 6a0eb8506bde7d4436ce5c4e63cf2aba5ae33c33
short: 6a0eb850
date: 2026-09-08
pr: null
related_issues:
  - docs/roadmap/issue-AR-414-reliable-staffing-failure-headers.md
  - docs/roadmap/issue-AR-416-retain-qualified-critic-veto-causes.md
---

# Capture the native handoff veto and retain its qualified cause

## Purpose

Continue from clean synchronized main de307051. Capture a failing native
proposal before judging its critic, then repair only a proven defect.

## Approach

An ephemeral loopback observer forwarded the existing critic HTTP request and
response bytes unchanged. Only the owner critic profile base URL temporarily
pointed to the observer; the original model, credential, call bounds and hooks
were preserved. Synthetic observer checks verified byte identity, credential
forwarding without logging headers, and exclusion of unrelated requests.
The owner configuration was restored byte-for-byte in a finally block;
observer_errors was empty. No hook edit or trust bypass occurred.

The exact request was `give me a handoff for a new session to continue` in
session `01a08208-d73f-7010-9ff0-f4977c68fce6`. Two bounded native observations
returned the same packet and valid qualified veto:

| Native trace | Critic UTC interval | Whole command |
|---|---|---|
| 01a0821b-af73-70b0-b3bd-4ffd84b98bc9 | 17:41:08.309558–17:41:37.415 | 95.235s |
| 01a0821d-2379-7dc2-a360-eb3bedbac25b | 17:42:35.530934–17:42:44.651 | 44.437s |

Both remained preflight_failed with only staffing_critic_rejected persisted.
The second observation occurred because the bounded observer's stop condition
looked for the very projected cause lost by this defect; the maximum was two.
There was no retry until acceptance and neither turn was accepted.

The self-contained [captured packet](../roadmap/evidence/AR-414-native-critic-packet.json)
contains the synthetic request, actual inferred plan/proposal, eligible cards,
critic response and hashes, without HTTP headers or credentials.
Request SHA256: 22dd712902d7ca8ab33d1af00dbe73ed994b8e2e3c09e013a222271918fcab33.
First response SHA256: 7cb2e56855c9ea72c117090c1411d81790d8ad8ea1a53eb8a9730af151d6ba16.
Second response SHA256: 08542ba73e2a86ee7a74b584f0357be81a6603e6e96196b064226a3d56177677.

## Challenges encountered

The proposal assigned project-delivery-response-documentation-specialist to
handoff drafting and experiment-tracker to review. The latter's actual contract
requires experiment hypotheses, metrics and decision rules; this handoff has
no experiment. That mismatch supports rejection. The critic returned
wrong-neighbor-selection-documentation-evidence-researcher. Its named
alternative was present only as an eligible identity, not a ranked full card.
Reading that alternative's full contract showed narrower primary-documentation
verification of framework APIs, versions and defaults. Therefore the capture
does not establish that the named alternative fits. No replacement is endorsed.
These newly captured proposals do not reconstruct either older failure receipt.

The critic accepts valid reasons up to128characters, but receipt projection
allows56including critic_. The qualified cause exceeded that limit and vanished.
The initial captured-response regressions failed4/8before the source fix.
Subsequent test-harness corrections used the actual finalizer argument and dict
return contract, and queried finalization events directly from the test store.

## Decisions and alternatives

ADR-0240 retains a recognized standard veto-ground prefix at a hyphen boundary
and explicitly reports critic_reason_detail_omitted for a valid oversized code.
Unknown oversized codes get only that marker. Ordinary fitting codes stay exact.
All existing validation, count, length and disclosure bounds remain. Expanding
reason lengths could overflow the512character disclosure when four reasons are
rendered. Truncating specialist identities would create misleading diagnostics.
No recruiter prompt, critic approval, selection or repair behavior changed.

## Verification

Focused captured-response/critic/receipt/inference suite:124passed. Named fast
production spine:1151passed,3skipped. Ruff check and format:779files pass.
The real SQLite failed-header/finalizer replay retains the cause and omission
marker, leaves the run failed, and creates zero accepted finalization events.
UI, routing, frozen-source conformance and final documentation checks remain
pending at this initial clean checkpoint. No exhaustive corpus or Windows matrix.

## Follow-ups

AR-416 remains open pending isolated acceptance verification. This is a source
fix and captured-response replay, not an upgraded installed native demonstration.
The installed c1ef8566wheel and f72f24a788ca hook projection remain unchanged.
AR-414 retains its earlier ordinary accepted native review and exact Stop-hook
acceptance; this package does not claim handoff acceptance or improved latency.
AR-414/415 remain open. Next bounded package: finish source verification and PR
integration; separately qualify installation/native evidence for this diagnostic
change under the release checklist before claiming installed behavior.
