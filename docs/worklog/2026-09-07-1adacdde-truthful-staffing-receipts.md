---
title: "Preserve actual staffing failure and timeout receipts"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [workforce, diagnostics, deadlines]
related:
  - docs/roadmap/issue-AR-408-preserve-staffing-failure-receipts.md
  - docs/roadmap/acceptance/evidence/AR-408-staffing-failure-receipts-20260907.md
supersedes: []
superseded_by: null
type: worklog
commit: 1adacdde58fdbf186e370e2d87677efc21da2516
short: 1adacdde
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-408-preserve-staffing-failure-receipts.md
---

# Worklog detail: Preserve actual staffing failure and timeout receipts

## Purpose

Make the live failure diagnosable: a critic that never ran did not veto a team,
and elapsed time without its effective allowance obscures timeout causality.

## Approach

Only a valid negative critic verdict produces the veto reason. Other failures
retain their closed causes. Routing forwards the existing timeout field;
expired admission cannot claim positive allowance. Real Store regressions
exercise durable failure projection and exclude synthetic secrets/body fields.

## Challenges encountered

The live five-call sequence exhausts the strict cap before review. Correcting
its diagnosis does not make it succeed; reservation policy is a separate
package. The existing positive-only receipt shape deliberately omits zero
allowance rather than adding a new stored schema.

## Decisions and alternatives

Apply ADR0209 truthful-cause policy. No budget, retry, selection, mandatory
critic, profile, credential or trust change. Do not infer provider latency
from total native-host wall time or rewrite old immutable failed receipts.

## Verification

Red8failed/2passed; focused23pass; broader325/one skip/one deselection;
independent32pass/no findings. Parent fresh spine1085/three skips69.50s,
UI224/current floors. Exact commands and scope in portable receipt.

## Follow-ups

Freeze isolated acceptance, run package/installed smoke, then PR/merge and
close732. Separately integrate the reviewed quality-preserving AR409 budget
reservations; no live-quality equivalence is claimed here.

Substantive `1adacdde` is the reviewed actual-cause/allowance repair; source tests and existing live traces establish this bounded diagnostic outcome without changing staffing budgets.

Artifact receipt `d9dde3cd` records canonical ef8c714f portable wheel/sdist, independent verifier/Twine, fresh installed MCP/dashboard and all-host generated smoke8/0/0 in5.03s. No native model turn or owner package replacement is claimed.

Packet `795ddf21` freezes three observation-only criteria against artifact-evidence candidate d9dde3cd. No builder verdicts.

Completion `7674aca9` records allthree satisfied isolated judgments against d9dde3cd. Owner CLI replacement and AR409 allocation remain separate.

Merge `8c1845e5` integrates accepted AR185/main00fc1aef and AR409 filing. Only documentary overlaps were resolved by retaining both histories and the accepted AR408 state.
