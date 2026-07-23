---
title: "Worklog: Add the matched upstream selection benchmark"
status: active
category: worklog
created: 2026-07-22
updated: 2026-07-22
tags: [evaluation, workforce, selection, upstream, handoff]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
  - docs/decisions/0082-schedule-assurance-by-artifact-lifecycle.md
supersedes: []
superseded_by: null
type: worklog
commit: ca893fed3fca8e6d8cc5ea6abf726a8e3d6877ac
short: ca893fe
date: 2026-07-22
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog: Add the matched upstream selection benchmark

## Purpose

Create the source-pinned, input-matched selection comparison required before
Agency can make any evidence-backed routing claim against upstream Agency
Agents. The commit is also a recovery boundary at the repository's 50-percent
context threshold; the benchmark package remains in progress because its first
configured-provider canary exposed a real staffing gap.

## Approach

The benchmark runs Agency and the exact pinned upstream Agents Orchestrator
prompt through one configured provider and requested model. Both arms receive
the same request, workforce snapshot, explicit eligible-worker set, host and
tool context, and shared scorer. It alternates arm order, clears Agency caches
per case, records actual model receipts, and invalidates malformed or unmatched
comparisons instead of interpreting them as baseline losses.

The held-out selection corpus now contains 19 scenarios with mandatory helpful
and forbidden workers, disabled-winner disclosure, composition separation,
typed artifact and lifecycle coverage, and latency. The CLI requires an exact
live-inference confirmation phrase. The pinned upstream prompt and MIT license
are package data with byte and SHA-256 verification; a narrow Git whitespace
attribute preserves source-authentic trailing spaces.

The live canary also found a general compact-plan defect. A model outcome may
contain 512 characters, but the compiler embedded it into acceptance evidence
whose contract permits 128. Locally derived evidence is now bounded and based
on the artifact kind.

## Challenges encountered

Upstream provides source-visible orchestration instructions but no executable
selector, so the baseline uses the exact prompt plus a format-only structured
selection adapter. Expected and forbidden labels never enter either arm.

The first live canary failed on overlong locally derived acceptance evidence;
after that general fix, the same case reached deterministic staffing and
truthfully abstained. The planner required `operations`, `investigation`, and
`risk-analysis`, while the audited incident contracts could not cover the
complete set. The canary also exceeded its predeclared 10-second Agency latency
budget. These are unresolved evidence, not reasons to relax scoring or claim
superiority.

## Decisions and alternatives

The report always sets superiority and release-claim eligibility to false.
Architecture differences, partial helpful recall, or a malformed upstream arm
cannot establish better outcomes. A format-only adapter was chosen because
inventing an upstream selector would not represent the pinned project. The
incident failure was not patched with a scenario-specific route; the governed
contract or planning semantics must be reconciled generally.

## Verification

- 55 compact-intent, matched-selection, workforce-safety,
  upstream-architecture, and CLI contract tests passed.
- Focused `ruff check` passed and all nine touched Python files were formatted.
- Metadata and documentation validation passed for 283 Markdown files.
- Policy availability and `git diff --check` passed.
- The configured Windows canary used `codex-subscription` with requested and
  actual model `gpt-5.6-luna`; it failed truthfully with Agency helpful F1
  `0.000`, upstream helpful F1 `0.667`, zero Agency forbidden, ineligible, or
  conflict selections, and Agency cold latency `11459.837` ms.

The full 19-case provider run and the expensive full repository matrix were
intentionally not claimed at this recovery checkpoint.

## Follow-ups

Continue [AR-119](../roadmap/issue-AR-119-inference-first-workforce.md) by
reconciling the incident capability mismatch without weakening coverage or
adding case-specific policy, rerun the canary, then run all 19 matched cases and
fix every unsafe or clearly inferior Agency result. Keep the larger
[AR-125](../roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md) outcome
and release gates open.
