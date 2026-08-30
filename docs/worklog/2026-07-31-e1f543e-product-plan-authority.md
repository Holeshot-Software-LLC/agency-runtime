---
title: "Worklog detail: Preserve Codex product plan authority"
status: active
category: worklog
created: 2026-07-31
updated: 2026-07-31
tags: [codex, preflight, product, diagnostics]
related:
  - docs/roadmap/issue-AR-214-preserve-codex-product-plan-authority-through-context-delivery.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - docs/decisions/0128-persist-exact-codex-plan-authority-and-serialize-launches.md
supersedes: []
superseded_by: null
type: worklog
commit: e1f543e
short: e1f543e
date: 2026-07-31
pr: null
related_issues:
  - docs/roadmap/issue-AR-214-preserve-codex-product-plan-authority-through-context-delivery.md
---

# Worklog detail: Preserve Codex product plan authority

## Purpose

Repair the exact context-delivery validation failure that stopped an accepted
multi-unit Codex product plan before ready commit, specialist delegation, or
workspace-write proof.

## Approach

The product prompt no longer emits a standalone prose slash that can be parsed
as absolute filesystem authority. Resource extraction now unwraps paired
Markdown backticks and recognizes bounded relative dotfiles, preserving the
requested proof and artifact paths. Explicit absolute authority still fails
closed. Failure receipt schema v3 adds one allowlisted invariant code, and Store,
CLI, dashboard, canary, and migration projections retain it without content.

## Challenges encountered

The first parser hypothesis about roster-version syntax was falsified before any
edit. The exact consumed prompt then reproduced `/` as the invalid resource.
A broader legacy preflight module still reaches the separately tracked AR-213
stale-token fixture; it was not folded into this bounded repair.

## Decisions and alternatives

Ignoring every standalone slash inside resource extraction was rejected because
an explicit request for `/` must not fall back to repository-wide `.` authority.
Persisting exception or path text was rejected; the new invariant is closed and
content-free. Staffing and unit ownership remain inference-authored.

## Verification

- AR-214 accepted-staffing and schema-migration fixtures: 3 passed.
- Named Python production spine: 641 passed, 6 skipped.
- Product harness contracts: 33 passed; canary/status projections: 24 passed.
- Dashboard UI: 110 passed.
- Routing evaluation: every gate passed.
- Decision conformance: passed in 700.5 seconds, every mutation killed, source
  unchanged.
- Repository-wide Ruff lint and format checks passed; `git diff --check` passed.

## Follow-ups

Install the reviewed merge commit and run exactly one supported activation and
one governed product trial. AR-214 remains in progress until specialist
delegation, workspace write, first-pass header, zero corrections, and independent
artifact checks all pass on that exact build.
