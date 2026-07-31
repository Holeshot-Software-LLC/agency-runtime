---
title: "Worklog detail: Classify Codex non-critical host notices"
status: active
category: worklog
created: 2026-07-31
updated: 2026-07-31
tags: [codex, canary, diagnostics, evidence, mutation]
related:
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
  - docs/roadmap/issue-AR-208-preserve-codex-host-notices-in-product-evidence.md
  - docs/decisions/0116-bind-product-trials-to-exact-workspace-proof.md
  - docs/decisions/0125-admit-only-exact-content-free-codex-host-notices.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: fb797f9
short: fb797f9
date: 2026-07-31
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/198
related_issues:
  - docs/roadmap/issue-AR-207-persist-preflight-delegation-failure-diagnostics.md
  - docs/roadmap/issue-AR-208-preserve-codex-host-notices-in-product-evidence.md
---

# Worklog detail: Classify Codex non-critical host notices

## Purpose

Prevent Codex 0.146 non-critical startup warnings from being reported as parent
tool execution while preserving the activation and product harnesses' exact
fail-closed boundary for unknown errors and non-collaboration tools.

## Approach

Classify only two exact Codex-owned messages: the supported hook-trust bypass
notice and the skill-catalog-description shortening notice. Project only fixed
content-free notice types and counts. Keep every unknown or near-miss `error`
item in the existing unexpected-item path, and carry the notice projection
through persisted activation and product collaboration evidence.

Add focused rollout and parser regressions plus a curated mutation that changes
the exact guard into arbitrary-error acceptance. The mutation must be killed by
the near-miss case.

## Challenges encountered

The exact-installed activation had actually selected and executed
`code-reviewer`, completed its native child, and finalized with zero
corrections. The failure label therefore contradicted the persisted rollout,
which contained only `spawn_agent` and `wait_agent`.

Codex 0.146 serializes non-critical warnings as completed JSONL items whose
item type is `error`. The exact canary catalog retained all 67 skills but
shortened 11,805 description characters, averaging 177 characters per skill
and crossing Codex's 100-character warning threshold. The exact warning string
was independently confirmed in the installed binary.

## Decisions and alternatives

Do not ignore all Codex `error` items and do not infer safety merely because a
persisted rollout is otherwise clean. Exact-message classification keeps the
known host notices non-fatal while an unknown config warning, deprecation,
reroute, hook failure, or arbitrary error remains visible as a failed proof.

## Verification

- Two bounded review passes completed with no remaining behavior defect.
- All 25 warning-strict activation-canary tests passed.
- Decision conformance killed all 63 curated mutations with zero survivors or
  invalid mutations and restored the source tree exactly.
- The accepted and rejected projections exclude the original message text.
- Focused Ruff check, Ruff format, documentation metadata, capsule bounds, and
  `git diff --check` passed.

## Follow-ups

Run the named fast spine, push and review the checkpoint, merge and
exact-install Codex, ZCode, and dashboard, then run one fresh activation canary
before spending the exact build's single product trial. Publish the local HTML
evidence page and OpenClaw handoff after the live proof.
