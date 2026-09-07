---
title: "Retain native source comparison with current manifest evidence"
status: active
category: worklog
created: 2026-09-07
updated: 2026-09-07
tags: [release, packaging, reproducibility, backlog]
related:
  - docs/roadmap/issue-AR-168-rebuild-canonical-sdist-source-manifest.md
  - docs/roadmap/acceptance/evidence/AR-168-source-manifest-20260907.md
  - docs/decisions/0219-retire-removed-helper-release-obligations.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 37040b321d495772dc851711ac87bf7795c9440f
short: 37040b32
date: 2026-09-07
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/718
related_issues:
  - docs/roadmap/issue-AR-168-rebuild-canonical-sdist-source-manifest.md
---

# Worklog detail: Current source-manifest evidence

## Approach and decisions

Distinguish a historical helper-license trigger from current generic manifest
integrity. Rebuilding from validated members and independent exact verification
already work. Keep all five criteria/states and ADR-0219's actual paired-source
gate; no code, tests, profile redesign or acceptance weakening. Retain this
implemented record with native Windows comparison as the exact owner hold.

## Verification

Fresh focused canonicalizer/build/verifier package: 308 pass/one actual
native-Windows deselection, 33.83s. Clean 6363a788 portable wheel/source pair
passes independent verification and strict Twine. Receipt records exact hashes,
2,258 source files/2,256 distinct manifest rows and exact newline/self/exclusions.
Fresh UI 190 pass (201.580005 ms) and deterministic routing passes. AR-166's
1085/three-existing-skip spine and earlier curated decision evidence are
same-byte reuse, not new runs. Metadata/policy/worklog, strict docs/tracker,
Ruff and diff pass; 1191 documents before this detail, 397 mapped items and
two historical PR exceptions. Actual open tracker count remains 40.

## Challenges and follow-ups

No test, build or artifact verification failure. An unrelated fresh runtime
directive required one Codex refresh; it again returned activation-required,
unverified trust and mixed installations. No retry or host-activation claim.
The owner supplies native Windows and a complete same-candidate source comparison
under AR-160. No duplicate legacy tracker; 84 legacy/124 total remain unfinished.
Normal PR/merge/readback precedes AR-170; AR-169 is already retired.

## Checkpoint

37040b32 (37040b321d495772dc851711ac87bf7795c9440f) records the bounded retention. The immediate ledger
keeps this checkpoint clean before publication; no acceptance runner is invoked
for a known native-platform hold.

PR #718 carries this retention. Final strict documentation validation covers
1192 Markdown files. End telemetry is 70.4 percent at 11:49:17Z; 37040b32 and
c94fcdc4 form the clean substantive/ledger checkpoint before publication.
