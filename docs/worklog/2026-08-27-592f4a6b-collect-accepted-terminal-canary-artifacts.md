---
title: "Collect accepted terminal Codex canary artifacts"
status: active
category: worklog
created: 2026-08-27
updated: 2026-08-27
tags: [ar-297, ar-326, codex, canary, host-artifact, finalization, security]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-326-admit-terminal-codex-host-artifact-collection.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0188-separate-codex-hook-parent-and-child-identities.md
  - docs/decisions/0189-admit-only-accepted-terminal-codex-parents-for-post-return-collection.md
supersedes: []
superseded_by: null
type: worklog
commit: 592f4a6bfdab323d4842c6189f106faf690f861c
short: 592f4a6b
date: 2026-08-27
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/337
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-326-admit-terminal-codex-host-artifact-collection.md
---

# Worklog detail: Collect accepted terminal Codex canary artifacts

## Purpose

Allow the bounded Codex backend to collect the already-proven native child
artifact after an accepted activation-canary run becomes terminal, without
making that completed parent visible to any hook-side caller.

## Approach

The restricted parent resolver remains live-only by default and gains one
explicit, exclusive accepted-terminal mode. Only the post-return backend
collector requests it. Store admits exactly one completed Codex run with one
bound accepted finalization, `missing=[]`, canonical non-pending metadata, and
the same session, trace, route, response identity, and terminal timestamp. All
existing host-authored delivery and independently parsed artifact requirements
remain downstream of that lookup.

Three lifecycle regressions cover the live-to-terminal transition, reject
closed, rejected, ambiguous, pending, and incomplete terminal shapes, and prove
that hook collection remains live-only while backend collection requests the
terminal mode. Two curated decision mutations guard both seams. ADR-0189 owns
the durable lifecycle boundary.

## Challenges encountered

The first named fast-spine run used a protected UV Python 3.13.13 interpreter
that lacks Linux `os.pidfd_open`; only two native process-supervision tests
failed. Their isolated retry reproduced the environmental failure. The same
spine passed under Linux-capable Python 3.12.3. The full evaluator then exposed
that canonical `/usr/bin/python3.12` lacks pytest even though its launcher path
can import it, so the evaluator was rerun through an existing owner-private
mode-0700 copy of that exact binary with pytest. The failed diagnostics and
their source-unchanged boundaries remain retained rather than being discarded.

## Decisions and alternatives

ADR-0189 rejects widening the default resolver, collecting from a generic
completed run, or trusting Store presence in place of finalization and native
delivery. Existing `19e0210b` live evidence remains a failed attestation and
cannot be relabelled after this source change.

## Verification

- The affected warning-strict suite passes 203/203 at stdout SHA-256
  `4e76af29...a318`; 17 evaluator tests pass at `9cd8ed59...a033`.
- Both focused mutations are killed with source unchanged at
  `34858754...5cc7`; the complete evaluator kills 165/165 with zero
  survived/invalid at `891defed...ab8`.
- The named fast Python spine passes 860 tests with 3 skips at
  `8cda02e1...4312`.
- Repository-wide Ruff and format, dashboard UI, routing, metadata, policy
  availability, worklog, docs, and diff checks exit 0. Final metadata/docs
  outputs cover 897 Markdown files; all retained passing stderr is empty.
- Capsule telemetry reports 62.7 percent remaining and no required clean
  checkpoint beyond this normal recovery pair.

## Follow-ups

- Rebuild exact artifacts and all six images from the resulting clean ledger.
- Run one new clean, sole-install Codex production-container transaction and
  require current-profile attestation plus the retained canonical child
  artifact before closing AR-326's live acceptance line.
- Continue AR-297 with separate Claude, Hermes, and OpenClaw installs, ordinary
  unattended runs, host/dashboard proof, final gates, and container teardown.
- Tracker creation remains prohibited by the active task and is not attempted.
