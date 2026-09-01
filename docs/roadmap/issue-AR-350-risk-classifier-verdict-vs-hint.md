---
title: "AR-350: classify_contractor_risk still acts as a binding verdict, not a hint"
status: open
category: roadmap
created: 2026-09-01
updated: 2026-09-01
tags: [workforce, hiring, governance, risk]
related:
  - docs/roadmap/issue-AR-235-autonomous-gap-hiring-with-isolated-security-review.md
  - docs/roadmap/issue-AR-238-isolated-security-review-with-bounded-repair.md
  - docs/roadmap/issue-AR-347-reconcile-tracker-parity-backlog.md
supersedes: []
superseded_by: null
type: issue
epic: reliability
issue_id: AR-350
priority: p3
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/408
depends_on: []
blocks: []
---

# AR-350: classify_contractor_risk still acts as a binding verdict, not a hint

## Problem

AR-235 specified the deterministic marker classifier as "a first-pass
filter ... with explicit 'hint, not verdict' semantics", and AR-238's
narrower slice kept it "as a first-pass hint source". In current code
the classifier is still a binding gate: `classify_contractor_risk`
(`agency_runtime/core/workforce/hiring_contract.py:612`, called at
`:778`) sets `human_approval_required` via
`OWNER_APPROVAL_RISK_CLASSES` (`:790`), which
`core/workforce/hiring.py:2172-2178` converts to `risk_tier="high"` and
`:2226-2228` routes to `status="pending_approval"` — a deterministic
verdict the isolated security reviewer cannot override in either
direction. The "hint" framing exists only as a code comment
(`hiring.py:2109-2113`). The marker list has also grown to 9 classes
(`exfiltration` added) while the docs still say 8.

## Current state

Found by the AR-347 per-criterion audit of AR-235 (2026-09-01). This
may be a deliberate safety posture (owner-approval classes stay
deterministic); the defect today is that the recorded contract and the
code disagree, and AR-238's claim that `human_approval_required`
is `False` holds only for non-owner-approval classes.

## Approach

Owner decision first: either bless the current behavior by rewording
AR-235/AR-238's contract ("markers are hints for the reviewer, except
owner-approval classes, which deterministically require human
approval") or demote the classifier to reviewer input only. Then align
docs, comments, and the marker-count references with the decision.

## Dependencies

- Owner decision on the owner-approval class posture.

## Acceptance

- [ ] The recorded contract and the code agree on the classifier's
      authority, in whichever direction the owner decides.
- [ ] Marker-class counts in docs match the code (currently 9).
- [ ] A focused test pins the decided authority boundary.
