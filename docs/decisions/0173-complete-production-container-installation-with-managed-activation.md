---
title: "Complete production-container installation with managed activation"
status: accepted
category: decisions
created: 2026-08-25
updated: 2026-08-26
tags: [installation, containers, codex, hooks, trust, automation]
related:
  - docs/roadmap/issue-AR-297-complete-unattended-container-bootstrap.md
  - docs/roadmap/issue-AR-300-bind-explicit-install-config-to-managed-canary.md
  - docs/roadmap/issue-AR-307-project-canary-inference-credentials.md
  - docs/roadmap/issue-AR-308-bind-activation-canary-delegation.md
  - docs/roadmap/issue-AR-309-restore-codex-0149-activation-proof.md
  - docs/roadmap/issue-AR-310-require-managed-codex-canary-store.md
  - docs/roadmap/issue-AR-311-inject-exact-codex-canary-native-plan.md
  - docs/roadmap/issue-AR-312-validate-explicit-production-config.md
  - docs/roadmap/issue-AR-314-bind-codex-default-canary-role.md
  - docs/roadmap/issue-AR-315-project-codex-canary-install-home.md
  - docs/roadmap/issue-AR-204-reconcile-readme-story-contract.md
  - docs/decisions/0036-capability-bound-host-canary-attestations.md
  - docs/decisions/0118-require-inference-owned-staffing.md
  - docs/decisions/0156-host-artifacts-prove-native-child-delivery.md
  - docs/decisions/0180-project-current-profile-canary-install-home.md
  - README.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes:
  - docs/decisions/0119-separate-native-trust-modes-from-activation-proof.md
superseded_by: null
id: ADR-0173
type: decision
deciders: [maintainers]
---

# ADR-0173: Complete production-container installation with managed activation

## Context

Agency Runtime's production consumer creates a fresh Codex, Claude Code, or
OpenClaw container, installs Agency, and then lets Conveyor invoke the harness.
There is no operator available between installation and work. The defining
product invariant is therefore stronger than an interactive setup wizard:
after one explicit Agency runtime-install transaction, the environment must
already carry the dynamic staffing, hiring, host-integration, and evidence
control plane needed by later ordinary harness invocations.

ADR-0119 separated attended trust from an autonomous Codex trust bypass and
required behavioral activation proof for both. The bypass is deliberately
invocation-scoped. It can prove one canary, but it does not persist trust and
cannot make a later Codex process started by Conveyor execute Agency's plugin
hooks. Describing that mode as a fresh-container installation solution was
therefore too broad.

Codex now supports administrator-managed hooks in system
`requirements.toml`. Those hooks are policy-trusted, can be pinned on, and can
exclude unmanaged user, project, session, and plugin hook sources. This is the
documented persistent authority suitable for a dedicated container, but it
would be intrusive on an ordinary shared developer profile.

## Decision

Retain attended and invocation-scoped bypass modes, but add a third explicit
`managed_policy` trust mode owned by
`agency install --production-container --config <path>`.

Production-container mode is only for an owner-controlled dedicated or
disposable environment. It requires an exact validated config and at least one
selected or detected harness. The transaction binds that config through
Agency's Store, every installed native payload, and the optional dashboard
service. Conveyor invokes work only after the transaction exits successfully;
it does not finish setup, settle trust, or repair configuration.

For Codex, the transaction installs the ordinary Agency plugin for its skill,
MCP, native-registration, and installation-identity surfaces. It then owns one
system `requirements.toml` and one absolute managed relay. The requirements
pin hooks on, set managed-only hook loading, and define every canonical Agency
event inline. The relay executes Agency's published private runtime with the
exact config and runtime-control bindings. Agency may update only a
digest-valid prior Agency document. A foreign or malformed requirements file
or relay is a hard refusal; Agency does not merge, reinterpret, or overwrite
enterprise policy.

Before any managed-policy mutation, the exact configured Store clears prior
Codex activation proof. A successful fresh canary repopulates it; a policy or
canary failure therefore cannot leave an older attestation looking current.
Read-only host inspection parses and validates the owned TOML and relay without
executing them, and projects policy authority separately from activation proof
through doctor, status, and dashboard surfaces.

Installation is incomplete until a fresh current-profile Codex Agency canary
runs through a normal invocation without
`--dangerously-bypass-hook-trust`. The canary must prove hook start, routing,
exact card delivery, native child lifecycle, and finalization and persist the
current installation attestation. Managed policy is an activation mechanism,
not evidence by itself. Claude Code, OpenClaw, ZCode, and Hermes retain their
native registration lifecycles and must reach registration completeness when
selected by production-container mode.

Package acquisition remains outside this transaction: an image builder must
first make the Agency package and target harness available. That is ordinary
software distribution, not post-install Agency configuration. Once the
`agency install` transaction begins, no later human or Conveyor setup step is
part of the success path.

## Consequences

Fresh container builders gain one deterministic runtime-install transaction
whose exit code means the later harness process is ready, rather than merely
that one bypassed canary worked. Existing developer machines retain attended
native trust by default and are never silently converted to managed-only hook
policy.

The dedicated container must grant the installer authority to create the
documented system Codex policy path. Its system requirements target must be
absent or already Agency-owned, and the harness must already have working
authentication plus Agency inference configuration. These are explicit image
preconditions. A shared enterprise requirements file requires the image owner
to compose policy outside Agency; automatic merging is intentionally refused.

The optional dashboard and CLI remain observability and owner-control surfaces,
not runtime prerequisites. They must reflect the same config, trust mode,
provider topology, workforce, and evidence, but Conveyor does not depend on
them.

## Alternatives

Keeping the invocation-scoped trust bypass as the production path was rejected
because it does not affect the later harness invocation. Writing Codex's
undocumented user trust store was rejected because it would forge native trust
and drift across versions. Automatically merging arbitrary system requirements
was rejected because Agency cannot safely preserve unknown enterprise
constraints or comments. Installing managed-only hooks on every Codex profile
was rejected because it would suppress unrelated unmanaged hooks on ordinary
developer machines. Letting Conveyor finish setup was rejected because it
would make provisioning success depend on the first production work request.
