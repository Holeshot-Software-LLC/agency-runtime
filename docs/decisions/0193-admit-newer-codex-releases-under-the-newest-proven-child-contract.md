---
title: "Admit newer Codex releases under the newest proven child contract"
status: accepted
category: decisions
created: 2026-08-29
updated: 2026-08-29
tags: [host-integrations, codex, canary, versioning, delivery]
related:
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/roadmap/issue-AR-334-support-codex-0151-collaboration-and-hook-contract.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - agency_runtime/core/child_delivery_evidence.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
id: ADR-0193
type: decision
deciders: [maintainers, owner]
---

# ADR-0193: Admit newer Codex releases under the newest proven child contract

## Context

codex-cli updates itself on the operator's machine on a near-daily cadence.
The child-metadata parser that binds a spawned Codex child to its
host-authored canary parent dispatched on an exact allowlist of proven CLI
versions (0.149.1, 0.150.1). When the host auto-updated to 0.151.0, whose
child `session_meta` is byte-compatible with the 0.150.1 contract except for
the version string, the dispatch returned empty, the child hook staffed no
specialist card, and every downstream delivery proof failed closed. The owner
directed on 2026-08-29 that nothing on the host system is pinned and the code
accounts for new host versions.

## Decision

Keep the exactly-proven variants exact. For a release-shaped CLI version
strictly newer than the newest proven baseline, admit the child metadata
under that newest proven contract with bounded additive tolerance: all
required keys must be present, at most eight unknown additional payload keys
are tolerated, keys that change lineage semantics (`forked_from_id`) are
never tolerated, and every structural, lineage, ordering, and timing
invariant stays exact. Prerelease-shaped or older-than-baseline versions
remain rejected. When live evidence proves a newer release exactly, its
version becomes the new baseline.

## Consequences

A routine host auto-update whose metadata is shape-compatible no longer
orphans children or fails activation on version identity alone; 0.151.0
passes today under the 0.150.1 contract. A release that actually changes the
structure still fails closed, now attributable to a real contract change
rather than a version string. The tolerance ceiling bounds what an unknown
release can smuggle past the parser, and the disallowed-key set records the
semantic markers that additive tolerance must never admit.

## Alternatives

Pinning the host CLI version was rejected by the owner: updates arrive daily
and the host system stays unpinned. Admitting any version without shape
constraints was rejected as removing the delivery proof's meaning. Keeping
exact-version allowlists and shipping a runtime update per host release was
rejected as guaranteed recurring breakage with the same failure mode.
