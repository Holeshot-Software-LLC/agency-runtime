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

## Progress (2026-09-01) — observability fixed; live blocker is host auth

The secondary defect is resolved (PR #392, deployed): the verification
report now passes the child report's real unmet reasons through as
bounded printable ASCII instead of collapsing them to one generic
sentence. Live-proven immediately — successive runs named their actual
blockers layer by layer: first ``route_not_found`` with
``codex_hook_trust_not_ready`` (hooks restaged by the deploy, trust
stale), then after trust re-acceptance ``host invocation did not
complete successfully`` / ``did not return a nonempty response``.

That last reason traces to genuine host auth breakage, not Agency:
``codex exec`` fails with "Your access token could not be refreshed
because your refresh token was already used. Please log out and sign in
again" (401 on the responses websocket) while ``codex login status``
still claims a valid ChatGPT login. Every canary invocation therefore
returns empty. Owner action required: ``codex logout && codex login``,
then rerun ``agency install --agent codex --verify-activation``.

The primary question — whether routing reliably selects
``code-reviewer`` for the canary work unit — remains open and can only
be re-measured against a live canary once host auth is restored;
offline ``agency route`` runs on the unit text still fail
(``inference_invalid``, finance-heavy recruiter rankings on some runs,
critic rejection on others), so the selection investigation stands.

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
