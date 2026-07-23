---
title: "Worklog: Record matched incident selection variance"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [evaluation, workforce, selection, inference, stability, handoff]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
  - docs/decisions/0082-schedule-assurance-by-artifact-lifecycle.md
  - docs/decisions/0083-use-capability-indexed-recall-and-bounded-inference.md
supersedes: []
superseded_by: null
type: worklog
commit: 978e02cefee20d41a7798b8c69ade76ac0e340fd
short: 978e02c
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog: Record matched incident selection variance

## Purpose

Run the next unchanged complete matched-selection corpus, preserve its exact
evidence, and distinguish Agency selection stability from upstream benchmark
validity without advancing AR-119 into contractor lifecycle work.

## Approach

The complete 19-case Windows corpus retained the predeclared 15000 ms cold
gate, one-call fast budget, `codex-subscription` provider, requested and actual
`gpt-5.6-luna` model, low reasoning effort, explicit-model receipts, and
applied inference in all 38 arms. Stdout and stderr were captured as separate
byte streams outside the repository before parsing, and the compact projection
was checked against the saved machine-readable report.

After the sole Agency abstention, two matched bounded reruns isolated the
active-incident case. A final Agency-only cold diagnostic tested whether the
same governed inputs always produced the failing plan shape. The canonical
AR-119 record now preserves the complete run, both bounded confirmations, the
diagnostic, and the smallest safe next package.

## Challenges encountered

Agency passed 18/19 in the complete corpus and failed closed only on
`active-incident-containment` with `selection_margin_too_low`. Both matched
bounded reruns reproduced that safe abstention. The cold diagnostic then
produced a different, valid two-unit security plan that staffed
`incident-responder` with accepted margins, demonstrating plan-shape variance
rather than a stable deterministic product or policy defect.

The comparison remained invalid independently: five upstream arms were
malformed through unknown disabled shadows or invalid assignment rows. Those
arms cannot be interpreted as losses, and the prior 19/19 Agency observation
does not make the incomplete benchmark comparative evidence.

## Decisions and alternatives

No product, policy, parser, fairness, coverage, latency, or call-budget rule
changed. The evidence did not justify scenario-specific routing, weakened typed
coverage, a higher 15000 ms gate, or a larger one-call budget.

The next package stays in matched selection. It runs one more bounded matched
active-incident confirmation before deciding whether an unchanged complete
corpus is warranted or whether a genuinely general semantic defect exists.
Contractor lifecycle and all superiority, untouched-corpus, activation,
completed-outcome, and release claims remain deferred.

## Verification

- The complete process finished in 426.744 seconds, returned status 1, emitted
  1,183,869 stdout bytes and zero stderr bytes, and its saved hashes were
  independently reproduced.
- Agency passed 18/19 with 18/19 complete typed coverage, precision 0.887097,
  recall 0.948276, F1 0.916667, p95/max latency 13284.288 ms, complete required
  disabled-winner disclosure, and zero forbidden, ineligible, or conflict
  selections.
- The two bounded matched reruns reproduced only the safe
  `selection_margin_too_low` abstention; the cold Agency-only diagnostic
  accepted a valid two-unit incident-response plan with margins 0.2 and 1.0.
- Five upstream arms remained malformed, so benchmark validity and every
  superiority or release claim stayed false.
- All 19 documented projection lines matched the saved machine-readable report
  exactly. Provider, model, receipt, call-count, inference, budget,
  fingerprint, capture-hash, and bounded-evidence assertions passed.
- Metadata for 301 Markdown files, policy availability, worklog currency for
  128 substantive commits, documentation validation for 301 Markdown files,
  and `git diff --check` passed before the roadmap evidence commit.

## Follow-ups

Continue [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) and
[AR-125](../roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md) from this
recovery and ledger pair. Run one more unchanged matched
`active-incident-containment` confirmation first. If Agency passes, make no
policy change and run one further unchanged complete corpus; if it fails again,
compare the plan shape with the accepted diagnostic before considering only
governed, general semantics.
