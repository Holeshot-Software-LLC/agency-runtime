---
title: "AR-119 no-cost hiring diagnostic for pair fcffd96c"
status: active
category: roadmap
created: 2026-08-20
updated: 2026-08-20
tags: [roadmap, evidence, recruiter, hiring, diagnostics, AR-119, AR-259]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-252-record-verified-acceptance-outcomes.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/roadmap/issue-AR-259-preserve-terminal-hiring-state.md
  - docs/roadmap/AR-119-39ff6dca-recruiter-diagnostic-evidence.md
  - docs/roadmap/AR-119-vision-loop-status.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - agency_runtime/core/accepted_outcome_canary_contract.py
  - agency_runtime/core/preflight_failure.py
  - agency_runtime/core/selector/pipeline.py
supersedes: []
superseded_by: null
type: reference
issue_id: AR-119
---

# AR-119 no-cost hiring diagnostic for pair fcffd96c

This package records the first accepted-outcome draw after the recruiter
safe-team repair reached main. The Store was opened read-only, the fixed parent
prompt was reconstructed from source, the target contractor was inspected
through the read-only CLI, and the gap-to-hiring code path was traced locally.
No provider, host CLI, canary, install, config write, push, or hosted workflow
ran during this diagnosis.

## Exact draw and terminal boundary

- PR #304 merged exact tree `24fc346c471c248c3b464fd3a19b15b27976186e`
  to main as `c279bca9fc0429b6c30a30c261b90b2668ea6b3b` with `[skip ci]` and no
  hosted check run.
- Pair `fcffd96cf0fe7e2ef01ad7a3e030c8a9`; run
  `905edae0-00e1-4406-ae09-80a8091b2046`; session
  `b6aed0c9-d43a-45cd-a28c-f80a0891abc1`; trace
  `6ded2097-44b6-41c1-addc-1d71c6e5221f`.
- The run started `2026-08-20T22:30:03.950623Z` and ended
  `2026-08-20T22:34:22.376Z` as `preflight_failed`.
- Failure receipt `9864c8f6-bd13-4712-afb8-2a339751c0c1` records
  `routing / substantive_specialist_unavailable / runtime_error`.
- Claude Code 2.1.226 exited 0 without timeout or truncation. The canary failed
  closed at `delivery_marker_absent`; no accepted outcome, attestation, or
  promotion was written.

## What changed after the recruiter repair

The parent planner reached `claude-haiku` / `haiku` and returned
`structured_response_applied`. The parent recruiter then reached the explicitly
pinned `codex-subscription` / `gpt-5.6-terra` and also returned
`structured_response_applied`. This is different from pair `39ff6dca...`, where
both recruiter attempts were rejected `staff_without_safe_team`.

The terminal verifier codes were `no_safe_sufficient_team` and
`recruiter_abstained`. That is a valid, safe abstention, not an unsafe output
and not a provider-routing failure. It is also poor selection for this request:
the active `typescript-application-engineer` contract explicitly covers
TypeScript, implementation, runtime validation, Claude, and Windows. The draw
did not staff that existing exact-match contractor.

No routing decision, specialist or skill load, delegation, worker run, or
child-judge response exists for the trace. The requested child judge remained
`codex-subscription`, but parent staffing stopped before it could answer. No
matrix cell moves.

## Prompt reconstruction

The exact parent prompt is reconstructable from the immutable pair identity and
source builder. It is 2,367 UTF-8 characters, SHA-256
`0f4673c68eea4444bd614e881ac0da8ab4d9d8d3d53fcfb75ca5de9e38c8a972`.
Its first 2,000 characters hash to
`ea0d639d11a52f53c832cec66ad33cfa04fea48da18097462b42237e92516774`,
which matches the bounded Store capture. The production indivisible-unit
detector returns true.

The byte-exact dynamic planner and recruiter documents are not recoverable.
CLI structured providers run ephemerally in private temporary directories; the
Store intentionally retains content-free receipts rather than raw model
responses. This package therefore does not invent the applied recruiter's
ranking, classifications, or prose evidence.

## The hiring ambiguity on disk

The receipt's `hiring_reason_codes` is empty, but that has two possible source
states:

1. no hiring event was produced; or
2. hiring reached `hired`, `amended`, or `pending_approval`, whose successful
   deferred outcome has an empty reason list, and a later failed restaff caused
   atomic preflight to roll the pending mutation back.

The Store has zero hiring cases and worker events for the trace in either state,
because failed atomic preflight must not commit them. Hiring model attempts are
not copied into the parent workforce attempt list. Elapsed time alone cannot
settle which branch ran, so it is not promoted as evidence.

AR-259 closes that diagnostic hole without retaining content: terminal failure
receipts preserve the allowlisted event status and whether a positive number of
hiring inference calls was consumed. Focused preflight and dynamic-hiring
verification, including Store persistence, passes 103 warning-strict tests.
This local diagnostic change does not repair selection, prove a hire, authorize
a provider retry, or move any rule or matrix cell.
