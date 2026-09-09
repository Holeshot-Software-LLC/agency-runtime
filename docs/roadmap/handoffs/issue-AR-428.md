---
title: "AR-428 Hermes planner evidence checkpoint"
status: active
category: roadmap
created: 2026-09-09
updated: 2026-09-09
tags: [handoff, hermes, planner]
related:
  - docs/roadmap/issue-AR-428-avoid-test-results-units-without-test-results.md
  - docs/worklog/2026-09-09-hermes-planner-evidence.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-428
branch: codex/ar428-hermes-planner-evidence-20260909
evidence_commit: 7b263fb9f6d0d8a422eb7d047a97d997e435942f
minimum_ledger_commit: 16ae94261722c3ed4f35859a01db13caa2925a60
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/826
---

# AR-428 Hermes test-result planning

## Checkpoint

Scoped outcome: supplied-code-only tasks retain independent static review without
inventing test-result analysis for unexecuted tests. Active compact planner and
repairer share the boundary; recipe20 separates new planning context.

## Completed evidence

Original exact native plan, selected contracts and critic veto remain in
AR-428-captured-native-critic-packet-20260909.json. OpenClaw priority diagnostic
passed headers/terminal twice; its old veto did not recur and no repair was inferred.
PR830 merged; its exact ledger is the first commit on this owned branch.

## Exact blocker

Fresh Hermes session20260909_153129_1f3091 failed wrong-neighbor staffing in81.860s.
Planner/recruiter applied; exact plan was not retained. Finalization absent.
Observed session20260909_153433_eef6b8 also failed, but its exact critic packet
shows four units, no invented test-evidence, and independent static review.
First isolated planning acceptance remains pending; no whole-host pass.

## Same-task continuity

Continue in this owned branch. At or below50percent keep a substantive/ledger
checkpoint and continue. Preserve unrelated work and failed receipts.

## Next bounded work package

Run the first isolated AR-428 acceptance against the frozen original/new packets.
Retain both failed receipts. Remaining nomination relevance needs separate diagnosis
under AR-404; Codex and Claude follow in owner priority.

## Verification

Final recipe20 focused164/1skip and production1151/3skip pass. UI224, routing,
Ruff788, docs1379 and strict tracker419 pass. Frozen conformance passed188/188;
canonical artifact and616 installed files verify. Fresh native failed;
no exhaustive/Windows run.

## Constraints

Inference selects every worker. Critic, validators, trust, native limits and caller
scope remain enforced. Host order OpenClaw, Hermes, Codex, Claude; Zcode deferred.
