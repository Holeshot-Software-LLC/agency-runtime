---
title: "AR-235: Make gap contractor hiring autonomous with isolated security review and amend-first staffing"
status: done
category: roadmap
created: 2026-08-04
updated: 2026-08-04
tags: [workforce, hiring, security, routing, observability, inference]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-122-contractor-hiring-and-lifecycle.md
  - docs/roadmap/issue-AR-228-eliminate-deterministic-staffing-authority.md
  - docs/roadmap/issue-AR-142-instrument-runtime-boundaries.md
  - docs/roadmap/issue-AR-155-bound-dashboard-hiring-evidence.md
  - docs/roadmap/issue-AR-153-complete-worker-detail-evidence.md
  - docs/roadmap/issue-AR-236-achieve-full-cli-dashboard-parity.md
  - docs/analysis/2026-08-04-cli-dashboard-parity.md
  - docs/roadmap/reference-workforce-inference-stages.md
  - agency_runtime/core/workforce/hiring.py
  - agency_runtime/core/workforce/hiring_contract.py
  - agency_runtime/core/workforce/inference.py
  - agency_runtime/core/config_defaults.yaml
  - agency_runtime/core/structured_provider.py
  - agency_runtime/dashboard/dashboard-render.js
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-235
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/244"
depends_on: []
blocks: []
---

# AR-235: Make gap contractor hiring autonomous with isolated security review and amend-first staffing

## Problem

Gap contractor hiring is the recovery path for "no audited specialist fits" and it
needs to keep the runtime productive without a 24/7 human gate, while staying
auditable. Today the path is conservative in three ways that make it slow and
silent in failure:

1. The safety gate is a deterministic regex classifier
   (`classify_contractor_risk` in `agency_runtime/core/workforce/hiring_contract.py:385`)
   over eight hand-listed marker phrases. It catches obvious cases and misses
   anything the marker list does not anticipate. Inference is the right tool for
   this judgment; the regex is not.
2. `allow_existing_worker_amendment: bool = False` in `hire_contractor_for_gap`
   (`agency_runtime/core/workforce/hiring.py:1430`) forces every gap to spawn a
   new contractor. Near-matches that would be cheap and safe to amend are
   rejected as "stretch a near-match into a generalist" (the recruiter's own
   contract at `hiring.py:59-63`). The result is workforce duplication for
   scenarios that differ only in narrow scope.
3. `max_hires_per_task: 1` and `max_hires_per_day: 3`
   (`agency_runtime/core/config_defaults.yaml:76-77`) cap hiring at levels that
   cause silent incompleteness with no operator visibility. The intent
   (prevent runaway, prevent stretch-into-generalist) is right but the
   enforcement is wrong: a hard cap hides the failure mode instead of
   instrumenting it.
4. `auto_promote_successes: 0` (`config_defaults.yaml:78`) keeps promotion
   human-controlled by default, which is incompatible with autonomous 24/7
   operation. A contractor with N independently verified successful
   assignments is a known-good asset that does not need a human in the loop.
5. The four per-stage model knobs (`planner_model`, `recruiter_model`,
   `hiring_model`, `critic_model` at `config_defaults.yaml:63-66`) are flat
   model names. They cannot express `(model, thinking_level)`, cannot route
   the safety reviewer to a different profile than the creator, and cannot
   carry capability-class or independence metadata. The conveyor project
   (sibling repo) already documents the (profile, route, default_profile)
   shape that this work should adopt.

## Current state

- Gap hiring flows `hiring → hiring-critic → commit` (or fail) inside
  `hire_contractor_for_gap` (`hiring.py:1418`). The critic is the existing
  `_invoke` stage `hiring-critic` (`hiring.py:1498-1507`) and uses the same
  provider chain as the creator by default. Repair mechanics exist
  (`hiring-repair`, `hiring-repair-critic` at `hiring.py:718, 758`) for
  malformed JSON output but are not wired to safety verdicts.
- Risk tier is `high` iff `classify_contractor_risk` returns a non-empty
  tuple; otherwise `standard`. High risk gates the case behind
  `apply_approved_hiring_case` (`hiring.py:1212`). The 8 marker classes
  (`hiring_contract.py:68-80`) are: legal, medical, financial, destructive,
  approval, credential, security_offensive, external_mutation.
- The recruiter's `duplicate_evidence` block
  (`hiring.py:374-388`, schema) already returns
  `decision: {"enum": ["hire", "reuse", "amend"]}` with a
  `coherent_amendment_target` slug and a `maximum_overlap` (0–1) score.
  The amendment agent `_amendment_agent` (`hiring.py:977`) is implemented
  and produces a byte-preserving additive amendment. Only the gating
  default is conservative.
- The conveyor project (sibling repo) provides the reference pattern for
  per-stage inference configuration: `inference.routes` mapping consumer
  names to named profiles, and `inference.profiles` with `(adapter, model,
  thinkingLevel, capabilityClass)`. The reviewer is required to be
  independent of the builder, recorded explicitly
  (`conveyor/src/config/types.ts:259-271`).
- The dashboard's worker detail view already renders a per-worker
  "Promotion readiness" card with verified successes, evidence reasons,
  and the closest-workers comparison
  (`agency_runtime/dashboard/dashboard-render.js:1449-1466`). What it
  lacks is a per-contractor activity log showing every assignment, the
  outcome, the verifier, and the evidence.

## Approach

### 1. Inference-based safety review (replaces deterministic regex)

Replace `classify_contractor_risk` with an explicit `security_review` stage
on the hiring path. The reviewer runs in a **fresh isolated session** — no
shared context, no shared memory, no shared tool state with the creator.
It receives only the request, the work unit, the compiled contract, and the
contract hash, plus a system prompt listing the review categories (the 8
risk classes, with concrete examples per category).

The reviewer returns `{verdict: "safe" | "unsafe", reasons: [...],
required_changes: [...]}`. The verdict is the source of truth.

The 8 marker classes from the old regex are preserved as a **first-pass
fast filter** on the contract body, with the explicit purpose of routing
obviously-bad inputs to rejection without invoking the reviewer. The
filter is a hint, not a verdict; the reviewer's call is final.

The `risk_tier` field on the case becomes `safe | unsafe` instead of
`standard | high`. The `human_approval_required` flag and the
`apply_approved_hiring_case` approval gate are removed from the standard
gap-hire path. The reviewer is the gate.

The creating model's system prompt (in `_HIRE_SYSTEM`,
`hiring.py`) is updated to instruct the creator to produce narrow, safe,
auditable contracts on the first attempt, and to call out the review
categories explicitly so the creator is told, in the same call, what
the reviewer will check for.

### 2. Bounded repair on unsafe verdict (not on the happy path)

The 3-turn repair loop is a **recovery path**, not a normal path. Wiring:

```
hiring (compile) ──► security_review (isolated, fresh session)
                          │
                ┌─────────┴─────────┐
                │ safe              │ unsafe
                ▼                   ▼
             commit            hiring.repair (creator, with reviewer
                                feedback as repair_context)
                                   │
                            ┌──────┴──────┐
                            │ turn < N    │ turn == N
                            ▼             ▼
                         security_review  reject → generalist fallback
                              again          (Recruited via: none)
```

- `N` is `hiring_repair_budget: 3` (new knob, default 3).
- The per-attempt budget `hiring_call_budget: 4`
  (`config_defaults.yaml:70`) is unchanged; the repair budget is a
  separate counter on the case.
- After 3 unsafe verdicts, the case → `rejected` (status), the worker
  is never instantiated, and the affected work unit fails open to a
  generalist with the existing `Recruited via: none` header.
- The reviewer never runs a "look for things to find" mode. A clean
  contract that would have passed on attempt 1 still passes on attempt
  1. The repair path is entered only when the reviewer says unsafe.
- Every attempt and verdict is recorded in the case's
  `attempts` array and the durable audit trail. Operator can replay
  the full repair history from the dashboard.

### 3. Per-stage (model, thinking) profile config (conveyor pattern)

Adopt the conveyor project's inference configuration shape in
`config_defaults.yaml`. Replace the four flat `*_model` knobs with an
`inference` block:

```yaml
inference:
  default_profile: "agency-default"
  routes:
    workforce.planner: "agency-planner"
    workforce.recruiter: "agency-recruiter"
    workforce.hiring: "agency-hiring"
    workforce.hiring.security_review: "agency-security"
    workforce.hiring.repair: "agency-hiring"
  profiles:
    agency-default:
      adapter: "litellm"
      model: "gpt5.6-luna"
      thinking_level: "medium"
    agency-planner:
      model: "gpt5.6-luna-medium"
      thinking_level: "medium"
    agency-recruiter:
      model: "gpt5.6-luna-medium"
      thinking_level: "medium"
    agency-hiring:
      model: "gpt5.6-luna-low"
      thinking_level: "low"
    agency-security:
      model: "gpt5.6-luna-high"
      thinking_level: "high"
```

- The `structured_provider` passes `thinking_level` to the adapter as a
  provider-native parameter (OpenAI `reasoning_effort`, Anthropic
  `thinking` budget, LiteLLM `thinking` param, etc.). When the adapter
  does not support thinking, the field is recorded in the receipt and
  ignored.
- `agency-security` and `agency-hiring` are required to use different
  models and different `thinking_level`s. Same provider is allowed. When
  the same provider is used, the case's `critic_evidence` records a
  `same_provider_as_creator: true` flag and the dashboard surfaces a
  warning on the case detail. The operator can opt into strict mode
  (different provider required) per-deployment via
  `inference.strict_independence: true`.
- The receipt records `(provider, model, thinking_level, receipt_id,
  model_receipt_source)` for the creator, the reviewer, and every
  repair attempt.

### 4. Amend-first staffing default

Invert the default for `allow_existing_worker_amendment` from `False`
to `True`. Wiring:

- When the recruiter returns
  `action: "amend"` with a `coherent_amendment_target` slug and
  `maximum_overlap ≥ amend_overlap_threshold` (new config, default
  `0.7`), execute `_amendment_agent` against the target.
- When `action: "amend"` with `maximum_overlap < threshold` or no
  `coherent_amendment_target`, fall through to the standard hire path.
- When `action: "reuse"` (existing worker is a perfect match), keep the
  current reuse path.
- When `action: "hire"`, proceed to the new security-review path.

The recruiter system prompt and the schema prompt
(`hiring.py:59-63` currently says "Do not stretch or amend a
near-match to fill an ordinary task gap") are updated to reflect the
amend-first policy: prefer amend with a coherent target; only stretch
when no coherent target exists.

The existing `amendment` case type and `apply_approved_hiring_case`
amendment path are reused unchanged.

### 5. Hiring cap removal and dashboard visibility

Remove `max_hires_per_task: 1` and `max_hires_per_day: 3` as hard caps.
Replace with:

- `max_hires_per_turn: 16` (matches the existing
  `max_selected_total: 16` at `config_defaults.yaml:73`).
- `daily_hire_alert_threshold: 50` — soft warning, no rejection.
- The dashboard exposes per-turn hire count, per-day cumulative, and
  per-day top hiring gaps. The case ledger records the per-turn count
  and the per-day cumulative so the dashboard can chart them.

The cap is a hint, not a wall. The amend-first default is the actual
guard against runaway.

### 6. Autonomous promotion with first-batch review window

- `auto_promote_successes: 3` (was `0`) — three independently verified
  successful assignments auto-promote a contractor to `employee`.
- `contractor_review_days: 7` (was `30`) — for the first batch of
  contractors created after this change ships, the dashboard surfaces
  a "review window" badge and the auto-promotion is suppressed for
  contractors younger than 7 days. After the first batch ages out, the
  auto-promotion path runs unconditionally for new contractors.
- The review window is per-contractor, computed from
  `created_at`. Evidence is recorded when the window expires.

### 7. Operator review plane (dashboard)

The existing per-worker "Promotion readiness" card is extended. The
new views:

- A per-contractor **activity log**: every assignment the contractor
  has handled, with outcome, score, evidence hash, and
  `independent_verifier_worker_id` + `independent_verification_receipt_id`.
  Source data: existing `agent_performance_events` table — no schema
  change required.
- A per-case **security review trail**: the original contract, the
  reviewer's verdict and reasons, every repair attempt's diff, and
  the final verdict. Visible in the case detail view.
- A **workforce health** summary on the main dashboard: contractors
  younger than the review window, contractors with 2 of 3 verified
  successes, contractors that hit 3 unsafe reviews (operator-triageable).

Quarantine / suspend / retire semantics are unchanged and explicit:

- `case.status = rejected` — this specific hiring attempt had unsafe
  evidence; the contractor was never instantiated.
- `worker.standing = suspended` — this contractor exists, but routing
  will not pick it. Operator primary action for "this is bad."
- `worker.standing = retired` — this contractor is gone permanently;
  evidence kept. Deliberate "never coming back" decision.

## Dependencies

- AR-122 (Implement governed contractor hiring and workforce lifecycle)
  — done; the underlying hiring, lifecycle, and event stores are in
  place.
- AR-119 (Implement inference-first real-time workforce and contractor
  lifecycle) — in progress; this issue is a sub-effort under the
  same parent epic.
- AR-228 (Fail open with an honest header when no specialist is
  selected) — related; the generalist fallback at the end of the
  3-turn repair loop reuses the fail-open path AR-228 hardens.
- AR-153 (Complete and bound worker-detail evidence) and
  AR-155 (Bound dashboard hiring evidence delivery) — related; the
  per-contractor activity log and per-case security trail ride on
  these.
- The structured_provider and its adapters must accept and forward a
  `thinking_level` parameter (small additive change).

## Acceptance

- [ ] `classify_contractor_risk` and the regex marker list in
      `hiring_contract.py:68-80` are removed from the runtime path.
      The 8 marker classes are preserved as a first-pass filter on
      the contract body with explicit "hint, not verdict" semantics.
- [ ] A new `security_review` inference stage runs on a fresh isolated
      session, sees only the request, work unit, contract, and contract
      hash, and returns `{verdict, reasons, required_changes}`. The
      session is constructed without shared creator context (no shared
      memory, no shared tool state, no conversation history).
- [ ] The reviewer and creator use different models and different
      `thinking_level`s. When the same provider is used, the case
      records `same_provider_as_creator: true` and the dashboard
      surfaces a warning. `strict_independence: true` enforces a
      different provider and surfaces a config error otherwise.
- [ ] A clean contract that would have passed on attempt 1 still
      passes on attempt 1 — the repair path is entered only when the
      reviewer returns `unsafe`. No "look for things to find" mode.
- [ ] An unsafe verdict triggers a repair loop with
      `hiring_repair_budget: 3` (configurable). After 3 unsafe
      verdicts, the case → `rejected`, the worker is never
      instantiated, and the affected work unit fails open to a
      generalist with `Recruited via: none`. Every attempt and verdict
      is recorded in the case's `attempts` array and the audit trail.
- [ ] The flat `*_model` knobs in `config_defaults.yaml` are replaced
      with an `inference.routes` / `inference.profiles` block of the
      same shape used in the conveyor project. `adapter`, `model`,
      `thinking_level`, and `capability_class` are supported on each
      profile. The `structured_provider` passes `thinking_level`
      through to the adapter as a provider-native parameter and
      records the actual value in the receipt.
- [ ] The amend-first default is on. When the recruiter returns
      `action: "amend"` with a `coherent_amendment_target` and
      `maximum_overlap ≥ amend_overlap_threshold: 0.7`, the
      `_amendment_agent` runs against the target. Below threshold or
      with no coherent target, the standard hire path runs.
- [ ] `max_hires_per_task: 1` and `max_hires_per_day: 3` are removed
      from the runtime. `max_hires_per_turn: 16` and
      `daily_hire_alert_threshold: 50` are added. The dashboard
      exposes per-turn and per-day hire counts and a top-gaps chart.
- [ ] `auto_promote_successes: 3` and `contractor_review_days: 7` are
      the new defaults. For contractors younger than the review window,
      the auto-promotion is suppressed and the dashboard shows a
      "review window" badge. The review window is computed per
      contractor from `created_at`.
- [ ] The dashboard worker detail view shows a per-contractor activity
      log (every assignment, outcome, verifier, evidence hash) sourced
      from `agent_performance_events` with no schema change. The case
      detail view shows the security review trail (original contract,
      verdict, reasons, every repair diff, final verdict).
- [ ] Quarantine / suspend / retire semantics are explicit in the
      dashboard: `case.status = rejected` is for the audit trail;
      `worker.standing = suspended` is the operator's reversible
      primary action; `worker.standing = retired` is the deliberate
      "gone permanently" decision. Both standing transitions are
      surfaced on the workforce health summary.
- [ ] The new test spine
      (`test_workforce_dynamic_hiring`,
      `test_workforce_hiring_contract`,
      `test_workforce_selection_safety`,
      `test_workforce_promotion`,
      `test_routing_correctness`) passes with the new code paths.
      New focused tests cover: isolated security review, bounded
      repair loop, same-provider warning, amend-first default,
      cap removal, auto-promotion with review window, dashboard
      activity log and review trail.
