---
title: "AR-166: Keep dashboard disclosure and correlation truthful"
status: in_progress
category: roadmap
created: 2026-07-27
updated: 2026-09-07
tags: [dashboard, security, privacy, observability, ui]
related:
  - docs/roadmap/acceptance/issue-AR-166.md
  - docs/roadmap/acceptance/evidence/AR-166-dashboard-authority-20260907.md
  - docs/decisions/0229-reconcile-dashboard-disclosure-with-owner-authority.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/roadmap/issue-AR-298-expose-complete-workforce-prompts.md
  - docs/decisions/0027-authoritative-runtime-evidence-traces.md
  - docs/decisions/0029-secure-local-dashboard-and-bounded-observability.md
  - docs/decisions/0096-require-operator-presence-for-persistent-controls.md
  - docs/roadmap/issue-AR-138-coherent-observable-dashboard-ui.md
  - docs/roadmap/issue-AR-149-fresh-dashboard-request-ids.md
  - docs/roadmap/issue-AR-153-complete-worker-detail-evidence.md
  - agency_runtime/dashboard/app.js
  - agency_runtime/dashboard/dashboard-actions.js
  - agency_runtime/dashboard/dashboard-config.js
  - agency_runtime/dashboard/dashboard-core.js
  - agency_runtime/dashboard/dashboard-live.js
  - agency_runtime/dashboard/dashboard-render.js
  - tests/dashboard_ui.test.mjs
supersedes: []
superseded_by: null
type: issue
epic: dashboard
issue_id: AR-166
priority: p2
tracker_url: null
depends_on: []
blocks: [AR-170, AR-171, AR-173]
---

# AR-166: Keep dashboard disclosure and correlation truthful

## Problem

Three low-severity presentation gaps remained after the production dashboard
trace. Provider-option rendering could re-enable one selector after the settings
form became read-only. Failed requests retained a safe request ID internally but
most user-visible notices omitted it, and a successful Route Lab receipt did not
show it. Finally, the global `Metadata only` chip did not say that it described
runtime observation capture while owner-only worker detail can display a bounded
compiled governed specialist definition.

None of these gaps bypassed dashboard authentication or mutation denial. They
could nevertheless mislead an operator about available authority, complicate
support correlation, or make the privacy boundary appear broader than it is.

## Current state

September 7 review found a stale selector restriction after ADR-0117 restored
owner controls. Two red tests reproduce disabled=true for valid providers.
The nonempty-list renderer now enables selection and preserves the chosen
provider. Empty/unparseable/non-array lists remain disabled; keys stay redacted.
All 189 UI and 235 backend/owner cases pass, with 1085/three existing skips in
the fresh named spine. ADR-0229 explicitly reconciles only criterion 1 before
isolated review. Eighteen source-served browser checks pass for the selector.
Criterion 2 also exposed a null-JSON HTTP error throwing TypeError before
retaining status/request identity. A null-safe error lookup and 401/403/503
regression cover it. Latest UI 190 and final source-served browser 20 checks
pass, including null-401 terminal identity. Five current criteria satisfy at
4a244776; criterion 2 needs a citation-only recheck of existing reconciliation
message forwarding. All first verdicts remain at bc28bf66; no source change.

Client request IDs are canonical UUIDv4 values;
HTTP and transport failures append only a validated identifier to their inert
text notice, and hostile response identifiers fall back to the browser's safe
request identity. Successful Route Lab receipts show the validated request ID.

The privacy chip now says `Runtime metadata only` or
`Redacted runtime content`, matching the `observability.capture_content`
runtime-observation setting. AR-298 replaced the historical 8192-character
preview with a Store-backed complete bounded definition (at most 262144
characters in dashboard detail). Provenance and stored-definition/not-runtime-
delivery labeling keep it separate from runtime capture. This slice changes no
backend, broker scope, retention or content-capture authority.

## Approach

Centralize bounded request-ID validation and notice formatting in the dashboard
core, then reuse it for API errors and fixed terminal notices. Render a Route Lab
request ID only after the same validation. Apply ADR-0117 owner authority in
the provider-option renderer, with empty/invalid-list disabling and key redaction.
Make runtime-capture wording explicit both during bootstrap and after config or
overview refresh, and disclose the owner-only compiled-definition distinction at
the preview.

## Dependencies

ADR-0027 requires request-level traceability. ADR-0029 governs local dashboard
privacy and runtime observation capture. ADR-0117 restores owner controls while
preserving model-facing broker restrictions; the old ADR-0096 rule is superseded. AR-138, AR-149, and AR-153 own the broader coherent
UI, request identity, and bounded worker-detail contracts respectively.

The governed pre-tracker exemption applies while unmapped; no duplicate tracker
or outward tracker state change is needed.

## Acceptance

- [ ] Owner-authorized provider choices remain usable after rendering; empty,
  non-array or unparseable provider lists stay disabled, stored keys are not
  reflected, and broker write scope remains unchanged.
- [ ] HTTP, transport, authentication, and reconciliation failures expose a safe
  request ID when one exists without reflecting an invalid identifier.
- [ ] Successful Route Lab receipts display their validated request ID; malformed
  identifiers remain absent from rendered evidence.
- [ ] The privacy chip explicitly describes runtime observation capture.
- [ ] The bounded owner-only compiled specialist definition is labeled separately
  from runtime capture without changing authentication or broker scope.
- [ ] Focused dashboard UI, documentation, formatting, and diff checks pass.

## Requirement reconciliation

Original criterion 1: "Provider rendering cannot re-enable the provider-secret
selector or any other persistent dashboard control." ADR-0229 explicitly
replaces that superseded requirement under ADR-0117. Criteria 2–6 remain
unchanged; all six await isolated verification.

## Historical implementation evidence

The complete dashboard UI suite passes 102 tests, including provider re-render,
hostile request-ID fallback, terminal authentication notice, successful Route
Lab receipt, runtime-capture wording, and owner-preview disclosure regressions.
Ruff check and format validation pass across 577 files. Metadata validation and
documentation verification pass across 424 Markdown files, the policy and
worklog generated-state checks pass, and `git diff --check` passes.
Installed-browser and full release validation are not claimed by this bounded
slice.
