---
title: "AR-212: Repair verifier-rejected recruiter proposals once"
status: in_progress
category: roadmap
created: 2026-07-31
updated: 2026-07-31
tags: [product, inference, recruitment, reliability, diagnostics]
related:
  - README.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0121-gate-deterministic-recall-without-selection-authority.md
  - docs/decisions/0129-repair-verifier-rejected-recruiter-proposals-once.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: product
issue_id: AR-212
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/208
depends_on: [AR-207]
blocks: [AR-203, AR-204]
---

# AR-212: Repair verifier-rejected recruiter proposals once

## Problem

Exact installed build `e62d0adc6daaf91f99bdc125217a523665d1dad4`
passes default installation and supported-bypass activation. Its one governed
product trial, `ar207-e62d0adc-readme-01`, nevertheless ended before parent
generation with `substantive_specialist_unavailable`. Planner and recruiter
both returned structurally applied responses, but the final route contained no
accepted specialist, plan binding, delegation, finalization, or workspace
write.

Full staffing verification currently runs after the recruiter stage has
already been marked applied and cached. A structurally valid proposal that
fails whole-team verification therefore cannot spend the recruiter stage's
existing single semantic-repair attempt. The terminal preflight receipt also
drops the content-free staffing and hiring reason codes needed to distinguish
that condition from an actual roster gap.

## Current state

The failed product session `019fbad4-6358-70e1-856f-ec89d5c7ecd2`, trace
`019fbad4-63d2-7e23-a688-ba3a21353de3`, and run
`65525f38-914f-450d-ac4e-8145e4a5eca6` retained one planner and one recruiter
receipt, both `structured_response_applied`, followed by zero routes and one
bounded preflight failure. Correction count was zero, but header and workspace
write evidence were absent.

A single read-only route diagnostic reconstructed the exact 1,962-character
executed prompt and matched hash `7ae24437002a7ea68da7f05e236ac8a88d214bf2ad79d8fd349c1a9b041660da`.
It immediately produced an accepted eight-unit team from the same installed
roster. The roster and host are therefore sufficient; the product failure is
an accepted-but-unusable inference sample with no verifier-driven repair.

The local AR-212 implementation now runs complete staffing verification inside
recruiter semantic acceptance, resets rejected proposal state before the one
full replacement response, and caches only accepted or verifier-clean explicit
gap proposals. Preflight failure schema v2 persists bounded staffing and hiring
reason-code arrays. The exact eight-test acceptance slice passes, as do 24
canary/CLI compatibility tests and all 110 dashboard UI tests. The named fast
production spine now also passes: 639 Python tests passed with 6 skips, every
routing-evaluation threshold passed, and decision-conformance passed with a
green baseline, every curated mutation killed, and the source unchanged.
Review, merge, exact reinstall, and fresh live proof remain.

One broader compatibility run exposed an unrelated stale preflight-token
failure in untouched native plan-scope code. It is isolated as
[AR-213](issue-AR-213-reject-stale-preflight-tokens-before-plan-validation.md)
and does not expand this package.

## Approach

1. Make whole-team staffing verification part of recruiter-stage acceptance.
   A verifier rejection enters the already bounded second semantic attempt for
   that provider; it does not add an unbounded retry or another selector.
2. Cache and project a recruiter proposal only after the full verifier accepts
   it. Preserve explicit inference-declared gaps so the existing governed
   contractor-hiring path remains authoritative.
3. If the repair budget is unavailable or the repaired proposal remains
   invalid, fail loudly with no parent-generalist fallback.
4. Persist only bounded staffing abstention and hiring reason codes with a
   terminal preflight failure. Do not retain prompt, response, exception, path,
   or credential content.
5. Reproduce the exact accepted-before-verification shape in focused tests and
   prove one repair call, accepted restaffing, terminal exhaustion, and safe
   evidence projection.

## Dependencies

ADR-0118 keeps selection inference-owned. ADR-0121 permits deterministic code
to recall and reject but never select. AR-207 owns the product failure receipt
and active recovery capsule; AR-203 and AR-204 own final workspace and README
acceptance.

## Acceptance

- [x] Full verifier rejection participates in exactly one bounded recruiter
  semantic-repair attempt without deterministic selection.
- [x] Explicit inferred gaps continue to governed contractor hiring; an
  unrepaired result still blocks the substantive parent.
- [x] Terminal preflight evidence preserves bounded verifier and hiring reason
  codes without prompt or provider-response content.
- [x] Focused regression tests reproduce the accepted-but-unusable proposal
  and prove repair, exhaustion, caching, and evidence behavior.
- [x] The named local gate passes before review and merge.
- [ ] One new exact build passes supported-bypass activation and at most one
  governed product trial with zero corrections and proven workspace write.
