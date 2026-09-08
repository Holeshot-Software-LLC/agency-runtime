---
title: "AR-414 staffing and failure-header checkpoint"
status: active
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [handoff, staffing, headers]
related:
  - docs/worklog/2026-09-08-native-staffing-receipts.md
  - docs/worklog/2026-09-08-recruiter-fallback-recovery.md
  - docs/roadmap/issue-AR-415-respect-negated-change-requests.md
  - docs/worklog/2026-09-08-negated-request-scope.md
  - docs/roadmap/issue-AR-414-reliable-staffing-failure-headers.md
  - docs/worklog/2026-09-08-failed-headers-and-planner.md
  - docs/decisions/0239-render-failed-turn-diagnostics-without-acceptance.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-414
branch: codex/ar414-native-receipts-20260908
evidence_commit: 9e6d05c001910e21928f60834d84199075757664
minimum_ledger_commit: 39cfdfd9136bed94b7c7bf7ce292d60210dcd7b1
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/773
---

# AR-414 staffing and failure-header checkpoint

## Checkpoint

Phase live_demo. One ordinary installed native review has uncached accepted
staffing and exact-response Stop-hook acceptance. The stale-process blocker is
resolved for the current MCP process and all eight hook hashes are trusted.
The exact historical handoff request reproduced a semantic critic veto in the
fresh native session; diagnosis remains in progress. No production/config edits.
See the native-receipts worklog for exact trace IDs and response hash.

## Completed evidence

Header repair merged PR774/905d37b8; planner instructions PR775/975ce7b4.
Actual SQLite/MCP diagnostic renders truthful failed headers without accepting
the failed run. Earlier normal native session01a081a6-c4bf-7ee3-916a-5dff92d0b43b
delivered all five failure-header fields and exposed AR-415's negated-scope bug.
AR-415 repair merged PR779/d0bb4127, evidence PR780/21a8a39e, ledgercea0020b.
Installed c1ef8566 wheel74988840e7f2e01aebd1db45ccef56372cfe07a1c87b7ce515b6df19577590bc;
all614package files matched. Historical native evidence is not new-artifact proof.

Recruiter failure isolated: same captured real53,782-character packet returns
200 on MiniMax,404/model_not_found on the GPT-5.5 fallback. Owner configuration
had no content-fallback route and strict budget5 could starve fallback/critic.
GPT-5.6-sol candidate timed out60s and was not adopted. GLM candidate passed
the actual nomination accumulator and staffing verifier. See worklog for IDs.

Two existing recruiter fallback deployments now use openai/glm-5-turbo, existing
ZAI credential reference and low reasoning through extra_body. Stored mode is
chat, base_model glm-5-turbo; failing intermediate /responses mismatch corrected.
Original MiniMax primary, critic and unrelated gateway deployments unchanged.
Agency adds only recruiter content-fallback profile/mapping and strict budget8.
Budget covers subject1, planner2, recruiter2, fallback2, critic1; bounds unchanged.
Unrelated owner configuration compared equal after excluding these additions.

Explicit fault demo: inject two primary empty objects; actual fallback first
returns non-JSON15.282s, repair accepted18.783s, actual critic approved3.171s.
Accepted37.282s including two synthetic faults and three simulated prior calls;
all8funded budget units used, no hidden retry, no validator changes.

Fresh unmodified installed pipeline: {} then units:string rejected with exact
recruiter_response_shape_invalid; content fallback12.509s and critic2.396s pass.
Accepted96.503s: subject2.963, planner6.413, embedding38.258, reranker8.880,
primary3.639+21.166seconds. Naturally reproduced failure recovered, not just a retry.
Embedding latency is recorded, not bundled into this recruiter repair.

## Exact blocker

Historical failure receipt ba132c4d records successful recruiter and critic calls
followed by wrong-neighbor-selection. Subject classification failure was nonfatal.
Fresh native handoff trace01a0820a-fc29-74c0-8063-d53748450a7f repeats that veto.
Neither failure receipt retains the proposed team, so the critic cannot yet be
judged right or wrong. One instrumented installed-provider diagnostic is pending.
No operator trust/restart gate remains for this demonstrated native process.

## Same-task continuity

Read the recruiter recovery worklog for changes, negative probes and reversal
limitations. Keep unrelated worktrees intact. Source baseline was maincea0020b;
current delivery branch is named above. Continue from substantive/ledger pairs.

## Next bounded work package

Inspect the handoff diagnostic, finish the frozen-source conformance run, and
record the scoped native outcome. Keep AR-414/415 open until their actual
isolated acceptance gates are satisfied. Do not retry until a critic approves.

## Verification

Current focused189pass, production1151pass/3skip, UI224pass; Ruff/docs/routing
and strict tracker pass. Current conformance remains pending after two runner
environment setup failures; corrected copied-interpreter/private-umask run is
in progress. The following paragraph describes the prior recovery checkpoint.


Focused inference/configuration/installer336pass including12fallback regressions.
Named fast production spine1151pass/3skip; dashboard224pass. Metadata/docs1325
and Ruff778files pass. Routing and strict tracker406items pass. The first
conformance run was invalidated by a test edit; frozen-source repeat passes:
188mutations killed,0survived/invalid, source_unchanged=true. Corrected focused
336pass. Installed614file identity and six scope boundaries rechecked.
No exhaustive suite, Windows matrix, new wheel, host reinstall or trust bypass.

## Constraints

No manual specialist choice, weaker validator, false acceptance, credential
replacement, cross-provider nomination merge, OpenClaw restart or backlog wave.
Preserve failed-run immutability and correlation. Owner config backup exists;
reverse only owned fields after concurrent-change checks. Gateway PATCH ignores
ordinary null fields: do not claim a null PATCH clears the new ZAI parameters.
