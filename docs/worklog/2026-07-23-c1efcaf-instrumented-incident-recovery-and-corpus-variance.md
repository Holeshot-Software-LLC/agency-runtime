---
title: "Worklog: Record instrumented incident recovery and corpus variance"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [evaluation, workforce, selection, inference, instrumentation, handoff]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
  - docs/decisions/0082-schedule-assurance-by-artifact-lifecycle.md
  - docs/decisions/0083-use-capability-indexed-recall-and-bounded-inference.md
supersedes: []
superseded_by: null
type: worklog
commit: c1efcafed676bf6f7c1db6747fec38c0f5358589
short: c1efcaf
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog: Record instrumented incident recovery and corpus variance

## Purpose

Preserve the complete active-incident Agency inference outcome before matched
benchmark projection, resolve the preceding incident abstention uncertainty,
and run the required unchanged complete corpus without advancing to contractor
lifecycle work.

## Approach

A pass-through benchmark router called `plan_and_staff_workforce` with the
supplied arguments, durably serialized the unchanged outcome outside the
repository, and returned it for normal scoring. The instrumented case retained
the audited Store snapshot, Windows/Codex staffing context, full tool union,
`codex-subscription`, requested and actual `gpt-5.6-luna`, low effort, the
15000 ms gate, and one-call fast budget. After that arm passed, the unchanged
19-case CLI corpus ran with both streams captured before parsing.

## Challenges encountered

The instrumented outcome showed that the same governed two-unit incident plan
accepted in both cold diagnostics also passes in matched execution. The full
corpus repeated that incident pass but produced two different safe Agency
abstentions in installed release and clinical/legal review. Three upstream arms
were malformed. This remains configured-model plan-shape and response-contract
variance, not valid comparative evidence.

## Decisions and alternatives

No product, policy, parser, coverage, latency, or call-budget rule changed. The
accepted incident plan did not prove a defect, and the new corpus abstentions
need their own pre-projection evidence before any governed semantic change is
considered. Malformed upstream arms remain benchmark-validity errors rather
than comparative losses, and no superiority claim is made.

## Verification

- The instrumented benchmark returned status 0 in 23.211480 seconds; its
  688,497-byte report and stdout had SHA-256
  `2ba2801b64f965a107c85f63b881cbe74a673673202a1f5fd484b3ae034306fb`.
- The complete 23,641-byte Agency outcome had SHA-256
  `9afceec23eeecd8a4292dfc0731df2550fdeb1001bca647f5e04c0fed10cba25`;
  Agency passed with complete typed coverage and zero safety selections.
- The full process finished in 414.760604 seconds; its 1,188,059-byte stdout
  had SHA-256
  `f5b462bc32bcaa000cb6ee426312022a62a3058c7518f598d09afb720572184a`.
- The full corpus retained all provider, model, receipt, call-count, inference,
  roster, eligibility, and case bindings. Agency passed 17/19 with zero
  forbidden, ineligible, or conflict selections; three malformed upstream arms
  invalidated comparison.
- Metadata, policy availability, worklog currency, documentation validation,
  capture-hash reproduction, exact projections, and `git diff --check` passed
  before the recovery commit.

## Follow-ups

Continue [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) and
[AR-125](../roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md) from this
recovery and ledger pair. Instrument the installed-release and clinical/legal
Agency outcomes before projection, then run another unchanged complete corpus
only if both bounded arms pass.
