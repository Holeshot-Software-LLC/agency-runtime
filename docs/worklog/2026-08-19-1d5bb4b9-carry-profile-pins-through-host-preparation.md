---
title: "Worklog detail: carry profile pins through host preparation"
status: active
category: worklog
created: 2026-08-19
updated: 2026-08-19
tags: [canary, inference, zcode, glm, credentials, evidence]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
  - docs/decisions/0160-pin-child-judge-providers-per-canary-harness.md
  - agency_runtime/core/canary_backends.py
supersedes: []
superseded_by: null
type: worklog
commit: 1d5bb4b99c3d0a4a01574f6971f08a3016876c99
short: 1d5bb4b9
date: 2026-08-19
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-253-dynamic-team-dispatch-on-every-harness.md
---

# Worklog detail: carry profile pins through host preparation

## Purpose

Review of the preceding ZCode/GLM checkpoint found that inference-profile
resolution returned no CLI transport, while top-level canary preparation still
required a provider and transport together. The resolver worked in staffing
tests but a real canary backend would reject it before invocation.

## Approach

Canary preparation now projects every exact provider identity through
`AGENCY_CANARY_CHILD_JUDGE_PROVIDER`. When the pin is a named inference profile,
no CLI transport or credential home is required. Codex and Claude CLI pins keep
their existing isolated same- or cross-provider credential projection. A
transport without a provider still fails closed.

Source tests also drive the documented ZCode Agent `PreToolUse` envelope through
`HookBridge("zcode")` and prove it reaches native-child staffing with the ZCode
host identity. The docs distinguish that source contract from live proof:
ZCode is hook-only on this installation, has no launchable CLI backend here,
and emits no child lifecycle events. Current provider attribution therefore
needs an attended installed ZCode session; a direct hook simulation is not host
proof.

## Challenges encountered

The initial profile tests stopped below the host-preparation boundary and
therefore missed the provider/transport coupling. Tracing the real canary path
exposed it before installation. The same trace showed that implementing a
synthetic ZCode process backend would not create the host-authored evidence
required by AR-119.

## Decisions and alternatives

ADR-0160 remains the durable decision. Profile pins carry identity only; CLI
pins own CLI authentication projection. A synthetic ZCode backend was rejected
because it would neither invoke the installed hook-only host nor supply its
missing child lifecycle evidence.

## Verification

- Focused canary/profile regression slice: 119 passed.
- Expanded affected slice: 238 passed.
- `python scripts/run_local_gates.py --fast`: all 12 gates passed, including
  161 workflow-contract tests and 134 dashboard tests.
- Ruff lint/format and documentation validation passed for 705 Markdown files.
- The AR-119 recovery capsule remains exactly 180 lines and 10,078 bytes.

## Follow-ups

- After renewed approval, publish/install the clean candidate and collect an
  attended ZCode Agent call that records requested and actual GLM provider.
- Collect the fresh Claude host artifact with the measured passing Codex pin.
- Keep ZCode Rule 4 and Codex native-child proof open until host-authored
  evidence satisfies their separate boundaries.
