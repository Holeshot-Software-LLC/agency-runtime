---
title: "AR-287: Bind host hook timeouts to inference budgets"
status: in_progress
category: roadmap
created: 2026-08-25
updated: 2026-08-25
tags: [host-integrations, reliability, inference, timeouts, evidence]
related:
  - docs/roadmap/issue-AR-266-dense-hybrid-workforce-recall.md
  - docs/roadmap/handoffs/issue-AR-266.md
  - docs/roadmap/reference-workforce-inference-stages.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-287
priority: p0
tracker_url: null
depends_on: [AR-266]
blocks: []
---

# AR-287: Bind host hook timeouts to inference budgets

## Problem

Generated host bridges and preflight Store leases used a host-agnostic legacy
provider timeout. Hermes therefore received an 80-second bridge and lease even
though its harness-scoped Agency profile permits 120 seconds per call. A fresh
Hermes turn exhausted the bridge timeout, continued without verified preflight
context, and was correctly blocked by finalization instead of returning an
unverified response.

Updating only the generated bridge would be unsafe. If its process outlived the
Store lease, another same-trace caller could recover an attempt that the first
process still owned.

## Current state

- The original regression proves Hermes rendered 80 seconds instead of the
  required capped 595 seconds. A separate regression proves `run_preflight`
  also allocated an 80-second lease.
- The implementation computes one static budget per owning harness. It covers
  the mode-specific parent workforce budget, optional embedding and reranker
  calls, and synchronous gap-hiring calls, then applies the unchanged
  595-second host ceiling and five-second margin contract.
- Bundle generation and `run_preflight` now call the same host-aware helper.
  Environment overrides and live-provider probes do not influence installed
  timeout values.
- 160 focused installer and preflight tests pass with warnings as errors. A
  fresh Hermes install and native turn remain pending.
- Independent review returned GO with no Critical, High, or Medium findings.
- Tracker creation is pending explicit authorization.

## Approach

Resolve the exact planner, recruiter, strict critic, hiring, hiring critic, and
hiring security-review routes using normal harness precedence. Multiply the
longest reachable profile timeout by each bounded call budget. Resolve recall
only through its explicit capability routes and add the embedding and reranker
timeouts when both are active. Keep the legacy provider-chain calculation as a
floor and fund it when an unresolved hiring route can fall back, then apply the
existing host cap.

Use the resulting value both when rendering a host bundle and when beginning
the corresponding preflight attempt lease. Preserve harness isolation: one
host's profile must not expand another host or a host with no matching profile.

## Dependencies

- AR-266 supplies the separate bounded embedding and reranker calls.
- Host profiles and explicit routes must already validate under the checked-in
  configuration schema.
- OpenClaw's native-child-specific helper remains a separate lower bound; the
  overall host hook takes the maximum applicable bounded budget.
- The 595-second host ceiling remains authoritative. Configurations whose
  theoretical worst case exceeds it receive the ceiling, not an unbounded
  launcher.
- Tracker creation requires separate authorization.

## Acceptance

- [x] A failing-before regression preserves the observed Hermes 80-second
      under-budget.
- [x] Host bundle timeouts use only statically reachable profiles for the
      owning harness.
- [x] Parent workforce, explicit dense recall, and synchronous gap-hiring call
      budgets contribute to the bounded hook timeout.
- [x] The Store preflight lease receives the exact same host-aware value as the
      generated bridge.
- [x] Inverse OpenClaw/Hermes tests prove cross-host isolation, and a host with
      no matching profile keeps its independent legacy budget.
- [x] Focused installer and preflight tests pass with warnings as errors.
- [ ] Agency is reinstalled into Hermes only and the generated plugin records
      the capped 595-second timeout without changing Hermes native config.
- [ ] One genuinely new Hermes turn returns a Store-backed Agency result after
      the original timeout failure is preserved.
- [ ] Tracker creation and linkage remain pending separate authorization.
