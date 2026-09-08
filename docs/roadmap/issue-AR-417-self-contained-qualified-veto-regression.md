---
title: "AR-417: Keep qualified-veto regression self-contained in source archives"
status: done
category: roadmap
created: 2026-09-08
updated: 2026-09-08
tags: [packaging, tests, critic]
related:
  - docs/roadmap/acceptance/issue-AR-417.md
  - docs/roadmap/acceptance/evidence/AR-416-installed-qualified-veto-20260908.md
  - docs/roadmap/issue-AR-416-retain-qualified-critic-veto-causes.md
  - docs/decisions/0074-build-byte-deterministic-release-artifacts.md
  - docs/worklog/2026-09-08-installed-qualified-veto-verification.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-417
priority: p2
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/790
depends_on: []
blocks: []
---

# AR-417: Keep qualified-veto regression self-contained in source archives

## Problem

The new AR-416 regression reads a JSON evidence attachment excluded by the
existing governed source-archive allowlist. The test is distributed without
its input and fails before exercising the diagnostic behavior.

## Current state

Phase done for this issue’s acceptance scope. All three isolated criteria are satisfied at candidate caab4851. The verified
source archive runs all eight regressions with no excluded JSON dependency.
The test-only fix leaves production behavior and archive policy unchanged.

The following paragraphs preserve earlier checkpoints.

Phase focused_review. Canonical b0dfd631 wheel/sdist passed strict Twine and
independent verification. Running the regression from the extracted sdist
produced one FileNotFoundError failure and seven passes. The fix pins the exact
captured critic verdict in the test. Focused suite: 124 passed. Rebuilt source
archive verification passes: extracted regression8passed. No production behavior
changed; isolated acceptance pending.

## Approach

Make the behavioral test self-contained while retaining the complete native
packet in repository evidence. Preserve the archive allowlist and all existing
veto, receipt and failed-finalizer assertions.

## Dependencies

AR-416 owns the receipt repair and installed verification. ADR-0074 owns the
existing canonical build boundary; this fix does not change its policy.

## Acceptance

- [x] The qualified-veto regression passes from the verified extracted source
      archive without requiring the excluded JSON attachment.
- [x] The exact native qualified verdict still exercises the preserved veto,
      receipt projection and failed finalizer, with unchanged production code
      and archive allowlist.
- [x] The issue, tracker, worklog and packaged verification evidence agree.
