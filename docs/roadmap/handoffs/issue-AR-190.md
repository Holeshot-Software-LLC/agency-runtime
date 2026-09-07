---
title: "AR-190 exact installed uv-plan evidence handoff"
status: active
category: roadmap
created: 2026-07-28
updated: 2026-09-07
tags: [handoff, updates, uv, security, recovery]
related:
  - docs/roadmap/issue-AR-190-make-upgrade-plans-runnable-in-uv-tools.md
  - docs/roadmap/acceptance/issue-AR-190.md
  - docs/roadmap/acceptance/evidence/AR-190-installed-uv-plan-20260907.md
  - docs/decisions/0107-resolve-updates-immutably-and-keep-application-attended.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-190
branch: codex/ar190-uv-plan-reconciliation
evidence_commit: c64ce3ce54c6e51280292298b5e3600611cb72fc
minimum_ledger_commit: d28ccc232dcc00af0162a2409930dd272bf97b5f
hard_checkpoint_percent: 50
tracker_url: null
---

# AR-190 exact installed uv-plan evidence handoff

## Checkpoint

Evidence branch begins at exact main
`c64ce3ce54c6e51280292298b5e3600611cb72fc`, then fast-forwarded to its
existing clean ledger `d28ccc23`. The worker owns this worktree's substantive/
ledger checkpoints and acceptance runs; parent serializes PR publication and
merge. This evidence-only package is not a done issue. Product implementation
already exists at `8c7d8df44aa35d4bb7ab7698abaf0f7b2a93e47b`.

## Completed evidence

A clean detached c64ce3ce producer under `umask 077` built the canonical
portable wheel and sdist. Strict Twine and independent portable verification
exit zero. Wheel SHA-256:
`cbf2ce558636cc160c6f0656d6fb0760e0d368ca5d1619fc988596e306c91c7d`.

An existing exact local Docker image ran an isolated default-root uv 0.11.8
installation. Its real tool environment contains only Agency Runtime 0.1.0 and
PyYAML 6.0.3, no pip. No UV/XDG or HOME target override was supplied. The
actual installed CLI plan to the SAME c64ce3ce SHA exits zero at 23:31:01 UTC,
selects `uv-tool`, emits an immutable install command and a separate isolated
Codex refresh command, and reports no package/host mutation.

All 669 compared non-bytecode prefix files, the uv receipt and the Agency
entrypoint hash remain unchanged after planning. No displayed command ran.
Owner wrappers/input artifacts remained unchanged and both disposable
containers were removed. The earlier 08fab1c4-to-c64ce3ce success and the
bubblewrap uid-map failure are preserved separately, not silently upgraded.

Fresh focused update/CLI tests: 67 passed in 0.83 seconds. Targeted Ruff lint
and formatting pass. The portable receipt and two raw JSON receipts preserve
commands, actual output, source/artifact identities, bounds and limitations.

## Exact blocker

The live installed-uv-plan gap is now evidenced. Normal ledger reconciliation
resolved the inherited c64ce3ce merge-row failure: docs, metadata, worklog,
policy-availability and diff checks now pass. Isolated acceptance verification
is not yet complete.
The pending builder has no verdict rows, and status remains `in_progress`.

The wheel's self-reported source revision is null, truthfully; its full source
SHA is bound by the clean detached canonical build and independent verifier.
No upgrade, Codex refresh, native activation or owner installation change is
claimed or required by this plan-only proof. The ordinary owner AR-348 venv
is not uv-owned and was not used as a false uv receipt.

## Same-task continuity

Parent serializes PR publication and merge. Worker now owns AR-190 records,
ledger/registry reconciliation, builder freeze and isolated verdict execution
in this exclusive worktree. Preserve unrelated changes.

The telemetry checkpoint applies to durable records, not permission to retry
failed namespaces or execute a displayed upgrade. The clean source checkpoint
was reused before the isolated proof; worker checkpoints the completed slice.

## Next bounded work package

1. Commit the exact c64ce3ce source/artifact/plan chain and clean record gates,
   then record the faithful substantive commit in its ledger pair.
2. Freeze the pending builder at its committed documentation
   candidate, explicitly retaining c64ce3ce runtime-source equivalence.
3. Run isolated acceptance checks, then change status only if all satisfy.
   Parent then authorizes the serialized PR. No owner reinstall or host canary
   is needed for this plan task.

## Verification

Real canonical builder, strict Twine, explicit portable verifier and the
default-directory installed uv plan all exit zero. The update/CLI package
passes 67 tests. Exact commands and raw stdout are in the portable receipt.
Final record-gate results must be read there before freezing acceptance.

## Constraints

Only an existing local Unix-socket Docker engine/image was used. No image
pull, remote Docker host, privileged container, owner-home mount, credential,
service/admin change, host uv install, or provider call. Public dependency and
official GitHub lookup traffic was bounded. No native Windows execution,
exhaustive corpus, coverage shards, compatibility matrix or release signing.
The container setup installs a disposable package; the subsequent plan does
not execute either displayed package-upgrade or host-refresh command.
