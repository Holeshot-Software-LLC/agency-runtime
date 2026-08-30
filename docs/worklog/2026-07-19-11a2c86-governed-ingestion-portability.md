---
title: "Worklog detail: Close governed ingestion and hosted portability gaps"
status: active
category: worklog
created: 2026-07-19
updated: 2026-07-19
tags: [roster, remediation, provenance, ci, portability, security]
related:
  - docs/roadmap/README.md
  - docs/decisions/0013-approval-gated-roster-activation.md
  - docs/decisions/0030-versioned-quantitative-evaluation-gates.md
  - docs/decisions/0040-preserve-environment-owned-python-launchers.md
  - docs/decisions/0066-package-audited-roster-and-sync-quarantined-deltas.md
supersedes: []
superseded_by: null
type: worklog
commit: 11a2c86188c53eeacfede56a75da89a6d5e3a269
short: 11a2c86
date: 2026-07-19
pr: "https://github.com/Holeshot-Software-LLC/agency-runtime/pull/104"
related_issues:
  - docs/roadmap/issue-AR-86-govern-complete-upstream-roster-lifecycle.md
  - docs/roadmap/issue-AR-95-bind-remediation-resolution-authority-to-complete-durable-evidence.md
  - docs/roadmap/issue-AR-102-refresh-legacy-bundled-roster-contracts.md
  - docs/roadmap/issue-AR-103-import-windows-ctypes-fixtures-portably.md
  - docs/roadmap/issue-AR-104-run-hosted-portability-gates-in-trusted-boundaries.md
---

# Worklog detail: Close governed ingestion and hosted portability gaps

## Purpose

Complete the governed repair path for the two known quarantined upstream
definitions, close the source-bound projection provenance gap, and make the
hosted Windows and Linux verification lanes use private runtime boundaries
without weakening production filesystem or executable trust.

## Approach

The remediation registry now recognizes reviewed LF and CRLF byte identities
separately. Each raw source keeps its exact content hash, deterministic edit
offsets, and repaired intermediate hash while resolving to one canonical
semantic contract. Ingestion may apply only those exact registered repairs;
unknown or ambiguous content remains quarantined.

Projected candidates now require durable source-bound remediation evidence.
The semantic projection registry has a deterministic policy fingerprint over
its source identities, routing-contract metadata, and rendered prompt hashes.
Candidate audit policy version 2 binds that fingerprint and the required
provenance rule, invalidating pre-upgrade passing audits so they must be rerun
before approval or activation.

Hosted tests run through a private, per-run virtual environment and isolated
home and temporary directories below a validated current-user boundary. The
environment copies its interpreter instead of trusting an environment-owned
symlink, preserves the installed development dependency set, and gives Windows
and Linux the same test command. Test fixtures create private parent chains
through the production helper, while Windows path simulations retain native
`PureWindowsPath` and `ntpath` behavior on real Windows.

## Challenges encountered

Line-ending conversion changes raw hashes and edit byte offsets, so accepting a
canonicalized approximation would have weakened immutable source evidence. The
CRLF variants therefore required distinct reviewed hashes and offsets rather
than normalization before verification.

Senior review found that the first source-bound provenance guard did not change
the candidate audit-policy fingerprint. A stored passing version-1 audit could
therefore remain current across upgrade and activate a copied projected prompt.
The final design fingerprints the semantic registry and provenance requirement,
and an upgrade regression proves the legacy receipt is rejected.

Hosted portability also exposed unsafe shortcuts in the test harness:
environment-owned Python launchers could escape the trusted runtime, recursive
fixture creation could inherit permissive modes, and unconditional POSIX path
seams could mask native Windows behavior. The fixes stay in private CI and test
boundaries instead of changing production trust checks or the process-wide
umask.

## Decisions and alternatives

Raw source identity is never line-ending-normalized. Portability is provided by
explicit exact-hash aliases, not by broad repair heuristics. A governed prompt
is not sufficient provenance by itself; activation requires its immutable
source, transformation event, remediation receipt, semantic projection, and a
current passing audit.

Production storage, executable, and parent-chain validation remains unchanged.
The rejected alternatives were relaxing those controls for hosted runners,
using a process-global umask, reusing symlinked setup interpreters directly, or
making Windows tests pass by replacing native path semantics on Windows.

## Verification

- Final warning-strict Windows shards: 5,909 passed, 20 skipped, and 3
  deselected.
- Combined Windows production coverage: 39,036 statements and 13,174 branches
  at 100.00%.
- The prior final Linux suite, before the policy-fingerprint-only follow-up,
  completed with 5,899 passed, 27 skipped, and 3 deselected.
- Dashboard UI: 88 passed at 100% line, branch, and function coverage.
- Uninstrumented performance lane: 3 passed.
- Routing evaluation: all 25 gates passed.
- Delegation evaluation: 12 of 12 cases passed.
- Full-roster evidence: 263 approved agents and zero quarantined agents.
- Ruff, formatting, release hygiene, Bandit, dependency audit, offline workflow
  audit, documentation validation, tracker validation, and whitespace checks
  passed.

## Follow-ups

Run PR #104's hosted Windows and Linux jobs against the committed ledger state,
then build and smoke-test the immutable wheel and source distribution artifacts.
Local coverage and security evidence does not replace those hosted and packaged
release gates. Reconcile roadmap acceptance and tracker state only after those
checks pass.
