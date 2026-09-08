---
title: "AR-414 staffing and failure-header checkpoint"
status: active
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [handoff, staffing, headers]
related:
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
branch: codex/ar414-recruiter-20260908
evidence_commit: c1ef85662b01da7e8bbfa93917d6afdda1534aca
minimum_ledger_commit: 6291746a3916f6c2ee08be94197c9d2470b2597d
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/773
---

# AR-414 staffing and failure-header checkpoint

## Checkpoint

Recruiter configuration recovery is live-demo complete at the installed provider
boundary. Phase fast_verification before repository delivery. Fresh normal
staffing reproduced two malformed primary replies, reached the new content
fallback, passed strict staffing and critic, and accepted in96.503s. No native
session or latency improvement claim. No production Python/defaults changed.

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

Current long-lived hook reports projection14852134f0aa but last published
projectionf72f24a788ca. Normal operator reconnect/restart and a fresh session
are required for native verification. That mismatch does not verify installed
hook files. Reinstalling alone cannot refresh the current process. Do not
reinterpret earlier trust/installation receipts as proof of this process.

## Same-task continuity

Read the recruiter recovery worklog for changes, negative probes and reversal
limitations. Keep unrelated worktrees intact. Source baseline was maincea0020b;
current delivery branch is named above. Continue from substantive/ledger pairs.

## Next bounded work package

Finish remaining routing/conformance/tracker gates, commit and ledger the
recruiter evidence, open PR and merge. After the owner refreshes the long-lived
Agency integration, verify one ordinary native turn on the current installation.
Keep AR-414/415 open until their actual isolated acceptance gates are satisfied.

## Verification

Focused inference/configuration/installer336pass including12fallback regressions.
Named fast production spine1151pass/3skip; dashboard224pass. Metadata/docs1325
and Ruff778files pass. Routing, decision-conformance and tracker pending here.
No exhaustive suite, Windows matrix, new wheel, host reinstall or trust bypass.

## Constraints

No manual specialist choice, weaker validator, false acceptance, credential
replacement, cross-provider nomination merge, OpenClaw restart or backlog wave.
Preserve failed-run immutability and correlation. Owner config backup exists;
reverse only owned fields after concurrent-change checks. Gateway PATCH ignores
ordinary null fields: do not claim a null PATCH clears the new ZAI parameters.
