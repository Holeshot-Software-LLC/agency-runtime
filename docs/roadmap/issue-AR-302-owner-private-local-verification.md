---
title: "AR-302: Make local verification owner-private by construction"
status: open
category: roadmap
created: 2026-08-26
updated: 2026-08-26
tags: [testing, packaging, security, linux, developer-experience]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/RELEASE_CHECKLIST.md
  - scripts/build_distributions.py
  - tests/conftest.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: release
issue_id: AR-302
priority: p0
tracker_url: null
depends_on: []
blocks: [AR-297]
---

# AR-302: Make local verification owner-private by construction

## Problem

Two documented local verification paths inherit a cooperative host umask of
0002 even though their security contracts require owner-private or at least
non-group-writable paths. The release builder creates archive modes that the
independent verifier rejects. The named pytest spine creates its shared
`offline-config` directory as mode 0775, so configuration trust rejects it and
produces broad secondary failures. Both paths pass when the operator first
establishes an owner-private umask and trusted temporary root.

## Current state

- The AR-297 build under ambient umask 0002 fails independent `RECORD`
  permission verification; the same exact source under umask 0077 passes.
- The named spine under ambient umask 0002 exits 1 with 191 failures, 667
  passes, and 3 skips because the shared config parent is mode 0775.
- With umask 0077 and a private temp root, the remaining failures come only
  from intentionally running a development interpreter below untrusted `/tmp`.
  Using trusted `/usr/bin/python3` then passes 858 tests with 3 skips.
- CI already establishes private temporary roots. No trust predicate was
  weakened and no failed run is relabelled successful.
- Tracker creation is prohibited by the active task.

## Approach

Make repository-owned creation boundaries establish and verify the required
permissions independently of ambient cooperative umasks. Keep executable and
configuration namespace checks strict. Give local commands an early bounded
diagnostic when the selected interpreter itself is below an untrusted path.
Retain CI's explicit private-root setup as defense in depth.

## Dependencies

- AR-297 owns the exact Linux candidate evidence that exposed both failures.
- The release verifier and namespace validators remain authoritative.
- Tracker creation requires separate outward-write authorization.

## Acceptance

- [ ] Distribution build and verification produce canonical safe modes under
      ambient umask 0002 without an operator preamble.
- [ ] The named fast spine creates a trusted offline configuration under umask
      0002 when invoked with a trusted interpreter.
- [ ] An interpreter below an untrusted namespace fails early with one bounded
      actionable diagnostic rather than broad secondary failures.
- [ ] Focused packaging, configuration-trust, and suite-isolation regressions
      pass with warnings treated as errors.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.
