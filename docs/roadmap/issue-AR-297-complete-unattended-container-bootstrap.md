---
title: "AR-297: Complete unattended container bootstrap"
status: in_progress
category: roadmap
created: 2026-08-25
updated: 2026-08-25
tags: [installation, containers, codex, hooks, automation, configuration]
related:
  - README.md
  - CHANGELOG.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/roadmap/issue-AR-290-end-to-end-guided-setup.md
  - docs/roadmap/handoffs/issue-AR-290.md
  - docs/decisions/0173-complete-production-container-installation-with-managed-activation.md
  - agency_runtime/cli/install_commands.py
  - agency_runtime/core/codex_managed_policy.py
  - agency_runtime/core/canary.py
  - tests/test_codex_managed_policy.py
  - tests/test_cli_coverage_complete_install.py
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: host-integrations
issue_id: AR-297
priority: p0
tracker_url: null
depends_on: []
blocks: []
---

# AR-297: Complete unattended container bootstrap

## Problem

Production will dynamically create an OpenClaw, Claude Code, or Codex
container, install Agency Runtime, and let Conveyor invoke work. No person is
available after provisioning to settle hook trust or finish configuration.
The existing Codex `--autonomous --verify-activation` path uses a trust bypass
for one canary invocation only. It can prove that invocation, but it cannot
make the later ordinary Codex process started by Conveyor load Agency hooks.
Installation also lacks a first-class exact config argument, so image builders
must rely on ambient shell state.

## Current state

- Package acquisition and the Agency runtime-install transaction are separate;
  after the package exists, `agency install` owns roster, host, dashboard, and
  activation state.
- Attended Codex installation correctly leaves persistent trust to Codex, but
  that is not an unattended-container solution.
- The invocation-scoped autonomous bypass is useful diagnostic evidence and
  remains explicitly nonpersistent.
- Claude Code, OpenClaw, ZCode, and Hermes already use their native
  registration/enablement lifecycles without Agency inventing a trust store.
- Tracker creation remains pending explicit tracker authorization.

## Approach

Add `agency install --production-container --config <path>` as an explicit
dedicated-container transaction. Bind that exact validated config through the
Store, host payloads, and optional dashboard service. Require at least one
selected or detected host and fail before installation when the config or host
scope is missing.

For Codex, install the normal Agency plugin for skills and MCP, then install a
system `requirements.toml` that enables managed hooks, restricts hook loading
to managed sources, and references one Agency-owned absolute relay under the
managed directory. The relay binds the published private interpreter/runtime,
exact config, runtime control, and canonical eight events. Refuse any existing
system requirements or relay file that does not carry a valid Agency ownership
and payload digest; never merge or overwrite foreign enterprise policy.

After policy installation, run the existing current-profile Agency canary in
`managed_policy` mode through a normal Codex invocation with no hook-trust
bypass. Completion requires live hook/route/card/child/finalization proof and a
persisted current-profile attestation. A failed policy step or canary exits
nonzero while retaining bounded recovery evidence. Other selected hosts must
reach native registration completeness in production-container mode.

## Dependencies

- ADR-0173 owns the dedicated-container/system-policy boundary.
- ADR-0118 retains inference-only staffing authority; this installation change
  does not let Agency dispatch children.
- ADR-0156 retains host-written card-delivery proof.
- A live Codex canary still requires a working authenticated Codex provider and
  the configured Agency inference routes.

## Acceptance

- [x] `agency install` accepts and binds one explicit config path.
- [x] Production-container mode requires an explicit config and nonempty host
      scope and is incompatible with rollback and verification-only modes.
- [x] Codex system policy pins hooks on, loads only managed hooks, and installs
      all eight Agency events through an absolute managed relay.
- [x] Existing foreign requirements or relay files are refused without being
      overwritten.
- [x] The production Codex canary uses `trust_mode=managed_policy`, does not use
      `--dangerously-bypass-hook-trust`, and requires persistent attestation.
- [x] Prior Codex activation proof is invalidated before system-policy mutation;
      doctor, status, and dashboard inspection distinguish managed, attended,
      absent, drifted, and foreign-or-modified policy state.
- [x] Focused source tests cover policy generation, idempotence, refusal,
      parser closure, and fail-closed activation.
- [ ] A clean Linux Codex container proves the exact transaction, then a later
      ordinary Conveyor-equivalent Codex invocation loads Agency unattended.
- [ ] Clean Linux Claude Code and OpenClaw containers prove native registration,
      loading, and a bounded Agency turn without human input.
- [ ] Release-artifact and remaining release-checklist gates pass on the exact
      merge candidate.
- [ ] Tracker creation and linkage receive separate authorization.

## Verification evidence

Current source coverage parses the generated managed requirements as TOML,
checks all canonical hook events and immutable relay bindings, proves an
idempotent second install, and refuses both foreign system policy and a foreign
relay before preparing runtime artifacts. Read-only inspection parses the
owned TOML and relay without executing them, invalidates current proof on
policy drift, and projects managed authority through the CLI and dashboard.
Focused installer and canary tests prove the managed mode uses the normal
current-profile Codex argv, skips the non-managed plugin trust probe, records
no trust bypass, and fails before a canary when managed policy is refused.

The exact guided dashboard is 386,366 bytes. The audited 378 KiB ceiling leaves
706 bytes (0.18 percent) of headroom after the managed-policy and complete-prompt
projections; the release packaging gate passes at that bound.

The required Linux container and post-install Conveyor-equivalent evidence are
intentionally still open. Windows source tests cannot establish Linux `/etc`
permissions, real Codex managed-policy loading, Claude/OpenClaw process state,
or release artifact portability.
