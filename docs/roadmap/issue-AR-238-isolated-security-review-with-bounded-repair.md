---
title: "AR-238: Isolated security review with bounded repair (slices 2-3 of AR-235)"
status: done
category: roadmap
created: 2026-08-04
updated: 2026-08-12
tags: [workforce, hiring, security, routing, inference, sub-issue]
related:
  - docs/roadmap/issue-AR-235-autonomous-gap-hiring-with-isolated-security-review.md
  - docs/roadmap/reference-workforce-inference-stages.md
  - docs/roadmap/issue-AR-228-eliminate-deterministic-staffing-authority.md
  - docs/decisions/0153-adopt-per-stage-inference-profile-routes.md
  - agency_runtime/core/workforce/hiring.py
  - agency_runtime/core/workforce/hiring_contract.py
  - agency_runtime/core/inference_profiles.py
  - agency_runtime/core/config_defaults.yaml
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-238
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/248"
depends_on: []
blocks: []
---

# AR-238: Isolated security review with bounded repair (slices 2-3 of AR-235)

## Problem

AR-235 §1-§2 replace the deterministic regex risk classifier
(`classify_contractor_risk` in `hiring_contract.py:385`) with an
inference-based `security_review` stage that runs in a fresh isolated
session, and wire a bounded repair loop that runs only when the reviewer
returns `unsafe`. These two slices are one coherent feature: the
reviewer's verdict is the gate, and the repair loop is its only recovery
path. Landing one without the other leaves a half-feature (an unsafe
verdict with no recovery, or a repair loop with nothing to repair
against).

The deterministic regex over eight hand-listed marker phrases catches
obvious cases and misses anything the marker list does not anticipate.
Inference is the right tool for this judgment.

## Current state

- `hire_contractor_for_gap` flows `hiring → hiring-critic → commit` (or
  fail) in `agency_runtime/core/workforce/hiring.py:1418`. The critic is
  the `_invoke` stage `hiring-critic` (`hiring.py:1498-1517`) and uses
  the `workforce.hiring.critic` route.
- Risk tier is `high` iff `classify_contractor_risk` returns a non-empty
  tuple; otherwise `standard` (`hiring.py:1590`). High risk gates the
  case behind `apply_approved_hiring_case` (`hiring.py:1212`). The 8
  marker classes (`hiring_contract.py:68-80`) are: legal, medical,
  financial, destructive, approval, credential, security_offensive,
  external_mutation.
- The repair mechanics for malformed JSON exist
  (`_repair_rejected_candidate`, `hiring.py:679`) for the critic
  rejection path, but are not wired to safety verdicts.
- AR-235 slice 1 (ADR-0153) landed the `inference.routes` /
  `inference.profiles` block. The route `workforce.hiring.security_review`
  already maps to `agency-security` and `workforce.hiring.safety_repair`
  maps to `agency-hiring` in `config_defaults.yaml`.
- The `_SECURITY_REVIEW_SYSTEM` and `_SAFETY_REPAIR_SYSTEM` prompts and
  the `HIRING_SECURITY_REVIEW_SCHEMA` are drafted in the
  [inference-stages reference](reference-workforce-inference-stages.md)
  but not yet in the code.

## Approach

### 1. Security review stage (isolated session)

Add `_SECURITY_REVIEW_SYSTEM` and `HIRING_SECURITY_REVIEW_SCHEMA`
(`{verdict, reasons, required_changes}`) to `hiring.py`, matching the
reference doc drafts.

New `_security_review(...)` helper:

- Resolves `workforce.hiring.security_review` providers via
  `configured_workforce_providers`. If unavailable, abstain with a
  content-free code (the deterministic path is not a silent fallback —
  the reviewer is the gate).
- Constructs a **fresh isolated session**: no shared creator context,
  memory, conversation history, or tool state. The prompt carries only
  `request_hash`, the work unit, the compiled contract, the contract
  hash, and the runtime gap projection (content-free facts). It does
  **not** carry the creator's system prompt, prior attempts, or the
  full workforce.
- Returns the verdict as the source of truth.

The 8 marker classes from `classify_contractor_risk` are preserved as a
**first-pass fast filter** on the contract body with explicit "hint, not
verdict" semantics. When the filter finds an obvious marker, the case is
routed to rejection **without** invoking the reviewer (saves a call on
obvious-bad inputs). The filter never approves; the reviewer's call is
final for everything the filter does not catch.

### 2. Bounded repair on unsafe

Add `_SAFETY_REPAIR_SYSTEM` (reuse `_HIRE_SYSTEM` + the reviewer's
`required_changes` as repair context) and wire the loop:

```
hiring (compile) ──► security_review (isolated)
                          │
                ┌─────────┴─────────┐
                │ safe              │ unsafe
                ▼                   ▼
             commit            safety_repair (creator profile, with
                                reviewer feedback as repair_context)
                                   │
                            ┌──────┴──────┐
                            │ turn < N    │ turn == N
                            ▼             ▼
                         security_review  reject → fail open to generalist
                              again          (Recruited via: none, AR-228)
```

- `N` is `hiring_repair_budget: 3` (new config knob on `WorkforceConfig`).
- The per-attempt budget `hiring_call_budget: 4` is unchanged; the repair
  budget is a separate counter on the case.
- After 3 unsafe verdicts, the case → `rejected`, the worker is never
  instantiated, and the affected work unit fails open to a generalist
  with the existing `Recruited via: none` header (AR-228).
- A clean contract that would have passed on attempt 1 still passes on
  attempt 1 — the repair path is entered only when the reviewer says
  unsafe. No "look for things to find" mode.
- Every attempt and verdict is recorded in the case's `attempts` array
  and the durable audit trail.

### 3. risk_tier and approval gate

The `risk_tier` field becomes `safe | unsafe` instead of
`standard | high` on the gap-hire path. The reviewer's verdict is the
source of truth for the standard path; the `human_approval_required`
flag and `apply_approved_hiring_case` approval gate are removed from
the standard gap-hire path. The reviewer is the gate.

## Dependencies

- AR-235 slice 1 (ADR-0153) — done; the inference profile routes and
  `agency-security` profile are in place.
- AR-228 (fail-open generalist) — done; the reject → generalist path
  reuses it.

## Acceptance

- [x] `classify_contractor_risk` remains as a first-pass hint source on
      the contract body. The marker classes are passed to the reviewer as
      scrutiny hints; the filter never rejects on its own. The reviewer's
      verdict is final.
- [x] A new `security_review` inference stage runs on a fresh isolated
      session, sees only the request hash, work unit, compiled contract,
      and contract hash, and returns `{verdict, reasons,
      required_changes}`. The session is constructed without shared
      creator context.
- [x] The reviewer and creator use different models and different
      `thinking_level`s (via the existing `agency-security` vs
      `agency-hiring` profiles). When the same provider is used, the
      case records `same_provider_as_creator: true`.
- [x] A clean contract that would have passed on attempt 1 still passes
      on attempt 1 — the repair path is entered only when the reviewer
      returns `unsafe`.
- [x] An unsafe verdict triggers a repair loop bounded by
      `hiring_repair_budget: 3`. After 3 unsafe verdicts, the case →
      `rejected`, the worker is never instantiated, and the affected
      work unit fails open to a generalist with `Recruited via: none`.
- [x] Every attempt and verdict is recorded in the case's `attempts`
      array and the audit trail.
- [x] The `human_approval_required` flag is `False` and `risk_tier` is
      `standard` on the gap-hire path (the reviewer is the gate). The
      full verdict is recorded in `critic_evidence.security_review`.
- [x] The focused test spine (`test_workforce_dynamic_hiring`,
      `test_workforce_hiring_contract`, `test_workforce_selection_safety`,
      `test_routing_correctness`) passes with the new code paths. New
      focused tests cover: isolated security review, bounded repair loop,
      reject-after-N, same-provider flag, reviewer-approved external hire.
