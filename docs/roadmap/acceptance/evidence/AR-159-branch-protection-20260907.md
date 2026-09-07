---
title: "AR-159 current branch-protection audit"
status: active
category: roadmap
created: 2026-09-07
updated: 2026-09-07
tags: [evidence, security, governance, ci, backlog]
related:
  - docs/roadmap/issue-AR-159-enforce-production-branch-protection.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/acceptance/evidence/AR-156-verification-workflow-20260907.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0097-gate-expensive-ci-fanout-behind-quality-contracts.md
  - .github/workflows/ci.yml
  - .github/workflows/codeql.yml
  - .github/workflows/dependency-review.yml
supersedes: []
superseded_by: null
---

# AR-159: Read-only enforcement audit

## Scope and disposition

Audit September 7, 2026, beginning at 08:46 UTC, against clean main
b2ea5946515123a95ef4ce13a6ea7c333aec76d4, after PR #710. This branch only records
the audit. Product, scripts, tests and workflow bytes are unchanged. Retain
AR-159 open: its security requirement remains relevant and unenforced. This is
not an acceptance verdict or settings change. All seven original criteria stay
unchanged. Hosted enforcement is waiting_for_operator; the backlog continues.

## Current API evidence

Authenticated read-only calls target Holeshot-Software-LLC/agency-runtime.
Paths below are relative to that repository's REST API endpoint.

| Read | Observed result |
|---|---|
| GET branches/main | protected=false; protection enabled=false, enforcement off, checks and contexts empty. |
| GET branches/main/protection | HTTP 404, message Branch not protected. |
| GET rulesets?includes_parents=true | Empty array. |
| GET commits/b2ea5946515123a95ef4ce13a6ea7c333aec76d4/check-runs | total_count=0, no checks. |
| Same commit's status endpoint | total_count=0, no contexts, aggregate pending. |
| gh pr view 710, check rollup/merge/head fields | Empty rollup; merge b2ea5946 at 08:41:00Z; reviewed head 699db08da4a1e56d5c324103860223af25142bee. |

GET actions/workflows reports repository CI (312401887), CodeQL (312401888),
dependency review (312401880), and roster audit (316334814) workflows active.
Another active CodeQL entry 344283851 has path
`dynamic/github-code-scanning/codeql`. Its intended role and check identity
must be reconciled before enforcement; do not silently equate it with the
repository aggregate or change its settings.

Latest runs returned by `gh run list --workflow <file> --limit 1`:

| Workflow | Latest listed run | Conclusion / source |
|---|---|---|
| ci.yml | [33437822949](https://github.com/Holeshot-Software-LLC/agency-runtime/actions/runs/33437822949) | Cancelled; August 31 at 20:46:13Z, pull request. |
| codeql.yml | [33437822950](https://github.com/Holeshot-Software-LLC/agency-runtime/actions/runs/33437822950) | Cancelled; same timestamp and event. |
| dependency-review.yml | [33437823066](https://github.com/Holeshot-Software-LLC/agency-runtime/actions/runs/33437823066) | Success; same timestamp/event. Jobs readback: one successful dependency review job, 20:46:16Z–20:46:27Z. |

All three name head c6e9e46cd1d90b965b4a87f398a1fac7d125cfcd, not current main.
The three-entry CI query also lists failed August 31 runs 33436382699 and
33435789901. No logs, billing records or current entitlement probes were read:
these results establish missing current proof, not its cause. July 27's billing
explanation is historical, not a fresh diagnosis. Empty checks and ordinary
merge success are not evidence of a green or protected branch.

## Local contract and verification

Source candidates for future required contexts:

- CI job quality: `automatic gates; integration suites are manual`.
- CodeQL job codeql: `CodeQL result`.
- Dependency-review job dependency-review: `dependency review`.

These are source names, not approved check/app bindings. Only current observed
contexts from verified producing apps should be bound. Conditional analyzers
and manual integration suites are not substitute stable aggregates. ADR-0037's
exact unavailable paths remain fail-closed and non-equivalent to native analysis.

Fresh execution in the development virtual environment with this worktree first
on the import path:

```bash
PYTHONPATH=. python -m pytest tests/test_release_packaging.py -q -W error \
  -k 'quality or codeql or dependency_review or docs_only_lane'
```

Result: **104 passed, 16 deselected, 3.02 seconds**, no skips/failures. Cases
exercise coherent/incoherent aggregate results, missing/failed gates, event and
scope constraints, stable security checks and exact capability classification.
`git diff b2ea5946 -- agency_runtime tests scripts .github` is empty. This is
local workflow evidence, not hosted enforcement.

Explicit reuse of AR-156's named spine (1085 passed/three existing skips), UI
(188/current floors) and installed-wheel browser receipt (21 loaded checks):
no production or named-spine input changed in this docs-only package. No new
corpus, coverage matrix, workflow dispatch, native Windows or host activation.

## Next authorized package

Obtain owner approval for enforcement and the exact bypass/emergency/rollback
policy. Establish current successful PR contexts/apps and reconcile both CodeQL
entries. Apply the approved PR/check/force-push/deletion policy, then read back
the main target and all bindings. Execute an explicitly approved, recoverable
compliant/rejected update demonstration without destructive main probes. Freeze
all criterion evidence for isolated verification before completion. Preserve
the legacy tracker exemption.

No account, branch, Actions, licensing or bypass setting was changed. Counts
remain 40 open trackers plus 89 unfinished legacy records, 129 local unfinished.
The owner retains native Windows and interactive hook trust.
