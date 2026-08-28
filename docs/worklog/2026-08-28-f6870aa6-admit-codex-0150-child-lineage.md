---
title: "Worklog: Admit Codex 0.150 child lineage"
status: active
category: worklog
created: 2026-08-28
updated: 2026-08-28
tags: [codex, hooks, child-lineage, activation, compatibility]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-330-support-codex-0150-collaboration-rollouts.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - agency_runtime/core/child_delivery_evidence.py
  - tests/test_canary_activation_snapshot.py
  - tests/test_child_delivery_evidence.py
supersedes: []
superseded_by: null
type: worklog
commit: f6870aa69e69fb68977fbb18c2e8565e9b62b9fd
short: f6870aa6
date: 2026-08-28
pr: null
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-330-support-codex-0150-collaboration-rollouts.md
---

# Worklog detail: Admit Codex 0.150 child lineage

## Purpose

Repair the strict child-lineage boundary reached by the rebuilt Codex 0.150.1
current-profile canary after attended 8/8 hook trust. The parent rollout was
already accepted, but the child received only generic identity because the
lineage reader still admitted only the older implicit-role and UTC-filename
shape.

## Approach

Keep the existing bounded, link-resistant, owner-integrity reader and add one
closed 0.150.1 variant. It requires the exact `Code Reviewer` value in both
top-level and nested host-authored role fields. The timestamp join accepts only
the UTC or current host-local wall-time spelling that Codex uses for rollout
filenames; payload time and UUIDv7 time remain UTC-bound and causal. The legacy
0.149.1 implicit-role variant remains unchanged.

## Challenges encountered

The first 0.150 repair covered collaboration calls, activity, and the product
projection but not the separate hook-lineage parser. Replaying the retained
content-free lifecycle against a private Store copy isolated two independent
rejections: the new role field and the four-hour America/New_York filename
offset from the JSON/UUID UTC time.

## Decisions and alternatives

No Codex downgrade, package pin, hook-trust bypass, broad version range, or
ambient-parent lookup was added. Accepting arbitrary role or timestamp drift
would weaken the existing ADR-0156/ADR-0179 artifact authority, so only the two
observed exact version-shaped schemas and two host filename conventions are
admitted.

## Verification

- The retained real child `01a048b6...1301` now resolves exact parent
  `01a048b4...33cd` through the production lineage reader.
- Focused lineage and activation-snapshot tests pass 103/103 warning-strict.
- The wider activation, provenance, delivery, and storage-file set passes
  523/523 warning-strict.
- Ruff lint/format, metadata, policy availability, worklog generation,
  documentation validation for 920 Markdown files, and `git diff --check`
  pass before the recovery commit.

## Follow-ups

Build and install the exact clean candidate, obtain the expected fresh attended
Codex hook trust, and repeat the live no-bypass activation proof. Then complete
the four ordinary host proofs and named repository gates under
[AR-297](../roadmap/issue-AR-297-complete-unattended-container-bootstrap.md).
