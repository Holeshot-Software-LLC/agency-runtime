---
title: "AR-208: Preserve exact Codex host notices in product evidence"
status: in_progress
category: roadmap
created: 2026-07-31
updated: 2026-07-31
tags: [product, evidence, multi-harness, diagnostics, security]
related:
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/decisions/0125-admit-only-exact-content-free-codex-host-notices.md
  - docs/worklog/2026-07-31-fb797f9-codex-host-notice-classification.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: product
issue_id: AR-208
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/200
depends_on: []
blocks: [AR-207]
---

# AR-208: Preserve exact Codex host notices in product evidence

## Problem

Codex 0.146 emits a small set of non-critical host notices as completed JSONL
items whose type is `error`. Agency classifies two exact messages into
content-free notice types for activation evidence, but the product collaboration
projection reconstructs a fixed shape that omits `host_notice_types` and
`host_notice_count`. A product report therefore loses the admitted notice facts
even when the backend observed and classified them correctly.

The exception is also a durable security and operating boundary: recognized
messages do not fail the canary, while every unknown or near-match error remains
fatal. That boundary was implemented under AR-207 without its own issue or ADR.

## Current state

PR 198 introduced exact-message classification for the supported hook-bypass
notice and one skill-catalog-shortening spelling. PR 199 added Codex's second
exact packaged spelling. Activation evidence retains fixed notice types and a
count without raw messages, and arbitrary or one-character near-miss errors
remain fatal.

PR 201 preserves the validated fields through product evidence, merged as exact
revision `dd85e7d981f9214104c61815b49f51e178896295`, and exact-installed cleanly.
A late GitHub Codex review then identified that an invalid projection became
`null` without participating in the product pass predicate. That P1 is valid:
malformed notice evidence can still produce a passing verdict. Tracker #200 is
reopened, and the repair now makes the projection itself a required proof gate.

Commit `e4ceb89` implements that fail-closed gate. The focused product suite,
the named fast spine, and all 69 decision mutations now pass; every PR 198 and
PR 201 review thread has an evidence-backed resolved disposition. The repair
still requires reviewed merge before tracker #200 can close.

The review's separate ancestry claim is disproven by canonical Git history:
`ea376a5`, `947dafb`, `bb1122c`, and `096570a` are all ancestors of reviewed
head `57fba809` and merge `dd85e7d`.

## Approach

1. Validate product notice evidence against the same fixed allowlisted type set
   used by the Codex stdout classifier.
2. Require a canonical unique type list and a non-boolean count whose value is
   consistent with the listed types and bounded by the rollout line ceiling.
3. Preserve only the validated types and count in the product collaboration
   projection; never persist the original host message.
4. Add focused regressions for preservation and for unknown, duplicate,
   malformed, inconsistent, and unbounded values.
5. Record the exact-message exception and fail-closed consequences in
   ADR-0125, then close the valid review threads with commit-backed evidence.

## Dependencies

AR-207 owns the product execution and routing-diagnostics path that exposed this
gap. AR-203 and AR-204 remain blocked until a fresh exact-installed product
trial proves both the product projection and the wider README story.

## Acceptance

- [x] Product evidence retains validated `host_notice_types` and
  `host_notice_count`.
- [x] Raw host messages never enter persisted product evidence.
- [x] Unknown, near-match, duplicate, malformed, inconsistent, and unbounded
  notice data fail closed.
- [x] ADR-0125 and reciprocal roadmap, decision, and worklog traceability are
  complete.
- [x] Focused warning-strict tests and the named fast spine pass.
- [x] Every PR 198 and PR 201 review thread has a commit-backed response and
  accurate resolved disposition.
- [ ] **codex**: The fail-closed repair is reviewed, merged, and exact-installed.
- [x] **zcode**: The fail-closed repair is reviewed, merged, and exact-installed.
- [ ] **claude**: The fail-closed repair is reviewed, merged, and exact-installed.
- [ ] **hermes**: The fail-closed repair is reviewed, merged, and exact-installed.
- [ ] **openclaw**: The fail-closed repair is reviewed, merged, and exact-installed.

## Harness scope

This issue's concept applies across all supported execution hosts (codex,
claude, zcode, hermes, openclaw). The shared code path lives in the product
collaboration projection that preserves validated `host_notice_types` and
`host_notice_count` for every host, while the host-notice classifier itself is
host-specific: `agency_runtime/adapters/hooks.py` (codex/claude/zcode via
HookBridge) and `agency_runtime/adapters/base.py` (hermes/openclaw via
BaseAdapter). Each host's live-trial checkbox above is independent.
