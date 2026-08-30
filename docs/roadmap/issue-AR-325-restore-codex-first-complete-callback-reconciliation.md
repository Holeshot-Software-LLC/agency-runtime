---
title: "AR-325: Restore Codex first-complete-callback reconciliation"
status: in_progress
category: roadmap
created: 2026-08-27
updated: 2026-08-27
tags: [bug, codex, canary, hooks, native-child, evidence, security]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-309-restore-codex-0149-activation-proof.md
  - docs/roadmap/issue-AR-324-bind-codex-canary-child-through-host-lineage.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/roadmap/issue-AR-326-admit-terminal-codex-host-artifact-collection.md
  - docs/decisions/0144-claim-codex-spawn-execution-at-the-first-complete-callback.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - docs/decisions/0188-separate-codex-hook-parent-and-child-identities.md
  - agency_runtime/adapters/hooks.py
  - agency_runtime/core/evals/decision_conformance.py
  - agency_runtime/core/store/native_child.py
  - tests/test_canary_activation_snapshot.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-325
priority: p0
tracker_url: null
depends_on: [AR-321, AR-324]
blocks: [AR-297, AR-326]
---

# AR-325: Restore Codex first-complete-callback reconciliation

## Problem

The exact AR-297 Codex production-container run proves a real Qwen-selected
`code-reviewer` child, complete prompt delivery, exit-0 execution, and a
host-artifact delivery receipt, but finalization still rejects the turn. Codex
delivered the parent `PostToolUse` callback before restricted `SubagentStart`.
The early callback persisted a synthetic delegation against the opaque parent
message, while the later real worker remained unbound to that delegation.

The same pre-spawn callback also retained an honest
`native_child_inference_failure` diagnostic for the encrypted channel. Once the
restricted child route succeeded, that extra routing row made ready-receipt
integrity fail before the header could be reconciled.

## Current state

- Exact install receipt `c56eb749...c44` exits 1 after parent
  `01a04311...10a4`, child `01a04313...1872`, one successful native-child
  route, one verified delivery, and one exit-0 real worker.
- Parent and child rollouts hash to `fb580c43...a383` and
  `c60cc6a6...d079`; Store `3e41479f...48a6` retains the complete evidence.
- Revision 20 reproduces the live policy result exactly as
  `missing=["evidence_verification"]`. Removing only the diagnostic in a
  temporary Store copy exposes the second exact mismatch:
  `Agency/Agencies delegated: none - executed worker has no validated Agency specialist`.
- The real worker has fixed unit `unit-05d45f7553` but no
  `delegation_event_id` or dispatch receipt. The sole delegation has the
  synthetic `task:code_reviewer` identity and a different opaque-message unit.
- Two regression tests fail before implementation: the restricted opaque
  pre-tool path retains a failure route, and post-tool-first ordering retains
  no fixed-unit pending dispatch to promote.
- The repair now recognizes the existing exact Codex ciphertext shape plus the
  fixed `code_reviewer` input and identity-free `/root/code_reviewer` response.
  It suppresses the ordinary failure row only inside the proven managed canary
  parent. A wrong native task in that same parent still persists
  `native_child_inference_failure`.
- Post-tool-first now records synthetic `task:code_reviewer` only as an exact
  fixed-unit pending dispatch. The validated SubagentStart atomically rekeys it
  to the real UUID, or merges it into an already-observed unbound real worker.
  A real worker with a conflicting dispatch fails closed with both receipts
  unchanged. Subagent-start-first can attach and claim the matching dispatch
  even after the child terminal callback arrived.
- Five targeted warning-strict cases pass across pending rekey, overlapping
  real-worker merge, conflicting-real rejection, the opposite callback order,
  replay, ordinary opaque diagnostics, header projection, and ready-routing
  integrity. The affected six-file suite passes 149/149; the
  decision-conformance unit suite passes 17/17. Two new curated mutations each
  fail their named regression and are killed with source unchanged. Retained
  stdout SHA-256 values are `394d9276...1c4d` (149 tests),
  `74a9f4f9...4141` (17 tests), and `ea4477e5...3695` (two mutations); each
  command exits 0, each 12-byte exit receipt hashes to `bde29436...0120`, and
  all three empty stderr files hash to `e3b0c442...b855`. An additional 145
  security-boundary, Store-atomicity, audit, canary-coverage, and delegation
  tests pass at stdout `ae7689e3...7a84`, exit 0, and empty stderr.
- Metadata, policy availability, worklog generation, and validation of 893
  Markdown files pass at stdout `c5d005ae...18ac`; repository-wide Ruff and
  format checks pass at `94423e2d...0564`. `git diff --check` is empty. All
  three commands exit 0 with empty stderr.
- Tracker creation is prohibited by the active AR-297 task.
- Fresh exact `19e0210b` live evidence proves this repair: finalization
  `d5b3d58f...928c` accepts with `missing=[]`, the exact real child and dispatch
  agree, and the header is valid. AR-326 owns the later independent attestation
  failure caused by post-return collection consulting a live-only parent lookup.

## Approach

Keep ordinary encrypted Codex spawns unstaffed and diagnostic. Inside only the
existing managed current-profile canary boundary, recognize the exact fixed
parent route plus exact `code_reviewer` spawn shape. Do not write the ordinary
opaque-channel failure row for that restricted spawn because ADR-0179 assigns
staffing authority to its later host-authored `SubagentStart` lineage.

When `PostToolUse` arrives first, retain its exact tool-use ID as a fixed-unit
synthetic pending worker and dispatch. When the validated restricted
`SubagentStart` later supplies the real child UUID and successful inference
route, atomically promote that sole pending worker and delegation to the real
child while preserving the dispatch receipt. When `SubagentStart` arrives
first, retain the existing direct reconciliation path. Reject ambiguity,
foreign units, terminal parents, wrong synthetic identities, conflicting real
workers, and ordinary processes.

## Dependencies

- ADR-0144 already requires claiming at the first callback where the spawn
  delegation and real child identity can be joined; this item restores that
  invariant after one-use activation-grant writers were retired.
- ADR-0179 and ADR-0188 continue to own the restricted canary authority and
  host-authored parent/child lineage. This repair grants no ordinary encrypted
  Codex spawn new staffing authority.
- AR-321 and AR-324 supply the exact successful judge route and real child
  identity that exposed this later reconciliation defect.

## Acceptance

- [x] Restricted opaque `PreToolUse` preserves only the canonical parent route;
      ordinary opaque spawns still retain their failure diagnostic.
- [x] Post-tool-first ordering persists one exact fixed-unit pending dispatch
      and promotes it atomically to the real child at `SubagentStart`.
- [x] Subagent-start-first ordering and callback replay remain idempotent.
- [x] Completion evidence projects the verified `code-reviewer` delegation and
      the exact ready-routing receipt remains valid.
- [x] Focused warning-strict hook, Store, header, and decision-conformance tests
      pass.
- [ ] A rebuilt fresh no-bypass Codex install proves accepted finalization,
      exact Store correlation, and current-profile attestation.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.
