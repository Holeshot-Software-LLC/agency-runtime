---
title: "AR-426 Hermes context delivery checkpoint"
status: active
category: roadmap
created: 2026-09-09
updated: 2026-09-09
tags: [handoff, hermes, context]
related:
  - docs/roadmap/issue-AR-426-preserve-hermes-hook-specialist-context.md
  - docs/worklog/2026-09-09-hermes-context-spill.md
  - docs/decisions/0244-deliver-large-hermes-card-sets-through-native-tools.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-426
branch: codex/ar404-terminal-reliability-20260909
evidence_commit: 23ae46bf382e68f945cfaf90c83a00aa6c8c4f4c
minimum_ledger_commit: 1c0e3c16921b38974b02280cf8334834a90ec0a3
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/823
---

# AR-426 Hermes specialist context

## Checkpoint

Owned PR 824 branch contains recipe 19 complete-team delivery and bounded Hermes
callbacks. Source `176adc19`, canonical artifact `20c49e0d`; all 616 installed
files match. PR 827 retained Claude audit evidence and merged into this branch;
main remains at `c6c3e7b5` until PR 824's acceptance and merge checkpoint.

## Completed evidence

Fresh Hermes session `20260909_143551_e08888` passed in 114.863s. Native message
535391 contains all five inferred immutable cards, contract and delivery rules
without a spill pointer. Five Store headers match; first authoritative response
hash `6546ecb6525a7f1237f47e519b7971574e9d7424862bf50e23ee364f9a980968`.
AR-427 evidence retains exact native context, each full card, terminal and request.

Corrected original-source regressions fail seven cases across all five host paths
and both native retrieval paths; recipe 19 preserves the fifth selected worker
or rejects incomplete delivery before any load. Host/context ceilings are unchanged.
Focused 66 / 1 skipped, production 1151 / 3 skipped, UI 224, routing and frozen
conformance 188/188 pass. Canonical build, independent artifact and installed smoke
pass. Earlier permissive-umask and invalid-fixture failures remain recorded.

The one critic observer diagnostic restored owner configuration byte-for-byte.
Its real plan requested test-result interpretation without results; AR-428/#826
records that concern. The critic veto remains authoritative.

## Exact blocker

AR-426 authorized third isolated pass and AR-427 first pass satisfied all three
criteria each. Both scoped issues are done; PR 824 is ready for merge. AR-423 third pass satisfied criteria 1/3, left criterion 2 absent:
prior Claude routing selected five but native delivery retained four, omitting an
independent security reviewer. Fresh Claude session `0a59da24` / trace `28c8db15`
failed planner contracts in 118.255s before delivery. No unchanged retry is queued.

AR-418/#796 remains open: actual Hermes checkout `7cd91114`, upstream PR106490
still OPEN at `30f421ecce`; default adoption and original output cap are unproven.
Zcode first review/follow-up outputs put permission prose before headers and are
valid terminal rejections; later headers cannot replace those failed receipts.
Claude ordinary review and OpenClaw follow-up staffing failures remain retained.

Codex's eight refreshed hooks are now trusted with no modified/missing entries.
A fresh native Codex process and UserPromptSubmit hook run published projection
`37c1bf7d5eb0`; the parent still runs `6db15efbecbe`. The fresh probe passed in 103.434s, five exact cards and authoritative finalization. OpenClaw refresh completed; subsequent gateway RPC is healthy.

## Same-task continuity

Continue in the owned branch and preserve unrelated scratchpad and Windows work.
At or below 50 percent, keep a clean substantive/ledger checkpoint and continue.
No empty recovery pair, forced transfer or failed-receipt reopening.

## Next bounded work package

Merge PR 824, then record its exact merge ledger. Continue AR-428 planning repair from the captured packet; diagnose
Claude's exact second planner response before assigning its semantic failure.
All five hosts remain in scope; original fixed sample 8/15 is historical only.

## Verification

Metadata, policy availability, docs, exact worklog, strict tracker parity (419
items), Ruff and diff checks pass at the prior checkpoint. Recheck changed records
before handoff. No exhaustive or Windows workflow ran.

## Constraints

Inference alone selects specialists. Preserve critic, validators, trust, caller
scope and native limits. No manual selection, acceptance, external messages or
unbounded retries. AR-419 and AR-425 stay closed; umbrella AR-404 stays open.
