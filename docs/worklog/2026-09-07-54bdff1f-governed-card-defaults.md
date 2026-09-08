---
title: "Align read-only cards with governed TTY defaults"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [cli, presentation, review]
related:
  - docs/roadmap/issue-AR-251-cli-presentation-richness.md
  - docs/decisions/0154-plain-text-cli-cards-over-rich-dependency.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 54bdff1f2ac3044bb0931ca4202a2320059a6f47
short: 54bdff1f
date: 2026-09-07
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/753
related_issues:
  - docs/roadmap/issue-AR-251-cli-presentation-richness.md
---

# Worklog detail: fix(cli): follow governed TTY defaults for read-only cards

## Purpose

Correct the initial source-only opt-in implementation before publication:
ADR-0154 governs automatic cards on a TTY, not just the older consumers.

## Approach

All five views now call the existing `use_card_default`; parser defaults are
`None`, with `--card` and `--no-card` explicit overrides. Piped/default non-TTY
plain bytes and existing JSON serialization remain unchanged. TTY output now
follows the governed automatic-card behavior. Truncation notes point to
`--no-card` or existing `--json`, not omission of the positive flag.

## Challenges encountered

The parent review corrected its earlier default-false instruction after
checking ADR-0154. Preserve the original commits and reasoning as history;
this correction removes the contemplated policy exception. No new ADR.

## Decisions and alternatives

Use the existing renderer's policy instead of introducing a second presentation
default. Redaction, explicit raw access, validation, mutation surfaces, and
dependencies are unchanged.

## Verification

Written regressions now cover all five views across four TTY/override modes
and existing JSON precedence. They remain **unrun**. Mechanical parser-golden
generation produced `ca0221ef36d806dc4bf86dcf53136b7d5c3553e135c2eb284bac32b4a6ef9863`.
Formatting and diff hygiene only; no tests, CI, provider, native, installed CLI,
or acceptance execution.

## Follow-ups

Update the current canonical/capsule projection to this corrected source and
its immediate ledger, then use parent-coordinated publication. Verification
remains deferred at owner direction; do not close AR-251.

Integration `93866796` preserves the published installed-delivery and retained Hermes purpose-boundary records with their faithful merge ledgers. Independent source ownership and deferred execution remain unchanged.
