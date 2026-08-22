---
title: "Preserve planner repair diagnostics"
status: in_progress
category: roadmap
created: 2026-08-22
updated: 2026-08-22
tags: [inference, planning, observability, repair, litellm]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-273-model-agnostic-structured-inference-profiles.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/roadmap/AR-119-openclaw-hermes-verification-packet.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0164-delegate-exact-schema-translation-to-litellm.md
  - agency_runtime/core/preflight_failure.py
  - agency_runtime/core/workforce/inference.py
  - agency_runtime/core/workforce/intent.py
  - tests/test_preflight_failure_diagnosis.py
  - tests/test_workforce_inference.py
supersedes: []
superseded_by: null
type: issue
epic: provider-runtime
issue_id: AR-275
priority: p0
tracker_url: null
depends_on: [AR-273]
blocks: [AR-119]
---

# AR-275: Preserve planner repair diagnostics

## Problem

A strict planner rejection already carries bounded deterministic detail and,
for plan-policy failures, exact runtime-owned violation codes. Workforce
routing serialized the free-text detail, but the terminal preflight receipt
projector kept only recruiter failure rows. Both OpenClaw substantive failures
therefore collapsed to `provider_response_contract_invalid`, forcing another
live inference attempt to learn whether the schema, ontology, dependency
ordering, or completeness policy rejected the plan.

The one allowed planner repair also reused the ordinary intent-planner system
instruction. That prompt is correct for a first attempt but does not give a
failed model a concise, stage-specific contract to apply every runtime code,
emit one complete replacement, and preserve strict safety invariants.

## Current state

The expected-red slice retained four exact failures and four passes: planner
codes were absent from the preflight receipt, attempts had no structured code
field, the policy repair feedback omitted that field, and routing could not
serialize it. The repaired focused slice passes all eight cases.

The affected planner, intent, preflight bounds, and routing/header modules pass
178 tests with one skip under the repository-required private temp-file umask.
An earlier broader attempt is retained rather than hidden: 29 Store tests
failed because the process inherited shell umask `0002`, and one existing test
still expected the old shared system prompt. The changed private-umask input
and corrected assertion pass without any production namespace relaxation.

No Agency installation or live inference has used this candidate yet.
OpenClaw remains on native `litellm/task-general`; Agency alone requests exact
alias/model-group `task-agency-router`. The alias target, strict validator,
fallback rules, and all OpenClaw, Hermes, Codex, Claude, and ZCode
configuration remain unchanged.

The docs gates, full ruff checks, 827-test production spine, 134-test UI gate,
and routing evaluation pass. Decision conformance remains a tooling limitation,
not a code verdict: both the default checkout invocation and a changed trusted
`/usr/bin/python3` invocation resolve the isolated fixture runner to
`/usr/bin/python3.12`, where pytest is unavailable. Both failed receipts are
retained; neither mutation execution nor a pass is claimed.

## Approach

Attach a tuple of content-free validation reason codes to every rejected
planner attempt. Preserve exact plan-policy codes and use one fixed generic
code for other deterministic planner semantic failures. Serialize the tuple
through workforce routing, then project it into terminal preflight evidence
only when every item belongs to the closed runtime vocabulary and the complete
list stays within the existing receipt bound.

Use a compact planner-repair system instruction on the one existing repair
attempt. It requires a complete inference-authored replacement, schema-only
fields, all listed corrections, earlier-only dependencies, and unchanged
assurance requirements. Provider type and model remain opaque; the prompt does
not inspect or specialize for an alias target.

## Dependencies

- AR-273 exact-schema delivery and harness-scoped inference profiles.
- ADR-0027 authoritative, bounded runtime evidence.
- ADR-0164 LiteLLM-owned target translation with strict local validation.
- The existing one-repair call budget and zero protected-provider fallback.

## Acceptance

- [x] Focused regressions fail before repair for missing planner codes and repair guidance.
- [x] Exact plan-policy codes and one fixed generic semantic code survive in attempts.
- [x] Routing and terminal receipts preserve only allowlisted, bounded codes.
- [x] The single planner repair uses provider- and model-agnostic complete-plan guidance.
- [x] Strict local validation, call budget, fallback policy, and alias opacity remain unchanged.
- [x] Focused and affected local tests pass.
- [x] Docs, ruff, fast production spine, UI, and routing-eval gates pass.
- [ ] Decision conformance is platform-blocked because its trusted Python 3.12 fixture lacks pytest.
- [ ] A clean local substantive/ledger commit pair exists.
- [ ] Agency alone is reinstalled into the stopped OpenClaw host from this checkout.
- [ ] One genuinely new OpenClaw turn proves either strict acceptance or an exact diagnostic receipt.
- [ ] Tracker creation remains pending separate authorization.
