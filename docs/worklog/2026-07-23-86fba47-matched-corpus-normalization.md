---
title: "Worklog: Harden matched corpus normalization"
status: active
category: worklog
created: 2026-07-23
updated: 2026-07-23
tags: [evaluation, workforce, selection, inference, assurance, handoff]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
  - docs/decisions/0082-schedule-assurance-by-artifact-lifecycle.md
  - docs/decisions/0083-use-capability-indexed-recall-and-bounded-inference.md
supersedes: []
superseded_by: null
type: worklog
commit: 86fba4779bcae7ff31085cd2f96bc959a3324cba
short: 86fba47
date: 2026-07-23
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog: Harden matched corpus normalization

## Purpose

Run the complete matched-selection corpus, preserve an exact case-by-case
projection, and reconcile the remaining general Agency failures without adding
scenario routes, increasing the one-call fast budget, raising the predeclared
15000 ms cold gate, or weakening malformed-arm fairness checks.

## Approach

Read-only test evidence now retains the `testing` lifecycle. Original-request
tokens can disambiguate bounded PostgreSQL query-performance and runtime-routing
analysis when a compact plan uses generic wording, while unrelated request text
remains excluded. Research is normalized as a method inside a named subject
domain even when the model does not repeat it on the capability axis, and
routine software diagnosis no longer acquires incident-only investigation
coverage. Explicit breach, containment, forensic, incident, malware, outage,
and ransomware signals preserve that capability.

Assurance dependency binding now connects downstream review and test evidence
to every local implementation unit as well as local tests. A separate
observability implementation therefore cannot be incorrectly classified as
unreviewed merely because the test unit names only the primary API and
dashboard implementations.

## Challenges encountered

Configured-provider plan shape remained variable. In one complete run, Agency
failed closed on installed release, runtime routing, and the broad application;
the first two passed unchanged on direct and matched bounded reruns, while the
broad case exposed and then verified the assurance-binding defect. Provider
arms also returned malformed assignments and unknown disabled shadows. Those
arms remain benchmark-invalid and were never scored as upstream losses.

One runtime rerun selected the correct team but took 17407.239 ms. Other valid
runs completed at 10832.251, 10834.705, and 11743.515 ms. The latency gate was
not changed in response.

## Decisions and alternatives

The implementation normalizes governed semantic axes and artifact
dependencies, not case identifiers or exact prompt phrases. Safe abstention
remains preferable to an unsafe substitute. A planner validation failure still
consumes the single fast call and cannot receive a hidden retry.

The complete run's aggregate F1 delta is retained only as descriptive bounded
selection evidence. It is not a superiority claim because the benchmark was
invalid and outcome, activation, untouched-corpus, and statistical gates remain
open.

## Verification

- 129 intent, inference, selection-safety, matched-selection, and staffing
  foundation tests passed with warnings treated as errors.
- Focused Ruff check and format checks passed, as did `git diff --check`.
- Metadata, policy availability, worklog-current, and documentation validation
  passed for 285 Markdown files.
- Two complete 19-case configured Windows runs used `codex-subscription`,
  requested/actual `gpt-5.6-luna`, low effort, and one call per arm.
- The recorded second complete run had zero Agency forbidden, ineligible, or
  conflict selections and a 14041.516 ms Agency maximum, but four malformed
  upstream arms invalidated fairness and three Agency arms safely abstained.
- The post-fix bounded rerun passed installed release, runtime routing, and the
  broad application on Agency with zero safety violations. The broad case
  selected its exact nine helpful workers at 14758.804 ms. Its matched runtime
  upstream arm remained invalid because it disclosed an unknown disabled
  worker.

The final complete post-fix 19-case run was intentionally deferred when context
telemetry reached 20.1 percent remaining and triggered the mandatory fresh-task
handoff rule.

## Follow-ups

Continue [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) from
this recovery and ledger pair. Run one complete 19-case corpus immediately with
unchanged budgets. If every Agency arm passes but only upstream provider arms
remain malformed or timed out, record that exact blocker instead of changing
the parser or fairness gates. Keep [AR-125](../roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md)
and every deferred activation, untouched-corpus, outcome, and release gate open.
