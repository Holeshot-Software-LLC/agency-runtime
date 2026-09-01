---
title: "AR-346: Hermes fail-open turns replace the host's answer with the finalization block message"
status: open
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [hermes, finalization, fail-open, rule-8, reliability]
related:
  - docs/roadmap/issue-AR-344-codex-fail-open-stop-terminal-exit.md
  - docs/roadmap/issue-AR-345-release-verification-matcher-rejects-natural-plans.md
  - docs/roadmap/issue-AR-341-deliver-capsules-to-hermes-interactive-sessions.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-346
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/403
depends_on: []
blocks: []
---

# AR-346: Hermes fail-open turns replace the host's answer with the finalization block message

## Problem

When a hermes turn's preflight fails open (`workforce_inference_failed`
/ `inference_invalid`), the turn still runs, but at output time the
bridge's `_transform_output`
(`agency_runtime/adapters/hermes/bridge.py:279-316`) evaluates the
completion policy against a turn that Agency itself failed, gets a
rejection (the policy demands header/staffing evidence the failed
preflight never produced), and **replaces the model's entire answer**
with:

    Agency Runtime blocked an unverified draft because turn-scoped
    finalization did not accept it. Restore correlation and evidence,
    then start a new turn.

This is the same lifecycle-vs-bound-response conflation as AR-344, one
step worse: codex fail-open turns at least display the answer before
mis-terminating; hermes withholds the user's answer entirely. Rule 8
("Agency being unavailable is not a finding about the response" — the
exact reasoning already written into the bridge's own unavailability
comment at `bridge.py:323-329` and into `_publish_unverified` in
`adapters/hooks.py`) requires pass-through when the missing evidence is
missing because Agency failed, not because the host misbehaved.

## Measured 2026-09-01 (runtime e5e2e193, hermes 0.21.0, cloud model alias-hermes-chat)

Session `20260901_100009_f7574e` (interactive openclaw-operations
session): turns 776 (14:00:40Z) and 777 (14:12:21Z) both closed
`preflight_failed` with `workforce_inference_failed
["inference_invalid"]` receipts — the AR-345 planner signature
(`plan_missing_release_verification` across primary and
content-fallback planner models) — and the user saw the block message
in place of the drafted answer. No `finalization_events` row was
committed for either turn (`_terminalize_policy_rejection` could not
commit an authoritative rejection), yet the replacement was returned
anyway: the withhold is unconditional on the policy saying anything
but "accept" (`bridge.py:308-316`), even when the rejection could not
be persisted as terminal evidence.

Distinct from AR-341 (closed): capsule delivery and finalization
correlation work on staffed hermes turns — same session, turn 685
(01:33Z) staffed, finalized, and accepted normally.

## Acceptance

- [ ] A hermes turn whose run is `preflight_failed` (or otherwise
      fail-open with no bound accepted response) passes the host's
      draft through unchanged, per Rule 8, while still recording the
      rejection diagnostics.
- [ ] An evaluated policy rejection on a *staffed* turn still withholds
      exactly as today (the block replacement is reserved for turns
      Agency actually verified).
- [ ] Regression coverage for the hermes fail-open transform path.
