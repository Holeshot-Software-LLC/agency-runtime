---
title: "Scope install residual drift to resolved hosts"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [install, drift, testing]
related:
  - docs/roadmap/issue-AR-407-scope-install-drift-to-requested-hosts.md
  - docs/roadmap/acceptance/evidence/AR-407-scoped-install-drift-20260907.md
supersedes: []
superseded_by: null
type: worklog
commit: 15a18861b3d32fe55e3092d918bb63c494913e45
short: 15a18861
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-407-scope-install-drift-to-requested-hosts.md
---

# Worklog detail: Scope install residual drift to resolved hosts

## Purpose

Fix an actual live misleading refresh warning without touching another host.

## Approach

Pass resolved targets into the existing advisory projection helper and filter
before selecting its first report. Leave global status and completion policy
unchanged. Real temporary pointer serialization backs 35 new regressions.

## Challenges encountered

The first regression fixture selected prepared Codex refresh instead of generic
install; explicit profile selection corrected it before the valid red run.
That valid run had ten output failures plus two new-signature failures.
The live diagnostic must import installed runtime comparison, not a checkout
overlay, and use existing-directory validation without permission repair.

## Decisions and alternatives

No new authority or product policy: apply the established host scope.
Do not suppress global drift, reinstall OpenClaw, load a credential file,
change trust or claim the current running parent's hook state is repaired.

## Verification

Valid red 12 failed/7 passed; same19 green. Expanded focused158/one Windows
deselection. Independent review no findings and35passes. Fresh spine1085/three
skips; UI224/current floors. Actual live mixed-pointer fragment comparison
passes with allfive pointer bytes/metadata and directory metadata unchanged.
Precise transcripts and limitations are in the evidence receipt.

## Follow-ups

Build and validate the exact portable artifact, freeze the evidence candidate,
run isolated acceptance and publish through normal PR/merge. Keep native
activation and operator process-environment repair separate.

Substantive `15a18861` is the bounded implementation/source proof; later artifact and acceptance records must retain their exact candidates.

Evidence freeze `dcd58720` adds the exact ef6523b3 portable artifact under producer umask077, fresh installed MCP/dashboard and all-host generated smoke8/0/0 in5.09s. Candidate source hash equals the live-pointer helper source; no native model-turn claim is added.

Builder packet `625a1488` freezes all three criteria at dcd58720 with bounded source/test/live-state/artifact excerpts. The builder supplies evidence, not verdicts.

Acceptance `d5aed828` records allthree satisfied at dcd58720 and marks AR-407 done. Initial unavailable verifier produced no verdict; exact Claude package/bin group-write removal restored trusted execution, then unchanged packet passed. Tracker closure is queued with normal PR merge.
