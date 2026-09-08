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
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/743
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

Normal merge `1acaf7b4` integrates AR191/PR741 `a8c2ca54`, preserving current
main product/tests/scripts and all frozen AR185/190/408/409 acceptance files
byte-identically. Four shared documentation conflicts are resolved as current
main record unions plus this retained AR194 slice. This immediate ledger also
records the incoming AR191 merge, with its exact subject and detail link.

The identical focused command above was rerun on the integrated tree:

```text
........................................................................ [ 62%]
............................................                             [100%]
116 passed, 42 deselected in 2.46s
```

Exit0. This is a fresh test result, not a rerun of owner status. The original
four-module installed/source comparison and healthy status remain explicitly
bound to their earlier read, before any parent-owned upgrade. Main integration
does not alter those four source modules or authorize another service action.

Parent coordinates normal main integration, PR URL and serial publication.
PR743 carries the retained record; final docs require-tracker pass1,267 files,
strict tracker parity400, repository Ruff/format770 and diff checks pass.
AR192/PR742 merged `bad847ab` at00:40:01Z; normal integration `0799b3df`
includes its exact immediate ledger `fde0d891`. Two documentation conflicts
preserve both current rows and the retained AR194 slice. Product/tests/scripts
and frozen acceptance files remain identical to incoming main; the fresh116
result above is explicitly reused, not rerun. Parent now authorizes AR194's
normal PR/merge, then the final runtime-fix package rather than another oldest
record. No owner status or service operation was repeated.
Before publication preserve concurrent AR-190/191/192/409 records and frozen
acceptance evidence. AR-194 remains open for exact native Windows stale-task
repair and post-repair reachability on the owner's Windows machine.
