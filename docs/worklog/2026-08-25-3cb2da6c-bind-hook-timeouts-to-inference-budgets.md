---
title: "Worklog detail: Bind hook timeouts to inference budgets"
status: active
category: worklog
created: 2026-08-25
updated: 2026-08-25
tags: [host-integrations, reliability, inference, timeouts]
related:
  - docs/roadmap/issue-AR-287-bind-host-hook-timeouts-to-inference-budgets.md
  - docs/roadmap/issue-AR-266-dense-hybrid-workforce-recall.md
  - docs/roadmap/handoffs/issue-AR-266.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 3cb2da6c3a0b69d36a4d8ea04248c8b68475b15c
short: 3cb2da6c
date: 2026-08-25
pr: null
related_issues:
  - docs/roadmap/issue-AR-287-bind-host-hook-timeouts-to-inference-budgets.md
  - docs/roadmap/issue-AR-266-dense-hybrid-workforce-recall.md
---

# Worklog detail: Bind hook timeouts to inference budgets

## Purpose

Prevent a valid harness-scoped inference path from outliving its generated
host bridge or Store ownership lease. The observed Hermes bridge stopped after
80 seconds even though its Agency profile permits 120 seconds per provider
call, so finalization correctly rejected the resulting unverified draft.

## Approach

Compute a static budget from the owning harness's resolved parent, recall, and
gap-hiring routes plus any reachable legacy provider fallback. Apply the
existing five-second margin and 595-second ceiling, and use the same result for
both installed host payloads and `begin_preflight_attempt` leases.

## Challenges encountered

The first repair covered parent routing but not synchronous gap hiring. Review
then exposed the same omission for unresolved hiring routes that fall back to
the legacy provider chain. Both paths received failing-before regressions and
were included without changing the host ceiling or inference policy.

## Decisions and alternatives

Timeouts resolve from static checked-in configuration only. Runtime environment
overrides or live provider probes were rejected because they would make an
installed launcher nondeterministic. Expanding only the Hermes plugin was also
rejected because its Store lease would then expire while the bridge still
owned the attempt.

## Verification

- 160 installer and preflight tests pass with warnings as errors; one unrelated
  platform test is skipped.
- The external bundle-helper monkeypatch regression passes.
- Full Ruff check and format-check, documentation validation, and
  `git diff --check` pass.
- Independent review returned GO with no Critical, High, or Medium findings.

## Follow-ups

Reinstall Agency into Hermes only, verify the generated 595-second timeout, and
run one genuinely new native Hermes turn before resuming the four-host smoke.
Tracker creation remains pending explicit authorization.
