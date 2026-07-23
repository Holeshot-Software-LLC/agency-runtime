---
title: "Worklog: Build the inference-first routing foundation"
status: active
category: worklog
created: 2026-07-22
updated: 2026-07-22
tags: [routing, workforce, inference, delegation, contractors, handoff]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/decisions/0080-plan-before-recruiting-from-the-whole-workforce.md
  - docs/decisions/0083-use-capability-indexed-recall-and-bounded-inference.md
supersedes: []
superseded_by: null
type: worklog
commit: 743a9827bc9ff05bacbca79711cc29af42c83016
short: 743a982
date: 2026-07-22
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-120-normalized-workforce-recruitment-index.md
  - docs/roadmap/issue-AR-121-inference-planning-and-staffing.md
  - docs/roadmap/issue-AR-122-contractor-hiring-and-lifecycle.md
  - docs/roadmap/issue-AR-123-workforce-cli-and-dashboard.md
  - docs/roadmap/issue-AR-124-lifecycle-assurance-and-native-delegation.md
  - docs/roadmap/issue-AR-125-workforce-and-one-shot-evaluation.md
---

# Worklog: Build the inference-first routing foundation

## Purpose

Establish a recoverable implementation boundary for AR-119 after the work grew
across workforce planning, selection, contractor governance, native delegation,
operator surfaces, evaluation, and portability. The commit also makes the
repository's autonomous context-handoff rule measurable from Codex session
telemetry so long-running work no longer depends on one chat retaining all
acceptance criteria.

## Approach

The runtime now plans typed work before selecting specialists, narrows the
versioned workforce through controlled capabilities, applies deterministic
eligibility and composition policy around bounded inference, and carries exact
specialist recipes into native-child activation. It adds contractor admission
and lifecycle foundations, CLI and dashboard controls, selection and product
evaluation scaffolding, and cross-host delivery paths for Codex, Claude,
OpenClaw, and Hermes.

The final routing slice rejects isolated Agency participation when selection
does not produce an exact unit plan. Host guidance names only the native tool
for that host, and exact planned agents must be available before activation.
The context helper reads the active `CODEX_THREAD_ID` token-count event and
reports whether the 50-percent autonomous handoff threshold has been reached.

## Challenges encountered

The implementation spans four native host protocols, provider and cache
identity, concurrent child routing, exact-version evidence, and large roster
policy. Unsafe semantic-only or incidental lexical selections must abstain
rather than producing a plausible-looking but unqualified worker. Multiple
power interruptions and a very large uncommitted diff also made a durable local
checkpoint necessary before further benchmark work.

## Decisions and alternatives

Planning-before-selection follows ADR-0080. Capability-indexed whole-roster
recall plus bounded inference follows ADR-0083. The implementation does not
claim superiority over upstream from architecture alone; a pinned, matched,
held-out benchmark remains mandatory. Native hosts retain scheduling authority,
while Agency supplies typed recipes and verifies exact activation instead of
replacing host delegation.

## Verification

- Five new cross-host guidance and safe-abstention cases passed.
- 82 unit-aware delegation, native-child hook, and child-routing cases passed.
- Four context-handoff telemetry tests passed.
- `ruff check agency_runtime tests scripts` passed.
- `ruff format --check agency_runtime tests scripts` passed.
- All 97 dashboard UI tests passed.
- Metadata and documentation validation passed for 282 Markdown files.
- `scripts/update_policy_availability.py --check` and `git diff --check` passed.

The full pytest, coverage, packaging, installed-host, Linux, and hosted matrices
were intentionally not claimed at this checkpoint.

## Follow-ups

Continue AR-119 with the pinned, matched upstream selection benchmark and
held-out safety corpus documented in its execution checkpoint. Then complete
the remaining AR-120 through AR-125 gates, run the deferred full verification
matrix once, publish and merge the final PR, reinstall the merged artifact, and
run all four live host canaries before closing issue #132.
