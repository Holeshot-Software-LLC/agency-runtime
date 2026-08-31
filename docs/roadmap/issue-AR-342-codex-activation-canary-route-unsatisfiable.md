---
title: "AR-342: Codex activation canary route unsatisfiable after typed-coverage enrichment"
status: open
category: roadmap
created: 2026-08-31
updated: 2026-08-31
tags: [reliability, codex, canary, workforce, selection]
related:
  - docs/roadmap/issue-AR-338-verify-windows-harness-set.md
  - docs/decisions/0195-admit-role-null-codex-canary-child-lineage.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-342
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/387
depends_on: []
blocks: []
---

# AR-342: Codex activation canary route unsatisfiable after typed-coverage enrichment

## Problem

`agency install --agent codex --verify-activation` cannot produce a bound
attestation. Hook trust is green (all 8 events carry `trusted_hash`
records in `~/.codex/config.toml`; the trust inspector reports
observed=8, missing=0 once the private projection is republished), the
live canary launches, and the run still ends `canary_passed: false` with
only the generic "fresh current-profile canary reported unmet
prerequisites".

The activation canary contract
(`render_codex_activation_canary_delegation_plan`) requires the turn's
routing to be `accepted` with `selected_ids == ["code-reviewer"]`
exactly. Selection no longer produces that route for the frozen canary
work unit.

## Measured 2026-08-31 (runtime f91541c3, roster fix #382 live)

- `agency route` on the exact canary work unit ("Identify the primary
  behavioral regression risk of replacing return value with return
  value.strip() ...") returns `status=abstained`, `selected_ids=[]`, top
  candidates `test-results-analyzer, minimal-change-engineer, historian,
  investment-researcher, legal-document-review` — `code-reviewer` absent.
- AR-338 recorded a passing codex live canary earlier the same day,
  before #382 enriched 11 `review-report`-task-typed contracts (four
  finance snapshot reviewers among them) with `review-report` artifact
  and `review` lifecycle coverage. Those contracts now appear atop ranked
  lists for unrelated review-flavored units, so selection drift is the
  suspected mechanism; local judge-stack flakiness
  (`provider_no_valid_response` retries, routing p95 far over budget) may
  contribute nondeterminism.

## Secondary defect: no failure observability

The failed canary leaves nothing to inspect: `host_canary_attestations`
is empty, `~/.agency-runtime/manual-live/codex/` is empty, and the CLI
prints only the circular unmet-prerequisites sentence with a hook-trust
remediation that no longer applies. The blocked route (or whatever
prerequisite actually failed) should be named in the report.

## Direction

Either the canary contract must tolerate the roster's real selection for
its work unit (or pin its route deterministically, as the canary already
pins delivery), or selection must be corrected so a pure code-review unit
reliably ranks and selects `code-reviewer`. In both cases the canary
report must surface the failing prerequisite verbatim.

## Acceptance

- `agency install --agent codex --verify-activation` produces a bound
  attestation on this machine, or fails naming the exact unmet
  prerequisite (e.g. the rejected route) in its report.
- `agency route` on the canary work unit yields an accepted route
  consistent with the canary contract.
