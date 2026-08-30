---
title: "Worklog: Record complete-corpus confidence variance"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [evaluation, workforce, selection, inference, evidence]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
  - docs/decisions/0083-use-capability-indexed-recall-and-bounded-inference.md
  - docs/decisions/0085-continue-in-task-after-context-checkpoints.md
supersedes: []
superseded_by: null
type: worklog
commit: 06d12cf64195e7825a95d03b42f0a9e45e8448fe
short: 06d12cf
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog: Record complete-corpus confidence variance

## Purpose

Run the complete matched selection corpus required after installed-release
recovery, preserve byte-faithful evidence, and determine the next smallest
instrumented package without weakening governed controls or treating invalid
upstream output as a comparative loss.

## Approach

The unchanged 19-case Windows benchmark ran only after the repository's live-
work gate admitted it at 72.2% context remaining. A detached capture wrapper
wrote stdout and stderr directly as raw bytes outside the repository, recorded
elapsed time and exit status, and atomically produced hashes and byte counts.
The report was then parsed as exactly 19 cases; a deterministic projection
script generated the exact compact evidence and independently summarized every
arm binding.

## Challenges encountered

The complete corpus returned two different safe Agency abstentions after the
previously failing installed-release case recovered. Application observability
and the broad application both failed closed on selection confidence. Four
upstream arms also violated the response contract, so the complete comparison
remained invalid despite all 38 arms retaining their provider, model, receipt,
call-count, inference, and latency-budget bindings.

Immediately after the corpus, telemetry was 55.7%, below the fixed 65% gate
for another live package. The conditional instrumented rerun was therefore
left unstarted in this same task; no task was created, dispatched, or awaited.

## Decisions and alternatives

Neither Agency failure selected a forbidden, ineligible, or conflicting
worker. One configured-model confidence abstention per case does not prove a
general semantic defect, so the package did not tune selection confidence,
add a scenario route, weaken typed coverage, broaden worker authority, raise
the 15000 ms gate, or increase the one-call budget.

The malformed TypeScript, application-integration, runtime-routing, and broad-
application upstream arms remain benchmark-validity failures. Their aggregate
rows are descriptive only and are not upstream losses. No Agency superiority
claim is available.

## Verification

- The process returned status 1 in 422.492054 seconds. Its 1,179,731-byte
  stdout had SHA-256
  `cd3b36733b56b4c631da9ffea259fa278c597438ecbe59e3275f3e1d25e687d0`;
  stderr was empty. Independent byte and hash checks matched the manifest.
- The exact 13,055-byte projection had SHA-256
  `c835cc1ea1a9fa6cc22a31d847f1beb30b1ecc7f9e4ecbfb5b23ba858598cb5d`,
  and all 19 embedded roadmap lines matched the derived projection.
- Agency passed 17/19 with zero forbidden, ineligible, or conflict selections;
  the benchmark remained invalid because of four upstream arm errors.
- The focused matched-selection test module passed 7/7 tests.
- Metadata, policy availability, worklog, documentation, and diff checks passed
  against the substantive worktree.

## Follow-ups

The next admitted live package is one instrumented matched confirmation of
`application-observability` and `broad-python-typescript-application`, with both
complete Agency outcomes preserved before projection. Compare their plan
shapes, proposal scores, confidence, margins, and rejection reasons with prior
accepted observations. Contractor lifecycle, exact activation, blinded
completed-outcome trials, and every superiority claim remain deferred.
