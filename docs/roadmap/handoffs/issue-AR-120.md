---
title: "AR-120 normalized index reconciliation handoff"
status: active
category: roadmap
created: 2026-09-05
updated: 2026-09-05
tags: [handoff, roster, audit, ingestion, backlog]
related:
  - docs/roadmap/issue-AR-120-normalized-workforce-recruitment-index.md
  - docs/roadmap/AR-404-oldest-first-reconciliation-20260905.md
  - docs/roadmap/issue-AR-86-govern-complete-upstream-roster-lifecycle.md
  - docs/decisions/0066-package-audited-roster-and-sync-quarantined-deltas.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: handoff
issue_id: AR-120
branch: codex/ar120-oldest-first-reconciliation
evidence_commit: 8b8b594ec4b67c1c45ba68e647939c73ddfc1d00
minimum_ledger_commit: 7334814d756ff472c4816cdc4991ba1cc7546282
hard_checkpoint_percent: 50
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/133
---

# AR-120 normalized index reconciliation handoff

## Checkpoint

Third oldest-first disposition under AR-404; AR-115 is retired and AR-119 is
retained with its reconciliation merged in PR #691. AR-120 stays open, partly
implemented. The owner wants backlog records reconciled one PR/merge at a time.

## Completed evidence

- At 8b8b594e, bounded immutable schema-2 contracts exist for all 265 bundled
  agents. Typed composition separates same-context conflict, exclusivity,
  requirements and complements. Full-worker snapshots validate current
  lineage/hash/identity atomically; contractor lifecycle preserves history.
- Existing AR-86 quarantine, audit and activation authority protects prior
  approved versions. The scheduled job imports deltas and publishes review
  evidence; it does not activate them or execute the commented enrichment step.
- Daily-to-weekly cadence was intentional in 30ab92f9. No scheduler change,
  upstream fetch, provider call or hosted run is part of this reconciliation.
- Focused contract/lifecycle/overlay/snapshot/review/activation/adapter tests:
  219 passed in 15.34s. An initial invocation used a nonexistent filename and
  ran zero tests; the corrected run used seven existing modules.

## Exact blocker

The source does not yet deliver every promise. The slug-keyed enrichment
overlay has no universal independent source/version-bound projection review;
the manual enricher consumes metadata. No description-quality/reachability
baseline implements the September 1 approved addition. The weekly workflow
does not regenerate proposed contracts, confusion groups and evaluations.
Keep all four acceptance boxes unchanged and #133 open; this is not a verdict.

## Same-task continuity

Use the owned worktree/branch, commit substantive changes then the exact narrow
worklog ledger, PR and merge. Do not make a duplicate issue for these existing
AR-120 gaps. At the context threshold checkpoint the smallest safe pair and
continue; an unimplemented feature is not proof that the old entire index must
be rebuilt. No manual staffing or native subagent delegation was used.

## Next bounded work package

For backlog cleanup, merge this disposition then inspect AR-125.
For later AR-120 implementation, start with one source/version-bound
enrichment-review artifact and a changed-source invalidation regression. Then
add the reviewed discoverability baseline and connect proposed refresh artifacts
to the existing non-activating scheduled review path. Keep inference staffing
authority and active-version quarantine gates unchanged throughout.

## Verification

Focused command: pytest tests/test_workforce_contract.py
tests/test_workforce_lifecycle.py tests/test_roster_enrichment_overlay.py
tests/test_roster_snapshot_generation.py tests/test_roster_lifecycle_review.py
tests/test_roster_activation_authority.py tests/test_roster_inference_adapter.py
-q -W error --tb=short. All 219 passed. Run standard metadata/policy/worklog/
strict docs/tracker/diff checks before publication. Source remains unchanged;
this turn's 1075 fast-spine passes/three skips and 138 UI passes are reusable.

## Constraints

Windows stays with the owner. No new hosted schedule/spending, credential
creation, automatic roster activation or live proof claim. No deterministic
runtime staffer may be reintroduced through this offline index-quality work.
The shared Codex unverified-header problem is separate and not waived here.
