---
title: "Worklog detail: Reconcile OpenClaw one-shot child terminal receipts"
status: active
category: worklog
created: 2026-08-24
updated: 2026-08-24
tags: [openclaw, native-child, lifecycle, reconciliation, telegram]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-278-deliver-openclaw-finalizer-results.md
  - docs/roadmap/issue-AR-280-route-native-children-through-host-profiles.md
  - docs/roadmap/issue-AR-281-deliver-finalized-openclaw-child-announcements.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0168-authorize-finalized-openclaw-child-announcements.md
supersedes: []
superseded_by: null
type: worklog
commit: 933d9f4a5bb3dcade7ad6dc726b0d267f0582cde
short: 933d9f4a
date: 2026-08-24
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-264-compile-actionable-contractor-execution-profiles.md
  - docs/roadmap/issue-AR-278-deliver-openclaw-finalizer-results.md
  - docs/roadmap/issue-AR-280-route-native-children-through-host-profiles.md
  - docs/roadmap/issue-AR-281-deliver-finalized-openclaw-child-announcements.md
---

# Worklog detail: Reconcile OpenClaw one-shot child terminal receipts

## Purpose

Close Agency's OpenClaw child lifecycle when the native host reports one
terminal callback. The changed live draw delivered the exact finalized child
result through Telegram and OpenClaw recorded `succeeded` / `delivered`, but
Agency finalized the parent while leaving its delegation and worker open.

## Approach

Observation-only end state now falls through to the Store's exact
launch-bound reconciliation path instead of being treated as fully handled.
When trace-bound persistence fails or loses its receipt, the generated plugin
immediately retries through trace-less durable reconciliation using the exact
accepted requester, worker, and native-run identity already held in child
state. The same fallback runs when an early end is consumed by the later
accepted tool result.

Only the matching in-memory state is removed after the Store confirms the
terminal transition. Genuine pre-acceptance races retain their pending end,
ambiguous or mismatched identities remain rejected, and later duplicate hooks
do not create another transition.

## Challenges encountered

The first expected-red reproduced the split-instance observation swallow and
missing same-callback retry. Independent review then rejected the partial fix
because an early end followed by failed persistence, and sparse reset/delete
events without requester/run fields, still depended on a duplicate hook.
Additional expected-red coverage captured both cases before the exact-state
fallback completed the repair.

An initial Store characterization command inherited shell umask `0002` and
correctly failed the trusted configuration-parent boundary; the changed
`0077` run passed. The ordinary conformance launcher lacked isolated `pytest`,
and the first private evaluator also inherited `0002`; both failures are
retained before the owner-private `0077` pass.

## Decisions and alternatives

The repair uses the Store's existing launch-bound, uniqueness-checked,
replay-safe reconciliation API. It does not infer success from Telegram
delivery, mutate the live Store manually, rely on a duplicate host hook, or
create a `native_child_delivery_verifications` row. Operational return therefore
remains separate from ADR-0156 Rule 4.

No OpenClaw source/configuration or native model route changed. Hermes remained
active and untouched. Codex OAuth/configuration/canary, Claude, and ZCode were
not changed or re-proven.

## Verification

- Expected-red split-instance/retry pair failed before the first correction.
- Expected-red early-end/sparse-reset extension failed before the state-bound
  correction.
- Four-file focused suite: 146 passed, 1 existing skip under `umask 077`.
- Named fast Python spine: 849 passed, 3 skipped.
- Docs metadata/policy/worklog/verification: 783 documents; worklog current at
  1,158 substantive commits before this commit.
- Full Ruff check and format: 682 files; dashboard UI: 134 passed.
- Routing evaluation passed.
- Decision conformance passed baseline and killed 160/160 curated mutations;
  zero survived or invalid; source unchanged.
- `git diff --check` passed.
- Independent re-review found no Critical, High, or Medium issue.

## Follow-ups

Install this Agency-only candidate while OpenClaw is natively stopped, restart
it natively, and prove a genuinely changed child closes the parent,
delegation, and worker while delivering through Telegram. Only after OpenClaw
passes, perform the equivalent Agency-only Hermes proof. ADR-0156 Rule 4 remains
unproven without a host-authored pre-speech artifact receipt.
