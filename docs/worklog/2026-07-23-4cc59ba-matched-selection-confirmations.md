---
title: "Worklog: Record matched selection confirmations"
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
commit: 4cc59ba33ad964b27e8b5f842cf7c65444a82dc6
short: 4cc59ba
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog: Record matched selection confirmations

## Purpose

Run the next complete matched-selection corpus from the clean recovery
checkpoint, preserve its exact configured-provider evidence, and determine
whether the complete-run Agency failures represented governed semantic defects
or provider and latency variance before advancing AR-119.

## Approach

The complete 19-case Windows corpus kept the predeclared 15000 ms cold gate,
one-call fast budget, `codex-subscription` provider, requested and actual
`gpt-5.6-luna` model, and low reasoning effort. Stdout and stderr were captured
as separate byte streams outside the repository before parsing, then verified
by byte count and SHA-256.

The two complete-run Agency failures received one bounded matched rerun under
the same controls. PostgreSQL recovered immediately. The broad application
selected its exact team but missed the gate by 9.149 ms, so it received two
immediate single-case confirmations. AR-119 records every stream receipt,
aggregate, fingerprint, provider/model binding, and the exact 19-line,
two-line, one-line, and one-line compact projections.

## Challenges encountered

The complete corpus produced one confidence abstention above the latency gate
for the broad application and one fail-closed lifecycle-owner abstention for
PostgreSQL analysis. Four upstream arms were malformed, so the complete
benchmark remained invalid and none was scored as an upstream loss.

The broad application then selected the exact complete team in all three
bounded runs. It exceeded the unchanged gate at 15009.149 and 15867.544 ms
before passing at 10081.549 ms. Its first one-case benchmark was valid; its
second was invalid because the upstream arm returned an invalid assignment
row. This separated configured-provider cold-latency variance from selection
semantics without weakening any fairness or safety gate.

## Decisions and alternatives

No product or policy code changed. Both complete-run Agency failures passed
under the same governed controls in bounded confirmation, and every bounded
broad-application run selected the exact team with complete typed coverage and
zero safety defects. Changing planner semantics, staffing thresholds, typed
coverage, response parsing, the latency gate, or the one-call budget would have
tuned policy to variable model output.

The next package remains in matched selection and starts with another unchanged
complete corpus. Malformed upstream arms remain benchmark-validity failures,
and no comparative superiority claim is allowed.

## Verification

- The complete process finished in 429.572 seconds, emitted 1,179,064 stdout
  bytes and zero stderr bytes, and preserved verified stream hashes.
- Agency passed 17/19 with F1 0.821429, 17/19 complete typed coverage, and zero
  forbidden, ineligible, or conflict selections.
- The two-case rerun recovered PostgreSQL in 5523.005 ms; the broad application
  selected its exact team with complete coverage and zero safety defects.
- The final broad-only confirmation passed in 10081.549 ms with exact
  nine-worker coverage and zero safety defects.
- All four captured reports preserved the expected provider, requested and
  actual model, receipt source, one-call count, applied inference, 15000 ms
  budget, roster fingerprint, and allowed-agent fingerprint.
- Metadata passed for 291 Markdown files; policy availability, worklog-current
  for 117 preceding substantive commits, documentation validation for 291
  Markdown files, exact 19/2/1/1 projection comparisons, and
  `git diff --check` passed.

## Follow-ups

Continue [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) and
[AR-125](../roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md) from
this recovery and ledger pair. Run one unchanged complete 19-case corpus,
capture both streams before parsing, retain malformed upstream arms as
validity failures, and do not advance to contractor lifecycle until one
complete Agency corpus passes safely.
