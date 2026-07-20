---
title: "AR-79: Prove exact Agency headers in the installed isolated Codex canary"
status: done
category: roadmap
created: 2026-07-17
updated: 2026-07-20
tags: [codex, canary, headers, evidence, installation]
related:
  - docs/decisions/0076-bind-isolated-canaries-to-explicit-agency-modes.md
  - docs/decisions/0036-capability-bound-host-canary-attestations.md
  - docs/decisions/0045-turn-scoped-specialist-activation.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-79
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/84"
depends_on: [AR-25, AR-27, AR-43, AR-90]
blocks: [AR-88]
---

# AR-79: Prove exact Agency headers in the installed isolated Codex canary

## Problem

The isolated Codex activation recipe required a six-line Agency header but did
not name the six exact labels. A live canary could therefore prove correlated
routing and terminal finalization while the final response still omitted the
required evidence header.

## Current state

The isolated activation context now supplies the exact field labels, the replay
policy version invalidates stale recipes, and an installed Codex 0.144.3 canary
has persisted a passing header-valid attestation. PR #114 passed the complete
hosted, artifact, coverage, and security matrix. The exact merged wheel then
passed a fresh installed Codex canary with all six labels and correlated route
and finalization evidence.

## Approach

Keep header rendering in the host while making the activation contract
unambiguous. Require the canary to validate all six labels in addition to exit
status, correlation, route evidence, and finalization evidence. Preserve the
boundary between an isolated-profile canary and real-profile hook trust.

## Dependencies

AR-25 owns turn-scoped evidence, AR-27 owns authoritative finalization, and
AR-43 owns installed-module isolation.

## Acceptance

- [x] Isolated activation names the exact six Agency header labels.
- [x] Replay-policy versions invalidate older ambiguous activation recipes.
- [x] An installed Codex canary proves a complete correlated header.
- [x] The attestation remains explicit about isolated-profile scope.
- [x] Full branch, artifact, and merged-install gates pass.
