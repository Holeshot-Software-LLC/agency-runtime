---
title: "AR-404 evidence-led backlog completion handoff"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [handoff, backlog, acceptance, delivery]
related:
  - docs/roadmap/AR-404-backlog-dispositions-20260905.md
  - docs/roadmap/acceptance/issue-AR-285.md
  - docs/roadmap/issue-AR-405-make-directory-identity-regressions-portable.md
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
branch: codex/ar404-backlog-reconciliation
evidence_commit: 6edfa6d8b5cb34155a249ae37896e7de2013768b
minimum_ledger_commit: 6edfa6d8b5cb34155a249ae37896e7de2013768b
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/672
---

# AR-404 evidence-led backlog completion handoff

## Checkpoint

The owner asked to commit review artifacts, plan and implement the findings,
then clean up and complete the backlog. This item owns the full baseline, not
just the completed review slice. The latest request prioritizes semantically
triaging done, contradictory and unwanted records before more implementation.
Phase: focused_review. No implementation agents were delegated. The current
batch retires four obsolete contracts, reconciles current no-helper release
acceptance and prepares AR-285 verification. Worklog identifies delivery commits.

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
- First semantic batch retires AR-132/167/169/267, preserves original criteria
  and records successors. ADR-0219 retires helper-specific release/signing
  obligations while keeping the existing two wheel profiles and cross-OS proof.
- AR-285 offline parent/current replay reproduces unknown before the repair and
  proven stopped now, plus eleven current negative/legacy cases. Focused
  installer/registration suite: 181 passed in 4.49 seconds. Builder record cites
  historical stopped-host install receipts separately; isolated verdicts pending.
- Wider focused run: 443 passed, two skipped, two failed on Linux-only absence
  of Windows file attributes. Filed AR-405 (#675); no code was changed.
- At this checkpoint: 147 unfinished baseline records plus AR-404 and AR-405.

## Exact blocker

The current record batch awaits isolated AR-285 verdicts and final docs/PR
gates. It does not require an exhaustive workflow, Windows machine or host
restart. AR-405's two existing release-test failures remain a separate package.

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

1. Finish AR-285 isolated acceptance, final verification and PR merge for the
   first disposition batch. Never count an absent/contradicted verdict as done.
2. Verify implemented inspection/observability work such as AR-298; reconcile
   AR-337's four-host battery versus all-supported-harness wording and AR-351's
   obsolete domain-axis clause before implementing old proposals.
3. Deliver genuine AR-271 uninstall-classifier and AR-348/349 hiring-safety
   gaps as separate packages; retain AR-405's Linux regression follow-up.
4. Continue AR-253 quality/latency proof and explicitly reconcile AR-393's
   impossible retroactive-receipt wording. No historical data rewrite.

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
