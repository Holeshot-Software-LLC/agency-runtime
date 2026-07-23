---
title: "Worklog: Record matched selection recovery evidence"
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
commit: d69237976885a047710766f127fa489bc01629da
short: d692379
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog: Record matched selection recovery evidence

## Purpose

Run the next complete matched-selection corpus from the clean recovery
checkpoint, preserve its exact configured-provider evidence, and determine
whether its three Agency failures represented governed general semantic defects
before advancing AR-119.

## Approach

The complete 19-case Windows corpus kept the predeclared 15000 ms cold gate,
one-call fast budget, `codex-subscription` provider, requested and actual
`gpt-5.6-luna` model, and low reasoning effort. Stdout and stderr were captured
as separate raw byte streams outside the repository before parsing, then
independently verified by byte count and SHA-256.

The three complete-run Agency failures received one immediate bounded matched
rerun under the same controls. Installed release and clinical/legal review
recovered immediately. Active incident containment repeated a fail-closed
selection-margin abstention, so it received one final incident-only matched
confirmation. AR-119 records every stream receipt, aggregate, fingerprint,
provider/model binding, and the exact 19-line, three-line, and one-line compact
projections.

## Challenges encountered

The complete corpus produced an installed-release team abstention, an
active-incident selection-margin abstention, and a clinical/legal latency miss
after selecting the exact required team. Two upstream arms returned unknown
disabled shadows, so the complete benchmark remained invalid and neither was
scored as an upstream loss.

Installed release and clinical/legal review passed in the immediate bounded
rerun. Active incident containment remained fail-closed on margin, then passed
in the immediate single-case confirmation with complete typed coverage and a
valid matched benchmark. This separated configured-provider plan-shape and
latency variance from a repeatable selection-semantic defect without weakening
any fairness or safety gate.

## Decisions and alternatives

No product or policy code changed. All three complete-run Agency failures
passed under the same governed controls in bounded confirmation, and each
recovery had complete typed coverage with zero safety defects. Changing planner
semantics, staffing thresholds, typed coverage, response parsing, the latency
gate, or the one-call budget would have tuned policy to variable model output.

The next package remains in matched selection and starts with another unchanged
complete corpus. Malformed upstream arms remain benchmark-validity failures,
and no comparative superiority claim is allowed.

## Verification

- The complete process finished in 433.173 seconds, emitted 1,188,929 stdout
  bytes and zero stderr bytes, and preserved independently reverified stream
  hashes.
- Agency passed 16/19 with F1 0.904348, 17/19 complete typed coverage, and zero
  forbidden, ineligible, or conflict selections.
- The three-case rerun recovered installed release in 6549.592 ms and
  clinical/legal review in 7888.950 ms, both with complete coverage and zero
  safety defects.
- The incident-only confirmation passed in 13155.609 ms with complete
  coverage, F1 0.666667, and zero safety defects; its benchmark was valid.
- All captured arms preserved the expected provider, requested and actual
  model, receipt source, one-call count, applied-inference state, 15000 ms
  budget, roster fingerprint, and allowed-agent fingerprint.
- Metadata, policy availability, worklog-currentness, documentation validation,
  exact 19/3/1 projection comparisons against the raw captures, capture-hash
  verification, and `git diff --check` passed.

## Follow-ups

Continue [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) and
[AR-125](../roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md) from
this recovery and ledger pair. Run one unchanged complete 19-case corpus,
capture both streams before parsing, retain malformed upstream arms as
validity failures, and do not advance to contractor lifecycle until one
complete Agency corpus passes safely.
