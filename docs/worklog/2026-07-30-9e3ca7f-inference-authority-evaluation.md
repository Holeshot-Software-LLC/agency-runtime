---
title: "Worklog detail: preserve inference authority through evaluation"
status: active
category: worklog
created: 2026-07-30
updated: 2026-07-30
tags: [routing, inference, evaluation, mutation]
related:
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/decisions/0121-gate-deterministic-recall-without-selection-authority.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 9e3ca7f
short: 9e3ca7f
date: 2026-07-30
pr: null
related_issues:
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
---

# Worklog detail: preserve inference authority through evaluation

## Purpose

Close the remaining path where a terminal inference failure could acquire a
deterministically chosen policy companion, and make the offline routing gate
measure the production shortlist without claiming it selected a team.

## Approach

The route merge now treats `inference_unavailable` and `inference_invalid` as
terminal for every specialist identity projection while preserving policy
action classification for diagnosis. Routing report/corpus v1.4 evaluates the
affirmative-intent candidate-union path under the explicit
`deterministic_candidate_recall_only` authority. The full-pipeline cache
benchmark uses a labelled synthetic inference-shaped fixture under the exact
production cache key instead of relying on an offline fallback selection.

ADR-0121 supersedes ADR-0030's obsolete selection interpretation while carrying
forward policy, delegation, scale, startup, and performance gates. README,
troubleshooting, release, roadmap, and changelog text now describe the same
boundary. The commit also retains the preceding fast-spine repairs for the
closed-world autonomous install shape and inference-authored delegation test
fixture.

## Challenges encountered

The first corrected routing gate exposed that its cache benchmark also depended
on a no-provider selection. The benchmark was repaired at that first failure
instead of weakening the inference-only production contract or waiving the
gate.

## Decisions and alternatives

The durable authority and metric decisions are recorded in
[ADR-0121](../decisions/0121-gate-deterministic-recall-without-selection-authority.md).
Restoring deterministic fallback teams, calling shortlist candidates
recommendations, and dropping the offline regression gate were rejected.

## Verification

- 72 focused routing, evaluation, and selector-coverage tests passed warning
  strict.
- The standalone v1.4 routing evaluation passed every checked-in gate across
  37 routing, 30 policy, and 22 delegation cases.
- The new terminal-failure mutation was killed in an owner-private copy with
  the source checkout unchanged.
- Focused Ruff, format, metadata, policy-availability, worklog-currentness,
  documentation, and whitespace checks passed; 566 Markdown files validated.

## Follow-ups

- Complete the 38-mutation decision-conformance run and named fast spine under
  [AR-204](../roadmap/issue-AR-204-reconcile-readme-story-contract.md).
- Merge, install the exact build, run one supported-bypass Codex product trial,
  and generate the local evidence page under AR-204.
