---
title: "AR-194 service inspection reconciliation"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [dashboard, launcher, portability, evidence, backlog]
related:
  - docs/roadmap/issue-AR-194-inspect-owned-service-runtimes-across-python-versions.md
  - docs/roadmap/acceptance/evidence/AR-194-service-runtime-reconciliation-20260907.md
  - docs/roadmap/handoffs/issue-AR-194.md
  - docs/decisions/0117-unify-owner-control-authority.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: cd62d6588d8660033bf309220b74dcc1dbdebef6
short: cd62d658
date: 2026-09-07
pr: null
related_issues:
  - docs/roadmap/issue-AR-194-inspect-owned-service-runtimes-across-python-versions.md
---

# Worklog: reconcile service inspection and retain Windows repair proof

## Purpose

The July record mixed an implemented cross-interpreter inspection repair with
an uncompleted Windows task/runtime repair and an obsolete presence verifier.
Separate those claims without closing a meaningful platform-evidence gap.

## Approach

On source `f408b6f2`, inspected launcher, service core, inspection and CLI paths;
read governing ADR-0040, ADR-0050, superseded ADR-0109 and current ADR-0117.
Ran existing bounded tests and the installed owner's read-only service status.
Four relevant source modules match installed package bytes. Saved complete
status JSON with only the owner-home prefix normalized for portability.
No source/test edit, package change or service mutation was necessary.

Removed AR-194's obsolete dependency on retired AR-196 and the reciprocal
block edge, retaining historical narrative and all five original criterion
states verbatim. Added reciprocal ADR-0117 and registry/capsule links, queue
order47 after reserved AR-190/191/192, and exact AR-189 PR738 merge readback.
The AR-189 merge already had a faithful narrow ledger checkpoint `297e8fc2`
before this substantive change.

## Challenges encountered

The first documentation check correctly reported the removed dependency's
still-present reciprocal edge and the just-merged AR-189 missing ledger row.
Both are corrected; no verifier result was suppressed. Historical Windows
state cannot be inferred from a healthy Linux service. Synthetic
`cpython-999` fixtures prove bounded tag/identity behavior, not actual support
or execution for that interpreter. Native Windows cases remain unexecuted.

## Decisions and alternatives

Apply existing ADR-0117 authority only; no new ADR, verifier or human-presence
ceremony. Preserve current tag-only execution preparation and identity-bound
shell-free probes. Do not repair a healthy Linux service to imitate the July
Windows transition, and do not relabel current Linux status as migration proof.
No acceptance judge or done-state flip is part of this record reconciliation.

## Verification

- Exact focused command and stdout in the receipt:116 passed,42 deselected,
  2.75s, including a real current-interpreter cache-tag probe under Linux.
- Installed `agency dashboard service status --json` from `/tmp`: exit0 in
  0.202215105s; owned/current/enabled/active/reachable Linux systemd service;
  no drift or repair recommended. Existing pinned worker `4329d760` only.
- Metadata/docs require-tracker pass1,252 files; policy/worklog checks pass;
  strict tracker parity passes400 items/two historical PR exclusions.
- Repository Ruff passes;769 files formatted; diff whitespace clean; complete
  five-criterion checkbox block byte-identical to original source.
- No exhaustive corpus, native Windows, provider/model call, daemon mutation,
  packaging or broad installed-main claim. This documentation-only checkpoint
  does not relabel earlier spine runs as new verification.

## Follow-ups

Parent coordinates normal main integration, PR URL and serial publication.
Before publication preserve concurrent AR-190/191/192/409 records and frozen
acceptance evidence. AR-194 remains open for exact native Windows stale-task
repair and post-repair reachability on the owner's Windows machine.
