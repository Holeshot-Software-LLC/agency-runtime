---
title: "AR-190 exact installed uv-plan evidence handoff"
status: active
category: roadmap
created: 2026-07-28
updated: 2026-09-08
tags: [handoff, updates, uv, security, recovery]
related:
  - docs/roadmap/issue-AR-190-make-upgrade-plans-runnable-in-uv-tools.md
  - docs/roadmap/acceptance/issue-AR-190.md
  - docs/roadmap/acceptance/evidence/AR-190-installed-uv-plan-20260907.md
  - docs/roadmap/acceptance/evidence/AR-190-product-source-candidate-20260908.md
  - docs/decisions/0107-resolve-updates-immutably-and-keep-application-attended.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-190
branch: codex/ar190-uv-plan-reconciliation
evidence_commit: eac2d6a20c43d6296741074ff93470470a178bae
minimum_ledger_commit: e4941a7556644b57bcd21efe407922b72c5ef0ff
hard_checkpoint_percent: 50
tracker_url: null
---

# AR-190 exact installed uv-plan evidence handoff

## Checkpoint

Evidence branch begins at exact main
`c64ce3ce54c6e51280292298b5e3600611cb72fc`, then fast-forwarded to its
existing clean ledger `d28ccc23`. Evidence is now committed at `d1a9260c`,
with faithful ledger `ae1fe0fc`; the acceptance candidate is frozen at
`d1a9260c`. Freeze commit `12bce920` and ledger `45716bd5` preceded the first
isolated acceptance run. The worker owns this worktree's substantive/
ledger checkpoints and acceptance runs; parent serializes PR publication and
merge. This evidence-only package is not a done issue. Product implementation
already exists at `8c7d8df44aa35d4bb7ab7698abaf0f7b2a93e47b`.

The new exact d1a9260c live proof and explicit product-source clarification are
committed at `eac2d6a2`, ledger `e4941a75`. The second-review receipt candidate
is frozen at `eac2d6a2`; the runtime under test remains exact d1a9260c.
Freeze `d5e36996` and ledger `14f332ec` form its clean pre-review checkpoint.

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

The first default isolated run accepted criteria 1–4 but returned `absent` for
criterion 5 (`AR-190.5-20260907-42c2bd69`). It found the tests, lint, docs and
live plan were at c64ce3ce/d28ccc23 rather than documentation candidate
d1a9260c, and that source equivalence was unverifiable in its snapshot.
All five actual verdicts are preserved at `a6efa01b`, ledger `0199f8d3`.
The owner authorized one changed-evidence response and a second/final all-five
review because changing the receipt candidate invalidates every digest.
Status remains `in_progress`; no verdict is transplanted or handwritten.

A fresh detached d1a9260c wheel (SHA-256
`98b87cf098bf0b35b4a266d8ee35288e1a366914b7e19f9c6a8579c2ce23e457`)
passed the canonical build/independent verifier and generated a same-SHA live
uv plan at 2026-09-08T00:00:19Z. Installed planner hashes equal source hashes;
all 669 compared files/receipt/entrypoint remain unchanged. Fresh focused tests
pass 67 cases and Ruff is clean. The original criterion is retained verbatim
beside the explicit final-product-source versus later receipt-commit wording.

At 00:08:38 UTC, Claude admission failed for all five checks with exit 2 and
no verdict rows: package directory `0775`, bin directory `0755`, production
resolver explicitly refusing namespace substitution risk. Actor unknown;
the worker made no chmod repair or unchanged retry. The owner chose supported
Codex verification against the unchanged candidate after safe version/auth
inspection; this is the second actual review, not a third judgment pass.

The second actual Codex review returned satisfied for 1, 2, 4 and 5, and
`absent` for 3 (`AR-190.3-20260907-67a91336`). Its bounded excerpts include
rejection-helper tests but omit the already-frozen production caller chain
at `update_service.py:1220-1263` and `:1285-1318` that maps refusal to no
commands. The first Claude review could inspect those in its snapshot;
Codex receives only excerpts. Preserve this evidence omission without
claiming a new runtime defect. No third review has run; status is in_progress.

Normal ledger reconciliation resolved the inherited c64ce3ce merge-row failure.
Documentation validation passes for 1,241 Markdown files with the new pending
builder and clarified criterion, alongside metadata, policy, worklog and diff.

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

1. Checkpoint the second actual results and faithful ledger; 1, 2, 4, 5 are
   satisfied and 3 is absent, with exact digests retained.
2. Stop for parent analysis. A targeted criterion-3 caller-excerpt addition
   could preserve the same candidate and four valid verdicts, but an extra
   review requires explicit authorization; the default two-pass bound is met.
3. No unchanged retry or authority weakening. Parent serializes publication;
   the branch was pushed only to expose d1a9260c to official lookup.

## Verification

Real canonical builder, strict Twine, explicit portable verifier and the
default-directory installed uv plan all exit zero. The update/CLI package
passes 67 tests. Exact commands and raw stdout are in the portable receipt.
The first acceptance run returned four satisfied and one absent; exit zero
means all verdicts were recorded, not completion. Its full stdout and reasons
are in the canonical issue and acceptance record.

## Constraints

Only an existing local Unix-socket Docker engine/image was used. No image
pull, remote Docker host, privileged container, owner-home mount, credential,
service/admin change, host uv install, or provider call. Public dependency and
official GitHub lookup traffic was bounded. No native Windows execution,
exhaustive corpus, coverage shards, compatibility matrix or release signing.
The container setup installs a disposable package; the subsequent plan does
not execute either displayed package-upgrade or host-refresh command.
