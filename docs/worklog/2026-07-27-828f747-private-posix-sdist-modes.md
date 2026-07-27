---
title: "Worklog detail: Normalize owner-private POSIX sdist modes"
status: active
category: worklog
created: 2026-07-27
updated: 2026-07-27
tags: [release, packaging, linux, reproducibility, security]
related:
  - docs/worklog/README.md
  - docs/roadmap/README.md
  - docs/roadmap/issue-AR-184-normalize-private-posix-sdist-modes.md
  - docs/decisions/0074-build-byte-deterministic-release-artifacts.md
supersedes: []
superseded_by: null
type: worklog
commit: 828f747b1fafef513e5891de6b956aa4802c83f0
short: 828f747
date: 2026-07-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-184-normalize-private-posix-sdist-modes.md
---

# Worklog detail: Normalize owner-private POSIX sdist modes

## Purpose

The first exact restrictive-umask Linux producer after AR-183 advanced through
wheel validation but failed closed on the raw source distribution. Setuptools
preserved owner-private file and directory modes that the finite source-tar
allowlist had not reviewed.

## Approach

Add only ordinary file `0600` and directory `0700` to the exact raw sdist mode
sets. Preserve the governed Windows PE exception and every member-type,
topology, identity, and size guard. Canonical output remains ordinary file
`0644` and directory `0755`; no subset or permission-mask rule is used.

## Challenges encountered

The canonical producer intentionally left its destination unpublished, so a
separate raw exact-commit build was required for diagnosis. It counted 1,353
regular files at `0600`, two metadata files at `0644`, and 40 directories at
`0700`, with no other mode or member type. This matched the pinned setuptools
`umask 077` behavior and exposed both required modes before another canonical
rerun.

## Decisions and alternatives

Weakening the producer umask, applying blanket post-build chmod, or accepting
every mode no more permissive than a public projection were rejected. Exact set
membership keeps executable, special-bit, special-file, and unreviewed modes
fail closed. ADR-0074 records this durable normalization boundary.

## Verification

- The canonicalizer suite passes 105 tests, including exhaustive permission-bit
  membership, private/public byte convergence, special bits, special member
  types, and nonempty-directory rejection.
- The four-file canonicalizer, builder, verifier, and release-package suite
  passed 411 tests in 137.69 seconds before the final defense-in-depth test
  expansion; production code did not change afterward.
- Two independent reviews found no Critical, High, or Medium issue. Their
  governance and defense-in-depth recommendations were incorporated.
- Ruff lint and format, metadata, policy, worklog, documentation, and diff
  checks passed.

## Follow-ups

Run the exact committed Linux producer under `umask 077`, prove strict Twine and
portable verification, compare its sdist byte-for-byte with Windows, and verify
the merged release set under
[AR-184](../roadmap/issue-AR-184-normalize-private-posix-sdist-modes.md).
