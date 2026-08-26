---
title: "Admit cooperative sdist modes"
status: active
category: worklog
created: 2026-08-26
updated: 2026-08-26
tags: [release, packaging, permissions, linux]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-302-owner-private-local-verification.md
  - docs/decisions/0177-make-local-verification-private-by-construction.md
supersedes: []
superseded_by: null
type: worklog
commit: 2a9dc984a904140fc0d744dd90629944cefeac53
short: 2a9dc984
date: 2026-08-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-302-owner-private-local-verification.md
---

# Worklog detail: Admit cooperative sdist modes

## Purpose

Complete AR-302's ambient-umask source normalization after the first immutable
build crossed the wheel repair and exposed the equivalent sdist projection.

## Approach

Add only mode 0664 regular files and mode 0775 directories to the finite raw
sdist allowlists. Canonical output remains exactly 0644/0755. A regression builds
cooperative and private raw sdists and requires byte-identical canonical output;
the exhaustive permission-bit allowlist test was updated to the exact new set.

## Challenges encountered

The original failure stopped at the wheel central directory, masking the later
setuptools sdist modes. The immutable ambient-0002 retry provided the exact next
failure rather than justification for a broader permission allowance.

## Decisions and alternatives

ADR-0177 owns the bounded producer-mode normalization. Relaxing canonical output
or accepting arbitrary tar modes remains rejected.

## Verification

`tests/test_canonicalize_distributions.py` passes 105 tests under caller umask
0002 with warnings as errors. Changed Ruff, documentation validation, capsule
bounds, and diff checking exit 0.

## Follow-ups

Rebuild and independently verify the new immutable commit under caller umask
0002, then complete AR-302's named spine and AR-297's live matrix.
