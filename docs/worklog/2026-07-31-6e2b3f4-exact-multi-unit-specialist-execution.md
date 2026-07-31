---
title: "Worklog detail: Prove exact multi-unit specialist execution"
status: active
category: worklog
created: 2026-07-31
updated: 2026-07-31
tags: [product, delegation, codex, diagnostics, evidence, mutation]
related:
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
  - docs/decisions/0122-use-one-agency-native-resident-steward.md
  - docs/decisions/0124-grade-product-trials-against-the-inferred-unit-graph.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 6e2b3f4
short: 6e2b3f4
date: 2026-07-31
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/197
related_issues:
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
---

# Worklog detail: Prove exact multi-unit specialist execution

## Purpose

Make a README-scale product trial prove the full inference-authored unit graph
instead of passing a one-child activation canary or allowing the parent model
to perform specialist work itself. Preserve enough content-free failure
evidence to diagnose a turn that stops before routing or native delegation.

## Approach

Add immutable schema-v39 preflight failure receipts with allowlisted stages,
reasons, categories, and provider-attempt metadata. Project the exact receipt
through Store snapshots, CLI status, and dashboard evidence without retaining
prompts, responses, errors, paths, credentials, or stderr.

Separate fixed activation-canary rollout grading from bounded product grading.
For product trials, correlate one through sixteen exact persisted units to
their parent session, native child rollout, activation grant, specialist load,
worker lifecycle, and completed delegation. Reject missing or merged units,
parent-side product tools, failed workspace proof, and any response correction.

## Challenges encountered

The first exact-build trial had accepted eight units and nine specialists but
zero native spawns, leaving too little durable evidence to separate parent
spawn absence from hook, child, or Stop failures. The new product contract also
needed to tolerate bounded default `wait` arguments while rejecting unrelated
parent tools and retaining no child content.

The first named fast-spine pass exposed a stale mutation anchor and the old CLI
parser golden hash. Both exact contracts were repaired, their focused tests
passed, and the complete spine was rerun successfully.

## Decisions and alternatives

Keep the activation canary deliberately small; do not claim it proves product
execution. Product proof instead follows the inference-authored unit graph and
requires every row exactly once. Concurrency and dependency order remain host
choices, but merge, omission, and parent substitution are not. ADR-0124 owns
this durable distinction.

## Verification

- Two bounded review passes completed and their findings were repaired.
- The warning-strict production spine passed 636 tests with six skips.
- Dashboard UI passed all 110 tests.
- Routing evaluation passed every quality, safety, scale, and latency gate.
- Decision conformance killed all 62 curated mutations with zero survivors or
  invalid mutations, and restored the source tree exactly.
- Documentation validation passed 582 maintained Markdown files.
- Ruff check, Ruff format, and diff integrity passed.

## Follow-ups

Push and review the checkpoint, merge and exact-install Codex, ZCode, and the
dashboard, then spend one fresh build's single 1,800-second product trial and
publish its local evidence page and OpenClaw handoff under AR-207.
