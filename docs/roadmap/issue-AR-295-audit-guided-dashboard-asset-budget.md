---
title: "AR-295: Audit guided dashboard asset budget"
status: done
category: roadmap
created: 2026-08-25
updated: 2026-08-26
tags: [testing, dashboard, packaging, release]
related:
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
  - docs/roadmap/issue-AR-296-project-effective-inference-topology.md
  - docs/roadmap/handoffs/issue-AR-290.md
  - docs/RELEASE_CHECKLIST.md
  - tests/test_release_packaging.py
  - agency_runtime/dashboard/app.css
  - agency_runtime/dashboard/app.js
  - agency_runtime/dashboard/dashboard-render.js
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: testing
issue_id: AR-295
priority: p0
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/333
depends_on: [AR-290]
blocks: [AR-296]
---

# AR-295: Audit guided dashboard asset budget

## Problem

The pre-push workflow-contract gate measured 374,372 bytes of shipped dashboard
assets after AR-290 added its first-run journey. That exceeded the existing
360 KiB ceiling by 5,732 bytes and correctly stopped publication. The old
comment named a 355,184-byte audit even though current main had already reached
365,821 bytes, leaving only 2,819 bytes for legitimate UI growth.

## Current state

- AR-290 adds 8,551 bytes across setup DOM construction, posture rendering,
  and minified responsive styling; its behavior is covered by all 136 UI tests.
- The setup surface is a required consumer feature, not generated debris or an
  accidentally bundled resource.
- A 368 KiB ceiling is 376,832 bytes, leaving a narrow 2,460-byte margin above
  the exact candidate rather than disabling or broadly relaxing the guard.
- Tracker issue [#333](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/333)
  is linked and closed to match this completed record.

## Approach

Keep the tested setup journey and update the release-packaging assertion and
its audit comment to the exact measured payload. Preserve a sub-one-percent
headroom so future dashboard growth still fails the pre-push gate and requires
an explicit new audit.

## Dependencies

- AR-290 owns the guided setup behavior and its UI coverage.
- The existing release-packaging test remains the authoritative shipped-asset
  inventory and byte ceiling.

## Acceptance

- [x] The pre-fix pre-push gate fails on the exact 374,372-byte payload.
- [x] Every counted asset is a required shipped dashboard resource.
- [x] The ceiling and diagnostic name agree at 368 KiB.
- [x] The new ceiling leaves less than one percent unmeasured headroom.
- [x] All 161 workflow-contract tests pass with warnings strict.
- [x] Tracker issue #333 is linked and closed to match canonical done status.

## Verification evidence

Current main totals 365,821 bytes across the ten guarded resources. AR-290 adds
1,761 bytes of CSS, 4,492 bytes of app orchestration, and 2,298 bytes of setup
rendering, producing the exact 374,372-byte candidate. The unchanged pre-push
gate failed `test_release_resources_are_addressable` at 360 KiB. After the
bounded audit update, all 161 workflow-contract tests pass in 26.59 seconds.
