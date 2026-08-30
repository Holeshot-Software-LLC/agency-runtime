---
title: "Worklog detail: repair verifier-rejected recruiter proposals"
status: active
category: worklog
created: 2026-07-31
updated: 2026-07-31
tags: [workforce, inference, preflight, diagnostics]
related:
  - docs/worklog/README.md
  - docs/roadmap/issue-AR-212-repair-verifier-rejected-recruiter-proposals.md
  - docs/roadmap/issue-AR-213-reject-stale-preflight-tokens-before-plan-validation.md
  - docs/decisions/0129-repair-verifier-rejected-recruiter-proposals-once.md
supersedes: []
superseded_by: null
type: worklog
commit: c31e715b6fa543b483f5ab1be01faa01bcde9a52
short: c31e715
date: 2026-07-31
pr: null
related_issues:
  - docs/roadmap/issue-AR-212-repair-verifier-rejected-recruiter-proposals.md
  - docs/roadmap/issue-AR-213-reject-stale-preflight-tokens-before-plan-validation.md
---

# Worklog detail: repair verifier-rejected recruiter proposals

## Purpose

Prevent a structurally valid but whole-team-unsafe recruiter sample from being
marked applied and cached before staffing verification, while preserving the
existing one-repair budget, inference authority, and explicit contractor-gap
path.

## Approach

Whole-team `verify_staffing` now participates in recruiter parser acceptance.
Verifier rejection emits only bounded unit IDs and reason codes, resets the
nomination accumulator, and asks the same provider for one complete replacement
inside the existing semantic-attempt loop. Only verifier-accepted proposals or
verifier-clean explicit inferred gaps reach the cache. Terminal preflight
failure schema v2 adds independently bounded staffing and hiring reason-code
arrays through Store, canary, CLI, and dashboard projections.

## Challenges encountered

The first regression fixture omitted the verifier's mirrored delegated-agent
budget code, and one cache fixture changed the invoker identity, correctly
invalidating its cache key. Both fixtures were corrected without changing the
product contract. A broader compatibility run also exposed a stale-token/native
plan-scope failure in untouched code; it is isolated as AR-213 rather than
expanding this package.

## Decisions and alternatives

ADR-0129 governs the repair. The verifier supplies rejection evidence but never
synthesizes a team or converts an ordinary failure into a gap. No retry loop or
new model call budget was added. Free-form verifier details, prompts, responses,
paths, credentials, and hiring notifications remain excluded from durable
failure evidence.

## Verification

- Exact AR-212 acceptance slice: 8 passed.
- Canary and CLI compatibility: 24 passed.
- Dashboard UI: 110 passed.
- Changed-file Ruff lint and format checks passed.
- Documentation metadata, policy availability, worklog preflight, and all 599
  Markdown validations passed.
- Named fast production spine and live exact-build evidence remain pending.

## Follow-ups

- Complete the named fast gate, review, merge, exact reinstall, and one fresh
  live product proof under AR-212.
- Repair stale-token fencing separately under AR-213.
