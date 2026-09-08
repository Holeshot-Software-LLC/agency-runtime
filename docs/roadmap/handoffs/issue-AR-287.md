---
title: "AR-287 static timeout routes handoff"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [handoff, inference, timeouts, host-integrations]
related:
  - docs/roadmap/issue-AR-287-bind-host-hook-timeouts-to-inference-budgets.md
  - docs/roadmap/acceptance/evidence/AR-287-static-timeout-routes-20260907.md
  - docs/decisions/0153-adopt-per-stage-inference-profile-routes.md
  - docs/decisions/0192-route-content-invalid-completions-to-a-content-fallback-profile.md
  - docs/decisions/0216-enforce-one-preflight-inference-deadline.md
  - docs/worklog/2026-09-07-fb360485-static-timeout-routes.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-287
branch: codex/ar287-complete-static-timeout-routes
evidence_commit: fb36048537277833a41a5189bd29621514a6d0d5
minimum_ledger_commit: 1829cdab970e2a4a590121e6bbc40ba4ec6efd7c
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/756
---

# AR-287 static timeout routes handoff

## Checkpoint

Source `fb360485` plus immediate ledger `66aa90ad` is frozen. Integration
`14899a51` and ledger `1829cdab` include published-main ledger `6d209d6d`,
preserving other workers' source and records. Canonical status stays in_progress.

## Completed evidence

Config-only timeout resolution now counts a distinct content fallback only after
a valid primary and includes safety repair when its repair budget is positive.
The same helper still governs generated hooks and Store leases. Root's first
independent source review found no scoped finding; scoped Ruff/diff checks pass.
Twenty installer cases and two Store-lease cases are written, **all unrun**.
The portable source receipt distinguishes expected arithmetic from measurement.

## Exact blocker

Owner explicitly deferred tests, CI and live/provider verification. No current
installed repair or acceptance verdict exists. Owner-authorized tracker #756
now maps this legacy record; do not duplicate filing. PR publication is pending.

## Same-task continuity

Agent owns this exclusive branch; parent coordinates review and normal PR
publication. Do not edit root's AR-251 tree or other workers' source. Continue
from this clean source/ledger checkpoint without retrying historical failures.

## Next bounded work package

Finish the canonical/receipt checkpoint, then let the parent publish through a
normal PR under the serialized publication token. Run focused regressions and an exact installed
bridge/lease check only when the owner's deferral ends. Do not mark AR-287 done.

## Verification

Executed: scoped Ruff lint/format and `git diff --check`. Deferred:
`tests/test_native_installer.py`, `tests/test_preflight_bounds.py`, production
spine, CI, acceptance verifier and native/provider calls. Existing August 25
results are historical and do not verify this source delta.

## Constraints

No changed call budgets, fallback selection, security independence, ten-second
terminal reserve, legacy floor or 595-second cap. No runtime environment lookup
in installed budget calculation. No owner profile, package, host or service
mutation. Original Acceptance wording and checkbox states remain unchanged.
