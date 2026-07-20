---
title: Harden hosted release proofs across Windows and Linux
status: active
category: worklog
created: 2026-07-20
updated: 2026-07-20
tags:
  - release
  - reproducibility
  - security
  - windows
  - linux
  - portability
related:
  - docs/roadmap/issue-AR-107-build-release-artifacts-from-canonical-git-blobs.md
  - docs/roadmap/issue-AR-108-atomic-owned-process-containment.md
  - docs/decisions/0073-own-subprocess-trees-atomically.md
  - docs/decisions/0074-build-byte-deterministic-release-artifacts.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: bb8ce93281935a659ecf8a10ddce04c499a557a4
short: bb8ce93
date: 2026-07-20
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/111
related_issues:
  - docs/roadmap/issue-AR-107-build-release-artifacts-from-canonical-git-blobs.md
  - docs/roadmap/issue-AR-108-atomic-owned-process-containment.md
---

# Worklog detail: Harden hosted release proofs across Windows and Linux

## Purpose

Repair the first hosted run of the canonical release pipeline without weakening
its provenance, containment, or byte-determinism guarantees. The failures
exposed real portability gaps in Linux interpreter selection, Python 3.10
exception handling, Windows source-tar validation, and the proof that a clean
CRLF checkout cannot influence canonical Git-blob artifacts.

## Approach

- Prefer the active private Python interpreter for the Linux supervisor while
  retaining the base executable only as an absence fallback; never fall back
  from a present but untrusted active interpreter.
- Preserve cleanup diagnostics through the shared Python 3.10-compatible
  exception-note helper and make simulated Windows process-handle transfer
  exact-once on every host.
- Validate PAX source mtimes with the same exact nearest-even integer semantics
  used by Python's tar writer instead of truncating positive subsecond values.
- Add a command-scoped `core.autocrlf=true` proof that authenticates the exact
  reviewed LF blob, rewrites only `LICENSE` to physical CRLF through stable
  descriptors, refreshes that worktree's index, and then re-proves clean HEAD,
  blob identity, path identity, and final bytes.
- Centralize the proof's six exact Git operations in a narrow public
  `ReleaseGit` API. It accepts no arbitrary command, path, configuration,
  standard input, or success code, and works in linked worktrees without
  mutating shared Git configuration or attributes.
- Run that proof immediately before both hosted platform builds and measure its
  production module in the same warning-strict 100% coverage gate.

## Challenges encountered

GitHub's Ubuntu environment provided a private copied interpreter through
`sys.executable` while `_base_executable` pointed into a shared toolcache whose
permissions correctly failed the runtime's executable trust policy. On
Windows, Python's PAX writer preserves fractional mtime in the extended record
but writes the adjacent USTAR header using nearest-even rounding, including
half ties.

The first CRLF proof design used `.git/info/attributes`. Independent review
caught that this path is shared across linked worktrees and was derived from
the wrong Git directory. The final design uses a command-scoped override and a
real linked-worktree regression, leaving common config and attributes byte-for-
byte unchanged. A second review moved the proof onto a public exact grammar and
made its receipt hash derive from a final post-Git identity-bound reread.

## Decisions and alternatives

The change preserves the fail-closed boundaries in
[ADR-0073](../decisions/0073-own-subprocess-trees-atomically.md) and
[ADR-0074](../decisions/0074-build-byte-deterministic-release-artifacts.md).
It rejects a permissive interpreter fallback, truncating archive timestamps,
building from normalized checkout bytes, persistent shared Git metadata, and a
generic command-scoped Git execution API.

## Verification

- Warning-strict full suite: 6,873 passed, 35 skipped, 3 deselected.
- Coverage: 44,046 statements and 14,986 branches at 100.00%, with zero misses
  or partial branches.
- Python 3.10 changed-file suite: 555 passed, 1 expected platform skip.
- Public Git API and CRLF proof: 110/110 passed on Windows Python 3.13, Windows
  Python 3.10, and WSL Python 3.12; 476 statements and 164 branches were covered
  at 100.00% on each measured host.
- Cross-platform release and owned-process regression set: 528 passed with one
  expected skip on both Windows and WSL before the final API-only expansion.
- Performance: 3/3 passed uninstrumented.
- Dashboard: 88/88 passed at 100.00% line, branch, and function coverage.
- Routing and delegation: all 25 gates and 12/12 contracts passed; precision@3
  was 0.9744 and required recall, top-1, top-k, and delegation metrics were 1.0.
- Full roster: all 263 approved agents participated through lexical and
  semantic retrieval; candidate and top-10 recall were 1.0 with zero identity
  leakage or quarantined bundled entries.
- Ruff, formatting, documentation metadata and links, worklog generation,
  release hygiene, Bandit, dependency audit, pip consistency, zizmor, tracker
  mapping, and diff checks passed.

## Follow-ups

Require the hosted Windows/Linux builds, byte-parity gate, and artifact smokes
to pass on the exact PR head and merge commit. Then install and smoke the exact
merged wheel on Windows/Codex and WSL before completing
[AR-107](../roadmap/issue-AR-107-build-release-artifacts-from-canonical-git-blobs.md).
