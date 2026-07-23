---
title: "Worklog: Record installed-release plan-shape variance"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [evaluation, workforce, selection, inference, instrumentation, handoff]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
  - docs/decisions/0083-use-capability-indexed-recall-and-bounded-inference.md
supersedes: []
superseded_by: null
type: worklog
commit: 1d3059dcfeddf3de9fe09582fb118e3f5129fc70
short: 1d3059d
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog: Record installed-release plan-shape variance

## Purpose

Preserve complete Agency outcomes for the installed-release and clinical/legal
matched cases before projection, classify the remaining safe abstention from
exact controlled-capability evidence, and advance the bounded AR-119 recovery
package without changing product or policy semantics.

## Approach

A pass-through benchmark router called `plan_and_staff_workforce` with the
matched harness arguments, atomically serialized each unchanged outcome under
its canonical case ID outside the repository, and returned it to the normal
scorer. The run retained the audited Store snapshot, Windows/Codex context,
full tool union, configured provider and model, 15000 ms cold gate, and one-call
fast budget. A read-only whole-roster coverage diagnostic then compared the
failed installed unit with its complete proposal and controlled capability
owners.

## Challenges encountered

Clinical/legal recovered with complete typed coverage. Installed release safely
abstained because its first software unit required
`generation-preparation`: every executable software candidate missed that
capability, while its only two roster owners were design specialists excluded
for authority and domain mismatch. The other four units had deterministic
staffing. Earlier accepted score projections did not retain their complete
plans, but they selected no design specialist and passed the same complete
coverage verifier.

## Decisions and alternatives

The verifier correctly failed closed. The evidence demonstrates configured
model plan-shape variance rather than a stable governed defect. No scenario
route, capability erasure, worker broadening, parser relaxation, typed-coverage
weakening, latency increase, or call-budget increase was justified. The full
corpus was not rerun because the bounded installed Agency arm did not pass.

## Verification

- The instrumented process completed in 49.659155 seconds with status 1;
  report/stdout were 714,064 bytes with SHA-256
  `4cafdb1280992ae775a71c250a424ab4c592d0994833ebec719b0b7e1d6f9989`,
  and stderr was empty.
- Complete installed and clinical/legal outcome SHA-256 values were
  `fd6ac7223283022a37e01b932a7da52b672a9850eb79cf90a756aba96a8514db`
  and
  `f3fd40b6342c668ba66cb601b26bf78132269bf93f8decd39acd0d878f0a4556`.
- The two-line exact projection was 1,645 bytes with SHA-256
  `ee48658669d609e278f3e364444a7de77059d6ba9c78b035873e5d9078df667d`.
- The benchmark was valid; both Agency arms retained one applied
  explicit-model call and zero forbidden, ineligible, or conflict selections.
- The diagnostic summary was 2,795 bytes with SHA-256
  `fd931f478c5205d50bdf82c132be91fbfcfe1d7cc1786365a0e6549b91ff5672`.

## Follow-ups

Continue AR-119 from the active recovery capsule. Run one unchanged
instrumented installed-release confirmation and only run another complete
19-case corpus if that Agency arm passes. Preserve malformed upstream arms as
validity failures and make no superiority claim.
