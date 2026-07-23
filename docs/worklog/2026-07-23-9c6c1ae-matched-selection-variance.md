---
title: "Worklog: Record matched selection variance"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [evaluation, workforce, selection, inference, latency, variance, handoff]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
  - docs/decisions/0082-schedule-assurance-by-artifact-lifecycle.md
  - docs/decisions/0083-use-capability-indexed-recall-and-bounded-inference.md
supersedes: []
superseded_by: null
type: worklog
commit: 9c6c1ae13007317c9971f86043fe3a242bd76581
short: 9c6c1ae
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog: Record matched selection variance

## Purpose

Run the next complete matched-selection corpus from the clean recovery
checkpoint, preserve its exact configured-provider evidence, and determine
whether the complete-run Agency failures represented governed semantic defects
or provider and latency variance before advancing AR-119.

## Approach

The complete 19-case Windows corpus kept the predeclared 15000 ms cold gate,
one-call fast budget, `codex-subscription` provider, requested and actual
`gpt-5.6-luna` model, and low reasoning effort. Stdout and stderr were captured
as separate raw byte streams outside the repository before parsing, then
reverified by byte count and SHA-256.

The three complete-run Agency failures received one bounded matched rerun with
the same controls. The remaining clinical/legal confidence abstention then
received one immediate single-case matched confirmation. AR-119 records every
stream receipt, aggregate, fingerprint, provider/model binding, and the exact
19-line, three-line, and one-line compact projections.

## Challenges encountered

The complete corpus produced two exact, complete Agency teams that exceeded
the unchanged latency gate and one fail-closed assurance and margin abstention.
The three-case rerun recovered the application-integration and incident cases,
but clinical/legal review changed to a confidence abstention before passing its
immediate one-case confirmation. Four complete-run upstream arms and one
bounded upstream arm were malformed; none was scored as an upstream loss.

The machine report serializes empty ineligible-selection maps as `{}` rather
than arrays. An initial temporary projection formatter treated those objects as
one item, which contradicted the report's zero-count aggregate. The formatter
was corrected before documentation changed, and the final roadmap projection
uses the exact zero counts. A first projection comparison also included the
Markdown fence's blank separator; normalizing only that fence whitespace
proved exact 19/3/1 line fidelity.

## Decisions and alternatives

No product or policy code changed. Every complete-run failure passed under the
same governed controls in bounded confirmation, so changing planner semantics,
staffing thresholds, typed coverage, response parsing, the latency gate, or the
one-call budget would have tuned the product to variable evidence.

The next package remains in matched selection and starts with another unchanged
complete corpus. Malformed upstream arms remain benchmark-validity failures,
and no comparative superiority claim is allowed.

## Verification

- The complete process finished in 506.068 seconds, emitted 1,188,204 stdout
  bytes and zero stderr bytes, and preserved verified stream hashes.
- Agency passed 16/19 with F1 0.916667, 18/19 complete typed coverage, and zero
  forbidden, ineligible, or conflict selections.
- The three-case rerun recovered two Agency cases below budget with zero safety
  defects; the one remaining abstention passed its immediate matched
  confirmation in 7810.931 ms with exact two-worker coverage.
- The clinical/legal-only benchmark was valid and returned status 0.
- Metadata passed for 290 Markdown files; policy availability, worklog-current
  for 116 substantive commits, documentation validation for 290 Markdown
  files, exact 19/3/1 projection comparisons, and `git diff --check` passed.

## Follow-ups

Continue [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) and
[AR-125](../roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md) from
this recovery and ledger pair. Run one unchanged complete 19-case corpus,
capture both streams before parsing, retain malformed upstream arms as
validity failures, and do not advance to contractor lifecycle until one
complete Agency corpus passes safely.
