---
title: "Worklog detail: Bind contractor risk to verified authority"
status: active
category: worklog
created: 2026-08-01
updated: 2026-08-01
tags: [workforce, contractors, security, inference, product, testing]
related:
  - docs/roadmap/issue-AR-219-preserve-exact-multi-unit-product-execution-evidence.md
  - docs/decisions/0081-compile-contractors-from-governed-structured-contracts.md
  - docs/decisions/0134-bind-contractor-risk-to-validated-authority.md
supersedes: []
superseded_by: null
type: worklog
commit: b258cfb686c14f2f506c5ad6ea3adb2c259a2cad
short: b258cfb
date: 2026-08-01
pr: null
related_issues:
  - docs/roadmap/issue-AR-219-preserve-exact-multi-unit-product-execution-evidence.md
---

# Worklog detail: Bind contractor risk to verified authority

## Purpose

Repair the first boundary exposed by consumed product trial
`ar219-386afca-readme-01`. Inference produced a contractor for a workspace-only
unit, but preflight classified the proposal as requiring human approval before
any route or specialist execution could publish.

## Approach

The validated work unit now owns mutation scope: `workspace_write` is ordinary
local authority and only `external_write` sets external-mutation risk. The
contract classifier evaluates individual assertions so explicit prohibitions
such as `no credential access` do not grant the prohibited authority, while a
later positive assertion and genuine legal, financial, medical, destructive,
credential, offensive, or external authority remain approval-gated. Rejected
outcomes retain only allowlisted risk-class codes.

Inference still designs the specialist and contract. Deterministic code only
binds the proposal to already-validated authority and enforces the security
ceiling described by ADR-0134.

## Challenges encountered

Atomic preflight correctly omitted the rejected contractor document, so the
historical receipt could not reveal which exact class fired. Code inspection
found two independently sufficient false-positive paths. The first review also
caught prompt wording that accidentally separated `Never` from `write
executable instructions`; the final prompt preserves that prohibition exactly.

## Decisions and alternatives

ADR-0134 records the authority boundary. Trusting the model-authored
`external_mutation` flag, treating all substring matches as granted authority,
or bypassing positive high-risk approval in autonomous mode were rejected.

## Verification

- Focused workforce, preflight-receipt, and decision-manifest checks: 81 passed.
- Named Python production spine: 654 passed, 6 skipped.
- Dashboard UI: 110 passed.
- Routing evaluation: all 39 gates passed.
- Decision conformance: baseline passed; 78/78 mutations killed, zero survived
  or invalid, and `source_unchanged=true`.
- Documentation: 617 Markdown files validated.
- Two bounded review passes, repository-wide Ruff lint/format, and
  `git diff --check` passed.

## Follow-ups

Review and merge the immutable repair, install the exact merge, then spend one
activation canary and at most one fresh product trial. Update the local evidence
page and OpenClaw handoff from that exact result.
