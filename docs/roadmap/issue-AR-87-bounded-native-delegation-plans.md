---
title: "AR-87: Produce bounded native delegation plans and correction"
status: done
category: roadmap
created: 2026-07-18
updated: 2026-07-20
tags: [delegation, routing, native-hosts, stop, evidence]
related:
  - docs/roadmap/issue-AR-27-authoritative-delegation-stop-enforcement.md
  - docs/roadmap/issue-AR-58-unit-aware-delegation-assignment.md
  - docs/decisions/0071-bound-native-delegation-correction.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: routing
issue_id: AR-87
priority: p0
tracker_url: "https://github.com/Holeshot-Software-LLC/agency-runtime/issues/88"
depends_on: [AR-27, AR-58, AR-82]
blocks: [AR-88, AR-89]
---

# AR-87: Produce bounded native delegation plans and correction

## Problem

Existing work-unit suggestions do not carry the complete guidance needed to keep
the parent responsive, distinguish optional from strongly preferred delegation,
or enforce one safe corrective pass without Stop loops.

## Current state

Unit-specific routing now produces a complete content-free durable plan with a
typed delegation policy and exact native guidance. Recommendations remain
separate from authoritative execution receipts; a strongly preferred plan gets
at most one evidence-checked correction before terminalization. Cross-host
hosted proof remains.

## Approach

Generate a replayable plan containing stable unit identity, goal and deliverable
references, compatible specialists, confidence and rationale, dependencies,
parallel hints, mutation and resource scope, required tools and evidence, and
delegation strength. Default configuration to `prefer` while letting the native
host refine or decline the topology. Permit one atomic Stop correction for an
unfulfilled strongly preferred plan, then terminate truthfully.

## Dependencies

AR-27 owns authoritative delegation and Stop evidence. AR-58 and AR-82 own
unit-specific full-roster assignment.

## Acceptance

- [x] Typed configuration exposes observe/prefer behavior and bounded thresholds.
- [x] Durable plans contain the complete metadata contract without raw prompt content.
- [x] Native host guidance names exact units, specialists, mechanisms, and evidence.
- [x] Recommendations remain distinct from authoritative worker and run receipts.
- [x] Preferred plans may be declined with a durable bounded reason.
- [x] Strongly preferred plans receive at most one evidence-checked correction.
- [x] The second Stop terminalizes without opening a new trace or claiming execution.
- [x] Cross-host lifecycle, full coverage, and portability gates pass.
