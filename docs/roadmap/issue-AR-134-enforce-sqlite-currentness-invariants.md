---
title: "AR-134: Enforce SQLite currentness and retention invariants"
status: done
category: roadmap
created: 2026-07-26
updated: 2026-07-27
tags: [sqlite, schema, migrations, integrity, retention]
related:
  - agency_runtime/core/store/schema.py
  - agency_runtime/core/native_child_activation.py
  - docs/decisions/0012-canonical-sqlite-audit-store.md
supersedes: []
superseded_by: null
type: issue
epic: operations
issue_id: AR-134
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-134: Enforce SQLite currentness and retention invariants

## Problem

Schema currentness can remain true after a critical guard trigger and unique
index are removed. ZCode is excluded from native activation consumption
constraints, legacy booleans lack domain checks, and a declared guarded-delete
object is not created.

## Current state

Dropping `agency_activation_consumption_insert_guard` and
`idx_worker_runs_native_scope` did not make currentness fail. Direct ZCode
activation consumption raises an integrity error. The declared guarded-delete
name is a phantom contract and direct deletion succeeds.
Deeper review also reproduced a constraint-stripped activation-consumption
table that passed the old host-substring check, same-name no-op workforce
authority triggers that passed name-only checks, and quoted-literal case drift
that disappeared under the former schema normalizer.

## Approach

Add a forward-only migration that rebuilds affected constrained tables while
preserving receipts, recognizes all canonical hosts, and verifies normalized
critical object SQL plus semantic invariants. Either implement the documented
retention-authorized delete guard or remove the false declaration and document
the actual retention contract. Add boolean checks through safe rebuilds.

## Dependencies

AR-135 owns ZCode behavior; this item owns the durable schema and currentness
proof required by it.

## Acceptance

- Fresh and upgraded databases accept canonical ZCode activation receipts.
- Missing or altered critical triggers, indexes, constraints, or host domains
  make currentness fail.
- Migration preserves existing evidence and is idempotent.
- Boolean domains reject values outside zero and one.
- Delete behavior matches one documented, tested retention contract.

## Implementation evidence

Schema 36 adds the canonical ZCode host domain, exact normalized SQL
currentness for critical triggers and the native-scope unique index, boolean
domain guards, and the previously phantom guarded-delete trigger. Direct child
receipt deletion is denied while an authorized parent-retention cascade removes
the dependent receipt. Eleven regressions prove fresh creation, v35 evidence
preservation, idempotent upgrade, same-name weakened-object rejection, boolean
domains, ZCode insertion, and retention behavior.
Currentness now additionally compares the complete activation-consumption DDL
and every workforce append-only/hiring-authority trigger and index. SQL
normalization ignores syntax case and whitespace outside quotes but preserves
literal and quoted-identifier bytes. Exact legacy v35 consumption DDL upgrades;
unknown or tampered shapes fail closed. The expanded focused package passes 58
tests and the broader Store/schema/roster/workforce package passes 434 with 2
skips.
All acceptance criteria are satisfied locally; tracker creation and
synchronization remain pending explicit outward-write authorization.
