---
title: "Worklog detail: Disambiguate technical diagnosis risk"
status: active
category: worklog
created: 2026-08-20
updated: 2026-08-20
tags: [hiring, risk-classification, AR-119, AR-261]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-261-disambiguate-technical-diagnosis-risk.md
  - docs/roadmap/AR-119-f4f3d45e-hiring-risk-evidence.md
supersedes: []
superseded_by: null
type: worklog
commit: 0b48bb51
short: 0b48bb51
date: 2026-08-20
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-261-disambiguate-technical-diagnosis-risk.md
---

# Worklog detail: Disambiguate technical diagnosis risk

## Purpose

Record the first ordinary Claude hiring smoke after AR-259/AR-260 and remove
the deterministic false positive that treated a technical SAP/database
diagnosis as medical authority requiring owner approval.

## Approach

Preserve bare `diagnosis` as owner-gated by default. Exempt it only when the
complete positive contract scope asserts bounded technical context and no
medical context. Medical, clinical, patient, and mixed medical/technical
contracts remain owner-gated, as do every other existing high-risk marker. The
mandatory isolated security-review stage is unchanged.

## Challenges encountered

Atomic preflight correctly rolled the approval-required candidate back, and
the Store intentionally retains no model body or proposed contract. AR-259's
content-free terminal receipt proves that hiring inference ran and reached
`pending_approval`; a provider-free synthetic contract reproduces the only
source-level false positive consistent with the requested `read-only
diagnosis` wording. The evidence record preserves that distinction rather than
inventing the unavailable model field.

## Decisions and alternatives

Requiring medical context before gating was rejected because it would make a
context-free diagnosis permissive. The implemented rule remains fail-safe by
default and recognizes only a bounded technical vocabulary. Changing provider
routing, retaining raw hiring content, or retrying the consumed draw was out of
scope.

## Verification

- Focused hiring-contract and dynamic-hiring tests: 88 passed warning-strict.
- Ruff check and format check: passed.
- Documentation metadata, policy, worklog, and contract checks: passed for 725
  Markdown files.
- All 12 proportional local gates: passed in 1.3 minutes.
- Hosted workflows, provider retries, and exhaustive optional gates: not run.

## Follow-ups

Create the required tracker issue after explicit authorization, publish through
a reviewed no-hosted-work PR, install the resulting exact main, and run one
genuinely different telemetry-preceded hiring draw. The consumed
`f4f3d45e-...` session must not be retried.
