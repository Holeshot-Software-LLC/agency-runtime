---
title: "AR-256: Establish the canonical nine-rule completion contract"
status: open
category: roadmap
created: 2026-08-12
updated: 2026-08-12
tags: [documentation, governance, acceptance, evidence, critical-path]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/AR-119-acceptance-evidence.md
  - docs/roadmap/AR-119-founding-vision.md
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
depends_on: []
blocks: [AR-119]
---

# AR-256: Establish the canonical nine-rule completion contract

## Problem

The repository now has the owner-confirmed canonical nine-rule rendering and
semantics, but it does not yet have one machine-checkable rule/host completion
matrix. Canonical files still mix deterministic selection, planned Job B
children, deleted work units, Agency-authored delivery claims, and stale Codex
activation history. Registry status is also unreliable: multiple `done` issues
retain unchecked acceptance boxes.

## Current state

`AR-119-founding-vision.md` is the repository-local wording authority. AR-119's
2026-08-11 restatement is the best current evidence authority, but its active
handoff was stale before this package and older acceptance, threat, and session
documents contradict it. Raw roadmap percentages therefore describe document
labels, not proven vision completion.

## Approach

Starting from the repository-local founding vision, publish one nine-rule matrix
with exact source, artifact, host, date, and proof authority per row. Separate
implementation, contract simulation, installed activation, and live host proof.
Reconcile or explicitly retire every competing current document and enforce
status-to-acceptance consistency in `verify_docs.py` without rewriting faithful
historical records.

## Dependencies

- AR-255, AR-180, AR-252, AR-253, and AR-125 will populate still-open evidence
  cells; this issue defines and verifies the contract they must satisfy.

## Acceptance

- [ ] One repository-local matrix names all nine rules and each supported host,
      with `proven`, `negative`, `unproven`, or `not-applicable` evidence state.
- [ ] `NORTH_STAR_ACCEPTANCE`, `SESSION_HANDOFF`, `THREAT_MODEL`, AR-119, its
      evidence record, README, and release checklist agree or are explicitly
      superseded with provenance retained.
- [ ] Every `done` issue has checked acceptance backed by cited evidence, is
      reopened, or records an explicit superseded/historical exception.
- [ ] Documentation verification rejects an unexplained `done` issue with
      unchecked acceptance and rejects more than one current AR-119 authority.
- [ ] Documentation verification recomputes the canonical vision block defined
      in `AR-119-founding-vision.md` and rejects any mismatch with its recorded
      SHA-256 provenance.
- [ ] The AR-119 capsule remains the single bounded recovery entry and names
      one next package, exact blockers, and a clean recovery pair.
- [ ] Documentation and tracker parity checks pass before AR-119 is closed.
