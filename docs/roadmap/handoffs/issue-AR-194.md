---
title: "AR-194 cross-version service inspection handoff"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [handoff, dashboard, launcher, portability, windows]
related:
  - docs/roadmap/issue-AR-194-inspect-owned-service-runtimes-across-python-versions.md
  - docs/roadmap/acceptance/evidence/AR-194-service-runtime-reconciliation-20260907.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-194
branch: codex/ar194-service-runtime-reconciliation
evidence_commit: cd62d6588d8660033bf309220b74dcc1dbdebef6
minimum_ledger_commit: 78ee74bafacece87a16af9bf51fd07b3a4eafa17
hard_checkpoint_percent: 50
tracker_url: null
---

# AR-194 cross-version service inspection handoff

## Checkpoint

Substantive `cd62d658` and ledger `78ee74ba` freeze the branch-only
reconciliation and its inspected source `f408b6f2`. Normal integration now
includes AR191/PR741 main `a8c2ca54`; frozen acceptance files and all incoming
product code remain unchanged. Parent owns publication after AR192.
No runtime/test change, owner service mutation or acceptance verdict occurred.

## Completed evidence

Read-only foreign-tag projection inspection is separate from strict
current-interpreter preparation. Launcher identity, canonical manifest/hash,
private namespace, isolated argv and bounded interpreter-probe guards remain.
Fresh focused launcher/service-core/service tests: 116 passed, 42 deselected,
2.75 seconds. Included Windows-shaped fixtures are not native Windows proof.

Installed `agency dashboard service status --json`, outside the checkout,
exited zero in 0.202 seconds: Linux systemd-user service installed, owned,
current, enabled, active and reachable; no definition drift or repair needed.
Four source inspection/CLI modules match the installed package byte-for-byte.
The existing worker remains pinned to runtime `4329d760`; there is no
whole-main-installed claim. Exact command/output/hash scope is in the receipt.

## Exact blocker

The original fifth acceptance clause requires the historical stale Windows
task/runtime repair followed by current installed reachability. No such
native transition occurred here. The healthy Linux status does not satisfy it.
AR-194 remains `in_progress`; the original five checkbox states are preserved.

ADR-0117 already removed the extra human-presence ceremony. AR-196 is retired,
not a missing service-authority implementation. No Windows Hello recreation or
fresh attendance ceremony is required. Existing owner authority and exact
ownership/transaction/postcondition controls remain.

## Same-task continuity

Owned changes include canonical AR-194, this capsule, portable receipt,
reciprocal AR-196/ADR-0117 records, registry/queue47 and worklog. AR-191 remains
at its separate clean checkpoint. Parent handles serial publication; do not
overwrite other agents' concurrent work. No PR exists at this checkpoint.

## Next bounded work package

Review this clean reconciliation checkpoint and merge current main normally
before parent-authorized publication. Leave native Windows proof
to the owner's Windows machine. Do not mark done or run acceptance against the
unproved final criterion. Do not repair the healthy Linux service to imitate
the historical Windows observation.

## Verification

Fresh command and raw output are retained in the receipt. Source/test checks
are bounded and existing; no extra test was needed. Documentation checks,
metadata, policy availability, worklog, repository Ruff/format and diff checks
are run before checkpoint. No full corpus, service mutation or Windows run.

## Constraints

No owner package/profile/credential/configuration change, provider call,
service start/restart/install/repair, live Windows execution, model canary,
new authority policy, tracker write, acceptance verdict or done-state flip.
