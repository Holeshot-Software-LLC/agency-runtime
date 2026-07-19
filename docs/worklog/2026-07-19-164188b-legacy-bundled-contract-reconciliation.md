---
title: "Worklog detail: Reconcile legacy bundled contracts"
status: active
category: worklog
created: 2026-07-19
updated: 2026-07-19
tags: [roster, upgrade, routing, delegation, security]
related:
  - docs/roadmap/README.md
  - docs/decisions/0013-approval-gated-roster-activation.md
  - docs/decisions/0062-isolate-directives-and-route-units-first.md
  - docs/decisions/0066-package-audited-roster-and-sync-quarantined-deltas.md
supersedes: []
superseded_by: null
type: worklog
commit: 164188bcc485ca048e17d39ff12fdfbfc35b8b37
short: 164188b
date: 2026-07-19
pr: "https://github.com/Holeshot-Software-LLC/agency-runtime/pull/104"
related_issues:
  - docs/roadmap/issue-AR-82-full-roster-unit-routing.md
  - docs/roadmap/issue-AR-84-bounded-semantic-agent-cards.md
  - docs/roadmap/issue-AR-86-govern-complete-upstream-roster-lifecycle.md
  - docs/roadmap/issue-AR-87-bounded-native-delegation-plans.md
  - docs/roadmap/issue-AR-91-enforce-governed-roster-activation.md
  - docs/roadmap/issue-AR-92-redact-roster-source-credentials.md
  - docs/roadmap/issue-AR-102-refresh-legacy-bundled-roster-contracts.md
---

# Worklog detail: Reconcile legacy bundled contracts

## Purpose

Repair the two quarantined upstream definitions through the governed ingestion
path, make future deterministic repairs part of ingestion, and prevent existing
installations from retaining obsolete package-owned routing contracts after an
upgrade.

## Approach

The remediation pipeline now recognizes the two known corrupt source hashes,
repairs only their exact malformed headings, and still requires the normal
semantic, inference, conflict, and approval gates before activation. Unknown or
ambiguous content stays quarantined with an immutable attempt receipt.

Installation reconciliation separately recognizes seven released legacy
starter identities by their complete immutable storage shape and hashes. It
replaces only those package-owned rows with current audited contracts, reports
additions and upgrades separately, and leaves current, synced, candidate-backed,
custom, and near-match rows unchanged.

Per-unit routing now restricts semantic roots to specialists with compatible
reviewed authority while preserving dependency closure over the complete
host/tool-eligible catalog. This prevents a review-only specialist from
receiving write work without excluding required reviewers from a valid
implementer selection.

## Challenges encountered

The installed Route Lab exposed a legacy version-1 starter roster that
missing-only seeding had preserved. A broad slug-based replacement would have
violated operator ownership, so migration authority had to bind both prompt and
active-projection hashes in addition to source, version, prompt URI, and empty
legacy provenance.

The warning-strict coverage run also exposed two test-harness defects: managed
adapter fixtures omitted turn-bound native capability receipts, and one race
test used a one-second lease unrelated to the behavior it asserted. The
fixtures now model production receipts and use a stable lease without relaxing
the runtime's fail-closed checks.

## Decisions and alternatives

No heuristic auto-repair is authorized. A known hash may propose a deterministic
repair, but it cannot bypass audit or approval. Legacy starter upgrades likewise
use a closed immutable allowlist instead of replacing by slug, package version,
or approximate content. Unit routing filters only primary semantic roots;
requirements and compatibility are still resolved over the full eligible
catalog so reviewed companion contracts remain enforceable.

## Verification

- Warning-strict non-performance suite: 5,892 passed, 19 skipped, 3 deselected.
- Production coverage: 39,017 statements and 13,170 branches at 100.00%.
- Uninstrumented performance lane: 3 passed.
- Dashboard UI: 88 passed at 100% line, branch, and function coverage.
- Delegation evaluation: 12 of 12 cases passed.
- Routing evaluation: all 25 gates passed; p95 was 2.681 milliseconds.
- Full-roster evaluation: 263 of 263 approved agents participated with 1.0
  candidate recall, 1.0 recall at 10, and zero quarantined entries.
- Release hygiene, Bandit, dependency audit, and offline workflow audit passed.
- Documentation, Ruff, formatting, and whitespace checks passed.

## Follow-ups

Build and verify immutable wheel/source artifacts, repeat fresh and legacy
upgrade smoke tests, run the hosted Windows/Linux matrix, and record the pull
request before closing AR-102.
