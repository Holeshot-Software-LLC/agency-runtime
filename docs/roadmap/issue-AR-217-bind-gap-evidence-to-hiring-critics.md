---
title: "AR-217: Bind independent gap evidence into contractor critiques"
status: done
category: roadmap
created: 2026-08-01
updated: 2026-08-01
tags: [bug, product, inference, hiring, contractor, evidence]
related:
  - README.md
  - agency_runtime/core/workforce/hiring.py
  - tests/test_workforce_dynamic_hiring.py
  - docs/roadmap/issue-AR-203-prove-product-canary-write-and-activation.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-215-repair-critic-rejected-contractor-proposals.md
  - docs/roadmap/issue-AR-219-preserve-exact-multi-unit-product-execution-evidence.md
  - docs/roadmap/handoffs/issue-AR-207.md
  - docs/decisions/0081-compile-contractors-from-governed-structured-contracts.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0130-repair-critic-rejected-contractor-proposals-once.md
  - docs/decisions/0131-bind-verifier-evidence-into-contractor-critiques.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: product
issue_id: AR-217
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/217
depends_on: [AR-215]
blocks: [AR-203, AR-204, AR-218]
---

# AR-217: Bind independent gap evidence into contractor critiques

## Problem

Exact merged and installed build
`9c2e9f8f9a687998c331d6081016a15d1816fc36` passes the named local production
spine and supported autonomous Codex activation. Its single governed
`python-cli-service` product trial still terminates during workforce routing.

The hiring analyst receives the complete workforce snapshot and the upstream
verified-gap projection. Each independent critic receives only the work unit,
candidate-authored gap and duplicate evidence, the candidate contract, and
compiler hashes. Because the critic must treat candidate evidence as untrusted,
it cannot independently compare the gap against the workforce. Both bounded
critic passes rejected the live proposal as self-asserted.

## Current state

Trial `ar215-9c2e9f8-readme-01` is consumed and terminal `NO-GO` after 166.4
seconds. Session `019fbbd5-5898-7a61-a5f9-e43888769741`, trace
`019fbbd5-590e-7953-8ccb-be57cd49c39f`, and run
`be99a177-3440-4bba-8886-7e0873348aeb` retain
`reason_code=substantive_specialist_unavailable` and hiring reason codes
`gap_not_independently_verified`, `evidence_is_self_asserted`, and
`nearest_worker_comparison_not_credible_without_verification`.

Planner and recruiter inference both applied through
`codex-subscription/gpt-5.6-luna`. Atomic failure preserved zero route,
specialist load, grant, delegation, finalization, header, or workspace-write
evidence. Correction count zero is not success because parent generation never
started. This exact build and trial must not be rerun.

PR 218 subsequently merged the evidence handoff as exact revision
`8cfd9751aa7290362b6e3fcdec60adc81315617c`. Its supported autonomous
activation passed on the first attempt with `code-reviewer`, one completed
delegation, an accepted first-pass header, and zero corrections. The one product
trial on that build stopped earlier than contractor hiring: the shared
three-call workforce budget funded planner rejection/repair and recruiter
rejection but not the recruiter's bounded repair. AR-218 owns that independent
budget boundary; the consumed trial neither disproves nor live-proves this
issue's critic handoff.

The later exact `f8e607d` product trial selected three already-governed
contractor versions in an accepted eight-unit team, but inference reported no
gap and performed no new hiring call. That trial therefore still does not
live-prove this issue's critic handoff. It advanced through eight completed
workers before AR-219's separate topology-projection and workspace-write
failure.

## Approach

1. Give both fresh critic passes the runtime-projected verified-gap codes and
   exact complete workforce snapshot already supplied to the hiring analyst.
2. Keep the candidate's gap comparison and contract untrusted. The critic must
   independently compare the work unit with the supplied workforce and remain
   veto-only.
3. Keep the raw user request out of critic authority; retain only its digest.
4. Preserve the four-call ceiling, one replacement maximum, deferred atomic
   commit, duplicate checks, disabled-worker checks, and high-risk approval.

## Dependencies

AR-215 and ADR-0130 govern the bounded candidate, critic, replacement, critic
sequence. ADR-0081 and ADR-0118 require independent inference evidence without
letting deterministic code design or select the contractor.

## Acceptance

- [x] Both critic prompts contain the same bounded upstream verified-gap
  projection and complete workforce snapshot used for candidate generation.
- [x] Evidence-sensitive fixtures prove a critic can verify a real gap without
  trusting candidate-authored claims.
- [x] Covered, duplicate, disabled, unsafe, and second-rejection cases remain
  terminal and mutation-free.
- [x] Raw user instructions are not promoted into critic system authority.
- [x] The named local production spine passes on one exact reviewed head.
- [ ] One next exact build passes autonomous activation and at most one fresh
  product trial with specialist delegation, workspace write, a first-pass
  valid header, zero corrections, and independent artifact checks.
