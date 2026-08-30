---
title: "Worklog: Separate the Codex activation child goal"
status: active
category: worklog
created: 2026-07-28
updated: 2026-07-28
tags: [codex, canary, delegation, operator-presence]
related:
  - docs/roadmap/issue-AR-195-separate-codex-canary-parent-and-child-goals.md
  - docs/roadmap/issue-AR-196-authorize-prepared-dashboard-service-repair.md
  - docs/decisions/0077-prove-codex-activation-behaviorally.md
  - docs/decisions/0109-prepare-dashboard-service-repair-before-operator-presence.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 42da9907c3d2389f6f8856c09f199da1da272d6a
short: 42da990
date: 2026-07-28
pr: null
related_issues:
  - docs/roadmap/issue-AR-195-separate-codex-canary-parent-and-child-goals.md
  - docs/roadmap/issue-AR-196-authorize-prepared-dashboard-service-repair.md
---

# Worklog detail: Separate the Codex activation child goal

## Purpose

Repair the exact installed canary failure without weakening ordinary Agency
delegation. The canary had persisted its parent instruction to delegate as the
child's own goal, so a direct child assignment could not satisfy the hook's
exact goal hash. The same investigation exposed the separate fail-closed
dashboard-service operator-presence gap.

## Approach

Keep the nonce-bound parent probe unchanged as the routing admission contract,
but add one bounded direct child review goal and use it in deterministic
routing and recipe replay. Preserve the general native-child equality check.
Add explicit no-retry/no-invalid-wait instructions and project a timeout only
from the owned-process `timed_out` bit through existing allowlists. Record the
dashboard-service gap as AR-196 and the prepared action-specific design as
ADR-0109 before implementation.

## Challenges encountered

Codex encrypts persisted parent spawn messages, so retained rollout text could
not prove whether the hook received an opaque value or a model-authored
paraphrase. The hook's fixed denial and absence of all child evidence were
authoritative; the parent/child contract contradiction supplied a safe repair
that did not require decrypting private host state or relaxing the guard.

## Decisions and alternatives

Do not accept opaque or merely label-matched child tasks. The canary uses a
direct child goal while every normal planned child remains bound to the exact
persisted goal hash. Do not reuse generic or adjacent Windows Hello authority
for dashboard repair; ADR-0109 requires a separate prepared transaction.

## Verification

- 121 focused canary, hook, proof, and activation tests passed.
- The strengthened activation-contract module passed 20 tests.
- An independent review ran 99 focused tests and found no scoped finding.
- Targeted Ruff lint/format, documentation validation for 499 files, and
  `git diff --check` passed.

## Follow-ups

- Run the named fast production spine and one exact installed live canary for
  [AR-195](../roadmap/issue-AR-195-separate-codex-canary-parent-and-child-goals.md).
- Implement and attend the state-bound dashboard-service repair in
  [AR-196](../roadmap/issue-AR-196-authorize-prepared-dashboard-service-repair.md).
