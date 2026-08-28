---
title: "Worklog detail: Bind exact Codex host-artifact role shape"
status: active
category: worklog
created: 2026-08-26
updated: 2026-08-26
tags: [codex, canary, evidence, filesystem, native-child]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-309-restore-codex-0149-activation-proof.md
  - docs/roadmap/issue-AR-311-inject-exact-codex-canary-native-plan.md
  - docs/roadmap/issue-AR-312-validate-explicit-production-config.md
  - docs/roadmap/issue-AR-313-trust-normal-umask-codex-artifacts.md
  - docs/roadmap/issue-AR-314-bind-codex-default-canary-role.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 0accd39ed80af15d2c4d53ae0fcef2b2804411f3
short: 0accd39e
date: 2026-08-26
pr: https://github.com/Holeshot-Software-LLC/agency-runtime/pull/337
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-309-restore-codex-0149-activation-proof.md
  - docs/roadmap/issue-AR-311-inject-exact-codex-canary-native-plan.md
  - docs/roadmap/issue-AR-312-validate-explicit-production-config.md
  - docs/roadmap/issue-AR-313-trust-normal-umask-codex-artifacts.md
  - docs/roadmap/issue-AR-314-bind-codex-default-canary-role.md
---

# Worklog detail: Bind exact Codex host-artifact role shape

## Purpose

The exact AR-311 container finally created and completed the fixed
`code_reviewer` child, but Agency still could not prove delivery. Codex wrote
normal-umask 0755 rollout directories, and MultiAgentV2 reported the omitted
optional child role as built-in `default`; the existing proof expected private
directories and `agent_type=code_reviewer`.

## Approach

Added a separate host-artifact parent guard that proves namespace integrity
without demanding confidentiality. Codex rollout, spawn-provenance, and child-
delivery readers use it; Agency-created Store and Claude collection boundaries
remain private. The restricted canary pins the exact 0.149.1 built-in role and
requires the child rollout to retain `agent_path=code_reviewer` with no explicit
role. Staffing selection still comes only from the accepted Store route and
fixed work unit.

The checkpoint also records AR-312 for the independently observed README/CLI
config-validation mismatch without implementing it or expanding AR-297.

## Challenges encountered

The parent and child host artifacts existed and the worker completed, but the
first reader failed before parsing because Codex's date directories were 0755.
A content-minimized diagnostic then showed the child had only Agency's identity
message. Version-pinned Codex 0.149.1 source established that an omitted
MultiAgentV2 role is emitted as `default`, while task name remains the agent
path.

## Decisions and alternatives

Accepting both `default` and `code_reviewer` was rejected because the exact
canary omits the role and must fail closed on schema drift. Treating `default`
as a specialist was rejected; it is only a host lifecycle discriminator.
Relaxing the canonical Store privacy guard globally was rejected in favor of a
Codex-host-artifact integrity guard that still rejects any substitution right.

## Verification

- Changed-file Ruff and formatting checks pass.
- Documentation metadata, policy availability, worklog, and all 866-document
  validation checks pass.
- The warning-strict activation, rollout, provenance, delivery, plaintext-hook,
  host-hook, and storage-file slice passes 586 tests.
- Two focused POSIX/Windows artifact-parent integrity regressions pass.
- `git diff --check` passes.

## Follow-ups

- Rebuild the exact candidate and require one no-bypass Codex delivery receipt,
  current first-pass header, accepted finalization, and attestation under
  AR-297, AR-309, AR-313, and AR-314.
- Address the explicit config-validation workflow separately under AR-312.
- Create/link AR-312 through AR-314 tracker issues only after explicit outward-
  write authorization.
