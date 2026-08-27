---
title: "AR-313: Trust normal-umask Codex artifacts by integrity"
status: in_progress
category: roadmap
created: 2026-08-26
updated: 2026-08-27
tags: [codex, evidence, filesystem, security, production-container]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-309-restore-codex-0149-activation-proof.md
  - docs/roadmap/issue-AR-324-bind-codex-canary-child-through-host-lineage.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - agency_runtime/core/store/security.py
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/codex_spawn_provenance.py
  - agency_runtime/core/child_delivery_evidence.py
  - tests/test_storage_parent_trust.py
  - tests/test_codex_activation_canary.py
  - tests/test_child_delivery_evidence.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-313
priority: p0
tracker_url: null
depends_on: [AR-309]
blocks: [AR-297, AR-324]
---

# AR-313: Trust normal-umask Codex artifacts by integrity

## Problem

Codex 0.149.1 writes its session/date directories with a normal umask, observed
as mode 0755, and its rollout JSONL as mode 0644. Agency's Codex readers reused
the canonical Store parent guard, which requires confidentiality at the final
directory. A real host-written rollout therefore failed before its immutable
content could become activation or delivery evidence even though no other
account could replace it.

## Current state

- Exact no-bypass container `c22a08de...1767d3` creates and completes child
  `01a04005-8353-7f42-9020-3453eed3b5b0`. The parent and child rollouts hash to
  `8b93d005...1b668` and `6e18884f...f73a0` and use mode 0644 below mode-0755
  Codex date directories and the owner-private mode-0700 `.codex` boundary.
- The pre-repair rollout reader raises `Codex rollout root was not private`.
  This is a reader admission defect; no activation bypass or permission
  mutation is involved.
- The bounded source repair separates foreign host-artifact integrity from
  Agency-created Store privacy. It requires a real owner/root directory chain,
  current-owner final directory and file, no group/other mutation, no links,
  one file link, no unsafe default ACL, and equivalent Windows mutation denial.
- Codex rollout, spawn-provenance, and child-delivery readers use that guard;
  Claude's product-created private collector retains the stricter privacy rule.
- Tracker creation is prohibited by the active AR-297 task.

## Approach

Use a named artifact-parent integrity guard only for host-owned Codex evidence.
Permit read/traverse bits that do not enable substitution, while retaining all
owner, type, link, write, ACL, bounded-read, identity-recheck, canonical-root,
and invocation-window checks. Do not chmod host files or weaken Agency Store,
configuration, control, or private temporary-directory boundaries.

## Dependencies

- ADR-0156 requires host-authored artifacts to originate delivery proof.
- ADR-0179 keeps the exact canary rollout and invocation window authoritative.
- AR-309 supplies the exact 0.149 rollout and receipt contract.
- Tracker creation requires separate outward-write authorization.

## Acceptance

- [x] A regression reproduces mode-0755 Codex directories and a mode-0644
      rollout below an owner-controlled namespace.
- [x] The real shape is accepted for bounded parsing and canonical delivery
      verification without changing permissions.
- [x] Group/other-writable paths, unsafe ACLs, foreign ownership, links,
      multiple links, and identity replacement remain fail-closed on POSIX and
      Windows-shaped tests.
- [x] Claude's fresh private collection and all Agency-created storage
      boundaries retain their prior confidentiality requirements.
- [x] Focused warning-strict activation, provenance, delivery, hook, and
      storage tests pass (586 plus two artifact-parent regressions).
- [ ] A rebuilt fresh no-bypass Codex transaction consumes the canonical child
      artifact and persists the exact receipt/attestation or exposes a later
      honest blocker.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.
