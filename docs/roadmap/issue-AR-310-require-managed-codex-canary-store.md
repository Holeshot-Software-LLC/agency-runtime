---
title: "AR-310: Require the exact Store for managed Codex canaries"
status: in_progress
category: roadmap
created: 2026-08-26
updated: 2026-08-26
tags: [codex, canary, installer, store, production-container]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-309-restore-codex-0149-activation-proof.md
  - docs/roadmap/issue-AR-311-inject-exact-codex-canary-native-plan.md
  - docs/roadmap/issue-AR-322-bind-codex-child-session-to-canary-parent.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0179-admit-exact-codex-canary-delivery-at-subagent-start.md
  - agency_runtime/cli/install_commands.py
  - agency_runtime/core/canary_proof.py
  - agency_runtime/core/canary_backends.py
  - tests/test_cli_coverage_complete_install.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-310
priority: p0
tracker_url: null
depends_on: [AR-309]
blocks: [AR-297, AR-311, AR-322]
---

# AR-310: Require the exact Store for managed Codex canaries

## Problem

The rebuilt AR-309 production-container install supplies the exact config and
database paths to the managed Codex canary, but does not set the canary's
`require_existing_store` boundary. The sealed host-delivery collector correctly
refuses that non-restricted backend before any Codex process or model call.
Production installation therefore cannot reach the exact canary it is required
to prove even though it has just materialized the Store.

## Current state

- Fresh image `9afefdb2...39442` and container `570506ea...39b9` bind ledger
  `fd163da2`, wheel `2d78f9c...16ab5`, Codex `0.149.1`, and exact config
  `87551b5b...25628`. The clean absence receipt passes at
  `eee05217...68a0`.
- The first rebuilt install exits 1 with empty stderr. Its private JSON hashes
  to `64b021ce...1b54`; it records managed-only policy, no bypass, no rollout,
  no Store run, and `safe host invocation failed before evidence could be
  evaluated`.
- A second bounded no-bypass diagnostic reproduces the same zero-run failure.
  JSON hashes to `d55536f7...2845`; private debug log `a2821a18...ba65`
  identifies only the fixed collector refusal at
  `SafeCodexCanaryBackend.execute_with_host_delivery`.
- The production installer passes `config_path` and `db_path`, while the
  verification-only and direct current-profile paths already pass
  `require_existing_store=True`.
- Rebuilt candidate `c60678ef` proves the repair reaches native Codex: the
  exact route, fixed delegate unit, and `code-reviewer` load persist under
  session `01a03fe6-c434-7432-a7ef-8d5535109e8c`. The later invalid native
  task label is isolated to AR-311.
- Tracker creation is prohibited by the active AR-297 task.

## Approach

Add `require_existing_store=True` only to the managed-policy canary arguments
after the installer has validated both exact paths. Keep attended and explicit
bypass shapes unchanged. Bind the existing production-container test to the
full call contract, then rebuild and repeat the fresh exact no-bypass proof.

## Dependencies

- ADR-0173 requires a normal managed-policy invocation and persisted
  attestation before production-container installation can complete.
- ADR-0179 permits exact Codex canary staffing only when the existing-Store
  environment marker is present.
- AR-309 supplies the sealed child-delivery collector this path must reach.
- Tracker creation requires separate outward-write authorization.

## Acceptance

- [x] A fresh exact container reproduces the pre-invocation refusal with exact
      exit, artifact hashes, managed trust mode, and zero Store/run counts.
- [x] The managed-policy installer passes the exact existing-Store requirement
      without changing attended, bypass, config, or credential boundaries.
- [x] Focused warning-strict installer and Codex canary tests pass (268 tests).
- [x] A rebuilt fresh no-bypass transaction reaches native Codex execution and
      reports AR-311's later missing-plan blocker with exact retained evidence.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.
