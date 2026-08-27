---
title: "Checkpoint exact terminal collector candidate"
status: active
category: worklog
created: 2026-08-27
updated: 2026-08-27
tags: [ar-297, ar-326, codex, container, artifacts, recovery]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-326-admit-terminal-codex-host-artifact-collection.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0189-admit-only-accepted-terminal-codex-parents-for-post-return-collection.md
supersedes: []
superseded_by: null
type: worklog
commit: 08264555e097eed7dceee0dea8887c1faf9c6f73
short: 08264555
date: 2026-08-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-326-admit-terminal-codex-host-artifact-collection.md
---

# Worklog detail: Checkpoint exact terminal collector candidate

## Purpose

Bind the exact rebuilt AR-326 artifacts, images, and clean Codex preinstall
state before the live one-install transaction required by AR-297 telemetry.

## Approach

Clean implementation ledger `4b443be2` produced one portable wheel and source
distribution through the canonical Git-blob builder. Strict Twine and the
independent distribution verifier both passed. Six images then bound the full
commit and exact wheel digest; an independent verifier checked labels, Agency
version, and each pinned harness version from a transient container.

The generic OpenClaw build first inherited Node 22.22.0. The version probe
correctly rejected that runtime because OpenClaw requires a newer patch line.
Both images were preserved under explicit `node22-failed` tags, then the base
was rebuilt with the already-established Node 24.15.0 argument and the systemd
child was rebuilt from it. The second independent verification passed.

A new Codex container was created from the exact image ID with host networking,
candidate/wheel/proof labels, private copied auth, and the approved mode-0600
config. Its absence receipt proves the Agency runtime home, Codex config, system
requirements, and managed relay were all absent. No install ran before this
checkpoint.

## Challenges encountered

The first distribution attempt safely refused a reused CI interpreter because
its `bin/` directory was group-writable. A dedicated owner-private AR-297 copy
was created, all group/other access was removed, and the pinned release tools
were installed there. The refusal remains retained at stderr SHA-256
`83e8a58a...54bd3`.

The first OpenClaw image verification failed for the expected Node version
boundary rather than a package or Agency defect. Its retained stderr hashes to
`e404ddeb...c427`; the failed images remain distinguishable from the passing
candidate.

## Decisions and alternatives

No failed artifact or image was relabelled as successful. The Codex container
will receive exactly one no-bypass install after this recovery pair; a failed
live result cannot be retried in place.

## Verification

- Wheel `aaf9b461...1f7d` is 9,341,603 bytes; sdist `869b2842...545f` is
  25,888,743 bytes. Build, strict Twine, verifier, and manifest exit 0.
- Artifact manifest `c8fdc3f6...9c9e` records exact hashes, modes, ownership,
  sizes, and paths.
- All six final image builds exit 0. Independent image JSON
  `f91c05d1...adde` verifies exact commit/wheel labels and pinned versions.
- Fresh Codex container `cf983a11...79b1` passes private-input and absence
  receipts `018f6d4f...494f` and `0a7d2818...50cb`.
- Metadata, policy availability, worklog, docs, and diff checks pass; the active
  capsule remains within 172 lines and 9,396 bytes.

## Follow-ups

- Execute the existing clean Codex container's sole production install and
  require current-profile attestation plus canonical child/Store correlation.
- Continue the remaining AR-297 checklist only after that live gate is recorded.
- Tracker, push, PR, merge, tag, signing, publication, and release actions remain
  prohibited and were not attempted.
