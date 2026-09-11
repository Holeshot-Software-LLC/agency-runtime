---
title: "AR-442 acceptance verification record"
status: active
category: roadmap
created: 2026-09-11
updated: 2026-09-11
tags: [acceptance, header, response-contract]
related:
  - docs/roadmap/issue-AR-442-a-host-model-reads-the-response-contract-as-an-injection.md
  - docs/decisions/0255-say-who-delivers-the-response-contract.md
supersedes: []
superseded_by: null
type: acceptance-verification
issue_id: AR-442
candidate_commit: 3c90d90bc83be11f234af60c1a185470d32eb696
evidence_cutoff: 2026-09-11
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/888
---

# AR-442 acceptance verification record

## Builder evidence

The builder cites observations and does not judge. Scope is the response
contract text (ADR-0255), its three delivery sites, and the fresh native
turns run on the owner machine after the reinstall of main `5c4e4787`
(runtime `50aae778c053`) through the liveness harness on the ordinary-review
wording. Codex was reinstalled to `activation-required` and its one exec
turn produced no Agency run, so codex is cited as unmeasured. Zcode's three
turns all ended `preflight_failed` at the critic, so its header lines are
cited on failed-preflight turns rather than completed ones.

| Criterion | Kind | Artifact | Observed | Source |
|---|---|---|---|---|
| 1 | file | The provenance names Agency Runtime as the owner-installed hook, calls the block host configuration, says the lines report Agency's record supplied in the snapshot or declared unavailable, reported as given and never invented, not identity claims | 2026-09-11 | agency_runtime/core/header/response_contract.py:44-68 |
| 1 | file | Every delivery site emits the same constant: claude/codex/zcode hook, openclaw bridge, hermes bridge | 2026-09-11 | agency_runtime/adapters/hooks.py:2648-2648 |
| 1 | file | Openclaw delivers the constant on INITIAL | 2026-09-11 | agency_runtime/adapters/openclaw/node_bridge.py:232-232 |
| 1 | file | Hermes delivers the constant above its delivery rules | 2026-09-11 | agency_runtime/adapters/hermes/bridge.py:97-97 |
| 1 | test | The pin, the provenance order and phrases, and the claude reserve are asserted | 2026-09-11 | tests/test_response_contract.py:102-160 |
| 1 | command-output | The named header, hook, hermes, context-budget and claude delivery suites pass under warnings-as-errors; the artifact lists the command and every node id, including the three response-contract tests and the Stop-path hook tests | 2026-09-11 | docs/roadmap/evidence/AR-442-focused-tests-20260911.txt:1-157 |
| 2 | file | Nine fresh turns after the reinstall with harness tags, store run ids, statuses, finalizations and the count of header lines in each response | 2026-09-11 | docs/roadmap/evidence/AR-442-per-host-measurement-20260911.json:10-190 |
| 2 | file | Per-host summary: claude and hermes each completed with five lines on their second turn, openclaw on its first; zcode three failed-preflight turns each with five lines; codex unmeasured at activation-required | 2026-09-11 | docs/roadmap/evidence/AR-442-per-host-measurement-20260911.json:191-197 |
| 2 | file | Per-host response_invalid counts since 2026-09-08 before and after the measurement, none added | 2026-09-11 | docs/roadmap/evidence/AR-442-per-host-measurement-20260911.json:198-213 |
| 2 | file | Limits: codex unmeasured, zcode never completed on this wording, latencies show live calls | 2026-09-11 | docs/roadmap/evidence/AR-442-per-host-measurement-20260911.json:214-220 |
| 2 | tracker | Tracker issue for parity | 2026-09-11 | https://github.com/Holeshot-Software-LLC/agency-runtime/issues/888 |

## Verification

| Criterion | Verdict | Verifier run | Evidence digest | Observed | Reason |
|---|---|---|---|---|---|
| 1 | satisfied | `AR-442.1-20260911-6ecdccd5` | `ec044a0c9d339d531669f85ecbe93aa37f5a8cebce6ddfdc25120ee83058c7cc` | 2026-09-11 | response_contract.py:44-52 names the owner-installed Agency Runtime hook and says header values are Agency's own turn record from the snapshot; test_response_contract.py:102-140 pins it; AR-442-focused-tests-20260911.txt shows 134 passed under -W error including Stop-path hook tests. |
| 2 | contradicted | `AR-442.2-20260911-ec699a65` | `e24babb5505502b6b61491734aea4c334a705ac198f606f408b52c65c746d40b` | 2026-09-11 | In AR-442-per-host-measurement-20260911.json only claude, hermes and openclaw reach status completed; zcode's three turns (lines 52-69, 127-146, 170-189) all end preflight_failed and codex has store_run null, and limits (lines 215-218) concede zcode never completed and codex is unmeasured. |
