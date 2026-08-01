---
title: "AR-215: Repair critic-rejected contractor proposals once"
status: in_progress
category: roadmap
created: 2026-08-01
updated: 2026-08-01
tags: [bug, product, inference, hiring, contractor]
related:
  - README.md
  - agency_runtime/core/workforce/hiring.py
  - tests/test_workforce_dynamic_hiring.py
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-212-repair-verifier-rejected-recruiter-proposals.md
  - docs/roadmap/issue-AR-214-preserve-codex-product-plan-authority-through-context-delivery.md
  - docs/roadmap/issue-AR-217-bind-gap-evidence-to-hiring-critics.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0121-gate-deterministic-recall-without-selection-authority.md
  - docs/decisions/0129-repair-verifier-rejected-recruiter-proposals-once.md
  - docs/decisions/0130-repair-critic-rejected-contractor-proposals-once.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: product
issue_id: AR-215
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/214
depends_on: [AR-212, AR-214]
blocks: [AR-203, AR-204, AR-217]
---

# AR-215: Repair critic-rejected contractor proposals once

## Problem

Exact installed build `d6ba36a50a7d0e9186938e3b1a0b4330fd553aa0`
passes default suite installation and supported autonomous Codex activation.
Its one governed `python-cli-service` product trial terminates during workforce
routing before parent generation. Because it stops earlier than context
delivery, that trial cannot provide AR-214's final live product proof. No
specialist, delegation, header, or workspace write is produced.

Two bounded read-only route diagnostics reproduce the product-level problem
without another host trial. Both Luna/low and Sol/xhigh author an eight-unit
plan and reach an explicit verified gap. The configured contractor path then
either returns no valid hiring response or produces a candidate that the
independent critic rejects. The current two-call hiring budget owns one
candidate proposal and one critic response, so a useful critic rejection has no
bounded repair path even though the README promises an open-ended contractor
pool for every defensible gap.

## Current state

Product trial `ar214-d6ba36a-readme-01` is consumed and terminal `NO-GO`.
Session `019fbb8c-8039-7a10-9b18-52f6a0378dce`, trace
`019fbb8c-80ad-7351-a17f-5f4b1c024830`, and run
`84ab3f57-8d6b-414b-9da8-59b7c3231681` retain one content-free routing failure
with `exception_category=validation_error` and zero committed route, plan,
specialist, grant, delegation, worker, finalization, header, or workspace
evidence. Correction count is zero only because parent generation never began.

A same-request Luna diagnostic reaches an applied planner and recruiter, then
declares a documentation-unit gap. Hiring uses both calls and the independent
critic rejects the proposed contractor for four bounded contract-quality
reasons. A Sol/xhigh comparison reaches the same eight-unit/gap shape and
returns `hiring_inference_failed`. Model choice therefore does not explain the
missing contractor.

The named local production spine passes, PR 215 merged as exact commit
`9c2e9f8`, and supported autonomous activation selected and delegated
`code-reviewer` with a valid first header and zero corrections. The one product
trial for that build reaches the bounded contractor sequence but both critics
reject candidate-authored gap evidence because their prompts omit the complete
workforce and upstream verifier projection. AR-217 owns that distinct evidence
handoff; the consumed trial does not satisfy this item's live-product gate.

## Approach

1. Keep inference authoritative over the contractor's identity, scope, and
   employment contract. Local code may validate and reject but may not author a
   replacement.
2. When the first complete candidate passes deterministic validation but the
   independent critic rejects it, feed only bounded critic reason codes into
   one complete replacement request.
3. Require a fresh independent critique of the replacement. Never apply a
   repaired candidate without that second approval.
4. Bound the whole sequence to candidate, critic, replacement, critic. Provider
   unavailability, invalid replacement, second rejection, or insufficient
   budget remains terminal and mutation-free.
5. Preserve deferred atomic commit, least-authority compilation, exact
   restaffing, and content-free evidence.

## Dependencies

AR-212 and ADR-0129 govern one recruiter repair before a verified gap exists.
AR-214 preserves the inferred plan through exact Codex context delivery. This
item begins only after both boundaries and does not reopen either one.

## Acceptance

- [x] Focused fixtures prove critic rejection, one complete inferred
  replacement, fresh independent approval, and immediate restaffing.
- [x] Replacement exhaustion remains terminal with bounded reason codes and no
  hiring case, worker, route, or preflight-ready mutation.
- [x] Budgets below four calls never launch an uncriticizable replacement.
- [x] Existing first-pass approved hiring behavior and high-risk approval gates
  remain unchanged.
- [x] The named local production spine passes on one exact head.
- [ ] One reviewed exact build passes autonomous activation and at most one
  fresh product trial with specialist delegation, workspace write, a first-pass
  valid header, zero corrections, and independent artifact checks.
