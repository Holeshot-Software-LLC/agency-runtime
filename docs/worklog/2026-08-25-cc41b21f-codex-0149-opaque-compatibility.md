---
title: "Worklog detail: Keep Codex 0.149 opaque children unstaffed"
status: active
category: worklog
created: 2026-08-25
updated: 2026-08-25
tags: [codex, native-child, hooks, compatibility, security]
related:
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
  - docs/roadmap/AR-180-codex-0149-compatibility-evidence.md
  - docs/decisions/0159-authenticate-codex-plaintext-spawns-from-host-transcripts.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: cc41b21f
short: cc41b21f
date: 2026-08-25
pr: null
related_issues:
  - docs/roadmap/issue-AR-180-prove-codex-specialist-activation-canary.md
  - docs/roadmap/issue-AR-255-inference-owned-host-proven-child-staffing.md
---

# Worklog detail: Keep Codex 0.149 opaque children unstaffed

## Purpose

Recheck the native-child assignment boundary after the local Codex CLI upgrade
to 0.149.1 without weakening Agency's authenticated staffing or host-delivery
requirements. Remove stale version-specific operator prose while keeping the
exact 0.147 attestation profiles closed to an unmeasured plaintext path.

## Approach

Ran four bounded, read-only native-child probes and retained only content-safe
rollout projections: parent and child identities, argument keys, ciphertext
shape and length, marker presence, and parent artifact hashes. Compared that
evidence with the current official hook contract. Added 0.149.1 to the exact
version-drift regression, made the fail-open child context version-neutral, and
recorded the unchanged security verdict in AR-180, AR-255, and ADR-0159.

## Challenges encountered

Three changed disposable project-hook capture attempts emitted no redacted hook
log, so they remain setup failures and support no undocumented schema claim.
The first focused test run used the machine's `0002` umask: 349 tests passed and
33 artifact-trust cases correctly rejected non-private fixtures. The unchanged
suite passed under the repository-prescribed process-local `0077` umask. The
first tooling gate also exposed latest main's missing PR #324 worklog row and an
uninitialized worktree environment; ledger `b5bc7a1e` repaired the former, and
the pinned `dev` extra supplied the latter.

## Decisions and alternatives

Do not install Agency into Codex or rerun the Agency canary when the host still
lacks an authenticated assignment surface. Do not broaden the exact 0.147
transcript attestor to 0.149.1 based only on similar ciphertext shape. Do not
restore AR-209's retired plan-row transport or treat a plaintext task label as
selection authority. Continue native execution fail-open and explicitly
unstaffed until the host provides a documented authenticated binding.

## Verification

- 382 focused hook, staffing, provenance, and child-delivery tests pass with
  warnings treated as errors under process-local `umask 0077`.
- Focused Ruff lint and format checks pass in the pinned project environment.
- Documentation metadata, policy availability, worklog consistency, link
  validation, and `git diff --check` pass for 806 Markdown files before the
  ledger update.

## Follow-ups

AR-180 and AR-255 retain exact installation, authenticated child delivery, and
live Rule-4 proof as open. A future Codex profile may be added only after a
content-safe host observation exposes a documented authenticated plaintext or
exact parent-call binding; 0.149.1 remains unsupported and unstaffed.
