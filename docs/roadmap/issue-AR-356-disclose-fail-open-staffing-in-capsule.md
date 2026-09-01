---
title: "AR-356: Disclose fail-open staffing honestly in the turn capsule"
status: open
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [preflight, capsule, fail-open, honesty]
related:
  - docs/roadmap/issue-AR-353-intermittent-staffing-verdict-window-linux.md
  - docs/roadmap/issue-AR-355-working-agreements-resident-manager.md
supersedes: []
superseded_by: null
type: issue
epic: product
issue_id: AR-356
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/426
depends_on: []
blocks: []
---

# AR-356: Disclose fail-open staffing honestly in the turn capsule

## Problem

When preflight fails open, the parent model sees nothing: the failure
receipt lands in the store and the turn runs Agency-blind with the
plain steward frame. The model has no way to know it is unstaffed, so
it can imply staffing it does not have, and the fail-open finalization
family (AR-344/AR-346) had room to grow precisely because the turn's
own context never said what happened. With the AR-353 intermittent
window still live, fail-open turns keep occurring.

## Current state

Fail-open turns deliver the steward kernel and (now) the operator
policy with no staffing information at all; the honest zero-specialist
result exists internally (`no_specialist_fail_open`) but is never
rendered.

## Approach

On fail-open turns only, append one bounded line to the delivered
capsule, e.g. "Staffing failed this turn (`<reason class>`); you are
unstaffed, proceeding under the steward alone." Source the reason
class from the recorded preflight failure receipt; never include
provider internals. Zero cost on staffed turns.

Scope note (2026-09-01, owner-approved lift): the same honesty rule
extends to specialist tooling — a card's requested capability is not
proof its tools were available (cards already say "availability must be
proven before use"). When a loaded specialist's required tool is
absent, the turn should disclose the degradation rather than let the
model imply capability it lacks (principle stated independently in
ECC's gan-evaluator: report the degraded mode instead of silently
scoring the requested one).

## Dependencies

- None; complements AR-353's measurement.

## Acceptance

- [ ] A fail-open turn's capsule states that staffing failed, with the
      bounded reason class, on every host.
- [ ] Staffed turns are byte-identical to today.
- [ ] The line is covered by regression tests and its wording is part
      of the recipe contract (hash-stable).
