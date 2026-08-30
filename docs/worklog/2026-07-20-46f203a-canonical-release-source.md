---
title: Build canonical release artifacts on an atomic process boundary
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
commit: 46f203aa52fd028fb0cd775064468197fa77dde7
short: 46f203a
date: 2026-07-20
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/111
related_issues:
  - docs/roadmap/issue-AR-107-build-release-artifacts-from-canonical-git-blobs.md
  - docs/roadmap/issue-AR-108-atomic-owned-process-containment.md
---

# Worklog detail: Build canonical release artifacts on an atomic process boundary

## Purpose

Make a reviewed commit—not checkout filters, host archive libraries, or a
partially owned child process—the authoritative source of every release
artifact byte. The change also closes the process-lifecycle gaps discovered
while exercising the builder on native Windows and Linux.

## Approach

- Materialize release input from exact Git blobs with hostile inherited Git
  configuration disabled, then rehash every file and validate its mode before
  invoking the pinned build backend.
- Canonicalize only container metadata through owned stored-ZIP, RFC 1951
  stored-block gzip, and PAX-tar writers while preserving source and generated
  payload bytes exactly.
- Independently parse and verify physical archive layout, generated metadata,
  dependency projection, manifest membership, and wheel/source parity under
  explicit count, size, path, and compression limits.
- Build on both hosted Windows and Linux, compare the complete pairs byte for
  byte, and expose the canonical artifact name only after parity succeeds.
- Route release, provider, and delegation subprocesses through one policy-free
  core. Windows assigns the kill-on-close Job at creation; Linux gates target
  execution until containment state and I/O workers are durably owned, then
  requires a post-drain terminal receipt.
- Use idempotent descriptor and handle owners across native call-to-store
  boundaries so asynchronous exceptions cannot leak, double-close, or close a
  recycled unrelated resource.

## Challenges encountered

Checkout cleanliness does not prove that Windows working-tree bytes match Git
blobs when line-ending filters are active. Pinned archive libraries also retain
host-dependent container metadata. Independent review then found several
sub-instruction resource-adoption races: Python could be interrupted after a
native resource was returned but before the result was stored. The final design
pre-owns native output storage, transfers aliases idempotently, preserves the
original interruption or error, and attempts every remaining cleanup action.

The Linux supervisor additionally needed to prevent an approved target from
changing its supervisor's limits, scheduler, affinity, priority, or I/O
priority while preserving the same operations against its own children. Native
fork/exec also had to restore the signal defaults normally supplied by
`subprocess.Popen`.

## Decisions and alternatives

[ADR-0074](../decisions/0074-build-byte-deterministic-release-artifacts.md)
rejects building from checkout-filtered bytes or weakening verification through
post-build source normalization. [ADR-0073](../decisions/0073-own-subprocess-trees-atomically.md)
rejects post-creation Job assignment, process-group-only cleanup, and any silent
fallback when strong ownership primitives are unavailable.

## Verification

- Warning-strict full suite: 6,797 passed, 35 skipped, 3 deselected.
- Coverage: 43,827 statements and 14,916 branches at 100.00%, with zero misses
  or partial branches.
- Focused lifecycle proof: 426 passed, 15 platform skips; 1,687 statements and
  490 branches at 100.00%.
- Native lifecycle proof: Windows launch returned `owned-ok`; WSL passed 12/12
  execution-gate, descendant, resource-control, terminal-receipt, interruption,
  and signal-restoration regressions.
- Performance: 3/3 passed uninstrumented.
- Dashboard: 88/88 passed at 100.00% line, branch, and function coverage.
- Routing and delegation: all gates passed; precision@3 was 0.9744 and required
  recall, top-1, top-k, and delegation metrics were 1.0.
- Full roster: 263/263 approved agents participated; candidate/top-10 recall,
  compatibility, abstention, and turn-state gates were 1.0; identity leakage
  was zero.
- Ruff, documentation metadata and links, worklog generation, release hygiene,
  Bandit, dependency audit, pip consistency, zizmor, and diff checks passed.

## Follow-ups

Complete the hosted Windows/Linux byte-parity and `core.autocrlf=true` gates,
merge [PR #111](https://github.com/Holeshot-Software-LLC/agency-runtime/pull/111),
then install and smoke the exact merged artifact before closing
[AR-107](../roadmap/issue-AR-107-build-release-artifacts-from-canonical-git-blobs.md)
and [AR-108](../roadmap/issue-AR-108-atomic-owned-process-containment.md).
