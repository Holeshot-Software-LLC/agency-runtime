---
title: "AR-227: Expand the specialist roster"
status: done
category: roadmap
created: 2026-08-03
updated: 2026-08-03
tags: [feature, roster-governance, workforce, inference]
related:
  - agency_runtime/core/workforce/known_contractors.py
  - agency_runtime/core/workforce/known_installer.py
  - tests/test_workforce_hiring_contract.py
  - tests/test_known_contractor_install.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: roster-governance
issue_id: AR-227
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/236
depends_on: []
blocks: []
---

# AR-227: Expand the specialist roster

## Problem

Agency's audited 263-agent roster and nine packaged contractors still leave
clear AI-evaluation, AI-native observability, documentation-evidence,
hallucination-investigation, AI-governance, and policy-guardrail gaps. The
VoltAgent `awesome-codex-subagents` catalog also contains useful activation and
quality boundaries for roles Agency already owns. Blindly copying its catalog
would create near-duplicate specialists and weaken Agency's governed contract
model.

## Current state

PR #235 is merged. This post-merge package uses Agency's existing first-party
contractor authority for genuinely missing roles. It retains the existing
`backend-service-engineer` instead of adding a synonymous backend implementer,
strengthens that contract's data, authorization, idempotency, rollback, and
failure-path evidence. Comparison of six other near-neighbors confirmed their
Agency contracts already contain the useful evidence and failure boundaries;
no duplicate or selection-changing overlay is added. The upstream catalog remains attribution-only research;
Agency's closed employment schema, security compiler, host policy, evidence
requirements, and inference selector remain authoritative.

The complete 278-worker inference index serializes to 263,700 bytes, 1,556
bytes above the former 256 KiB ceiling. The package raises that finite payload
envelope to 288 KiB, leaving 11.8 percent measured headroom while retaining an
exact-size regression assertion.

Tracker creation is pending explicit authorization.

## Approach

1. Add six narrow Agency-owned contracts with positive and hard-negative
   selection cases, explicit evidence, bounded authority, and closest-worker
   differentiation.
2. Reuse and strengthen `backend-service-engineer`; do not create a duplicate.
3. Preserve the six strong audited overlaps unchanged when comparison finds no
   material gap, avoiding selection drift and duplicate roles.
4. Prove automatic installation, roster projection, CLI/dashboard counts, and
   focused routing contract integrity.

## Dependencies

The package starts after PR #235 and does not alter inference ownership,
fallback behavior, host trust, or delegation execution.

## Acceptance

- [x] Six missing specialists install automatically as governed contractors.
- [x] No backend implementation duplicate is introduced.
- [x] Existing overlaps are compared without introducing selection drift.
- [x] Every new specialist has evidence requirements and positive/hard-negative cases.
- [x] Focused tests and the named fast production spine pass.
- [ ] A follow-up pull request is open with exact verification evidence.

## Verification

Commit `40353bb` adds the six specialists and raises the finite recruiter
index envelope. The named fast production spine passed 661 tests with 6
skips. The focused AR-227 suite (workforce hiring contract, known contractor
install, roster enrichment, selection safety, dynamic hiring, workforce CLI,
full roster eval) passed 139 with one skip after correcting the index
envelope exact-size assertion to the measured 263,616 bytes. Ruff check and
format, documentation validation (647 Markdown files), the dashboard UI test
(110/110), and the routing eval passed. The follow-up pull request is pending
operator authorization to push.
