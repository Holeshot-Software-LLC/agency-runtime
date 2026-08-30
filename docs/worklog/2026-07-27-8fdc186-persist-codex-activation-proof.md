---
title: "Worklog detail: Persist Codex activation proof"
status: active
category: worklog
created: 2026-07-27
updated: 2026-07-27
tags: [codex, canary, activation, delegation, security]
related:
  - docs/worklog/README.md
  - docs/roadmap/README.md
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
supersedes: []
superseded_by: null
type: worklog
commit: 8fdc186fdc86958d89ff6bc2e585d58fadc71737
short: 8fdc186
date: 2026-07-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
---

# Worklog detail: Persist Codex activation proof

## Purpose

Correct the Codex activation canary after a trusted current-profile attempt
proved the one-unit Agency route but produced no native child activation. The
change must prove the exact native topology without treating lossy exec JSONL
as complete or weakening the existing Store authority graph.

## Approach

The activation command now keeps its parent persisted, forces Codex V2
collaboration, and requires the one bounded spawn to use `fork_turns="none"`.
The verifier resolves a fixed-depth parent/child rollout pair, applies private-
path and stable bounded-read checks, validates exact call and lifecycle
cardinality, and returns only content-free identities and hashes for Store
reconciliation. The shared backend exposes this as an explicit activation-only
mode. Deferred product trials retain their custom ephemeral response contract;
native-only canaries use separate ephemeral, delegation-disabled instructions.

## Challenges encountered

Codex V2 exec JSONL omits a successful spawn activity and intentionally emits
wait events without receiver IDs. A same-binary control also showed that
`--ephemeral` removes the persisted parent history needed by the default V2
fork, producing a delayed missing-parent failure. Parent spawn messages may be
encrypted, so the proof treats them as opaque and binds child delivery through
content-free Agency identities instead of plaintext comparison.

## Decisions and alternatives

Stdout-only proof was rejected because it cannot establish a closed-world child
count. Reading Codex internal SQLite state was rejected as production authority.
Persisted rollouts are supplemental host-native evidence; the Agency Store
remains authoritative for grants, consumption, worker lifecycle, specialist
load, model receipt, finalization, header, and install identity. The evidence
mode is explicit rather than inferred from master enablement or custom options,
which prevents product and native-only callers from inheriting activation
topology requirements.

## Verification

- 156 focused warning-strict canary, backend, product, and complexity tests
  passed in 45.00 seconds.
- Ruff lint and format checks passed for all changed Python files.
- Metadata and policy checks passed; documentation validation passed for 476
  Markdown files.
- `git diff --check` passed; the active capsule is 176 lines and 10,304 bytes.
- No hosted workflow, exhaustive corpus, compatibility matrix, live model call,
  reinstall, or trust-store mutation ran in this checkpoint.

## Follow-ups

Installed checkpoint `194d697` predates this correction. After the operator
returns, build and verify the exact candidate, perform one attended refresh,
trust its changed hook inventory, and run one bounded current-profile activation
canary. AR-180 remains open until that exact graph passes; AR-119 remains open
for its wider production gates.
