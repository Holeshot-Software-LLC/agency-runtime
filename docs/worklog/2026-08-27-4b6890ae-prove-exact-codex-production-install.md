---
title: "Prove exact Codex production install"
status: active
category: worklog
created: 2026-08-27
updated: 2026-08-27
tags: [ar-297, ar-326, ar-327, codex, container, attestation]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-326-admit-terminal-codex-host-artifact-collection.md
  - docs/roadmap/issue-AR-327-replay-codex-delivery-receipts-across-append-only-completion.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0190-bind-codex-receipt-replay-to-an-exact-append-only-prefix.md
supersedes: []
superseded_by: null
type: worklog
commit: 4b6890ae5d7507d73680b8de3e16be436efc2cbd
short: 4b6890ae
date: 2026-08-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-326-admit-terminal-codex-host-artifact-collection.md
  - docs/roadmap/issue-AR-327-replay-codex-delivery-receipts-across-append-only-completion.md
---

# Worklog detail: Prove exact Codex production install

## Purpose

Close AR-297's repaired Codex installation row with one clean, exact,
no-bypass production-container transaction and independently retained native
artifacts, Store correlation, and current-profile attestation.

## Approach

Container `2ec2180b...17bb` was created from exact image ID
`206e94c4...a5b2e` with host networking and explicit proof/candidate labels.
Private Codex auth and the approved mode-0600 config were copied without
printing either value. A content-free absence probe preceded the sole install.
Immediately-prelive context telemetry passed, then the install used the exact
config, managed production-container policy, dashboard opt-out, and explicit
300-second activation window.

After the terminal result, the Store, both rollouts, native install/launcher
manifests, managed requirements, and relay were copied into owner-private
evidence. A separate read-only correlation checked the Store graph and SQLite
integrity. Ordinary status then read the persisted attestation without an
install, retry, or trust bypass.

## Challenges encountered

The first content-free correlation helper treated SQL `NULL` in a finalization
`missing` column as invalid JSON. That retained diagnostic exits 1 without
changing the Store. The corrected v2 accepts the Store's canonical null-as-empty
projection and exits 0; no live command or install was repeated.

## Decisions and alternatives

Qwen1 and Qwen2 were not rerun. The new container received exactly one install.
The persisted receipt's exact complete JSONL prefix, rather than later ordinary
Codex suffix records, supplies delivery authority under ADR-0190.

## Verification

- Fresh absence `e857f524...d9bd` exits 0 with exact image/candidate/config,
  private auth, Codex 0.149.1, and all Agency targets absent.
- Install `54572077...ac82` exits 0 with `complete=true`, managed-only eight
  events, no bypass, one route/delivery, one exit-0 child, one completed wait,
  valid header, and accepted `missing=[]` finalization `56de0046...e30b`.
- Current-profile attestation `ded810a5...6e66` persists. Read-only status
  `e4755e50...66a3` exits 0 and reports `runtime-verified`.
- Store correlation `ef8304ef...e30c` exits 0 with `quick_check=ok`. Store and
  parent/child rollout hashes are `7e767300...27b1`, `b3fc13a8...9274`, and
  `f7633d02...5e88`.
- Native decision `native-child-7738d04b...c06f` binds child
  `01a043de...206b` to full prompt `e409b2c8...20bd` before first speech.
- Documentation, metadata, policy-availability, worklog, and diff checks pass.

## Follow-ups

- Prove a separate clean exact Claude production-container install next.
- Do not treat this installation canary as the later ordinary unattended Codex
  process; that remains in the four-harness loading row.
- Tracker writes, push, PR, merge, tag, signing, publication, release, and
  hosted workflow dispatch remain prohibited.
