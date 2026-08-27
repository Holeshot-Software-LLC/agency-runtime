---
title: "Close named repository gates"
status: active
category: worklog
created: 2026-08-27
updated: 2026-08-27
tags: [ar-297, verification, tests, lint, mutation-testing]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0113-prove-decision-conformance-with-isolated-mutations.md
supersedes: []
superseded_by: null
type: worklog
commit: c914cc46ef4487df424129e877cb320436258900
short: c914cc46
date: 2026-08-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
---

# Worklog detail: Close named repository gates

## Purpose

Close AR-297's named repository-gate row on the exact committed candidate tree
with retained, content-addressed outputs and exits.

## Approach

Run every command named by `AGENTS.md` using the protected repository
interpreter where Python development dependencies are required. Capture each
command into owner-private stdout, stderr, and exit receipts, preserve failed
environmental diagnostics under distinct retry names, and run the mutation
evaluator with the strict umask required by its owner-private-copy contract.

## Challenges encountered

The protected venv did not contain a Ruff executable, so the first two Ruff
capture attempts never launched; isolated Ruff 0.16.5 then passed both gates.
The installed consumer launcher lacked pytest. The first protected
decision-conformance rerun inherited ambient `umask 0002`, and its production
private-path guard correctly rejected the group-writable copied checkout before
baseline. The retained `umask 077` rerun completed the full evaluator.

## Decisions and alternatives

No source or policy was changed to reinterpret an environmental failure. The
final evaluator ran from committed source with the protected interpreter and a
private creator mask; its earlier fail-closed receipts remain evidence rather
than being overwritten. Optional exhaustive workflow dispatch remains outside
this bounded Linux gate and is not required by `AGENTS.md`.

## Verification

- Metadata, policy availability, worklog currentness, documentation, and diff
  integrity all exit 0 for 912 Markdown documents.
- Ruff lint `82b3e6a6...4f18` and format `82826f75...0f1` exit 0.
- Named warning-strict Python spine `25cc4f01...4cb` passes 860 tests with 3
  skips; dashboard UI `2eb1981a...3ef9` passes 138/138.
- Routing 1.4.0 `eeb12164...10d4` passes.
- Decision conformance `9a45044f...0a71` passes baseline, kills 167/167
  mutations, has zero survivors/invalids, and leaves source unchanged.
- Every final gate's exit receipt hashes to `bde29436...120` (`exit_code=0`).

## Follow-ups

Complete the ordinary Claude, Hermes, and OpenClaw proofs, then tear down every
AR-297-labelled container and issue the Linux-scoped verdict.
