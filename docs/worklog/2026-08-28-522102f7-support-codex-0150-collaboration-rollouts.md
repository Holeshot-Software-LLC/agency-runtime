---
title: "Worklog: Support Codex 0.150 collaboration rollouts"
status: active
category: worklog
created: 2026-08-28
updated: 2026-08-28
tags: [codex, activation, rollout, compatibility, security, AR-330]
related:
  - docs/worklog/README.md
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-313-trust-normal-umask-codex-artifacts.md
  - docs/roadmap/issue-AR-330-support-codex-0150-collaboration-rollouts.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
supersedes: []
superseded_by: null
type: worklog
commit: 522102f7a72b6f5b48bc221673be7206f3617080
short: 522102f7
date: 2026-08-28
pr: null
related_issues:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-313-trust-normal-umask-codex-artifacts.md
  - docs/roadmap/issue-AR-330-support-codex-0150-collaboration-rollouts.md
---

# Worklog: Support Codex 0.150 collaboration rollouts

## Purpose

Restore exact Codex activation and ordinary-product evidence after the host
upgraded from Codex 0.149.1 to 0.150.1. The repair supports the installed
protocol without pinning or downgrading Codex and without accepting an
unstaffed child as Agency-loaded.

## Approach

The canary plan now carries one exact `Code Reviewer` native role and directs
the parent to pass it as `agent_type`. The hook admits that explicit role while
retaining the legacy implicit `default` role. Rollout readers bind the new
role/nickname lineage and optional terminal `completed` activity to the same
spawn call, child UUID, task path, and lifecycle. Product projections accept
the same two versioned shapes rather than special-casing only the canary.

AR-313's host-artifact guard now admits mode-0775/0664 Codex artifacts only
when POSIX account records prove the group is the owner's exclusive
user-private group. Shared groups, other-writable paths, links, multiple links,
foreign ownership, and drift remain refused.

## Challenges encountered

The first failed live run combined four changes behind one generic projection
error: explicit `agent_type`, role/nickname lineage, terminal activity, and the
machine's umask `0002`. Content-free inspection of owner-private copies kept
prompts and credentials out of diagnostics. Parent and child copies hash to
`0affc498...e4bd` and `429feb07...2902`; the old run correctly has no staffed
delivery because its pre-repair hook accepted only the implicit role.

## Decisions and alternatives

No Codex version pin or permission rewrite was added. Downgrading would conceal
the protocol defect; chmod would mutate foreign host state and still fail on a
later process inheriting the same umask. The existing ADR-0156 integrity rule
supports a proven exclusive group because no second account gains mutation
authority.

## Verification

- 593 focused activation-contract, rollout, verification, provenance,
  delivery, hook-trust, snapshot, and card-proof tests pass warning-strict.
- Both 0.149 legacy and 0.150 explicit-role canary/product projections pass.
- The live `~/.codex/sessions` root, date directory, and rollout file pass the
  repaired integrity predicates at their observed 0775/0664 modes.
- Ruff lint/format, documentation validation for 919 Markdown files, metadata,
  policy availability, and `git diff --check` pass for the checkpoint.

## Follow-ups

Rebuild and install the exact ledger candidate, settle the single expected
post-refresh Codex trust grant, rerun all four ordinary host proofs and Store
correlations, then run the named repository gates under AR-297.
