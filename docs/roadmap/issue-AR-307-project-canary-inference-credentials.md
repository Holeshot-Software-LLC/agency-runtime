---
title: "AR-307: Project exact canary inference credentials"
status: in_progress
category: roadmap
created: 2026-08-26
updated: 2026-08-26
tags: [canary, credentials, configuration, containers, security]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-300-bind-explicit-install-config-to-managed-canary.md
  - docs/roadmap/handoffs/issue-AR-297.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - docs/decisions/0178-project-config-declared-credentials-into-tool-reduced-canaries.md
  - agency_runtime/core/canary.py
  - agency_runtime/core/canary_backends.py
  - agency_runtime/core/canary_proof.py
  - agency_runtime/core/configuration_contracts.py
  - tests/test_canary_coverage_complete.py
  - tests/test_codex_activation_verification.py
  - tests/test_cli_judge_providers.py
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-307
priority: p0
tracker_url: null
depends_on: [AR-300]
blocks: [AR-297]
---

# AR-307: Project exact canary inference credentials

## Problem

The clean AR-297 Codex production transaction bound the exact configuration and
Store to its managed-policy canary, but additive embedding failed before
routing. A secret-safe, no-model probe proved that the install process had the
config-declared `LITELLM_API_KEY` while `safe_cli_environment` correctly
removed it from the Codex child. The managed relay then loaded the exact
configuration but could not resolve the process-only credential it named.

Adding the credential to the global CLI allowlist would expose it to unrelated
CLI judgments. Persisting the value in Codex policy, the Agency config, an
artifact, or evidence would violate the write-only credential contract.

## Current state

- The exact mode-0600 config declares one unique credential environment name,
  contains no direct provider key, and still hashes to
  `87551b5bc936a41742d6846523377e3cf869d8e5c2ce2e4941c447848e125628`.
- A no-model probe inside fresh container `agency-ar297-codex` recorded
  `source_has_declared_credential=true` and
  `safe_cli_has_declared_credential=false`; it printed no credential value.
- Codex canaries already disable shell, unified exec, web search, apps, and MCP,
  and expose only the native collaboration boundary. Claude canaries expose
  only its native Agent boundary.
- The candidate derives a names-only set from the exact validated config and
  projects only matching present values after the general CLI environment has
  been reduced. The general reduction remains unchanged.
- Tracker creation is prohibited by the active AR-297 task.

## Approach

Collect bounded credential-shaped ASCII environment-variable names from the exact configuration's
judge, provider chain, inference profiles, and native adapter references. Pass
that names-only tuple through live-canary preparation into the safe backend.
After building the ordinary minimal environment, copy only matching present
values from the invoking process for the duration of the tool-reduced canary.

Reject malformed, duplicate, excessive, control-variable-colliding, non-text,
NUL-bearing, or oversized inputs before process creation. Never render values in argv, configuration,
policy, reports, logs, evidence, or durable service definitions. Keep ordinary
later harness processes responsible for receiving the same process-local
credential from their container or service manager environment.

## Dependencies

- AR-300 binds the exact config and Store identity to the managed canary.
- ADR-0173 requires a normal no-bypass Codex canary before production-container
  installation can complete.
- ADR-0178 owns the bounded process-only credential projection.
- Tracker creation requires separate outward-write authorization.

## Acceptance

- [x] Names-only discovery includes inference-profile credential references and
      never reads their values.
- [x] The general CLI environment continues to strip LiteLLM and unrelated
      credentials.
- [x] A canary projects only explicitly declared, present credential values.
- [x] Invalid, process-control, colliding, or duplicate names and invalid values
      fail before the native process starts.
- [x] Focused canary, activation, CLI-environment, dashboard-helper, Ruff, and
      formatting checks pass.
- [ ] A rebuilt clean Codex production-container transaction completes its
      no-bypass canary and persists the exact current attestation.
- [ ] A same-repository tracker issue is created and linked after explicit
      authorization.
