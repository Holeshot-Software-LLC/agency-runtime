---
title: "AR-404 evidence-led backlog completion handoff"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [handoff, backlog, acceptance, delivery]
related:
  - docs/roadmap/issue-AR-404-evidence-led-backlog-completion.md
  - docs/roadmap/AR-404-backlog-inventory-20260905.md
  - docs/roadmap/handoffs/issue-AR-400.md
  - docs/roadmap/issue-AR-348-enforce-strict-independence-in-production.md
  - docs/roadmap/issue-AR-349-persist-rejected-hiring-cases.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-404
branch: codex/ar400-delivery
evidence_commit: e758f217c810399100ebf2909e4561d6a243bdda
minimum_ledger_commit: 969321f4a1ce22bac0e1a0eb9be3edb037d4fcfc
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 evidence-led backlog completion handoff

## Checkpoint

The owner asked to commit review artifacts, plan and implement the findings,
then clean up and complete the backlog. This item owns the full baseline, not
just the completed review slice. Phase: implementing. No implementation agents
were delegated. The ordered plan, inventory and accepted review records are
committed; the worklog registry identifies their delivery PR merge.

## Completed evidence

- Baseline inventory: 155 unfinished records, 56 open and 99 in_progress;
  105 p0 labels. Five acceptance files at inventory time, only two before the
  current package created its builder records. All 155 have an assigned lane;
  this is planning, not semantic verification of every record.
- AR-400/401/402/403 fixes merged in PR #669 at 1de05aea and installed from a
  non-editable pinned build; projection 349f1ae7fc74.
- All five deterministic host contracts pass. Claude isolated native-child
  canary passed at 16:51Z, including code-reviewer delivery and final header.
- Twelve isolated acceptance criteria for those four issues now satisfied.
  The first three absent judgments lacked production-wiring excerpts; their
  original verdicts are preserved in 606065f2 and the augmented excerpts were
  re-verified once. No judgment was written by the builder.
- Latest focused regression: 228 passed, one skipped. Previous named fast
  spine 1004 passed/three skipped, JS 138, routing pass, 182 mutation kills.
- Missing AR-398/399 trackers mapped to #670/#671 and closed against existing
  acceptance; stale-open AR-397 #654 also closed. The four accepted review
  issues close with the delivery PR; verify_tracker confirms resulting parity.
- After the four review closures, 151 baseline items remain plus AR-404.

## Exact blocker

The entire backlog is not complete. AR-348 was reproduced against current
production hiring with fake valid replies in a disposable Store:
strict_independence=true still returned hired and created a worker on one
provider. AR-349 still returns an in-memory rejection without a case and its
existing test asserts hiring_case is None. Neither was changed by AR-400.

Native rollout: Codex requires attended trust of eight changed hooks in a fresh
terminal TUI; OpenClaw requires permission to stop/restart the gateway; Hermes
and ZCode need supported ordinary-session proof (no bounded native-child
canary backend here; ZCode has no discovered CLI). These are not general
permission to stop unrelated work or waive proof.

## Same-task continuity

Keep source work in an owned branch/worktree, merge by PR, update exact ledgers.
Installed runtime stays pinned to code 1de05aea until another runtime change;
documentation-only delivery commits do not require another payload install.
Current global settings, gateway credentials and historical receipts were not
rewritten. The old PATH launcher was backed up before its interpreter changed.

## Next bounded work package

1. Reproduce and repair AR-348/349 in a fresh bounded code package. Include
   supported legacy providers, per-harness profiles, fallback winners and
   safety-repair creators; prevent any unsafe worker and preserve atomicity.
2. Follow lane C with a small retained multi-turn quality/latency corpus under
   AR-253. Report full staffing p50/p95 and rejected trials, not only recall.
3. Resolve AR-393 criterion 5's impossible retroactive receipt wording with the
   owner; no historical data rewrite. Continue the remaining lanes without
   mass closure or automatic priority relabeling.

## Verification

Run focused production-path regressions and the repository named fast spine,
then one bounded observable demo per package. verify_docs --require-tracker and
verify_tracker govern record parity; verify_acceptance supplies isolated
criterion verdicts. No exhaustive corpus, coverage matrix or workflow dispatch
was run in the current package.

## Constraints

No direct main commits, native trust bypass, unattended service interruption,
credential creation or hidden provider changes. Do not implement superseded
proposals just to check boxes. Scope every claim and keep platform/operator
exits visible. Never mark AR-404 done while any baseline item is unaccounted.
