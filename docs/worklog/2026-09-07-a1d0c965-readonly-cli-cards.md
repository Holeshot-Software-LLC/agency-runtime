---
title: "Explicit cards for read-only roster, policy, and config"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [cli, presentation, parity]
related:
  - docs/roadmap/issue-AR-251-cli-presentation-richness.md
  - docs/decisions/0154-plain-text-cli-cards-over-rich-dependency.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: a1d0c965edc8bfb503646dbe318462740911c3d0
short: a1d0c965
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-251-cli-presentation-richness.md
---

# Worklog detail: feat(cli): add explicit cards to read-only roster policy and config

## Purpose

Implement the remaining requested card presentation on five bounded read-only
surfaces: roster list, policy, config show/get, and config provider list.

## Approach

Reuse the existing plain-text renderer. Preserve enabled-roster filtering,
policy validation and exit codes, current config redaction and explicit `--raw`,
and the provider list's direct-key omission. Split config show's already-redacted
YAML projection into top-level cards, not raw configuration objects. Bound each
detail section with a visible truncation note and complete-output alternative.

All new flags default false, preserving these commands' existing TTY/plain
output under the owner's compatibility scope. Existing hiring/workforce TTY
defaults are unchanged. Existing policy/provider JSON branches precede cards
and retain their original serialization. No new JSON mode or mutation path.

## Challenges encountered

The parser uses one whole-manifest golden digest. Regenerated that artifact
from its contract-building helpers, without running test functions or pytest:
`281fdc085e51900d93fef7210e104920314831cd0d59e0c59d134246b1f73f3e`.
Current AR-410/411 source and faithful ledgers were fast-forwarded through
`c050be37` before this source commit, preserving all owned changes.

## Decisions and alternatives

No dependency, color layer, live-watch client, configuration wizard, mutation
command, roster-diff creation change, or authenticated model discovery was added.
The explicit opt-in scope follows the owner's request to preserve current default
output; it does not change existing automatic card consumers. Broader parity
remains AR-236, and upgrade UI scope remains AR-250.

## Verification

Source inspection, formatting, mechanical parser-manifest regeneration, and
`git diff --check` only. New focused regressions are written but **unrun**;
existing tests, CI, acceptance, installed CLI execution, native harnesses, and
provider calls are deferred at the owner's explicit direction. No passing-test
or installed-delivery claim is made. AR-251 remains verification pending.

## Follow-ups

The immediately following canonical/capsule update records the frozen source
and this ledger. Parent coordinates review/publication and any later authorized
verification. Do not close AR-251 or claim acceptance from source inspection.
