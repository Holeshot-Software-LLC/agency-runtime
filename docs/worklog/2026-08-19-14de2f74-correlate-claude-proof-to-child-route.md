---
title: "Worklog detail: correlate Claude proof to the child route"
status: active
category: worklog
created: 2026-08-19
updated: 2026-08-19
tags: [canary, claude, inference, child-delivery, provider, evidence]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0160-pin-child-judge-providers-per-canary-harness.md
  - agency_runtime/core/canary_proof.py
supersedes: []
superseded_by: null
type: worklog
commit: 14de2f74659eb87721daf433c927691a69c27aed
short: 14de2f74
date: 2026-08-19
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/298
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
---

# Worklog detail: correlate Claude proof to the child route

## Purpose

The first installed Option-A delivery exposed a proof-evaluator defect after
the child judge successfully staffed the control. The Claude-written artifact
carried `minimal-change-engineer`, exactly matching its native-child decision,
but the validator compared it with the distinct parent `code-reviewer` route.
The same report omitted the actual answering provider because it looked for
provider attempts on the artifact projection rather than the Store route.

## Approach

Claude evidence collection now reads the exact native-child route named by the
collector-sealed artifact capability. Proof validation revalidates that route,
compares its ordered cards and immutable decision/binding identities with the
host artifact, and checks the parent route independently. Requested and actual
answering providers remain separate; a configured pin mismatch fails proof.

## Challenges encountered

The pre-existing integration fixture used one text as both parent prompt and
child assignment. That made the child route look like the parent route and hid
the invalid comparison. The repaired fixture records a `code-reviewer` parent
route and a different child assignment whose judge selects
`minimal-change-engineer`, matching the live two-boundary topology.

## Decisions and alternatives

The fix does not weaken host authority or treat Store state as delivery. The
one-use collector capability remains the only way to introduce a verified
host artifact; the Store route only supplies the separately inference-owned
selection and provider receipt that artifact must match. Changing the control
unit, accepting the parent team as the child team, and adding a capture surface
were rejected.

## Verification

- Focused two-boundary Claude regression: 1 passed.
- Host canary, child delivery, provider pin, cohesion, and coverage slice:
  134 passed with warnings treated as errors.
- Ruff check and format check passed on both changed files.
- The installed pre-fix draw already produced one immutable Claude delivery
  verification row; no matrix cell was promoted from that provisional run.

## Follow-ups

- Reinstall this source checkpoint into the authorized three host profiles.
- Collect one Claude report that attests the exact child route and separately
  names requested and answering `codex-subscription`.
- Complete the attended installed ZCode Agent attribution call; keep Codex
  native-child proof explicitly waiting on the upstream collaboration surface.
