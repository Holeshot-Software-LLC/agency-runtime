---
title: "Worklog detail: fix(activation): bind autonomous proof to inferred replay"
status: active
category: worklog
created: 2026-07-30
updated: 2026-07-30
tags: [activation, codex, autonomous, inference, replay, evidence]
related:
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0119-separate-native-trust-modes-from-activation-proof.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: worklog
commit: 03dba7538779f9c1bc64a9f6e06e5dbe9581db42
short: 03dba75
date: 2026-07-30
pr: null
related_issues:
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
---

# Worklog detail: fix(activation): bind autonomous proof to inferred replay

## Purpose

Make unattended Codex installation and activation executable without writing
private host trust state or relabeling a bypass as trust, while preserving the
README requirement that inference owns every specialist decision.

## Approach

`agency install --autonomous --verify-activation --json` now follows the normal
auto-discovered full-suite install path and uses Codex's supported hook-trust
bypass only for the exact activation invocation. Backend and CLI evidence bind
the requested mode to the actual argument vector and distinguish requested,
attempted, passed, and persistent-profile states.

The Codex activation canary now runs normal workforce inference and requires a
nonempty provider-attempt receipt before any worker can be selected. The closed
canary adapter may validate and narrow only that already selected worker to the
fixed read-only diagnostic goal needed to recover Codex's encrypted child
message. It cannot hire, add, substitute, rank, or reorder a worker. The bounded
inferred unit binding persists through exact modern-plan replay without storing
the prompt body or generic workforce descriptors.

Product-host proof now correlates the exact Codex parent/child rollout, records
the invocation-only bypass as `bypassed`, and requires the exact workspace-
write sentinel before grading.

## Challenges encountered

Focused happy-path tests initially hid three evidence defects. Review found
that a requested bypass could be reported as used before invocation, the exact
read-only canary still entered generic gap hiring, and a diagnostic error patch
accidentally nested modern plan equality under the legacy branch. Restoring the
branch then exposed a missing Store projection for the bounded activation unit
binding. Each boundary received a direct regression and a curated mutation.

Two older helper tests also expected delegation from bare deterministic
`selected_ids`; they now use verifier-approved unit bindings under the current
inference-only contract.

## Decisions and alternatives

ADR-0118 keeps staffing inference-owned. ADR-0119 permits only an explicit,
invocation-scoped autonomous bypass and forbids any claim that bypassed hooks
were trusted. Editing undocumented Codex trust hashes, silently bypassing in
attended mode, restoring a deterministic canary specialist, or letting the
diagnostic hire a worker were rejected.

## Verification

- Expanded activation, product-host, complete-install, prepared-install,
  canary, durable-preflight, and conformance-test spine: 287 passed and 1
  intentional platform skip under warning-strict pytest.
- Last complete decision-conformance run: baseline passed; 29 of 29 curated
  mutations killed; zero survivors, zero invalid mutations, and source restore
  passed. Four review-added mutations passed manifest tests and await the
  immediately following complete 33-mutation run.
- Ruff check, Ruff format, metadata, policy, documentation, and diff-integrity
  checks passed before the checkpoint, except the expected temporary worklog
  currentness failure resolved by this ledger commit.
- Immediately preceding telemetry reported 33.1 percent context remaining and
  required this clean checkpoint before further evaluation.

## Follow-ups

Run all 33 decision-conformance mutations, then continue AR-204 with terminal
zero-correction header enforcement before the dashboard and exact-build live
product trial.
