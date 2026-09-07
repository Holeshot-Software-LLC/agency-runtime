---
title: "AR-189 owner-CLI uninstall evidence handoff"
status: active
category: roadmap
created: 2026-07-28
updated: 2026-09-07
tags: [handoff, uninstall, host-integrations, security, recovery]
related:
  - docs/roadmap/issue-AR-189-add-owned-host-integration-uninstall.md
  - docs/roadmap/acceptance/evidence/AR-189-owner-cli-reconciliation-20260907.md
  - docs/decisions/0108-retire-only-owned-host-integrations.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/worklog/README.md
  - tests/test_host_uninstall_live_boundary.py
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-189
branch: codex/ar189-private-uninstall-proof
evidence_commit: c64ce3ce54c6e51280292298b5e3600611cb72fc
minimum_ledger_commit: d28ccc232dcc00af0162a2409930dd272bf97b5f
hard_checkpoint_percent: 50
tracker_url: null
---

# AR-189 owner-CLI uninstall evidence handoff

## Checkpoint

The original private receipt ran on `08fab1c4`. Publication preparation safely
fast-forwarded to `d28ccc23`, including main `c64ce3ce` and its faithful AR-184
merge ledger; all four inherited draft file hashes survived unchanged.
Metadata names that source checkpoint. The branch prepares one substantive
test/records commit followed by its exact ledger; parent coordinates the normal
PR/merge after AR-185 and AR-408. It is not yet published to main.
No runtime source change, acceptance verdict or done-state change is included.

## Completed evidence

ADR-0117 supplies normal owner-CLI authority without a second native
human-presence ceremony. Product commit `45be7ea5` already removed the
unconditional unavailable exception; aggregate binding validation remains.
Canonical criteria 4/8/12 now use current authority terminology, with all twelve
original criteria preserved verbatim in the portable receipt. Windows-specific
clauses and every ownership/lock/retention requirement remain.

The new private in-process CLI regression installs ZCode into an explicit
disposable home, plans, refuses a wrong digest without writes/journal, applies
the exact digest, retains the original bundle byte-for-byte, removes seven
Agency handlers, and proves repeat no-op. Authority, primitives, locks,
re-planning, config removal and journal writer remain real and unpatched.
Private runtime config, history and all logical Store contents are preserved.

Focused host/CLI package: 68 passed, two native-Windows skips, 4.98 seconds.
Private proof: one passed in 2.24 seconds; retained-artifact recapture:
one passed in 2.21 seconds. Parser/owner-authority: 59 passed in 0.73 seconds.
On updated source `d28ccc23`, the combined focused package passes 127 with two
native-Windows skips in 5.49 seconds; named fast spine 1,085 with three skips in
69.11 seconds; UI 224 passes. These reruns do not relabel old receipt IDs.
The receipt contains exact commands, output, operation/plan/journal hashes,
retained-file hashes, scope, SQLite sidecar treatment and criterion mapping.

## Exact blocker

No fresh native Windows companion-binding, handle-bound directory retirement
or native PowerShell branch evidence is supplied. These meaningful clauses stay
open for the owner's Windows machine. No all-criteria acceptance builder was
prepared, no verdict was run, and the issue remains `in_progress`.

No second OS presence ceremony is required or awaited. No live owner
integration, package or service was removed. Real private ZCode config mutation
does not establish actual other-host unregistration or running-process unload.
The external same-account ZCode read-to-replace race remains residual, not CAS.

## Same-task continuity

This branch includes the private regression, canonical issue, capsule, receipt,
registry/AR-404 queue reconciliation, reciprocal ADR-0117 links and its faithful
substantive/ledger checkpoint. Parent owns PR/merge coordination and later
acceptance. Preserve other workers' changes. AR-189 is pre-tracker exempt; its
canonical tracker URL remains null without creating a duplicate issue.

## Next bounded work package

1. Await the parent's publication signal, then publish this authority
   reconciliation and private proof through one branch PR with its exact ledger.
2. Leave meaningful Windows obligations visible; do not delete them to obtain
   a completion verdict or reinterpret Linux fixtures as native Windows proof.
3. When owner Windows evidence is available, retain exact source/test identity
   and reconcile all criteria before preparing isolated acceptance checks.

## Verification

The portable receipt distinguishes current commands from historical July
observations and preserves all original criteria. No retired presence module
or native asset test should be resurrected merely to match old command lists.
The original 1,224-document draft check found the inherited `08fab1c4` ledger
gap. The source update includes that historical ledger and AR-184's merge row.
Fresh focused and named-spine results are above; repository Ruff lint passes,
format passes for 768 files and UI 224 passes. Publication metadata, policy,
worklog, docs (including require-tracker) and diff checks pass before the
substantive checkpoint; the narrow ledger is checked again after integration.
Routing evaluation passes every gate. Full mutation-conformance is not rerun
for this test/records-only slice; its focused tests are in the named spine.
Do not repeat private installation solely because its evidence appears in
multiple criteria.

## Constraints

No owner uninstall, profile/credential/provider change, host restart, native
Windows execution, new mutation endpoint or package/data purge. No exhaustive
corpus, coverage shards, compatibility matrix, signing or package publication.
An exact plan digest is stale-write safety, not separate human authentication.
SQLite read-only WAL/SHM coordination files are explicitly excluded from raw
snapshots; complete logical database contents remain separately compared.
