---
title: "AR-287: Include reachable repair and fallback profile timeouts"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [host-integrations, inference, timeouts]
related:
  - docs/roadmap/issue-AR-287-bind-host-hook-timeouts-to-inference-budgets.md
  - docs/decisions/0153-adopt-per-stage-inference-profile-routes.md
  - docs/decisions/0192-route-content-invalid-completions-to-a-content-fallback-profile.md
  - docs/decisions/0216-enforce-one-preflight-inference-deadline.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: fb36048537277833a41a5189bd29621514a6d0d5
short: fb360485
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-287-bind-host-hook-timeouts-to-inference-budgets.md
---

# AR-287: Include reachable repair and fallback profile timeouts

## Purpose

The generated bridge and preflight lease shared a budget helper that omitted
the independently routed safety-repair stage and configured content fallbacks.
Both are reachable runtime paths. A slower selected profile could therefore be
clamped to an underestimated request deadline even below the host ceiling.

## Approach

Resolve each primary using the existing static harness resolver, then include
the distinct configured content fallback exactly when the runtime appends it.
Include the safety-repair route only when its repair budget is positive. Reuse
the existing longest-timeout-by-call-budget calculation; do not add calls,
change profile selection, extend the deadline reserve or raise the 595-second
ceiling. The installer never calls the environment-sensitive workforce resolver.

## Challenges encountered

Source inspection caught two fixture assumptions before review: harness defaults
precede global routes, and profile projection caps an individual timeout at
120 seconds. Written cases use explicit harness overrides and legal projected
timeouts. No test outcome is inferred from this inspection.

## Decisions and alternatives

This repairs implementation of ADR-0153, ADR-0192 and ADR-0216; it creates no
new routing, budget or deadline policy. Increasing the host ceiling or disabling
security review would change the product contract and is out of scope.

## Verification

- Scoped Ruff format: one file reformatted, two unchanged.
- Scoped Ruff check: `All checks passed!`.
- `git diff --check`: clean.
- Twenty native-installer parameter cases and two Store-lease parameter cases
  are written but **UNRUN**, per the owner's code-first test/CI deferral.
- No pytest, CI, acceptance verifier, provider, native-host or owner-state action.

## Follow-ups

Root's first independent source review of `fb360485` found no scoped finding;
this is not executed verification. Integration `14899a51` normally merges
published main plus immediate ledger `6d209d6d`, preserving both worklog
histories and leaving the reviewed runtime delta unchanged.

Documentation checkpoint `185db01a` records the canonical issue, new capsule,
portable source receipt and reciprocal governing links. Owner-authorized
tracker #756 maps the existing legacy record; original Acceptance wording and
checkboxes remain unchanged. Markdown metadata checked 1293 documents and the
worklog index was current at 2147 substantive commits before that checkpoint.

Normal PR publication remains pending. No current installed repair, live Hermes
acceptance, test pass or completed issue is claimed. Run focused regressions
and live verification only when authorized.
