---
title: Canonicalize generated distribution metadata across Windows and Linux
status: active
category: worklog
created: 2026-07-20
updated: 2026-07-20
tags:
  - release
  - reproducibility
  - metadata
  - windows
  - linux
  - security
related:
  - docs/roadmap/issue-AR-107-build-release-artifacts-from-canonical-git-blobs.md
  - docs/decisions/0037-layered-pinned-supply-chain-gates.md
  - docs/decisions/0074-build-byte-deterministic-release-artifacts.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 9f98db3b6a67b916b850e47d51085fee9ae606c3
short: 9f98db3
date: 2026-07-20
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/111
related_issues:
  - docs/roadmap/issue-AR-107-build-release-artifacts-from-canonical-git-blobs.md
---

# Worklog detail: Canonicalize generated distribution metadata across Windows and Linux

## Purpose

Close the last byte-reproducibility gap in the release pipeline. Real builds
from the same reviewed source commit exposed platform-specific line endings in
backend-generated wheel and source-distribution metadata, which also changed
wheel `RECORD` hashes. The strict verifier additionally decoded a UTF-8
description body through a lossy email-message projection and expected the
generated `SOURCES.txt` manifest to end with a newline even though the pinned
backend does not emit one.

## Approach

- Share only finite declarative allowlists for generated wheel and
  source-distribution text.
- Preserve every source-derived payload byte exactly.
- Normalize CRLF and lone CR to LF only for allowlisted generated metadata.
- Rebuild wheel `RECORD` locally from the normalized payload set and reject
  ambiguous multiple-record roots.
- Keep the canonical writer and independent verifier implementations separate.
  The verifier imports the allowlists but not the writer or its `RECORD`
  implementation.
- Decode core-metadata bodies from raw bytes with strict UTF-8 and verify the
  pinned backend's exact sorted, no-final-newline `SOURCES.txt` payload.

## Challenges encountered

Container-only canonicalization was insufficient because the build backend
materializes generated metadata using the host's text conventions. Broad
newline conversion would have destroyed the promise that committed source
payloads remain byte-exact, so the normalization boundary had to be a finite
root-relative allowlist.

The standard email API's text projection replaced a valid UTF-8 em dash with
the replacement character. The verifier now requests decoded raw bytes and
performs strict UTF-8 decoding itself. Real backend inspection also showed that
the pinned `setuptools` `SOURCES.txt` payload has no final newline; reproducing
the backend contract exactly avoids a verifier-only fiction.

## Decisions and alternatives

The implementation follows
[ADR-0074](../decisions/0074-build-byte-deterministic-release-artifacts.md).
It rejects broad payload normalization, sharing executable writer logic with
the verifier, tolerating replacement decoding, trusting a backend-provided
`RECORD`, and accepting multiple distribution metadata roots.

## Verification

- Warning-strict full suite: 6,877 passed, 35 skipped, 3 deselected.
- Coverage: 44,098 statements and 15,004 branches at 100.00%, with zero misses
  or partial branches.
- Focused canonical writer and verifier suites: 340 verifier tests and 119
  canonicalizer/contract tests passed at 100% line and branch coverage.
- Dashboard: 88/88 passed at 100.00% line, branch, and function coverage.
- Performance: 3/3 passed in an isolated uninstrumented run.
- Routing and delegation: all 25 routing gates and 12/12 delegation contracts
  passed.
- Full roster: all 263 approved agents participated in lexical and semantic
  retrieval; every recall and compatibility gate was 1.0, with zero identity
  leakage and zero quarantined or retired bundled entries.
- Real Windows and WSL backend outputs converged after canonicalization to wheel
  SHA-256 `a3f4e94df2907158c33f96dc61c5e7c1aa65144caed63d865155de36902bcb3d`
  and source-distribution SHA-256
  `2e403206cf4ce38d3c1b9bbba064c75e1cf35d1c864e57bf36cf2d89dcb4081a`.
- Documentation, Ruff lint and format, release hygiene, Bandit, dependency
  audit, zizmor, and whitespace gates passed.

## Follow-ups

Build and independently verify the exact ledger commit on Windows and WSL,
require hosted byte parity and artifact smoke tests on the PR head and merge
commit, then install and smoke the merged wheel before completing
[AR-107](../roadmap/issue-AR-107-build-release-artifacts-from-canonical-git-blobs.md).
