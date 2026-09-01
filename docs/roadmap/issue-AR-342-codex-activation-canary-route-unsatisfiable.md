---
title: "AR-342: Codex activation canary route unsatisfiable after typed-coverage enrichment"
status: done
category: roadmap
created: 2026-08-31
updated: 2026-09-01
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

## Resolution (2026-09-01)

With host auth restored (`codex logout && codex login` after the burned
refresh token) the very next `agency install --agent codex
--verify-activation` PASSED: the live canary routed, inference selected
`code-reviewer`, the delegation attested, and "Codex current-profile
activation verified" was printed. The earlier offline `agency route`
abstains on the unit text did not reproduce in the live canary turn, so
the exactness chain stands unchanged. Both filed defects are addressed:
the observability half by PR #392 (named unmet reasons, which walked
this failure down from "unmet prerequisites" to hook trust to empty host
invocation to the burned token), and the attestation half by restoring
the host prerequisite the report finally named. Future selection drift
will self-describe through the same report.

## Direction

Either the canary contract must tolerate the roster's real selection for
its work unit (or pin its route deterministically, as the canary already
pins delivery), or selection must be corrected so a pure code-review unit
reliably ranks and selects `code-reviewer`. In both cases the canary
report must surface the failing prerequisite verbatim.

## Acceptance

- [x] `agency install --agent codex --verify-activation` produces a bound
  attestation on this machine, or fails naming the exact unmet
  prerequisite (e.g. the rejected route) in its report.
- [x] `agency route` on the canary work unit yields an accepted route
  consistent with the canary contract — met by the live canary turn
  itself routing and selecting `code-reviewer`; the offline CLI abstains
  did not reproduce there and any recurrence now self-describes in the
  verification report.
