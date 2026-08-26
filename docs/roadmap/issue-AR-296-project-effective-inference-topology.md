---
title: "AR-296: Project effective inference topology in the dashboard"
status: in_progress
category: roadmap
created: 2026-08-25
updated: 2026-08-25
tags: [dashboard, inference, configuration, delegation, truthfulness]
related:
  - README.md
  - CHANGELOG.md
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
  - docs/roadmap/issue-AR-293-safe-inference-profile-config-operations.md
  - docs/roadmap/issue-AR-295-audit-guided-dashboard-asset-budget.md
  - docs/roadmap/handoffs/issue-AR-290.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0138-request-automatic-codex-delegation-through-managed-global-guidance.md
  - docs/decisions/0153-adopt-per-stage-inference-profile-routes.md
  - docs/decisions/0171-separate-native-and-structured-reranker-transports.md
  - agency_runtime/dashboard/app.js
  - agency_runtime/dashboard/dashboard-render.js
  - tests/dashboard_ui.test.mjs
  - tests/test_release_packaging.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: dashboard
issue_id: AR-296
priority: p0
tracker_url: null
depends_on: [AR-290, AR-293, AR-295]
blocks: []
---

# AR-296: Project effective inference topology in the dashboard

## Problem

The authenticated Settings view exposes the ordered legacy provider builder and
an advanced “Judge and selector” section, but the effective named inference
profiles and per-stage/per-harness routes are visible only in raw redacted JSON.
On a configured installation this makes valid Jina embedding/reranker routes,
subscription models, and per-stage thinking levels look absent. It also leaves
the authority boundary ambiguous: Agency inference owns staffing, while the
native harness owns child spawning and execution.

## Current state

- `workforce.mode` is a staffing-assurance control; `strict` exercises the
  recruiter/critic path independently from dense recall mode.
- `workforce.dense_recall_mode` controls whether validated learned discoveries
  stay shadow-only or may be added to the typed candidate set.
- Named `inference.profiles`, global routes, and harness-scoped route/default
  profiles own current stage-model selection. The blank legacy judge field is
  therefore expected on a named-profile installation.
- `delegation.mode` still matters as optional/preferred/strongly-preferred
  guidance for an accepted plan and as bounded child-routing correction policy;
  it does not transfer spawn authority from the native host to Agency.
- The current dashboard does not project those facts as one comprehensible
  topology. Tracker creation remains pending explicit tracker authorization.

## Approach

Add a bounded, read-only “Inference roles” projection to Settings. Derive it
only from the dashboard’s already-redacted effective configuration. Show
assurance and dense-recall modes, every bounded global and harness route/default,
named profile adapter/transport/model/thinking/capability/dimensions, sanitized
endpoint identity, and credential indirection without rendering any secret.

State the authority boundary directly: inference selects staffing; the native
harness spawns and executes children. Explain the configured delegation strength
thresholds and per-parent child inference budget/concurrency/cache without
calling Agency a scheduler. Relabel the old judge section as a legacy fallback
surface and explain when it is intentionally blank.

Keep the projection fail-closed under oversized untrusted payloads. Re-audit the
packaged dashboard payload rather than bypassing its release guard.

## Dependencies

- ADR-0118 owns inference-only specialist staffing.
- ADR-0138 keeps the accepted plan separate from Codex native spawn execution.
- ADR-0153 owns named per-stage and per-harness profile resolution.
- ADR-0171 keeps Jina native reranking distinct from structured text inference.
- AR-295 requires every later dashboard payload increase to receive a new exact
  audit with narrow headroom.

## Acceptance

- [ ] Settings shows strict/balanced/fast assurance separately from recall mode.
- [ ] Global and harness-scoped routes/defaults identify the selected profiles.
- [ ] Named profiles show model, thinking level, capability, dimensions,
      sanitized endpoint, and credential indirection without secret values.
- [ ] A blank legacy judge is explained as expected when named routes own stage
      inference.
- [ ] Delegation copy says Agency selects staffing and the native harness owns
      child spawn/execution, while retaining the exact configured guidance and
      child-routing bounds.
- [ ] Oversized topology maps are withheld at explicit dashboard bounds.
- [ ] Dashboard UI, release-asset, documentation, and proportional repository
      gates pass.
- [ ] The exact candidate is installed and visually verified in the
      authenticated loopback dashboard.
- [ ] Tracker creation and linkage remain pending separate authorization.

## Verification evidence

The initial authenticated browser inspection reproduced the defect on the
installed dashboard: strict assurance could be selected and saved, but named
Codex/Claude/ZCode profiles, their thinking levels, Jina embedding/reranker
profiles, and effective global/harness routes appeared only in the raw JSON.
The configuration itself validated with only attended/cold-host degradation.

The first bounded UI implementation passes all 138 dashboard tests, including
secret-redaction, endpoint-sanitization, authority-copy, route/profile, and
oversized-map cases. The unchanged release-asset test then measured exactly
385,530 bytes and failed its prior 368 KiB ceiling. A 377 KiB ceiling is
386,048 bytes, leaving 518 bytes (0.13 percent) of audited headroom.
