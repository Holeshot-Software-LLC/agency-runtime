---
title: "AR-185 exact activation verification recovery capsule"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [handoff, codex, activation, owner-authority]
related:
  - docs/roadmap/issue-AR-185-bind-codex-activation-verification.md
  - docs/roadmap/acceptance/issue-AR-185.md
  - docs/roadmap/acceptance/evidence/AR-185-exact-activation-verification-20260907.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-185
branch: codex/ar185-activation-proof
evidence_commit: c64ce3ce54c6e51280292298b5e3600611cb72fc
minimum_ledger_commit: d28ccc232dcc00af0162a2409930dd272bf97b5f
hard_checkpoint_percent: 50
tracker_url: null
---

# AR-185 exact activation verification recovery capsule

## checkpoint

This records-only package follows AR184 PR #734/mainc64ce3ce and its merge
ledger. Source verification was observed at24eede12; subsequent main deltas
are documentation only. The exact installed live proof remains separately bound.
AR-185 remains in_progress; the acceptance builder has candidate_commit pending
and no verdicts. No runtime or owner-profile changes were made.

## completed-evidence

- Current exact CLI validates before the verification-only early return; it
  neither enters generic install nor overlaps prepared Codex refresh.
- ADR-0117 already permits owner CLI authority without a second presence
  ceremony. Criterion3 now says owner-CLI prepared mutation; original wording
  is preserved verbatim in the receipt, with transaction safeguards retained.
- Criterion2 explicitly scopes rejection to the exact no-bypass slice; the
  original wording is retained and ADR-0173's distinct autonomous/managed
  modes remain supported. No exact flag or timeout guard is weakened.
- Fresh focused source checks:175 passed2.31s;71 passed/40 Windows deselected
  1.31s;28 passed0.73s. Total274. Exact commands/raw stdout are portable evidence.
- Fresh hash inspection:328/328 installed Python modules equal hook4329 and
  manifest;326 equal08fab1c4,325 equal24eede12. Only AR131 public-ID additions
  and AR407 generic drift differ. All14 verification helpers and early-return
  prefix remain AST-identical. No whole-main-installed claim.
- Existing September7 current-profile Codex0.153.4 Linux proof:exit0,
  installation_attempted=false, no trust bypass, v4 attestation0bf5239c and
  trace01a07de5-15c3-7350-86c4-b38e886caa61. Main AR180 receipt correlates
  pre-speech v6 card, completed child and accepted parent finalization.

## exact-blocker

The nine pending builder criteria need parent publication, candidate freezing
and isolated verification. This builder makes no satisfaction judgment.
Existing hook trust, not a new TUI approval, preceded the live proof. Windows,
TUI/Desktop, multi-card and AR180 child-only placement are not claimed.

## same-task-continuity

After this smallest clean publication checkpoint, continue oldest-first
non-Windows backlog work in the same task. The owner authorized PR/merge
publication and unattended work until September8 01:00UTC; no repeated live
canary, credential change or new trust ceremony is needed for this package.

## next-bounded-work-package

Parent publishes these four owned files after AR183/184, creates the required
ledger, freezes the pending acceptance record at the substantive commit, and
runs the nine isolated checks. Preserve all known scope limits; only recorded
satisfied verdicts may authorize completion. No global records were edited by
the child worker.

## verification

The receipt owns the three fresh warning-strict commands and source comparison.
Worker metadata, policy availability and whitespace checks pass. The inherited
base merge-ledger gaps are now represented in publication ancestry. Parent
runs all record gates after candidate freezing. No full corpus,
provider call, native Windows execution or owner configuration mutation ran.

## constraints

Preserve the original criterion2/3 provenance and unchanged criterion9 wording.
Do not restore deterministic canary selection or retired presence machinery.
No raw private card, credential, full rollout or inaccessible receipt dependency
in these records. The positive native header belongs to the recorded canary,
not the still-unverified ongoing parent conversation.
