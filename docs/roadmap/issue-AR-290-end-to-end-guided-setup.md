---
title: "AR-290: Add end-to-end guided setup"
status: done
category: roadmap
created: 2026-08-25
updated: 2026-08-26
tags: [onboarding, install, configuration, dashboard, documentation]
related:
  - README.md
  - docs/roadmap/handoffs/issue-AR-290.md
  - docs/roadmap/issue-AR-05-guided-provider-configuration.md
  - docs/roadmap/issue-AR-112-public-user-readme.md
  - docs/roadmap/issue-AR-291-isolate-smoke-runtime-pointers.md
  - docs/roadmap/issue-AR-292-classify-setup-activation-pending.md
  - docs/roadmap/issue-AR-295-audit-guided-dashboard-asset-budget.md
  - docs/roadmap/issue-AR-296-project-effective-inference-topology.md
  - docs/decisions/0172-compose-first-run-setup-from-guarded-owner-operations.md
  - docs/RELEASE_CHECKLIST.md
  - docs/worklog/README.md
supersedes: []
superseded_by: null
type: issue
epic: install
issue_id: AR-290
priority: p1
tracker_url: https://github.com/Holeshot-Software-LLC/agency-runtime/issues/328
depends_on: [AR-05, AR-291, AR-292]
blocks: [AR-295, AR-296]
---

# AR-290: Add end-to-end guided setup

## Problem

Agency Runtime has safe, tested commands for provider configuration, config
validation, native harness installation, dashboard service installation,
diagnostics, and smoke checks. A consumer must nevertheless discover their
order and translate several separate surfaces into one first-run journey.
`agency configure` is described as guided setup even though it stops after the
provider chain and starter roster; it does not ask which harnesses to wire,
whether to install the dashboard, or whether to run verification.

The dashboard exposes the same configuration writer and provider builder, but
does not present a first-run checklist. The public README contains detailed
architecture and operating commands without one canonical setup path or a safe
prompt a consumer can paste to an installation agent.

## Current state

- `agency setup` now composes the existing guarded provider wizard, config
  validation, bounded harness/dashboard selection, doctor, and optional
  deterministic smoke stages. Existing config is retained by default and every
  stage reports independently.
- The dashboard Settings view now exposes the same four-stage journey with
  current configuration/registration posture, provider-editor navigation, and
  inert attended command copies. It gains no host-install or shell endpoint.
- AR-296 adds the missing redacted effective-profile topology, including
  per-stage/per-harness model and thinking routes, Jina recall roles, and the
  explicit Agency-staffing/native-host-spawn authority boundary.
- The consumer README now leads with the guided journey, a setup diagram,
  current-state and provider matrices, Jina/local/LiteLLM/API/subscription
  coverage, a paste-ready installation-agent interview, and explicit release
  limits.
- `agency configure` safely interviews for security posture, inference
  providers, fallback order, authentication indirection, detected adapters,
  and tuning.
- `agency install` safely auto-detects all five supported harnesses, can scope
  to one harness, and selects the optional user dashboard service by default.
- `agency config validate`, `agency doctor`, and `agency smoke --all` provide
  distinct configuration, diagnostic, and deterministic smoke evidence.
- The dashboard supports authenticated configuration and provider editing, but
  host lifecycle mutation intentionally remains an attended CLI operation.
- The repository is prerelease. AR-119 exact-candidate host evidence, current
  artifact matrices, benchmark outcomes, tracker parity, and publication
  authorization remain release blockers; additional local smoke alone cannot
  close them.
- Tracker issue [#328](https://github.com/Holeshot-Software-LLC/agency-runtime/issues/328)
  is linked and closed to match this completed record.

## Approach

Add `agency setup` as a thin owner-interactive orchestrator over the existing
guarded command implementations. It must preserve the provider wizard and
atomic writer, validate the resulting or retained config, ask for all detected
or one explicit harness, ask whether to install the dashboard, run diagnostics,
and offer deterministic smoke verification. Existing config is retained by
default; replacement and every optional mutation remain explicit.

Expose an ordered setup journey in the dashboard Settings view. It may report
configuration and host posture, navigate to the existing provider editor, and
copy attended CLI commands. It must not introduce a dashboard host-install
mutation endpoint or bypass native harness trust.

Rewrite the public entry path in `README.md` around a consumer journey. Include
plain-language product and support summaries, Mermaid architecture/setup
diagrams, current prerelease limits, and a paste-ready agent prompt that asks
the user for provider/model, fallback, harness, dashboard, recall, secret, and
verification decisions before running `agency setup` and the documented
advanced configuration surfaces.

## Dependencies

- AR-05 owns the interactive provider-chain wizard and secret-safe validation.
- Existing installer, dashboard service, doctor, and smoke commands remain the
  authorities for their stages; setup does not duplicate their mutations.
- ADR-0031 keeps the dashboard optional and user-scoped.
- Tracker writes, pushes, pull requests, hosted workflows, tags, and releases
  retain separate authority; tracker #328 and PR #326 received it.

## Acceptance

- [x] `agency setup` interviews for retained versus replaced configuration,
      inference provider setup, harness scope, dashboard installation, and
      smoke verification, then prints a stage-by-stage result.
- [x] Non-interactive setup has explicit bounded flags and never places secret
      values on command lines, in JSON, or in durable evidence.
- [x] Existing `agency configure`, install, validation, doctor, smoke, native
      trust, and dashboard-service contracts remain authoritative and
      independently callable.
- [x] The dashboard shows one ordered setup walkthrough with truthful current
      posture and copy-only attended commands; it gains no host mutation API.
- [x] The consumer README contains a clear quick start, capability/support
      tables, architecture and setup diagrams, current prerelease limits, and a
      paste-ready agent setup prompt.
- [x] Focused CLI/parser/dashboard tests, the named fast spine, dashboard UI,
      documentation, Ruff, routing, decision conformance, and diff gates pass.
- [x] Release readiness is reported against the canonical checklist without
      treating local smoke as current artifact, host, tracker, or publication
      proof.
- [x] Tracker issue #328 is linked and closed to match canonical done status.

## Verification evidence

The current worktree has passed 255 focused configuration/setup/parser/install/
dashboard-service tests, the named fast Python production spine plus setup
coverage (849 passed, 20 skipped, warnings strict), all 136 dashboard UI tests,
both full Ruff gates, all four documentation gates, every deterministic routing
evaluation threshold, and the eight-check network-free five-host source smoke.
Decision conformance passed its green baseline, killed all 160 curated
mutations with zero survived or invalid results, and proved its selected source
inputs unchanged. All 161 workflow contracts pass after AR-295 retained a
narrow audited byte ceiling above the required setup UI. Final metadata,
documentation, and diff checks are repeated at the clean checkpoint.

Read-only GitHub checks on 2026-08-25 found no release, tag, AR-290 tracker
issue, or AR-289/AR-290 pull request. Those absences are current remote state,
not authorization to create any of them.

Installed dogfood then exposed AR-291: deterministic source smoke had published
alternate-home Hermes/OpenClaw runtime pointers into the operator launcher
directory. The repaired install, identity-bounded cleanup, 8/8 installed smoke,
and repeated drift-free setup now complete that dependency.

The repaired repeat removed residual drift and kept every real host mutation
successful, then exposed AR-292: standalone install correctly withholds
completion until Codex activation is proven, but setup collapsed that attended
activation state into a hard stage failure. Guided setup must preserve strict
standalone install semantics while reporting this exact resumable case as
degraded.

The exact merged `aa2830d0` checkpoint was installed and its configuration,
provider, setup, and dashboard modules hash-matched source. A full all-harness
refresh retained the config, registered Codex, Claude, and ZCode, and cleared
the stale launcher projection; authoritative status now reports no runtime
drift. Deterministic installed smoke passes all 8 checks.

Final validation returns degraded 2 only for attended Codex trust and cold
Claude/ZCode loading uncertainty. Status includes the exact Codex trust and
verification walkthrough. Doctor confirms schema 48, 299 active agents, and
usable Codex and Claude subscription providers. Dashboard status returns 0
with installed, owned, enabled, active, current-manifest, and reachable all
true. `workforce.dense_recall_mode` is `additive`; bounded live calls applied
`jina-embeddings-v3` at 1,024 dimensions and `jina-reranker-v3.5` over two
documents without persisting or displaying the credential.

The separate AR-297 Linux candidate installs the exact wheel and native
Hermes, OpenClaw, Codex, and Claude bundles on the current host without using
Jina. Codex remains truthfully activation-required. The dashboard service
transaction rolls back because its normal non-root systemd namespace remaps
trusted root ancestors to UID 65534 under `PrivateTmp=true`; AR-301 owns that
new defect. This later scoped evidence does not revise AR-290's completed setup
feature or relabel its earlier Windows/Jina evidence as current Linux proof.
