---
title: "Worklog detail: Preserve OpenClaw refreshed headers through truncation"
status: active
category: worklog
created: 2026-08-24
updated: 2026-08-24
tags: [openclaw, headers, middleware, truncation, finalization]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md
  - docs/decisions/0168-refresh-openclaw-headers-through-awaited-tool-results.md
supersedes: []
superseded_by: null
type: worklog
commit: d7187e809523503b5d8162d3334afc497fe1d3f6
short: d7187e80
date: 2026-08-24
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-279-deliver-openclaw-finalizer-results.md
---

# Worklog detail: Preserve OpenClaw refreshed headers through truncation

## Purpose

Keep OpenClaw's exact post-tool Store snapshot visible to the native parent
when a large native tool result enters the host's proportional recovery
projection, without changing OpenClaw, model routes, or finalization policy.

## Approach

The OpenClaw-only middleware now prefixes the refreshed Agency context into the
first native text block. It clones and splits that result at OpenClaw's
UTF-16-safe 100,000-character text limit, preserves valid native text/image
order and details, and refuses a replacement if the host's 200-block ceiling
cannot admit the split. The existing finalization gate remains fail-closed.

This places the complete updated contract in the dominant block that receives
the live projection budget. The observed 100,000-character result validates as
two blocks, preserves all native text, and retains all five updated header
lines through the configured 4,000-character, zero-minimum projection.

## Challenges encountered

The original separate 878-character header received too little proportional
budget beside the 100,000-character native read. The expected-red failed at
exit 236. Independent review rejected an initial same-block candidate because
it exceeded OpenClaw's post-middleware text limit. A broad test invocation also
inherited umask `0002`, making the shared offline config directory untrusted;
the documented process-local `0077` run passed.

## Decisions and alternatives

ADR-0168 continues to own the awaited middleware decision. The repair does not
rewrite a final, add a second model pass, send directly, trim native evidence,
or modify host/model configuration. Separate short context blocks remain
unsafe under recovery `minKeepChars=0`; silent tail truncation at the 200-block
edge was rejected in favor of an unchanged-result, fail-closed outcome.

## Verification

- Focused OpenClaw security, installer, adapter-parity, and adapter suites: 251 passed, 1 intentional skip.
- Full repository Ruff check and format check: passed.
- Documentation metadata, policy availability, worklog, and verification checks: passed.
- `git diff --check`: passed.
- Independent installed-validator and recovery-projection review: no blockers.

## Follow-ups

Install Agency Runtime only into natively stopped OpenClaw from the clean
checkpoint, restart OpenClaw natively, and collect fresh status, skill-load,
substantive LiteLLM, header, Store, and Telegram evidence. Continue Hermes only
after OpenClaw's host-scoped acceptance set passes.
