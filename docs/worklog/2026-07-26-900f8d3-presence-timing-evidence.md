---
title: "Worklog detail: Correct presence and timing evidence"
status: active
category: worklog
created: 2026-07-26
updated: 2026-07-26
tags: [security, operator-presence, testing, performance, http]
related:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-157-quiet-public-http-disconnects.md
  - docs/roadmap/handoffs/issue-AR-119.md
  - docs/decisions/0096-require-operator-presence-for-persistent-controls.md
supersedes: []
superseded_by: null
type: worklog
commit: 900f8d3
short: 900f8d3
date: 2026-07-26
pr: null
related_issues:
  - docs/roadmap/issue-AR-119-inference-first-workforce.md
  - docs/roadmap/issue-AR-143-require-operator-presence-for-controls.md
  - docs/roadmap/issue-AR-156-restore-cost-bounded-verification.md
  - docs/roadmap/issue-AR-157-quiet-public-http-disconnects.md
---

# Worklog detail: Correct presence and timing evidence

## Purpose

Preserve the fourth rejected Windows timing sample, record the completed HTTP
disconnect repair, and replace AR-143 claims that exceeded the implemented
operator-presence boundary.

## Approach

The operator-presence contract now separates the current parsed-namespace guard
from the required prepare, verify, revalidate, and commit flow. It requires an
intelligible native prompt, command-specific authoritative resource/CAS
binding, pre-verification ingestion of deferred input, and no stable
secret-dependent digest oracle. A direct verification result is not a bearer;
any future transferable capability has separate expiry and replay obligations.

The rejected Windows native draft remains outside the worktree. Its SDK ABI
matched local headers, but callback lifetime, async cancellation settlement,
and message-loop ownership were not production-safe. Positive mutations remain
unavailable. AR-156 records the fourth invalid run and its bounded-fixture fix;
AR-157 records the implemented shared disconnect boundary and focused evidence.

## Challenges encountered

The current CLI receipt is a constructible informational Python value, not a
security capability. The parsed digest also binds positional low-entropy
secrets deterministically while failing to bind deferred stdin/prompt values.
Both distinctions were required to keep the roadmap and threat model honest.

## Verification

- Documentation metadata passed for 405 Markdown files before this detail was added.
- Documentation validation passed for all 405 files before this detail was added.
- Policy availability, worklog generation, capsule size, and diff checks passed.
- The active capsule is 178 lines and 10,007 bytes.

## Follow-ups

Obtain one unchanged green parallel corpus, then collect three comparable warm
four-worker runs and a matched one-worker control. Implement AR-143 first for
roster rollback through one prepared Store transaction; keep every unmigrated
mutation fail-closed.
