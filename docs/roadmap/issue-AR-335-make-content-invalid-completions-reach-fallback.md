---
title: "AR-335: Make content-invalid completions reach the different-provider fallback"
status: open
category: roadmap
created: 2026-08-29
updated: 2026-08-29
tags: [bug, reliability, workforce, inference, litellm, fallback]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/decisions/0185-enforce-child-judge-schema-at-litellm-alias.md
  - docs/decisions/0181-use-litellm-aliases-as-host-inference-control-plane.md
  - agency_runtime/core/structured_provider.py
  - agency_runtime/core/workforce/inference.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-335
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/350
depends_on: []
blocks: []
---

# AR-335: Make content-invalid completions reach the different-provider fallback

## Problem

A primary model returning HTTP 200 with content-invalid output defeats the
entire fallback architecture: LiteLLM sees a successful completion, so the
order-2 different-provider deployment never fires; the structured invoker
returns None (`provider_no_valid_response`) or the stage parser rejects the
contract; the zero-retry doctrine ends the stage; and the turn dies at
preflight. The live-proven GLM-5 Turbo planner fallback is unreachable for
exactly the failure class it was qualified against.

## Current state

- 2026-08-29 ordinary-turn matrix: all four hosts failed preflight.
  Planner: GPT-5.5-low emitted a structurally perfect plan terminated by a
  stray `]}` (specimen retained at
  `~/.agency-runtime/evidence/ar297-live-harness-20260829/diag-failing-response-1.txt`,
  sha256 `6b742a20…`) on the claude (twice), openclaw, and codex ordinary
  turns plus one instrumented in-process preflight. The identical alias
  returned valid plans in the same hour for fixture, `agency route`, and
  canary calls, so the emission is intermittent.
- This is the same extra-brace defect class that previously disqualified
  GPT-5.5-high; swapping primaries within the family is whack-a-mole.
- Recruiter: `provider_response_contract_invalid` twice in a row (primary
  plus semantic-repair retry) on the hermes ordinary turn and both
  2026-08-29T19:35/19:36Z codex canary parent turns; one `agency route`
  probe ended `no_safe_sufficient_team` with `inference-declared-gap`.
- Claude and codex `exec` turns proceeded natively after preflight failure
  (fail-open); interactive strict paths refuse at Stop, which blocks live
  operator turns while the defect stands. Agency master control is OFF
  globally pending this repair.

## Approach

ADR-0185 already enforces the child-judge response schema at the LiteLLM
alias so malformed content becomes a provider failure and LiteLLM's own
fallback chain fires. Extend alias-level schema enforcement to the planner
and recruiter aliases, following that precedent, without adding retries or
weakening strict assurance. Evaluate as alternatives: a second client-side
ProviderEntry per stage pinned to the fallback deployment, or bounded content
repair (previously rejected by decision). The selected mechanism requires an
owner decision and a decision record.

## Dependencies

None. Coordinate with the AR-297 latency exception: a fallback that fires
more often changes observed planner latency distribution.

## Acceptance

- [ ] A content-invalid primary completion demonstrably reaches the order-2
      different-provider deployment on the planner alias.
- [ ] The recruiter stage has an equivalent escape or a recorded decision
      declining one.
- [ ] A forced malformed-content proof is retained with exact receipts.
- [ ] All four ordinary host turns pass preflight against the promoted route.
