---
title: "AR-86: Govern the complete upstream roster lifecycle"
status: in_progress
category: roadmap
created: 2026-07-18
updated: 2026-07-18
tags: [roster, upstream, audit, quarantine, synchronization]
related:
  - docs/roadmap/issue-AR-83-manifest-roster-import.md
  - docs/roadmap/issue-AR-95-bind-remediation-resolution-authority-to-complete-durable-evidence.md
  - docs/roadmap/issue-AR-97-reconcile-required-inference-remediation.md
  - docs/decisions/0066-package-audited-roster-and-sync-quarantined-deltas.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: roster-governance
issue_id: AR-86
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/87"
depends_on: [AR-02, AR-28, AR-83]
blocks: [AR-89, AR-91, AR-93, AR-95, AR-97]
---

# AR-86: Govern the complete upstream roster lifecycle

## Problem

Generic manifest import does not provide the complete audited and packaged
specialist roster or a safe bounded update lifecycle. New and changed upstream
definitions need durable review without displacing the previously approved
version. Newly quarantined definitions also need a reusable remediation path;
stopping without a source-bound repair attempt would turn the two known repairs
into a one-off exception rather than an ingestion discipline.

## Current state

The complete pinned source snapshot has been classified into explicit approved
and quarantined outcomes and the approved routing contracts are packaged.
Delta-only source operations, immutable deterministic audits and candidate
status history, review commands, active-version preservation, and the
non-activating nightly workflow are implemented. Every rejected source now enters
an immutable remediation queue with attempted rules, exact source hash,
matched/no-match disposition, optional proposal hash, and next action. The queue
is visible through bounded CLI and dashboard projections without raw prompt
content. Resolution claims now require a keyed, exact dependency closure before
they can suppress pending work; unsigned duplicates remain quarantined
anomalies. Configured-provider inference audit integration and final
repository-wide gates remain in progress. The shared ingestion and packaged-
loader scanner now quarantines unsafe Unicode format controls and encoding
corruption across prompt, metadata, list, and path boundaries; re-signing local
bundle material cannot promote the unsafe content.

## Approach

Compare pinned source identities and content hashes to the verified packaged
manifest. Import only new or changed definitions into quarantine, run
deterministic security checks and configured inference-assisted semantic review,
regenerate routing contracts, and analyze conflicts against the active roster.
Keep the old version active until every gate passes. Preserve immutable audit,
status, rejection, activation, and superseding history.
For every quarantine, create a non-executable remediation-attempt receipt. Apply
repairs automatically only for an exact registered source hash and deterministic
rule; require a reviewed semantic projection and all normal approval gates before
activation. Unknown and ambiguous sources stay queued and quarantined.

## Dependencies

AR-83 owns the generic declared-manifest ingress boundary. AR-28 owns reversible
operator availability independently of governance state.

## Acceptance

- [x] Every source definition has an approved, quarantined, or retired outcome.
- [x] Normal routing is self-contained and reads a verified installed bundle.
- [x] Only new or content-hash-changed definitions enter nightly review.
- [x] The prior approved version remains active until the candidate passes every gate.
- [ ] Deterministic and configured inference-assisted audit findings are durable.
- [x] Conflict analysis runs against the exact active roster revision.
- [x] CLI commands cover status, dry run, import, findings, compare, approve, and reject.
- [x] The bounded nightly workflow never approves or activates a candidate.
- [x] Every quarantine records a bounded source-hash remediation attempt and next action.
- [x] CLI and dashboard queue projections expose no raw prompt content.
- [x] Automatic repair is exact-rule-only; activation still requires semantic audit and approval.
- [x] Resolution authority is durable, dependency-complete, and invalidated by evidence changes.
- [ ] Full coverage, documentation, packaging, Windows, and Linux gates pass.
