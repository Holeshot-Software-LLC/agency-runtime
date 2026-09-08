---
title: "Retain validated recall catalog digest"
status: active
category: worklog
created: 2026-09-08
updated: 2026-09-08
tags: [observability, recall, privacy, performance]
related:
  - docs/roadmap/issue-AR-411-retain-recall-catalog-identity-in-failure-receipts.md
  - docs/roadmap/handoffs/issue-AR-411.md
  - docs/decisions/0218-cache-only-roster-vectors-across-hook-processes.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: c514fb70b109adb2360758bafdb3bda2cd994e71
short: c514fb70
date: 2026-09-07
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/747
related_issues:
  - docs/roadmap/issue-AR-411-retain-recall-catalog-identity-in-failure-receipts.md
---

# Worklog: Retain validated recall catalog digest

## Purpose

Preserve the production catalog digest already emitted by hybrid recall when a
preflight becomes a durable failure. This enables comparison of cold catalog
attempts without claiming that their cache identity was equal or different
before new receipts actually exist.

## Approach

Add seven lines to the existing bounded recall-performance projection. Admit
only a string exactly matching `sha256:[0-9a-f]{64}` and only on
`recall_embedding`. Omit invalid values locally; do not reject the whole
failure. No stripping, coercion, case folding or raw-value persistence.
The producer's `_document_hash` is already this form; lower-level opaque
fixture labels intentionally do not pass. Existing counts and cache flags stay.

## Challenges encountered

Failure records do not establish that the cache is defective. This patch
adds the missing identity evidence, not a speculative cache repair. An initial
documentation patch had a malformed hunk and made no changes; the corrected
patch was applied. Tracker #746 was created only after AR-410/#744 filing.
Incoming AR-410 merge ledger 51a84b9c was fast-forwarded without changing
the independent projection/test edits.

## Decisions and alternatives

Use the existing ADR-0218 privacy boundary; no new ADR or cache policy.
Reject arbitrary opaque labels, paths and strings instead of truncating them
into diagnostic text. Do not change TTL, eviction, key inputs, provider calls,
staffing/hiring reviews or add a provider run to manufacture failure evidence.

## Verification

Source tracing proves the producer/ordinary-routing/failure-projection gap.
Targeted Ruff lint passes; two files are already formatted; diff whitespace
checks pass. Twenty parameterized regression cases were written, including
full-receipt and repeated projection, invalid values and stage/privacy bounds.
**Tests and CI were not run**, explicitly per owner direction. No red/green,
installed receipt, performance measurement or acceptance verdict is claimed.

## Follow-ups

Root owns normal source PR publication and owner installation. AR-411 remains
in_progress; focused execution and one organically produced failed-preflight
receipt are deferred until authorized. Capsule checkpoint metadata names the
clean inherited floor; this substantive source identity is c514fb70.

PR #747 merged as `e790c4d4d957ae7ed951285922f5bff6733934c5` at2026-09-08T01:01:33Z; read back MERGED. Source regression execution/acceptance remains deferred under the owner directive; issue #746 stays open.
