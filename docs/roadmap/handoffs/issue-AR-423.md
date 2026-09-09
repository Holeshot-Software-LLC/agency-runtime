---
title: "AR-423 Claude native context delivery checkpoint"
status: active
category: roadmap
created: 2026-09-09
updated: 2026-09-09
tags: [handoff, claude, context]
related:
  - docs/roadmap/issue-AR-423-preserve-claude-hook-specialist-context.md
  - docs/roadmap/issue-AR-424-preserve-last-card-whitespace.md
  - docs/worklog/2026-09-09-claude-native-context-delivery.md
  - docs/decisions/0241-deliver-large-claude-card-sets-through-versioned-mcp.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-423
branch: codex/ar423-acceptance-20260909
evidence_commit: 03a82c3b2314e847a70ae670b44c554ce67e94c7
minimum_ledger_commit: 2b19cce623a846b5b96f6a3803f9c4b32a1a8abc
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/811
---

# AR-423 Claude native context delivery

## Checkpoint

Owner authorized one third isolated pass on 2026-09-09 ("go for it"). The new
owned worktree starts at c6c3e7b5; the packet now includes all four exact native
MCP results, immutable card hashes and appended delivery disclosures. No new
native trial or permission change is needed for this retained acceptance scope.

Native full-card delivery now passes on PR821 candidate2b19cce6/source03a82c3b.
The underlying recipe16 delivery implementation came from PR814/cd86e40a.
615installed package files match the canonical wheel. Both exact Claude native
MCP Allow rules are saved and semantically unchanged; no operator tool wait.

## Completed evidence

Session545f5ca7-2937-412f-a9be-6b4e4c665204,
tracedf374667-2599-4798-a852-1e6f972aed25,239.508s,4exact selected full cards
through native MCP,5Store-matching fields, accepted matching response hash
f9b78ee4a8b0fd116e18fcffa0a9328ba67ff1b102586bf387f94845583f423b.
AR-404-claude-large-context-after-planner-context-20260909.json records exact
native tool-use/result correlation and card hashes. Planner repair and independent
critic both apply. The fixed Claude sample separately passes2/3, not all cases.

Original pointer evidence is now directly retained in
AR-423-original-native-pointer-20260909.json: native attachment81a967a9, saved
16076bytes/16067UTF16units, tracef725587c in the persisted body, same-session Store
correlation. Native limit10,000UTF16; prior denied and planner-failed probes remain.

## Exact blocker

Fresh recipe 19 Claude session `0a59da24-79ca-4bc5-afa2-b4f4e32ba5eb` / trace
`28c8db15-403f-4d27-85c2-c660b4e16ae1` failed both planner contracts in 118.255s
before card delivery. First reply missed correctness/security reviews; second
reported semantic invalidity. No unchanged retry or fourth isolated pass.


Authorized third pass: criteria 1/3 satisfied, criterion 2 absent because the
packet did not establish independent assurance. Read-only routing evidence then
found five selected workers but four persisted prompt references, omitting the
security reviewer. AR-427/#825 repairs that High delivery defect in PR 824.
AR-423 remains blocked until fresh complete-team proof and isolated evidence.

## Same-task continuity

PR821 owns this package and exact worklog. After merge the named branch is
historical; create a new owned worktree. Do not recreate historical fixes or
repeat native trials without changed conditions. At50percent checkpoint and
continue in the same task. No pending Claude tool or Codex trust approval.

## Next bounded work package

Resolve AR-427's High delivery finding, then prepare fresh complete-team evidence
for the remaining independent-assurance gate. Close AR-423
only if all three criteria receive satisfied verdicts. AR-404 retains the
separate five-host8/15fixed result and Hermes/Zcode/recruiter/critic failures.

## Verification

Fresh Claude context12pass, planner focused143pass, production1151pass/3skip,
UI224pass, frozen conformance188/188 and exact615file installed match. Full native
card/headers/finalization proof passes. No broad reliability or Windows claim.

## Constraints

Inference-owned staffing, independent critic, caller scope, trust and finalization
remain mandatory. No manual specialist choice, trust bypass, unbounded retries,
file-read workaround or manual acceptance. Owned worktree -> PR -> merge, exact
worklogs, preserved prior failures and isolated verdicts.
