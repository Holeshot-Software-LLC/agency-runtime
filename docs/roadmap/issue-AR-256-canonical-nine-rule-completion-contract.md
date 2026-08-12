---
title: "AR-256: Establish the canonical nine-rule completion contract"
status: in_progress
category: roadmap
created: 2026-08-12
updated: 2026-08-12
tags: [documentation, governance, acceptance, evidence, critical-path]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/AR-119-acceptance-evidence.md
  - docs/roadmap/AR-119-founding-vision.md
  - docs/roadmap/AR-119-rule-host-evidence-matrix.md
  - docs/roadmap/AR-256-done-acceptance-reconciliation.md
  - docs/roadmap/issue-AR-257-separate-decision-conformance-fixture-launcher.md
  - docs/NORTH_STAR_ACCEPTANCE.md
  - docs/SESSION_HANDOFF.md
  - docs/THREAT_MODEL.md
  - docs/RELEASE_CHECKLIST.md
  - docs/decisions/0025-self-contained-linked-documentation.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0157-automatically-promote-host-verified-contractors.md
  - scripts/verify_docs.py
supersedes: []
superseded_by: null
type: issue
epic: documentation
issue_id: AR-256
priority: p0
tracker_url: null
depends_on: [AR-257]
blocks: [AR-119]
---

# AR-256: Establish the canonical nine-rule completion contract

## Problem

At package start, the repository had the owner-confirmed canonical nine-rule
rendering but no machine-checkable rule/host completion matrix. Canonical files
mixed deterministic selection, planned Job B children, deleted work units,
Agency-authored delivery claims, and stale Codex activation history. Registry
status was also unreliable: multiple `done` issues retained unchecked
acceptance boxes.

## Current state

`AR-119-founding-vision.md` is now the one wording authority and
`AR-119-rule-host-evidence-matrix.md` the one completion authority. The matrix
binds its canonical vision digest and exact source baseline, separates four
evidence layers, derives aggregate and Rule-9 states, and remains conservative:
there is no current proven top-level cell. Current documents have been
reconciled, faithful historical records are explicitly non-authoritative, and
`verify_docs.py` rejects authority, matrix, digest, and done-acceptance drift.

## Approach

Starting from the repository-local founding vision, this package publishes one
nine-rule matrix with exact source, artifact, host, date, and proof authority
per row. It separates implementation, contract simulation, installed
activation, and live host proof; reconciles competing current documents; and
enforces status-to-acceptance consistency without rewriting faithful history.
Its final slice updates the single AR-119 recovery capsule and records a clean
substantive/ledger checkpoint before AR-255 begins.

## Dependencies

- AR-255, AR-180, AR-252, AR-253, and AR-125 will populate still-open evidence
  cells; this issue defines and verifies the contract they must satisfy.
- AR-257 must restore the required decision-conformance gate without weakening
  executable namespace enforcement before this package can checkpoint cleanly.

## Acceptance

- [x] One repository-local matrix names all nine rules and each supported host,
      with `proven`, `negative`, `unproven`, or `not-applicable` evidence state.
- [x] `NORTH_STAR_ACCEPTANCE`, `SESSION_HANDOFF`, `THREAT_MODEL`, AR-119, its
      evidence record, README, and release checklist agree or are explicitly
      superseded with provenance retained.
- [x] Every `done` issue has checked acceptance backed by cited evidence, is
      reopened, or records an explicit superseded/historical exception.
- [x] Documentation verification rejects an unexplained `done` issue with
      unchecked acceptance and rejects more than one current AR-119 authority.
- [x] Documentation verification recomputes the canonical vision block defined
      in `AR-119-founding-vision.md` and rejects any mismatch with its recorded
      SHA-256 provenance.
- [ ] The AR-119 capsule remains the single bounded recovery entry and names
      one next package, exact blockers, and a clean recovery pair.
- [x] AR-119's closure contract requires strict documentation and tracker
      parity; authorization-pending tracker mappings remain visibly unresolved
      rather than being treated as completion.
