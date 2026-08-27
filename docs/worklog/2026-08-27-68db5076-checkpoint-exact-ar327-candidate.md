---
title: "Checkpoint exact AR-327 candidate"
status: active
category: worklog
created: 2026-08-27
updated: 2026-08-27
tags: [ar-297, ar-327, codex, containers, artifacts, recovery]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-327-replay-codex-delivery-receipts-across-append-only-completion.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0190-bind-codex-receipt-replay-to-an-exact-append-only-prefix.md
supersedes: []
superseded_by: null
type: worklog
commit: 68db507633774e5f78667976dffbed6cbc7aaaba
short: 68db5076
date: 2026-08-27
pr: null
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-327-replay-codex-delivery-receipts-across-append-only-completion.md
---

# Worklog detail: Checkpoint exact AR-327 candidate

## Purpose

Bind the exact clean AR-327 artifacts and production-container images before
running the only live install allowed in a new Codex proof container.

## Approach

Canonical Git-blob build source was frozen at clean ledger
`7dbd0cbc5cbc77e46fc795568bb63ddcf5e3ee6f`. The owner-private protected
Python built the portable wheel and source archive. Strict Twine and the
independent distribution verifier then read those exact artifacts. Five final
proof images were built through six Docker builds because OpenClaw uses a
separate Node 24 base and systemd layer. A distinct verifier checked immutable
candidate and wheel labels plus every pinned Agency and harness version in
transient version-only containers.

## Challenges encountered

No build or verification failed. The retained protected interpreter and
already-established harness pins were reused without changing the approved
LiteLLM configuration, models, auth, or service-manager choices.

## Decisions and alternatives

The earlier `4b443be2` candidate remains historical evidence and was not
relabelled. New tags and artifacts bind only `7dbd0cbc`; the next Codex proof
will start from the new exact image and will not reuse or reinstall Qwen1/2.

## Verification

- Wheel `e117b362...fc03d` is 9,344,796 bytes; sdist
  `ac30feb0...9fb6c` is 25,929,703 bytes. Build, strict Twine, verifier, and
  artifact manifest exit 0.
- Artifact manifest `780512b2...b7876` records exact SHA-256 values, modes,
  owners, sizes, and paths.
- Codex, Claude, Hermes, OpenClaw base/systemd, and dashboard builds all exit 0.
  Independent image receipt `00fcf8e6...5f76` exits 0 with empty stderr.
- Final Codex, Claude, Hermes, OpenClaw systemd, and dashboard image IDs are
  `206e94c4...a5b2e`, `237c788d...d7e40`, `7869a7a3...121b8`,
  `91c3a5bc...0fde`, and `1b0653a5...cb87`.
- Metadata, worklog, docs, policy-availability, and diff checks pass. The
  recovery capsule is 178 lines and 9,974 bytes.

## Follow-ups

- Create one new exact Codex container, prove fresh absence, and run its sole
  no-bypass install with the explicit 300-second activation window.
- Continue Claude, Hermes, OpenClaw, ordinary-process, host/dashboard, gate,
  and teardown rows only after that live gate is durably checkpointed.
- Tracker writes, push, PR, merge, tag, signing, publication, release, and
  hosted workflow dispatch remain prohibited.
