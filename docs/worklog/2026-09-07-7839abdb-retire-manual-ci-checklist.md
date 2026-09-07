---
title: "Retire the superseded AR-177 manual-CI checklist"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [backlog, ci, evidence]
related:
  - docs/roadmap/issue-AR-177-make-exhaustive-python-ci-manual.md
  - docs/decisions/0234-retire-superseded-manual-ci-checklist.md
  - docs/roadmap/acceptance/evidence/AR-177-manual-ci-reconciliation-20260907.md
supersedes: []
superseded_by: null
type: worklog
commit: 7839abdb402c45bcbe4f468e44c895add46d75ac
short: 7839abdb
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-177-make-exhaustive-python-ci-manual.md
---

# Worklog detail: Retire the superseded AR-177 manual-CI checklist

## Purpose

Remove a duplicate mandatory diagnostic/release checklist while retaining the
implemented manual-only CI behavior and every original acceptance state.

## Approach

ADR-0234 applies the existing ADR-0105/AR-186 delivery rule. AR-177 is wont_do,
not accepted. Reciprocal successor and registry links preserve provenance.
The capsule and queue distinguish 118 on this branch from 119 on main.

## Challenges encountered

The one retained hosted manual run failed at whitespace validation before
coverage/compatibility allocation. It cannot prove a complete manual topology,
billing repair, current hosted health or savings. Its ten job rows are retained.

## Decisions and alternatives

Do not dispatch exhaustive CI merely to retire an obsolete mandatory gate.
Do not weaken the four shards, six sessions or unchanged 97-percent floor.
Keep AR-156/159 and AR-176's separate unresolved obligations.

## Verification

Fresh focused workflow/controller/classifier run: 222 passes, five Windows-named
deselections, 6.70s. Source equals d2125438; AR-176 spine/UI receipts are explicitly
reused, not relabelled as new runs. Strict metadata, policy, worklog, docs,
tracker, Ruff, 766-file formatting and whitespace checks pass.

## Follow-ups

Normal PR/merge/readback, then AR-178. Parallel read-only investigations now
cover AR-178 relevance, AR-176 historical mapping and the live Codex hook
warning/credential failure. No Windows, new key, trust bypass or service restart.

Substantive retirement `7839abdb` is recorded here exactly; this ledger does not alter the retirement or original acceptance states.
